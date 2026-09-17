"""Derive the natal zodiac/house layout facts and rule hits from structured facts.

布局解读链路的第一层（方案 N1）：只把 `astro-structured/1.0` 读成可核对的布局事实，
不新增排盘计算、不改 C++ 排盘核心、不下吉凶断语。

输出分三块，职责不混：

- `layout`：描述性统计（三核心、半球、象限、星座与宫位占据、元素模式、相位网络），
  每项都带统计口径与点位清单，即使规则配置为空也必须完整可用；
- `facts`：从布局统计与派生信号生成的原始信号（`signal_id` / `type` / `point_ids` / `evidence`）；
- `signals`：`config/astro/natal_rules.json` 命中的规则，用于选择文案与 observation code。
"""

import copy
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "astro" / "natal_rules.json"

RULER_SYSTEMS = ("modern", "traditional")
SIGN_ORDER = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
# structured 只保证星座 id，中文名只在 houses / angles 里出现，而这两处不一定覆盖全部 12 座。
# 这里作为兜底词表；structured 自身带的中文名优先。
SIGN_NAMES = {
    "aries": "白羊座", "taurus": "金牛座", "gemini": "双子座", "cancer": "巨蟹座",
    "leo": "狮子座", "virgo": "处女座", "libra": "天秤座", "scorpio": "天蝎座",
    "sagittarius": "射手座", "capricorn": "摩羯座", "aquarius": "水瓶座", "pisces": "双鱼座",
}
# 半球、象限、星座与宫位占据只统计十大行星，与常见星盘读法保持一致；
# 真交点、凯龙等虚点仍会出现在逐点位事实里，但不参与分布统计。
DISTRIBUTION_POINTS = (
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
)
# 逐点位卡片的展示顺序：先十大行星，再虚点。
POINT_ORDER = DISTRIBUTION_POINTS + ("true_node", "chiron")
HEMISPHERES = {
    "left": (1, 2, 3, 10, 11, 12),
    "right": (4, 5, 6, 7, 8, 9),
    "above": (7, 8, 9, 10, 11, 12),
    "below": (1, 2, 3, 4, 5, 6),
}
QUADRANT_HOUSES = {1: (1, 2, 3), 2: (4, 5, 6), 3: (7, 8, 9), 4: (10, 11, 12)}
HARMONY_ASPECTS = ("sextile", "trine")
TENSION_ASPECTS = ("square", "opposition")
NEUTRAL_ASPECTS = ("conjunction", "quincunx")
ASPECT_ORDER = ("conjunction", "sextile", "square", "trine", "opposition", "quincunx")
TIGHT_ORB = 3.0

MODERN_RULERS = {
    "aries": "mars", "taurus": "venus", "gemini": "mercury", "cancer": "moon",
    "leo": "sun", "virgo": "mercury", "libra": "venus", "scorpio": "pluto",
    "sagittarius": "jupiter", "capricorn": "saturn", "aquarius": "uranus",
    "pisces": "neptune",
}
TRADITIONAL_RULERS = {
    **MODERN_RULERS, "scorpio": "mars", "aquarius": "saturn", "pisces": "jupiter",
}
RULER_TABLES = {"modern": MODERN_RULERS, "traditional": TRADITIONAL_RULERS}

DERIVED_SIGNAL_TYPES = (
    "angular_planet", "retrograde_point", "element_emphasis", "modality_emphasis",
    "sign_stellium", "house_stellium", "tight_aspect",
)
LAYOUT_SIGNAL_TYPES = (
    "angle_in_sign", "point_in_sign", "point_in_house", "house_cusp_sign",
    "house_ruler_placement", "chart_ruler_placement", "hemisphere_stat",
    "quadrant_stat", "sign_occupancy_stat", "empty_house", "aspect_network_stat",
)
SUPPORTED_SIGNAL_TYPES = frozenset(DERIVED_SIGNAL_TYPES + LAYOUT_SIGNAL_TYPES)
DIMENSIONS = (
    "core", "placement", "field", "layout", "distribution", "aspect",
    "motion", "concentration", "angularity",
)

DISTRIBUTION_DEFINITION = (
    "半球、象限、星座与宫位占据只统计十大行星（太阳、月亮、水星、金星、火星、木星、"
    "土星、天王星、海王星、冥王星）中落宫有效的点位；真交点、凯龙等虚点不参与分布统计。"
)
ASPECT_DEFINITION = "统计 structured.aspects 中已计算的全部主要相位；顺畅为拱相与六合，张力为刑相与对冲。"


class AstroNatalAnalysisRequestError(ValueError):
    pass


class AstroNatalAnalysisConfigError(ValueError):
    pass


def _validate_rule(rule, seen):
    if not isinstance(rule, dict):
        raise AstroNatalAnalysisConfigError("每条本命布局规则必须是对象")
    required = ("rule_id", "signal_type", "dimension", "observation_code", "boundary")
    if any(not isinstance(rule.get(key), str) or not rule[key] for key in required):
        raise AstroNatalAnalysisConfigError(
            "每条本命布局规则必须包含 rule_id、signal_type、dimension、observation_code、boundary"
        )
    if rule["rule_id"] in seen:
        raise AstroNatalAnalysisConfigError(f"本命布局规则 ID 重复: {rule['rule_id']}")
    seen.add(rule["rule_id"])
    revision = rule.get("revision", 1)
    if not isinstance(revision, int) or revision < 1:
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 revision 必须为正整数")
    if rule["signal_type"] not in SUPPORTED_SIGNAL_TYPES:
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 signal_type 不支持")
    if rule["dimension"] not in DIMENSIONS:
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 dimension 不支持")
    match = rule.get("match")
    if match is not None and not isinstance(match, dict):
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 match 必须是对象")
    if "min_count" in rule and (not isinstance(rule["min_count"], int) or rule["min_count"] < 0):
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 min_count 必须是非负整数")
    if "min_ratio" in rule and (not isinstance(rule["min_ratio"], (int, float)) or not 0 <= rule["min_ratio"] <= 1):
        raise AstroNatalAnalysisConfigError(f"规则 {rule['rule_id']} 的 min_ratio 必须在 0 到 1 之间")


def load_rules(path=DEFAULT_RULES_PATH):
    try:
        rules = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroNatalAnalysisConfigError(f"无法读取本命布局规则配置: {error}") from error
    if not isinstance(rules, dict) or rules.get("schema_version") != "astro-natal-rules/1.0":
        raise AstroNatalAnalysisConfigError("本命布局规则配置的 schema_version 必须为 astro-natal-rules/1.0")
    entries = rules.get("rules")
    if not isinstance(entries, list) or not entries:
        raise AstroNatalAnalysisConfigError("本命布局规则配置必须包含非空 rules 数组")
    seen = set()
    for rule in entries:
        _validate_rule(rule, seen)
    return rules


def _structured(chart):
    if not isinstance(chart, dict) or chart.get("chart_type") != "natal":
        raise AstroNatalAnalysisRequestError("chart 必须是 natal 星盘 JSON")
    structured = chart.get("structured")
    if not isinstance(structured, dict) or structured.get("schema_version") != "astro-structured/1.0":
        raise AstroNatalAnalysisRequestError("chart 缺少 astro-structured/1.0 结构化事实包")
    if not isinstance(structured.get("points"), list) or not isinstance(structured.get("houses"), list):
        raise AstroNatalAnalysisRequestError("structured 缺少 points 或 houses 数组")
    return structured


def _ruler_system(value):
    if value is None:
        return "modern"
    if value not in RULER_SYSTEMS:
        raise AstroNatalAnalysisRequestError("ruler_system 只支持 modern 或 traditional")
    return value


def _index(items, key="id"):
    return {item[key]: item for item in items if isinstance(item, dict) and item.get(key)}


def _sign_names(structured):
    names = dict(SIGN_NAMES)
    for item in list(structured.get("houses") or []) + list(structured.get("angles") or []):
        if isinstance(item, dict) and item.get("sign_id") and item.get("sign_name"):
            names[item["sign_id"]] = item["sign_name"]
    return names


def _house_of(point):
    house = point.get("house")
    if isinstance(house, int) and 1 <= house <= 12:
        return house
    return None


def _distribution_points(points):
    """按十大行星口径挑选参与分布统计的点位，并记录缺失口径。"""
    counted = [points[point_id] for point_id in DISTRIBUTION_POINTS if point_id in points]
    counted = [point for point in counted if _house_of(point) is not None]
    counted_ids = [point["id"] for point in counted]
    missing = [point_id for point_id in DISTRIBUTION_POINTS if point_id not in points]
    return counted, counted_ids, missing


def _layout(structured, point_by_id, angle_by_id, sign_names, ruler_system, house_system):
    counted, counted_ids, missing = _distribution_points(point_by_id)
    total = len(counted)

    def build_groups(definition, groups):
        items = []
        for name, houses in groups:
            members = [point for point in counted if _house_of(point) in houses]
            items.append({
                "name": name,
                "houses": list(houses),
                "count": len(members),
                "total": total,
                "ratio": round(len(members) / total, 4) if total else 0.0,
                "point_ids": [point["id"] for point in members],
            })
        return {"definition": definition, "counted_point_ids": counted_ids,
                "counted_point_names": [point.get("name") or point["id"] for point in counted],
                "counted_total": total, "missing_point_ids": missing, "items": items}

    hemispheres = build_groups(DISTRIBUTION_DEFINITION, HEMISPHERES.items())
    quadrants = build_groups(DISTRIBUTION_DEFINITION, [(str(number), houses)
                                                      for number, houses in QUADRANT_HOUSES.items()])

    sign_counts = Counter(point["sign_id"] for point in counted)
    sign_occupancy = {
        "definition": DISTRIBUTION_DEFINITION,
        "items": [{
            "sign_id": sign_id,
            "sign_name": sign_names.get(sign_id, sign_id),
            "count": sign_counts.get(sign_id, 0),
            "point_ids": [point["id"] for point in counted if point["sign_id"] == sign_id],
        } for sign_id in SIGN_ORDER],
    }

    house_items = []
    for house in structured["houses"]:
        number = house.get("number")
        members = [point for point in counted if _house_of(point) == number]
        house_items.append({
            "house": number,
            "sign_id": house.get("sign_id"),
            "sign_name": house.get("sign_name") or sign_names.get(house.get("sign_id"), house.get("sign_id")),
            "cusp": house.get("cusp"),
            "count": len(members),
            "point_ids": [point["id"] for point in members],
        })
    house_occupancy = {
        "definition": DISTRIBUTION_DEFINITION,
        "items": house_items,
        "empty_houses": [item["house"] for item in house_items if item["count"] == 0],
    }

    aspects = [aspect for aspect in (structured.get("aspects") or []) if isinstance(aspect, dict)]
    by_type = Counter(aspect.get("type") for aspect in aspects)
    orbs = [aspect["orb"] for aspect in aspects if isinstance(aspect.get("orb"), (int, float))]
    aspect_items = [{
        "source_id": aspect.get("source_id"),
        "target_id": aspect.get("target_id"),
        "type": aspect.get("type"),
        "orb": aspect.get("orb"),
        "phase": aspect.get("phase"),
        "exact_angle": aspect.get("exact_angle"),
        "actual_angle": aspect.get("actual_angle"),
    } for aspect in sorted(aspects, key=lambda item: item.get("orb")
                           if isinstance(item.get("orb"), (int, float)) else 999.0)]
    harmony = sum(by_type.get(name, 0) for name in HARMONY_ASPECTS)
    tension = sum(by_type.get(name, 0) for name in TENSION_ASPECTS)
    if harmony > tension:
        dominant, ratio = "harmony", round(harmony / len(aspects), 4)
    elif tension > harmony:
        dominant, ratio = "tension", round(tension / len(aspects), 4)
    else:
        dominant, ratio = "balanced", 0.0

    aggregates = structured.get("aggregates") or {}
    elements = {name: int((aggregates.get("element_counts") or {}).get(name, 0) or 0)
                for name in ("fire", "earth", "air", "water")}
    modalities = {name: int((aggregates.get("modality_counts") or {}).get(name, 0) or 0)
                  for name in ("cardinal", "fixed", "mutable")}

    def core_point(point_id):
        point = point_by_id.get(point_id)
        if point is None:
            return None
        return {
            "point_id": point_id,
            "point_name": point.get("name") or point_id,
            "sign_id": point.get("sign_id"),
            "sign_name": sign_names.get(point.get("sign_id"), point.get("sign_id")),
            "house": _house_of(point),
            "longitude": point.get("longitude"),
            "degree_in_sign": point.get("degree_in_sign"),
            "retrograde": bool((point.get("motion") or {}).get("retrograde")),
        }

    def core_angle(angle_id):
        angle = angle_by_id.get(angle_id)
        if angle is None:
            return None
        return {
            "angle_id": angle_id,
            "sign_id": angle.get("sign_id"),
            "sign_name": angle.get("sign_name") or sign_names.get(angle.get("sign_id"), angle.get("sign_id")),
            "longitude": angle.get("longitude"),
            "degree_in_sign": angle.get("degree_in_sign"),
        }

    ascendant = core_angle("ascendant")
    chart_ruler = None
    if ascendant is not None:
        ruler_id = RULER_TABLES[ruler_system].get(ascendant["sign_id"])
        ruler = point_by_id.get(ruler_id) if ruler_id else None
        if ruler is not None:
            chart_ruler = {
                "point_id": ruler_id,
                "point_name": ruler.get("name") or ruler_id,
                "sign_id": ruler.get("sign_id"),
                "sign_name": sign_names.get(ruler.get("sign_id"), ruler.get("sign_id")),
                "house": _house_of(ruler),
                "ruler_system": ruler_system,
                "based_on": "ascendant",
            }

    return {
        "ruler_system": ruler_system,
        "house_system": house_system,
        "core": {
            "ascendant": ascendant,
            "midheaven": core_angle("midheaven"),
            "sun": core_point("sun"),
            "moon": core_point("moon"),
            "chart_ruler": chart_ruler,
        },
        "hemispheres": hemispheres,
        "quadrants": quadrants,
        "sign_occupancy": sign_occupancy,
        "house_occupancy": house_occupancy,
        "elements": elements,
        "modalities": modalities,
        "aspect_network": {
            "definition": ASPECT_DEFINITION,
            "total": len(aspects),
            "by_type": {name: by_type.get(name, 0) for name in ASPECT_ORDER},
            "items": aspect_items,
            "harmony": harmony,
            "tension": tension,
            "neutral": sum(by_type.get(name, 0) for name in NEUTRAL_ASPECTS),
            "dominant": dominant,
            "ratio": ratio,
            "tight": sum(1 for orb in orbs if orb <= TIGHT_ORB),
            "tight_threshold": TIGHT_ORB,
            "mean_orb": round(sum(orbs) / len(orbs), 4) if orbs else None,
        },
    }


def _signal(signal_id, signal_type, point_ids, evidence):
    return {
        "signal_id": signal_id,
        "type": signal_type,
        "point_ids": [point_id for point_id in point_ids if point_id],
        "point_names": [],
        "evidence": evidence,
    }


def _facts(structured, layout, point_by_id, angle_by_id, sign_names, ruler_system, house_system):
    facts = []
    for item in (structured.get("derived_signals") or {}).get("signals") or []:
        if isinstance(item, dict) and item.get("signal_id") and item.get("type"):
            facts.append(_signal(item["signal_id"], item["type"], item.get("point_ids") or [],
                                 copy.deepcopy(item.get("evidence") or {})))

    for angle_id, angle in angle_by_id.items():
        sign_id = angle.get("sign_id")
        facts.append(_signal(f"angle_in_sign:{angle_id}:{sign_id}", "angle_in_sign", [angle_id], {
            "angle_id": angle_id,
            "sign_id": sign_id,
            "sign_name": angle.get("sign_name") or sign_names.get(sign_id, sign_id),
            "longitude": angle.get("longitude"),
            "degree_in_sign": angle.get("degree_in_sign"),
        }))

    for point in point_by_id.values():
        point_id = point["id"]
        sign_id = point.get("sign_id")
        facts.append(_signal(f"point_in_sign:{point_id}:{sign_id}", "point_in_sign", [point_id], {
            "point_id": point_id,
            "point_name": point.get("name") or point_id,
            "sign_id": sign_id,
            "sign_name": sign_names.get(sign_id, sign_id),
            "longitude": point.get("longitude"),
            "degree_in_sign": point.get("degree_in_sign"),
        }))
        house = _house_of(point)
        if house is None:
            continue
        cusp = (layout["house_occupancy"]["items"][house - 1] or {}).get("cusp")
        facts.append(_signal(f"point_in_house:{point_id}:{house}", "point_in_house", [point_id], {
            "point_id": point_id,
            "point_name": point.get("name") or point_id,
            "house": house,
            "house_cusp": cusp,
            "sign_id": sign_id,
            "sign_name": sign_names.get(sign_id, sign_id),
            "house_system": house_system,
        }))

    for item in layout["house_occupancy"]["items"]:
        facts.append(_signal(f"house_cusp_sign:{item['house']}:{item['sign_id']}", "house_cusp_sign", [], {
            "house": item["house"],
            "sign_id": item["sign_id"],
            "sign_name": item["sign_name"],
            "cusp": item["cusp"],
            "house_system": house_system,
        }))
        ruler_id = RULER_TABLES[ruler_system].get(item["sign_id"])
        ruler = point_by_id.get(ruler_id) if ruler_id else None
        facts.append(_signal(f"house_ruler_placement:{item['house']}", "house_ruler_placement",
                             [ruler_id] if ruler else [], {
            "house": item["house"],
            "sign_id": item["sign_id"],
            "sign_name": item["sign_name"],
            "ruler_id": ruler_id,
            "ruler_name": (ruler or {}).get("name") or ruler_id,
            "ruler_house": _house_of(ruler) if ruler else None,
            "ruler_sign_id": (ruler or {}).get("sign_id"),
            "ruler_sign_name": sign_names.get((ruler or {}).get("sign_id"), (ruler or {}).get("sign_id")),
            "ruler_system": ruler_system,
        }))

    chart_ruler = layout["core"]["chart_ruler"]
    if chart_ruler is not None:
        facts.append(_signal("chart_ruler_placement", "chart_ruler_placement", [chart_ruler["point_id"]], {
            **copy.deepcopy(chart_ruler),
        }))

    for item in layout["hemispheres"]["items"]:
        facts.append(_signal(f"hemisphere_stat:{item['name']}", "hemisphere_stat", item["point_ids"], {
            "hemisphere": item["name"],
            "houses": item["houses"],
            "count": item["count"],
            "total": item["total"],
            "ratio": item["ratio"],
        }))
    for item in layout["quadrants"]["items"]:
        facts.append(_signal(f"quadrant_stat:{item['name']}", "quadrant_stat", item["point_ids"], {
            "quadrant": int(item["name"]),
            "houses": item["houses"],
            "count": item["count"],
            "total": item["total"],
            "ratio": item["ratio"],
        }))
    for item in layout["sign_occupancy"]["items"]:
        facts.append(_signal(f"sign_occupancy_stat:{item['sign_id']}", "sign_occupancy_stat", item["point_ids"], {
            "sign_id": item["sign_id"],
            "sign_name": item["sign_name"],
            "count": item["count"],
            "total": layout["hemispheres"]["counted_total"],
            "ratio": round(item["count"] / layout["hemispheres"]["counted_total"], 4)
            if layout["hemispheres"]["counted_total"] else 0.0,
        }))
    for item in layout["house_occupancy"]["items"]:
        if item["count"] == 0:
            facts.append(_signal(f"empty_house:{item['house']}", "empty_house", [], {
                "house": item["house"],
                "sign_id": item["sign_id"],
                "sign_name": item["sign_name"],
                "cusp": item["cusp"],
                "house_system": house_system,
            }))

    network = layout["aspect_network"]
    facts.append(_signal("aspect_network_stat", "aspect_network_stat", [], {
        key: copy.deepcopy(network[key]) for key in
        ("total", "harmony", "tension", "neutral", "dominant", "ratio", "tight",
         "tight_threshold", "mean_orb", "by_type")
    }))
    # 点位中文名在事实层就解析好，解读层即使只拿到 analysis 也不依赖 chart 还原名称。
    for fact in facts:
        fact["point_names"] = [(point_by_id.get(point_id) or {}).get("name") or point_id
                               for point_id in fact["point_ids"]]
    return facts


def _match_rule(rule, signal):
    if signal.get("type") != rule["signal_type"]:
        return False
    evidence = signal.get("evidence") or {}
    for key, expected in (rule.get("match") or {}).items():
        actual = evidence.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    if "min_count" in rule:
        count = evidence.get("count")
        if not isinstance(count, (int, float)) or count < rule["min_count"]:
            return False
    if "min_ratio" in rule:
        ratio = evidence.get("ratio")
        if not isinstance(ratio, (int, float)) or ratio < rule["min_ratio"]:
            return False
    return True


def match_rules(facts, rules):
    matched = []
    for rule in rules.get("rules", []):
        if rule.get("enabled", True) is False:
            continue
        for signal in facts:
            if not _match_rule(rule, signal):
                continue
            matched.append({
                "rule_id": rule["rule_id"],
                "revision": rule.get("revision", 1),
                "signal_id": signal["signal_id"],
                "signal_type": signal["type"],
                "observation_code": rule["observation_code"],
                "dimension": rule["dimension"],
                "point_ids": copy.deepcopy(signal["point_ids"]),
                "point_names": copy.deepcopy(signal.get("point_names") or []),
                "evidence": copy.deepcopy(signal["evidence"]),
                "boundary": rule["boundary"],
            })
    return matched


def _uncovered(facts, matched):
    covered = {item["signal_id"] for item in matched}
    return [{"signal_id": signal["signal_id"], "signal_type": signal["type"], "reason": "no_rule"}
            for signal in facts if signal["signal_id"] not in covered]


def analyze_natal_layout(chart, ruler_system=None, rules=None):
    """把本命盘 structured 事实读成布局统计 + 原始信号 + 规则命中。"""
    structured = _structured(chart)
    system = _ruler_system(ruler_system)
    rules = load_rules() if rules is None else rules
    for rule in rules.get("rules", []):
        _validate_rule(rule, set())

    point_by_id = _index(structured["points"])
    angle_by_id = _index(structured.get("angles") or [])
    sign_names = _sign_names(structured)
    house_system = (chart.get("input") or {}).get("house_system")
    layout = _layout(structured, point_by_id, angle_by_id, sign_names, system, house_system)
    facts = _facts(structured, layout, point_by_id, angle_by_id, sign_names, system, house_system)
    matched = match_rules(facts, rules)
    return {
        "analysis_version": "astro-natal-analysis/1.0",
        "input_kind": "astro_natal_structured_layout",
        "rules_version": rules.get("schema_version", "astro-natal-rules/unknown"),
        "ruler_system": system,
        "source_schema_versions": {
            "structured": structured.get("schema_version"),
            "derived_signals": (structured.get("derived_signals") or {}).get("schema_version"),
        },
        "layout": layout,
        "facts": facts,
        "signals": matched,
        "uncovered": _uncovered(facts, matched),
    }