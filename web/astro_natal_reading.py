"""Render the N1 natal layout facts into a score-free, evidence-only reading packet.

这是布局解读链路的第二层（方案 N2 的文案部分）：只把已经命中的规则翻成可读句子，
不新增事实、不写没有证据支持的段落。缺失模板时显式进入 `uncovered`，不臆造内容。
"""

import copy
import json
import re
from pathlib import Path

try:
    from astro_natal_analysis import SIGN_NAMES
except ImportError:  # pragma: no cover - 包内导入路径
    from web.astro_natal_analysis import SIGN_NAMES


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATES_PATH = PROJECT_ROOT / "config" / "astro" / "natal_reading_templates.json"

CORE_SLOTS = ("ascendant", "sun", "moon", "chart_ruler")
DIMENSION_ORDER = (
    "core", "layout", "distribution", "concentration", "aspect",
    "angularity", "motion", "placement", "field",
)
KNOWN_PLACEHOLDERS = frozenset({
    "aspect_label", "count", "degree_in_sign", "element_label", "harmony", "harmony_percent",
    "hemisphere_label", "house", "house_text", "houses", "longitude", "modality_label",
    "orb", "pair_text", "point_name", "point_names", "quadrant", "quadrant_label",
    "ratio_percent", "ruler_house_text", "ruler_name", "ruler_sign_name", "sign_name",
    "tension", "tension_percent", "threshold", "total",
})
PLACEHOLDER = re.compile(r"\{(\w+)\}")


class AstroNatalReadingRequestError(ValueError):
    pass


class AstroNatalReadingConfigError(ValueError):
    pass


def _check_text(text, where):
    if not isinstance(text, str) or not text:
        raise AstroNatalReadingConfigError(f"{where} 必须是非空字符串")
    unknown = set(PLACEHOLDER.findall(text)) - KNOWN_PLACEHOLDERS
    if unknown:
        raise AstroNatalReadingConfigError(f"{where} 使用了未知占位符: {', '.join(sorted(unknown))}")


def _check_entry(entry, where):
    if not isinstance(entry, dict):
        raise AstroNatalReadingConfigError(f"{where} 必须是对象")
    if not isinstance(entry.get("revision"), int) or entry["revision"] < 1:
        raise AstroNatalReadingConfigError(f"{where} 的 revision 必须为正整数")
    _check_text(entry.get("text"), where)


def load_templates(path=DEFAULT_TEMPLATES_PATH):
    try:
        templates = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroNatalReadingConfigError(f"无法读取本命解读模板配置: {error}") from error
    if not isinstance(templates, dict) or templates.get("schema_version") != "astro-natal-templates/1.0":
        raise AstroNatalReadingConfigError("本命解读模板配置的 schema_version 必须为 astro-natal-templates/1.0")
    core_text = templates.get("core_text")
    if not isinstance(core_text, dict) or set(core_text) != set(CORE_SLOTS):
        raise AstroNatalReadingConfigError("本命解读模板必须覆盖 ascendant、sun、moon、chart_ruler 四个核心槽位")
    for slot in CORE_SLOTS:
        _check_entry(core_text[slot], f"core_text.{slot}")
    layout_text = templates.get("layout_text")
    if not isinstance(layout_text, dict):
        raise AstroNatalReadingConfigError("本命解读模板必须包含 layout_text 对象")
    for rule_id, entry in layout_text.items():
        _check_entry(entry, f"layout_text.{rule_id}")
    labels = templates.get("labels")
    if not isinstance(labels, dict):
        raise AstroNatalReadingConfigError("本命解读模板必须包含 labels 对象")
    for group in ("hemisphere", "quadrant", "element", "modality", "aspect"):
        values = labels.get(group)
        if not isinstance(values, dict) or not values or any(
            not isinstance(value, str) or not value for value in values.values()
        ):
            raise AstroNatalReadingConfigError(f"labels.{group} 必须是非空字符串映射")
    boundaries = templates.get("boundaries")
    if not isinstance(boundaries, list) or not boundaries or any(
        not isinstance(item, str) or not item for item in boundaries
    ):
        raise AstroNatalReadingConfigError("本命解读模板必须包含非空 boundaries 数组")
    return templates


def _render(text, values):
    return PLACEHOLDER.sub(lambda match: str(values.get(match.group(1), "—")), text)


def _round(value, digits=4):
    return round(value, digits) if isinstance(value, (int, float)) else value


def _percent(part, total):
    if not isinstance(part, (int, float)) or not isinstance(total, (int, float)) or not total:
        return 0
    return round(part / total * 100)


def _house_text(house):
    return f"第{house}宫" if isinstance(house, int) else "落宫未定"


def _sign_names(layout):
    names = dict(SIGN_NAMES)
    for item in ((layout or {}).get("sign_occupancy") or {}).get("items") or []:
        if item.get("sign_id") and item.get("sign_name"):
            names[item["sign_id"]] = item["sign_name"]
    ascendant = ((layout or {}).get("core") or {}).get("ascendant") or {}
    if ascendant.get("sign_id") and ascendant.get("sign_name"):
        names[ascendant["sign_id"]] = ascendant["sign_name"]
    return names


def _layout_values(signal, labels, sign_names):
    """把命中规则的证据翻译成模板占位符，缺值一律显式降级，不做推测。"""
    evidence = signal.get("evidence") or {}
    point_names = list(signal.get("point_names") or [])
    values = {
        "count": evidence.get("count"),
        "total": evidence.get("total"),
        "threshold": evidence.get("threshold"),
        "house": evidence.get("house"),
        "harmony": evidence.get("harmony"),
        "tension": evidence.get("tension"),
        "point_names": "、".join(point_names),
        "pair_text": "与".join(point_names[:2]),
        "sign_name": evidence.get("sign_name") or sign_names.get(evidence.get("sign_id")) or evidence.get("sign_id"),
        "ratio_percent": _percent(evidence.get("count"), evidence.get("total")),
        "orb": _round(evidence.get("orb"), 4),
        "aspect_label": labels["aspect"].get(evidence.get("aspect_type"), evidence.get("aspect_type")),
    }
    if evidence.get("houses"):
        values["houses"] = "、".join(str(house) for house in evidence["houses"])
    if evidence.get("hemisphere"):
        values["hemisphere_label"] = labels["hemisphere"].get(
            evidence["hemisphere"], evidence["hemisphere"])
    if evidence.get("quadrant"):
        key = str(evidence["quadrant"])
        values["quadrant"] = evidence["quadrant"]
        values["quadrant_label"] = labels["quadrant"].get(key, key)
    if evidence.get("element"):
        values["element_label"] = labels["element"].get(evidence["element"], evidence["element"])
    if evidence.get("modality"):
        values["modality_label"] = labels["modality"].get(evidence["modality"], evidence["modality"])
    if evidence.get("total") is not None:
        values["harmony_percent"] = _percent(evidence.get("harmony"), evidence.get("total"))
        values["tension_percent"] = _percent(evidence.get("tension"), evidence.get("total"))
    if evidence.get("ruler_name"):
        values.update(
            ruler_name=evidence.get("ruler_name"),
            ruler_sign_name=evidence.get("ruler_sign_name"),
            ruler_house_text=_house_text(evidence.get("ruler_house")),
        )
    # chart_ruler_placement 的证据直接来自 layout.core.chart_ruler，字段名是 point_name/sign_name/house。
    if signal.get("signal_type") == "chart_ruler_placement":
        values.update(
            ruler_name=evidence.get("point_name"),
            ruler_sign_name=evidence.get("sign_name") or sign_names.get(evidence.get("sign_id")),
            ruler_house_text=_house_text(evidence.get("house")),
        )
    return values


def _core_item(slot, layout, templates, sign_names, signals):
    core = (layout or {}).get("core") or {}
    source = core.get("chart_ruler") if slot == "chart_ruler" else core.get(slot)
    if not source:
        return None
    entry = templates["core_text"][slot]
    if slot == "ascendant":
        sign_name = source.get("sign_name") or sign_names.get(source.get("sign_id"))
        values = {"sign_name": sign_name, "degree_in_sign": _round(source.get("degree_in_sign"), 2)}
        title = f"上升 {sign_name}"
        point_ids = ["ascendant"]
    elif slot in ("sun", "moon"):
        sign_name = source.get("sign_name") or sign_names.get(source.get("sign_id"))
        values = {
            "point_name": source.get("point_name"),
            "sign_name": sign_name,
            "house_text": _house_text(source.get("house")),
            "longitude": _round(source.get("longitude"), 4),
        }
        title = f"{source.get('point_name')} {sign_name} · {_house_text(source.get('house'))}"
        point_ids = [source.get("point_id")]
    else:
        sign_name = (core.get("ascendant") or {}).get("sign_name")
        values = {
            "sign_name": sign_name,
            "ruler_name": source.get("point_name"),
            "ruler_sign_name": source.get("sign_name") or sign_names.get(source.get("sign_id")),
            "ruler_house_text": _house_text(source.get("house")),
        }
        title = f"命主星 {source.get('point_name')} · {_house_text(source.get('house'))}"
        point_ids = [source.get("point_id")]
    return {
        "slot": slot,
        "point_id": source.get("point_id"),
        "angle_id": source.get("angle_id"),
        "sign_id": source.get("sign_id"),
        "sign_name": source.get("sign_name") or sign_names.get(source.get("sign_id")),
        "house": source.get("house"),
        "title": title,
        "summary": _render(entry["text"], values),
        "revision": entry["revision"],
        "signal_ids": [signal["signal_id"] for signal in signals
                       if signal["signal_id"] == "chart_ruler_placement"
                       or set(signal.get("point_ids") or []) & set(point_ids)],
    }


def _sort_key(entry):
    dimension = entry.get("dimension")
    index = DIMENSION_ORDER.index(dimension) if dimension in DIMENSION_ORDER else len(DIMENSION_ORDER)
    digits = tuple(int(value) for value in re.findall(r"\d+", entry.get("signal_id") or ""))
    orb = entry.get("evidence", {}).get("orb")
    return (index, entry.get("rule_id") or "", digits, orb if isinstance(orb, (int, float)) else 0)


def render_natal_reading(analysis, templates=None):
    if not isinstance(analysis, dict) or analysis.get("analysis_version") != "astro-natal-analysis/1.0":
        raise AstroNatalReadingRequestError("analysis 必须是 astro-natal-analysis/1.0 分析包")
    layout = analysis.get("layout")
    if not isinstance(layout, dict):
        raise AstroNatalReadingRequestError("analysis 缺少 layout 布局统计")
    signals = analysis.get("signals")
    if not isinstance(signals, list):
        raise AstroNatalReadingRequestError("analysis 缺少 signals 数组")
    for signal in signals:
        if not isinstance(signal, dict) or not signal.get("rule_id"):
            raise AstroNatalReadingRequestError("analysis 包含无效的规则命中")

    templates = load_templates() if templates is None else templates
    labels = templates["labels"]
    sign_names = _sign_names(layout)
    uncovered = [dict(item) for item in (analysis.get("uncovered") or []) if isinstance(item, dict)]

    entries = []
    core_skipped = 0
    for signal in signals:
        # core 维度由 highlights 的三大核心行承载，不再重复成一条布局速读。
        if signal.get("dimension") == "core":
            core_skipped += 1
            continue
        entry = templates["layout_text"].get(signal["rule_id"])
        if entry is None:
            uncovered.append({
                "signal_id": signal["signal_id"],
                "rule_id": signal["rule_id"],
                "reason": "no_template",
            })
            continue
        evidence = copy.deepcopy(signal.get("evidence") or {})
        entries.append({
            "slot": "layout",
            "rule_id": signal["rule_id"],
            "revision": entry["revision"],
            "signal_id": signal["signal_id"],
            "signal_type": signal.get("signal_type"),
            "dimension": signal.get("dimension"),
            "text": _render(entry["text"], _layout_values(signal, labels, sign_names)),
            "count": evidence.get("count"),
            "total": evidence.get("total"),
            "point_ids": copy.deepcopy(signal.get("point_ids") or []),
            "signal_ids": [signal["signal_id"]],
            "evidence": evidence,
            "boundary": signal.get("boundary"),
        })
    entries.sort(key=_sort_key)

    core_items = {slot: _core_item(slot, layout, templates, sign_names, signals) for slot in CORE_SLOTS}
    emphasis = [signal["signal_id"] for signal in signals
                if signal.get("signal_type") in ("element_emphasis", "modality_emphasis")]
    return {
        "reading_version": "astro-natal-reading/1.0",
        "templates_version": templates["schema_version"],
        "ruler_system": analysis.get("ruler_system", layout.get("ruler_system", "modern")),
        "highlights": core_items,
        "layout": entries,
        "layout_stats": layout,
        "distribution": {
            "element_counts": copy.deepcopy(layout.get("elements") or {}),
            "modality_counts": copy.deepcopy(layout.get("modalities") or {}),
            "emphasis": emphasis,
        },
        "points": [],
        "houses": [],
        "aspects": [],
        "coverage": {
            "facts": len(analysis.get("facts") or []),
            "matched": len(signals),
            "rendered": len(entries) + core_skipped,
            "layout_lines": len(entries),
            "uncovered": len(uncovered),
        },
        "boundaries": list(templates["boundaries"]),
        "uncovered": uncovered,
        "versions": {
            "structured": (analysis.get("source_schema_versions") or {}).get("structured"),
            "analysis": analysis.get("analysis_version"),
            "reading": "astro-natal-reading/1.0",
            "rules": analysis.get("rules_version"),
            "templates": templates["schema_version"],
        },
    }


def analyze_and_render_natal(chart, ruler_system=None, templates=None):
    try:
        from astro_natal_analysis import analyze_natal_layout
    except ImportError:  # pragma: no cover - 包内导入路径
        from web.astro_natal_analysis import analyze_natal_layout
    analysis = analyze_natal_layout(chart, ruler_system=ruler_system)
    return render_natal_reading(analysis, templates=templates)