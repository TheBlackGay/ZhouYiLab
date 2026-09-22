"""Map A1 transit facts to versioned, evidence-only life-domain signals."""

import copy
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "astro" / "transit_rules.json"
DIMENSIONS = ("love", "wealth", "career", "learning", "social")
RULE_TYPES = {"transit_planet_in_natal_house", "transit_aspect_to_natal_point"}
ASPECT_TYPES = {"conjunction", "sextile", "square", "trine", "opposition", "quincunx"}


class AstroTransitAnalysisRequestError(ValueError):
    pass


class AstroTransitAnalysisConfigError(ValueError):
    pass


def load_rules(path=DEFAULT_RULES_PATH):
    try:
        rules = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroTransitAnalysisConfigError(f"无法读取行运规则配置: {error}") from error
    if not isinstance(rules, dict) or rules.get("schema_version") != "astro-transit-rules/1.0":
        raise AstroTransitAnalysisConfigError("行运规则配置的 schema_version 必须为 astro-transit-rules/1.0")
    entries = rules.get("rules")
    if not isinstance(entries, list) or not entries:
        raise AstroTransitAnalysisConfigError("行运规则配置必须包含非空 rules 数组")
    seen = set()
    for rule in entries:
        _validate_rule(rule)
        if rule["rule_id"] in seen:
            raise AstroTransitAnalysisConfigError(f"行运规则 ID 重复: {rule['rule_id']}")
        seen.add(rule["rule_id"])
    return rules


def _validate_rule(rule):
    if not isinstance(rule, dict):
        raise AstroTransitAnalysisConfigError("每条行运规则必须是对象")
    required = ("rule_id", "revision", "rule_type", "dimension", "direction",
                "intensity", "observation_code", "boundary")
    if any(not rule.get(key) for key in required):
        raise AstroTransitAnalysisConfigError(
            "每条行运规则必须包含 rule_id、revision、rule_type、dimension、direction、intensity、observation_code、boundary"
        )
    if not isinstance(rule["revision"], int) or rule["revision"] < 1:
        raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 revision 必须为正整数")
    if rule["rule_type"] not in RULE_TYPES:
        raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 rule_type 不支持")
    if rule["dimension"] not in DIMENSIONS:
        raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 dimension 不支持")
    if not isinstance(rule.get("transit_points"), list) or not rule["transit_points"]:
        raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 必须包含 transit_points")
    if rule["rule_type"] == "transit_planet_in_natal_house":
        houses = rule.get("natal_houses")
        if not isinstance(houses, list) or not houses or any(not isinstance(house, int) or not 1 <= house <= 12 for house in houses):
            raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 natal_houses 无效")
    else:
        points = rule.get("natal_points")
        aspects = rule.get("aspect_types")
        if not isinstance(points, list) or not points:
            raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 必须包含 natal_points")
        if not isinstance(aspects, list) or not aspects or not set(aspects) <= ASPECT_TYPES:
            raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 aspect_types 无效")
        if not isinstance(rule.get("max_orb"), (int, float)) or not 0 <= rule["max_orb"] <= 10:
            raise AstroTransitAnalysisConfigError(f"规则 {rule['rule_id']} 的 max_orb 无效")


def _transit_points(facts):
    transit = facts.get("transit")
    if not isinstance(transit, dict):
        raise AstroTransitAnalysisRequestError("行运事实包缺少 transit 对象")
    points = transit.get("planets")
    if not isinstance(points, list):
        points = facts.get("structured", {}).get("transit_points")
    if not isinstance(points, list):
        raise AstroTransitAnalysisRequestError("行运事实包缺少 transit.planets")
    return points


def _aspects(facts):
    aspects = facts.get("aspects")
    if not isinstance(aspects, list):
        aspects = facts.get("structured", {}).get("aspects")
    if not isinstance(aspects, list):
        raise AstroTransitAnalysisRequestError("行运事实包缺少 aspects 数组")
    return aspects


def _signal_id(rule, suffix):
    return f"{rule['rule_id']}:{suffix}"


def _house_signal(rule, point):
    evidence = {
        "transit_point": copy.deepcopy(point),
        "natal_house": point.get("natal_house"),
        "source": "transit.planets",
    }
    return {
        "signal_id": _signal_id(rule, point.get("id", "unknown")),
        "rule_id": rule["rule_id"],
        "revision": rule["revision"],
        "dimension": rule["dimension"],
        "direction": rule["direction"],
        "intensity": rule["intensity"],
        "observation_code": rule["observation_code"],
        "point_ids": [point.get("id")],
        "evidence": evidence,
        "boundary": rule["boundary"],
    }


def _aspect_signal(rule, aspect):
    evidence = {
        "aspect": copy.deepcopy(aspect),
        "source": "aspects",
    }
    return {
        "signal_id": _signal_id(
            rule,
            ":".join(str(aspect.get(key, "unknown")) for key in
                     ("transit_point", "natal_point", "type")),
        ),
        "rule_id": rule["rule_id"],
        "revision": rule["revision"],
        "dimension": rule["dimension"],
        "direction": rule["direction"],
        "intensity": rule["intensity"],
        "observation_code": rule["observation_code"],
        "point_ids": [aspect.get("transit_point"), aspect.get("natal_point")],
        "evidence": evidence,
        "boundary": rule["boundary"],
    }


def match_transit_rules(facts, rules):
    points = _transit_points(facts)
    aspects = _aspects(facts)
    matched = []
    for rule in rules.get("rules", []):
        if rule.get("enabled", True) is False:
            continue
        if rule["rule_type"] == "transit_planet_in_natal_house":
            for point in points:
                if point.get("id") in rule["transit_points"] and point.get("natal_house") in rule["natal_houses"]:
                    matched.append(_house_signal(rule, point))
        else:
            for aspect in aspects:
                if (
                    aspect.get("transit_point") in rule["transit_points"]
                    and aspect.get("natal_point") in rule["natal_points"]
                    and aspect.get("type") in rule["aspect_types"]
                    and isinstance(aspect.get("orb"), (int, float))
                    and aspect["orb"] <= rule["max_orb"]
                ):
                    matched.append(_aspect_signal(rule, aspect))
    return matched


def _requested_dimensions(scope, dimensions):
    values = dimensions if dimensions is not None else scope
    if values is None:
        return list(DIMENSIONS)
    if not isinstance(values, list) or not values or any(not isinstance(item, str) for item in values):
        raise AstroTransitAnalysisRequestError("scope 或 dimensions 必须是非空字符串数组")
    requested = list(dict.fromkeys(values))
    if not set(requested).issubset(DIMENSIONS):
        raise AstroTransitAnalysisRequestError("scope 或 dimensions 包含不支持的生活领域")
    return requested


def analyze_transit(facts, scope=None, dimensions=None, rules=None):
    if not isinstance(facts, dict) or facts.get("chart_type") != "transit":
        raise AstroTransitAnalysisRequestError("chart 必须是 transit 行运事实包 JSON")
    structured = facts.get("structured")
    if not isinstance(structured, dict) or structured.get("schema_version") != "astro-transit-structured/1.0":
        raise AstroTransitAnalysisRequestError("chart 缺少 astro-transit-structured/1.0 结构化事实包")
    if scope is not None and dimensions is not None and scope != dimensions:
        raise AstroTransitAnalysisRequestError("scope 与 dimensions 只能提供一个")
    requested = _requested_dimensions(scope, dimensions)
    rules = load_rules() if rules is None else rules
    for rule in rules.get("rules", []):
        _validate_rule(rule)
    signals = [signal for signal in match_transit_rules(facts, rules)
               if signal["dimension"] in requested]
    grouped = {}
    for dimension in requested:
        items = [signal for signal in signals if signal["dimension"] == dimension]
        grouped[dimension] = {
            "signal_ids": [item["signal_id"] for item in items],
            "signals": items,
            "count": len(items),
        }
    return {
        "analysis_version": "astro-transit-analysis/1.0",
        "input_kind": "astro_transit_structured_facts",
        "rules_version": rules["schema_version"],
        "dimensions": grouped,
        "signals": signals,
        "source_schema_versions": {
            "transit": structured["schema_version"],
            "natal": (structured.get("natal") or {}).get("schema_version", "astro-structured/1.0"),
        },
    }
