#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
from pathlib import Path

from ziwei_research_engine import (
    ResearchConfigError,
    _read_json,
    load_research_resources,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTOCOL_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "blind_review_protocol.json"
)


def load_blind_review_resources(protocol_path=DEFAULT_PROTOCOL_PATH):
    resources = load_research_resources()
    protocol = _read_json(protocol_path)
    if protocol["experiment_version"] != resources["experiment"]["experiment_version"]:
        raise ResearchConfigError("盲评协议引用的实验版本不一致")
    if (
        protocol["dimension_dictionary_version"]
        != resources["dimensions"]["dictionary_version"]
    ):
        raise ResearchConfigError("盲评协议引用的维度词典版本不一致")
    if protocol["status"] != "frozen_before_collection":
        raise ResearchConfigError("盲评协议必须在评分收集前冻结")
    allowed = protocol["rating_scale"]["allowed_values"]
    if allowed != sorted(set(allowed)) or 0.0 not in allowed:
        raise ResearchConfigError("盲评量尺必须有序、唯一且包含 0.0")
    minimum = protocol["rater_plan"]["minimum_raters"]
    target = protocol["rater_plan"]["target_raters"]
    usable = protocol["agreement"]["minimum_usable_raters"]
    if target < minimum or usable < minimum:
        raise ResearchConfigError("盲评评分者数量约束不一致")
    thresholds = protocol["agreement"]["thresholds"]
    if thresholds["strong_agreement"] < thresholds["provisional_acceptance"]:
        raise ResearchConfigError("强一致阈值不能低于暂时接受阈值")
    return resources, protocol


def generate_blind_packet(resources, protocol, seed):
    seed = str(seed)
    fingerprint = "|".join((
        protocol["id"],
        protocol["protocol_version"],
        resources["experiment"]["id"],
        resources["experiment"]["experiment_version"],
        resources["dimensions"]["dictionary_version"],
        seed,
    ))
    packet_id = "blind-" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
    cases = list(resources["experiment"]["cases"])
    random.Random(seed).shuffle(cases)
    answer_key = {}
    blind_cases = []
    dimension_templates = [{
        "dimension_id": dimension["id"],
        "score": None,
        "rationale": "",
    } for dimension in resources["dimensions"]["dimensions"]]
    for case in cases:
        digest = hashlib.sha256(
            f"{packet_id}|{case['id']}".encode("utf-8")
        ).hexdigest()[:10].upper()
        code = f"CASE-{digest}"
        answer_key[code] = case["id"]
        blind_cases.append({
            "case_code": code,
            "source_layer": case["source_layer"],
            "focus": case["focus"],
            "stars": [{
                "name": star["name"],
                "physical_palace": star["physical_palace"],
                "earthly_branch": star["earthly_branch"],
                "relation": star["relation"],
                "brightness": star["brightness"],
                "transformation": star["transformation"],
                "fact_status": star["fact_status"],
            } for star in case["stars"]],
            "transformation_signals": case["transformation_signals"],
            "ratings": [dict(item) for item in dimension_templates],
        })
    packet = {
        "packet_id": packet_id,
        "protocol": {
            "id": protocol["id"],
            "version": protocol["protocol_version"],
        },
        "experiment_version": resources["experiment"]["experiment_version"],
        "dimension_dictionary_version": resources["dimensions"]["dictionary_version"],
        "fixture_boundary": resources["experiment"]["fixture_policy"],
        "rating_scale": protocol["rating_scale"],
        "instructions": {
            "independence_rule": protocol["rater_plan"]["independence_rule"],
            "missing_vs_neutral": (
                "无法判断填写 null；0.0 是有效的中性或方向并存判断。"
            ),
        },
        "dimensions": [{
            "id": dimension["id"],
            "name": dimension["name"],
            "definition": dimension["definition"],
            "positive_direction": dimension["positive_direction"],
            "negative_direction": dimension["negative_direction"],
            "includes": dimension["includes"],
            "excludes": dimension["excludes"],
        } for dimension in resources["dimensions"]["dimensions"]],
        "cases": blind_cases,
        "submission_template": {
            "packet_id": packet_id,
            "rater_id": "REPLACE_WITH_ANONYMOUS_ID",
            "rater_group": "REPLACE_WITH_SCHOOL_OR_COHORT",
            "ratings": [{
                "case_code": case["case_code"],
                "dimensions": [dict(item) for item in dimension_templates],
            } for case in blind_cases],
        },
    }
    return packet, answer_key


def analyze_submissions(packet, submissions, protocol):
    packet = packet.get("packet", packet)
    case_codes = {case["case_code"] for case in packet["cases"]}
    dimension_ids = {item["id"] for item in packet["dimensions"]}
    allowed = set(protocol["rating_scale"]["allowed_values"])
    minimum = protocol["agreement"]["minimum_usable_raters"]
    if packet["protocol"] != {
        "id": protocol["id"], "version": protocol["protocol_version"]
    }:
        raise ResearchConfigError("盲评包与协议不一致")
    if len(submissions) < minimum:
        raise ResearchConfigError(f"至少需要 {minimum} 份评分提交")

    rater_ids = [item.get("rater_id") for item in submissions]
    if any(not item or item == "REPLACE_WITH_ANONYMOUS_ID" for item in rater_ids):
        raise ResearchConfigError("评分提交必须使用有效的匿名评分者 ID")
    if len(rater_ids) != len(set(rater_ids)):
        raise ResearchConfigError("评分者 ID 重复")

    normalized = []
    for submission in submissions:
        normalized.append(_validate_submission(
            packet, submission, case_codes, dimension_ids, allowed, protocol
        ))

    dimensions = []
    for dimension in packet["dimensions"]:
        dimension_id = dimension["id"]
        units = []
        usable_raters = set()
        for case_code in sorted(case_codes):
            values = []
            for submission in normalized:
                score = submission[case_code][dimension_id]["score"]
                if score is not None:
                    values.append(score)
                    usable_raters.add(submission["__rater_id__"])
            units.append(values)
        alpha = krippendorff_alpha_interval(units)
        status = _agreement_status(alpha, len(usable_raters), protocol)
        dimensions.append({
            "dimension_id": dimension_id,
            "name": dimension["name"],
            "alpha": None if alpha is None else round(alpha, 6),
            "status": status,
            "usable_raters": len(usable_raters),
            "rated_units": sum(1 for unit in units if len(unit) >= 2),
            "rating_count": sum(len(unit) for unit in units),
        })
    return {
        "packet_id": packet["packet_id"],
        "protocol": packet["protocol"],
        "rater_count": len(submissions),
        "primary_metric": protocol["agreement"]["primary_metric"],
        "dimensions": dimensions,
        "overall_alpha": None,
        "overall_alpha_reason": "协议要求逐维度报告，不计算跨维度平均 alpha。",
        "model_parameter_decision": (
            "只有达到协议阈值的单个维度可以进入候选参数讨论；"
            "本报告本身不生成任何星曜权重。"
        ),
    }


def _validate_submission(packet, submission, case_codes, dimension_ids, allowed, protocol):
    if submission.get("packet_id") != packet["packet_id"]:
        raise ResearchConfigError("评分提交引用了错误的盲评包")
    ratings = submission.get("ratings")
    if not isinstance(ratings, list):
        raise ResearchConfigError("评分提交缺少 ratings 数组")
    submitted_codes = [item.get("case_code") for item in ratings]
    if len(submitted_codes) != len(set(submitted_codes)):
        raise ResearchConfigError("评分提交包含重复案例")
    if set(submitted_codes) != case_codes:
        raise ResearchConfigError("评分提交的案例集合与盲评包不一致")
    normalized = {"__rater_id__": submission["rater_id"]}
    for case_rating in ratings:
        case_code = case_rating["case_code"]
        items = case_rating.get("dimensions")
        if not isinstance(items, list):
            raise ResearchConfigError(f"{case_code} 缺少 dimensions 数组")
        ids = [item.get("dimension_id") for item in items]
        if len(ids) != len(set(ids)) or set(ids) != dimension_ids:
            raise ResearchConfigError(f"{case_code} 维度集合无效")
        normalized[case_code] = {}
        for item in items:
            score = item.get("score")
            rationale = item.get("rationale", "")
            if score is not None and score not in allowed:
                raise ResearchConfigError(
                    f"{case_code}.{item['dimension_id']} 分值不在允许量尺中"
                )
            if (
                score is not None
                and protocol["rating_scale"]["rationale_required"]
                and not str(rationale).strip()
            ):
                raise ResearchConfigError(
                    f"{case_code}.{item['dimension_id']} 有评分但缺少依据"
                )
            normalized[case_code][item["dimension_id"]] = {
                "score": score,
                "rationale": str(rationale),
            }
    return normalized


def krippendorff_alpha_interval(units):
    usable_units = [[float(value) for value in unit] for unit in units if len(unit) >= 2]
    if not usable_units:
        return None
    observed_rating_count = sum(len(unit) for unit in usable_units)
    observed_sum = 0.0
    for unit in usable_units:
        pair_sum = sum(
            (left - right) ** 2
            for left_index, left in enumerate(unit)
            for right_index, right in enumerate(unit)
            if left_index != right_index
        )
        observed_sum += pair_sum / (len(unit) - 1)
    observed_disagreement = observed_sum / observed_rating_count

    pooled = [value for unit in usable_units for value in unit]
    if len(pooled) < 2:
        return None
    expected_sum = sum(
        (left - right) ** 2
        for left_index, left in enumerate(pooled)
        for right_index, right in enumerate(pooled)
        if left_index != right_index
    )
    expected_disagreement = expected_sum / (len(pooled) * (len(pooled) - 1))
    if expected_disagreement == 0:
        return None
    return 1.0 - observed_disagreement / expected_disagreement


def _agreement_status(alpha, usable_raters, protocol):
    minimum = protocol["agreement"]["minimum_usable_raters"]
    if usable_raters < minimum or alpha is None:
        return "not_computed"
    thresholds = protocol["agreement"]["thresholds"]
    if alpha >= thresholds["strong_agreement"]:
        return "strong_agreement"
    if alpha >= thresholds["provisional_acceptance"]:
        return "provisional_acceptance"
    return "revision_required"


def _write_json(value, pretty):
    print(json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ))


def main():
    parser = argparse.ArgumentParser(description="生成紫微斗数盲评包并分析评分一致性")
    subparsers = parser.add_subparsers(dest="command", required=True)
    packet_parser = subparsers.add_parser("packet", help="生成随机化盲评包")
    packet_parser.add_argument("--seed", required=True, help="可复现随机种子")
    packet_parser.add_argument("--include-key", action="store_true", help="包含原始案例映射，仅供负责人")
    packet_parser.add_argument("--pretty", action="store_true", help="格式化输出 JSON")

    analyze_parser = subparsers.add_parser("analyze", help="分析多个评分提交")
    analyze_parser.add_argument("--packet", required=True, help="盲评包 JSON 文件")
    analyze_parser.add_argument(
        "--submission", action="append", required=True, help="评分提交 JSON 文件，可重复"
    )
    analyze_parser.add_argument("--pretty", action="store_true", help="格式化输出 JSON")
    args = parser.parse_args()

    resources, protocol = load_blind_review_resources()
    if args.command == "packet":
        packet, answer_key = generate_blind_packet(resources, protocol, args.seed)
        output = {"packet": packet, "answer_key": answer_key} if args.include_key else packet
        _write_json(output, args.pretty)
        return

    packet = _read_json(Path(args.packet))
    submissions = [_read_json(Path(path)) for path in args.submission]
    _write_json(analyze_submissions(packet, submissions, protocol), args.pretty)


if __name__ == "__main__":
    main()
