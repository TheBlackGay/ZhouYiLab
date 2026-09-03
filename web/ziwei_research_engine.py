#!/usr/bin/env python3
import argparse
import json
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_ROOT = PROJECT_ROOT / "config" / "ziwei" / "research"
DEFAULT_DIMENSION_PATH = RESEARCH_ROOT / "dimension_dictionary.json"
DEFAULT_PROFILE_PATH = RESEARCH_ROOT / "star_energy_profiles.json"
DEFAULT_INTERACTION_PATH = RESEARCH_ROOT / "star_interactions.json"
DEFAULT_EXPERIMENT_PATH = (
    RESEARCH_ROOT / "experiments" / "lianzhen_qisha_v0.1.json"
)
DEFAULT_BRIGHTNESS_PATH = PROJECT_ROOT / "config" / "ziwei" / "star_brightness.json"


class ResearchConfigError(ValueError):
    pass


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ResearchConfigError(f"无法读取研究配置 {path}: {error}") from error


def load_research_resources(
    dimension_path=DEFAULT_DIMENSION_PATH,
    profile_path=DEFAULT_PROFILE_PATH,
    interaction_path=DEFAULT_INTERACTION_PATH,
    experiment_path=DEFAULT_EXPERIMENT_PATH,
    brightness_path=DEFAULT_BRIGHTNESS_PATH,
):
    resources = {
        "dimensions": _read_json(dimension_path),
        "profiles": _read_json(profile_path),
        "interactions": _read_json(interaction_path),
        "experiment": _read_json(experiment_path),
        "brightness": _read_json(brightness_path),
    }
    _validate_resources(resources)
    return resources


def _validate_resources(resources):
    dimensions = resources["dimensions"]
    profiles = resources["profiles"]
    interactions = resources["interactions"]
    experiment = resources["experiment"]
    brightness = resources["brightness"]

    expected_versions = experiment["model_versions"]
    actual_versions = {
        "dimension_dictionary": dimensions["dictionary_version"],
        "star_profiles": profiles["catalog_version"],
        "star_interactions": interactions["catalog_version"],
        "brightness_table": brightness["table_version"],
    }
    if expected_versions != actual_versions:
        raise ResearchConfigError(
            f"实验模型版本不一致: expected={expected_versions}, actual={actual_versions}"
        )
    if profiles["dimension_dictionary_version"] != dimensions["dictionary_version"]:
        raise ResearchConfigError("星曜档案引用的维度词典版本不一致")
    if interactions["dimension_dictionary_version"] != dimensions["dictionary_version"]:
        raise ResearchConfigError("交互规则引用的维度词典版本不一致")
    if interactions["star_profile_catalog_version"] != profiles["catalog_version"]:
        raise ResearchConfigError("交互规则引用的星曜档案版本不一致")

    dimension_ids = _unique_ids(dimensions["dimensions"], "研究维度")
    profile_ids = _unique_ids(profiles["stars"], "星曜档案")
    interaction_ids = _unique_ids(interactions["interactions"], "交互规则")
    case_ids = _unique_ids(experiment["cases"], "实验案例")
    if case_ids != {f"LQ-{letter}" for letter in "ABCDEFGH"}:
        raise ResearchConfigError("廉贞七杀首轮实验必须完整包含 LQ-A 至 LQ-H")

    for profile in profiles["stars"]:
        for mechanism in profile["mechanisms"]:
            _validate_hypotheses(mechanism["dimension_hypotheses"], dimension_ids)
    for interaction in interactions["interactions"]:
        participant_ids = {item["star_id"] for item in interaction["participants"]}
        unknown = participant_ids - profile_ids
        if unknown:
            raise ResearchConfigError(
                f"{interaction['id']} 引用了未知星曜档案: {sorted(unknown)}"
            )
        _validate_hypotheses(interaction["base_hypotheses"], dimension_ids)
        modifier_ids = _unique_ids(interaction["modifiers"], f"{interaction['id']} 修正项")
        if not modifier_ids and interaction["modifiers"]:
            raise ResearchConfigError(f"{interaction['id']} 修正项 ID 无效")
        for modifier in interaction["modifiers"]:
            _validate_hypotheses(modifier["hypotheses"], dimension_ids)

    profile_by_id = {item["id"]: item for item in profiles["stars"]}
    for case in experiment["cases"]:
        _validate_case(case, profile_by_id, brightness)
        expected_unknown = set(case["expected"]["interaction_ids"]) - interaction_ids
        if expected_unknown:
            raise ResearchConfigError(
                f"{case['id']} 预期引用未知交互: {sorted(expected_unknown)}"
            )


def _unique_ids(items, label):
    ids = [item.get("id") for item in items]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ResearchConfigError(f"{label} ID 不能为空或重复")
    return set(ids)


def _validate_hypotheses(hypotheses, dimension_ids):
    for hypothesis in hypotheses:
        if hypothesis["dimension_id"] not in dimension_ids:
            raise ResearchConfigError(
                f"维度假设引用未知维度: {hypothesis['dimension_id']}"
            )
        if hypothesis["parameter_status"] != "proposed":
            raise ResearchConfigError("首轮定性实验只允许 proposed 维度假设")


def _validate_case(case, profile_by_id, brightness):
    if case["source_layer"] != "natal":
        raise ResearchConfigError(f"{case['id']} 首轮只允许本命层")
    branch_index = {name: index for index, name in enumerate(brightness["branches"])}
    for star in case["stars"]:
        profile = profile_by_id.get(star["star_id"])
        if profile is None:
            raise ResearchConfigError(f"{case['id']} 引用了未知星曜: {star['star_id']}")
        if profile["name"] != star["name"]:
            raise ResearchConfigError(f"{case['id']} 星曜 ID 与名称不一致: {star['star_id']}")
        branch = star["earthly_branch"]
        if branch not in branch_index:
            raise ResearchConfigError(f"{case['id']} 地支无效: {branch}")
        table = brightness["stars"].get(star["name"])
        if not table:
            raise ResearchConfigError(f"{case['id']} 缺少亮度表: {star['name']}")
        expected = table[branch_index[branch]]
        if star["brightness"] != expected:
            raise ResearchConfigError(
                f"{case['id']} {star['name']}在{branch}亮度应为{expected}，"
                f"实际为{star['brightness']}"
            )
        if star["source_layer"] != case["source_layer"]:
            raise ResearchConfigError(f"{case['id']} 星曜盘层与案例盘层不一致")
    for signal in case["transformation_signals"]:
        if signal["fact_status"] != "controlled_stimulus" or not signal["boundary"]:
            raise ResearchConfigError(f"{case['id']} 受控四化必须声明身份和边界")


def run_experiment(resources, case_id=None):
    cases = resources["experiment"]["cases"]
    if case_id:
        cases = [case for case in cases if case["id"] == case_id]
        if not cases:
            raise ResearchConfigError(f"实验案例不存在: {case_id}")
    results = []
    for case in cases:
        result = evaluate_case(resources, case)
        errors = _expectation_errors(case["expected"], result)
        results.append({
            "case_id": case["id"],
            "passed": not errors,
            "errors": errors,
            "result": result,
        })
    return {
        "experiment_id": resources["experiment"]["id"],
        "experiment_version": resources["experiment"]["experiment_version"],
        "status": resources["experiment"]["status"],
        "passed": all(item["passed"] for item in results),
        "case_count": len(results),
        "cases": results,
        "interpretation_boundary": (
            "定性研究夹具结果，不是完整命盘分析，不包含分数、概率或吉凶总评。"
        ),
    }


def evaluate_case(resources, case):
    profile_by_id = {item["id"]: item for item in resources["profiles"]["stars"]}
    signals = []
    profile_results = []
    for star in case["stars"]:
        profile = profile_by_id[star["star_id"]]
        mechanisms = []
        for mechanism in profile["mechanisms"]:
            mechanism_signals = _hypothesis_signals(
                case["id"], "star_mechanism", mechanism["id"],
                mechanism["dimension_hypotheses"], [deepcopy(star)],
                mechanism["source_refs"],
            )
            signals.extend(mechanism_signals)
            mechanisms.append({
                "id": mechanism["id"],
                "name": mechanism["name"],
                "definition": mechanism["definition"],
                "signal_ids": [item["signal_id"] for item in mechanism_signals],
            })
        profile_results.append({
            "star_id": profile["id"],
            "name": profile["name"],
            "fact": deepcopy(star),
            "mechanisms": mechanisms,
        })

    interaction_results = []
    for interaction in resources["interactions"]["interactions"]:
        required_trace = _match_interaction(interaction, case)
        if not required_trace["matched"]:
            continue
        base_signals = _hypothesis_signals(
            case["id"], "interaction_base", interaction["id"],
            interaction["base_hypotheses"], required_trace["evidence"],
            interaction["source_refs"],
        )
        signals.extend(base_signals)
        modifier_results = []
        for modifier in interaction["modifiers"]:
            trace = _match_modifier(modifier, case, required_trace["evidence"])
            modifier_signals = []
            if trace["matched"]:
                modifier_signals = _hypothesis_signals(
                    case["id"], "interaction_modifier", modifier["id"],
                    modifier["hypotheses"], trace["evidence"],
                    modifier["source_refs"],
                )
                signals.extend(modifier_signals)
            modifier_results.append({
                "id": modifier["id"],
                "name": modifier["name"],
                "matched": trace["matched"],
                "trigger": deepcopy(modifier["trigger"]),
                "actual": trace["actual"],
                "evidence": trace["evidence"],
                "signal_ids": [item["signal_id"] for item in modifier_signals],
            })
        interaction_results.append({
            "id": interaction["id"],
            "name": interaction["name"],
            "elemental_mechanism": deepcopy(interaction["elemental_mechanism"]),
            "required_trace": required_trace,
            "base_signal_ids": [item["signal_id"] for item in base_signals],
            "modifiers": modifier_results,
        })

    dimension_signals = {
        dimension["id"]: [
            signal["signal_id"] for signal in signals
            if signal["dimension_id"] == dimension["id"]
        ]
        for dimension in resources["dimensions"]["dimensions"]
    }
    return {
        "case_id": case["id"],
        "name": case["name"],
        "purpose": case["purpose"],
        "source_layer": case["source_layer"],
        "focus": deepcopy(case["focus"]),
        "fixture_completeness": resources["experiment"]["fixture_policy"]["completeness"],
        "profiles": profile_results,
        "interactions": interaction_results,
        "signals": signals,
        "dimension_signals": dimension_signals,
        "aggregation": {
            "performed": False,
            "reason": "首轮定性阶段保留全部方向信号，不计算权重、分数或总评。",
        },
    }


def _match_interaction(interaction, case):
    participant_ids = [item["star_id"] for item in interaction["participants"]]
    candidates = {
        star_id: [
            star for star in case["stars"]
            if star["star_id"] == star_id
            and (
                not interaction["required_context"]["same_source_layer"]
                or star["source_layer"] == case["source_layer"]
            )
        ]
        for star_id in participant_ids
    }
    missing = [star_id for star_id, stars in candidates.items() if not stars]
    relation = interaction["required_context"]["relation"]
    common_palaces = set()
    if not missing and relation == "same_palace":
        palace_sets = [
            {star["physical_palace"] for star in candidates[star_id]}
            for star_id in participant_ids
        ]
        common_palaces = set.intersection(*palace_sets)
    matched = not missing and relation == "same_palace" and bool(common_palaces)
    evidence = []
    if matched:
        palace = sorted(common_palaces)[0]
        for star_id in participant_ids:
            evidence.append(next(
                star for star in candidates[star_id]
                if star["physical_palace"] == palace
            ))
    return {
        "matched": matched,
        "expected_relation": relation,
        "participant_ids": participant_ids,
        "missing_participants": missing,
        "common_physical_palaces": sorted(common_palaces),
        "evidence": deepcopy(evidence),
    }


def _match_modifier(modifier, case, participant_evidence):
    trigger = modifier["trigger"]
    trigger_type = trigger["type"]
    values = set(trigger["values"])
    match_mode = trigger["match_mode"]
    target_ids = trigger.get("target_star_ids", [])
    evidence = []
    actual = {}

    if trigger_type == "brightness.in":
        stars = [star for star in participant_evidence if star["star_id"] in target_ids]
        flags = {
            star_id: any(
                star["star_id"] == star_id and star["brightness"] in values
                for star in stars
            ) for star_id in target_ids
        }
        evidence = [star for star in stars if star["brightness"] in values]
        actual = {star["star_id"]: star["brightness"] for star in stars}
        matched = _combine_flags(flags.values(), match_mode)
    elif trigger_type == "transformation.in":
        stars = [star for star in participant_evidence if star["star_id"] in target_ids]
        flags = {
            star_id: any(
                star["star_id"] == star_id and star.get("transformation") in values
                for star in stars
            ) for star_id in target_ids
        }
        evidence = [star for star in stars if star.get("transformation") in values]
        actual = {star["star_id"]: star.get("transformation") for star in stars}
        matched = _combine_flags(flags.values(), match_mode)
    elif trigger_type == "transformation.present_in_scope":
        scope_relations = {"self", "triad", "opposite"}
        facts = [
            {
                "transformation": star.get("transformation"),
                "relation": star["relation"],
                "physical_palace": star["physical_palace"],
                "source_layer": star["source_layer"],
                "fact_status": star["fact_status"],
                "star_id": star["star_id"],
            }
            for star in case["stars"] if star.get("transformation")
        ] + deepcopy(case["transformation_signals"])
        facts = [
            fact for fact in facts
            if fact["relation"] in scope_relations
            and fact["source_layer"] == case["source_layer"]
        ]
        actual_values = {fact["transformation"] for fact in facts}
        flags = {value: value in actual_values for value in values}
        evidence = [fact for fact in facts if fact["transformation"] in values]
        actual = {"transformations": sorted(actual_values)}
        matched = _combine_flags(flags.values(), match_mode)
    else:
        raise ResearchConfigError(f"不支持的研究修正触发器: {trigger_type}")

    return {"matched": matched, "actual": actual, "evidence": deepcopy(evidence)}


def _combine_flags(flags, match_mode):
    flags = list(flags)
    return all(flags) if match_mode == "all" else any(flags)


def _hypothesis_signals(
    case_id, source_kind, source_id, hypotheses, evidence, source_refs
):
    return [{
        "signal_id": f"{case_id}.{source_kind}.{source_id}.{index}",
        "source_kind": source_kind,
        "source_id": source_id,
        "dimension_id": hypothesis["dimension_id"],
        "direction": hypothesis["direction"],
        "rationale": hypothesis["rationale"],
        "evidence_level": hypothesis["evidence_level"],
        "parameter_status": hypothesis["parameter_status"],
        "source_refs": list(source_refs),
        "evidence": deepcopy(evidence),
    } for index, hypothesis in enumerate(hypotheses, start=1)]


def _expectation_errors(expected, result):
    actual_profile_ids = {item["star_id"] for item in result["profiles"]}
    actual_interaction_ids = {item["id"] for item in result["interactions"]}
    actual_modifier_ids = {
        modifier["id"]
        for interaction in result["interactions"]
        for modifier in interaction["modifiers"] if modifier["matched"]
    }
    errors = []
    for label, expected_values, actual_values in (
        ("profile_star_ids", set(expected["profile_star_ids"]), actual_profile_ids),
        ("interaction_ids", set(expected["interaction_ids"]), actual_interaction_ids),
        ("modifier_ids", set(expected["modifier_ids"]), actual_modifier_ids),
    ):
        if expected_values != actual_values:
            errors.append(
                f"{label} expected={sorted(expected_values)}, actual={sorted(actual_values)}"
            )
    return errors


def main():
    parser = argparse.ArgumentParser(description="运行紫微斗数廉贞七杀定性研究实验")
    parser.add_argument("--case", help="只运行指定案例，例如 LQ-A")
    parser.add_argument("--pretty", action="store_true", help="格式化输出 JSON")
    args = parser.parse_args()
    result = run_experiment(load_research_resources(), args.case)
    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
        separators=None if args.pretty else (",", ":"),
    ))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
