"""Evidence-only analysis packet and configurable rule matching."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = PROJECT_ROOT / "config" / "astro" / "rules.json"


class AstroAnalysisRequestError(ValueError):
    pass


class AstroAnalysisConfigError(ValueError):
    pass


def load_rules(path=DEFAULT_RULES_PATH):
    try:
        rules = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroAnalysisConfigError(f"无法读取占星规则配置: {error}") from error
    if not isinstance(rules, dict) or not isinstance(rules.get("rules"), list):
        raise AstroAnalysisConfigError("占星规则配置必须包含 rules 数组")
    for rule in rules["rules"]:
        if not isinstance(rule, dict) or not all(
            isinstance(rule.get(key), str) and rule[key]
            for key in ("rule_id", "signal_type", "observation_code")
        ):
            raise AstroAnalysisConfigError("每条占星规则必须包含 rule_id、signal_type、observation_code")
    return rules


def match_rules(signals, rules):
    matched = []
    for rule in rules.get("rules", []):
        if rule.get("enabled", True) is False:
            continue
        for signal in signals:
            if signal.get("type") != rule["signal_type"]:
                continue
            matched.append({
                "rule_id": rule["rule_id"],
                "signal_id": signal.get("signal_id"),
                "observation_code": rule["observation_code"],
                "dimension": rule.get("dimension", "structural"),
                "point_ids": signal.get("point_ids", []),
                "evidence": signal.get("evidence", {}),
            })
    return matched


def _index(items, key):
    return {item.get(key): item for item in items if isinstance(item, dict) and item.get(key)}


def analyze_natal_chart(chart, scope=None, rules=None):
    if not isinstance(chart, dict) or chart.get("chart_type") != "natal":
        raise AstroAnalysisRequestError("chart 必须是 natal 星盘 JSON")
    structured = chart.get("structured")
    if not isinstance(structured, dict):
        raise AstroAnalysisRequestError("chart 缺少 structured 结构化视图")
    signals_packet = structured.get("derived_signals") or {}
    signals = signals_packet.get("signals")
    if not isinstance(signals, list):
        raise AstroAnalysisRequestError("chart 缺少 derived_signals")

    points = _index(structured.get("points", []), "id")
    angles = _index(structured.get("angles", []), "id")
    aspects = structured.get("aspects", [])
    requested = set(scope) if isinstance(scope, list) else None
    valid_sections = {"core_points", "distribution", "signals", "aspect_network"}
    if requested is not None and not requested.issubset(valid_sections):
        raise AstroAnalysisRequestError("scope 包含不支持的分析分区")

    sections = {}
    if requested is None or "core_points" in requested:
        sections["core_points"] = {
            "source_ids": [item for item in ("sun", "moon") if item in points] +
                (["ascendant"] if "ascendant" in angles else []),
            "points": [points[item] for item in ("sun", "moon") if item in points],
            "angles": [angles["ascendant"]] if "ascendant" in angles else [],
        }
    if requested is None or "distribution" in requested:
        sections["distribution"] = structured.get("aggregates", {})
    if requested is None or "signals" in requested:
        grouped = {}
        for signal in signals:
            grouped.setdefault(signal.get("type", "unknown"), []).append(signal)
        sections["signals"] = {"items": signals, "by_type": grouped}
    if requested is None or "aspect_network" in requested:
        node_ids = sorted({node for aspect in aspects for node in
                           (aspect.get("source_id"), aspect.get("target_id")) if node})
        sections["aspect_network"] = {
            "node_ids": node_ids,
            "edges": aspects,
        }
    rules = load_rules() if rules is None else rules
    observations = match_rules(signals, rules)
    return {
        "analysis_version": "astro-analysis/1.0",
        "rules_version": rules.get("schema_version", "astro-rules/unknown"),
        "input_kind": "astro_natal_structured_signals",
        "source_schema_versions": {
            "structured": structured.get("schema_version"),
            "derived_signals": signals_packet.get("schema_version"),
        },
        "section_order": [name for name in
                          ("core_points", "distribution", "signals", "aspect_network")
                          if name in sections],
        "sections": sections,
        "observations": observations,
    }
