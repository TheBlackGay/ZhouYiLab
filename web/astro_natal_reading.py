"""Render the N1 natal layout facts into a score-free, evidence-only reading packet.

布局解读链路的第二层：把已经命中的规则翻成可读句子，并按「星体 × 星座 × 宫位」
组合出逐点位卡片，不新增事实、不写没有证据支持的段落。缺失模板的条目显式进入
`uncovered`，不臆造内容。
"""

import copy
import json
import re
from pathlib import Path

try:
    from astro_natal_analysis import (
        DISTRIBUTION_POINTS,
        POINT_ORDER,
        SIGN_NAMES,
        SIGN_ORDER,
    )
except ImportError:  # pragma: no cover - 包内导入路径
    from web.astro_natal_analysis import (
        DISTRIBUTION_POINTS,
        POINT_ORDER,
        SIGN_NAMES,
        SIGN_ORDER,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATES_PATH = PROJECT_ROOT / "config" / "astro" / "natal_reading_templates.json"

CORE_SLOTS = ("ascendant", "sun", "moon", "chart_ruler")
HOUSE_KEYS = tuple(str(number) for number in range(1, 13))
ASPECT_TYPES = ("conjunction", "sextile", "square", "trine", "opposition", "quincunx")
ASPECT_LABELS = {
    "conjunction": "合相", "sextile": "六合", "square": "刑相",
    "trine": "拱相", "opposition": "对冲", "quincunx": "梅花",
}
# 逐点位卡片上标注「重点」的信号，全部来自已有派生信号。
MARKER_SIGNAL_TYPES = (
    "tight_aspect", "angular_planet", "retrograde_point", "house_stellium", "sign_stellium",
)
DIMENSION_ORDER = (
    "core", "layout", "distribution", "concentration", "aspect",
    "angularity", "motion", "placement", "field",
)
KNOWN_PLACEHOLDERS = frozenset({
    "aspect_label", "aspect_short", "count", "degree_in_sign", "element_label", "harmony",
    "harmony_percent", "hemisphere_label", "house", "house_label", "house_short", "house_text",
    "houses", "longitude", "modality_label", "orb", "pair_text", "phase_label", "point_name",
    "point_names", "quadrant", "quadrant_label", "ratio_percent", "ruler_house_text",
    "ruler_name", "ruler_sign_name", "sign_name", "sign_short", "tension", "tension_percent",
    "threshold", "total", "virtual_names",
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


def _check_entry(entry, where, fields=("text",)):
    if not isinstance(entry, dict):
        raise AstroNatalReadingConfigError(f"{where} 必须是对象")
    if not isinstance(entry.get("revision"), int) or entry["revision"] < 1:
        raise AstroNatalReadingConfigError(f"{where} 的 revision 必须为正整数")
    for field in fields:
        _check_text(entry.get(field), f"{where}.{field}")


def _check_slots(container, keys, where, fields):
    if not isinstance(container, dict):
        raise AstroNatalReadingConfigError(f"{where} 必须是对象")
    missing = [key for key in keys if key not in container]
    if missing:
        raise AstroNatalReadingConfigError(f"{where} 缺少条目: {', '.join(missing)}")
    for key in keys:
        _check_entry(container[key], f"{where}.{key}", fields)


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

    # 组合式文案的覆盖范围必须完整，否则图上会出现没有文案的点位。
    _check_slots(templates.get("planet_core"), POINT_ORDER, "planet_core",
                 ("title", "short", "text"))
    _check_slots(templates.get("sign_style"), SIGN_ORDER, "sign_style",
                 ("label", "lead", "short", "text"))
    _check_slots(templates.get("house_field"), HOUSE_KEYS, "house_field",
                 ("label", "lead", "short", "text"))
    _check_slots(templates.get("aspect_style"), ASPECT_TYPES, "aspect_style",
                 ("label", "tone", "short", "text"))
    for section in ("ascendant_sign", "sun_sign", "moon_sign"):
        _check_slots(templates.get(section), SIGN_ORDER, section, ("short", "text"))
    _check_slots(templates.get("house_ruler"), HOUSE_KEYS, "house_ruler", ("text",))

    summary = templates.get("summary")
    for key in ("point", "house_empty", "house_planets", "house_planets_virtual",
                "house_virtual_only", "aspect"):
        _check_text((summary or {}).get(key) if isinstance(summary, dict) else None, f"summary.{key}")

    overrides = templates.get("overrides")
    if not isinstance(overrides, dict):
        raise AstroNatalReadingConfigError("本命解读模板必须包含 overrides 对象")
    unknown_overrides = set(overrides) - {"point_sign", "point_house", "point_sign_house"}
    if unknown_overrides:
        raise AstroNatalReadingConfigError(f"overrides 包含不支持的槽位: {', '.join(sorted(unknown_overrides))}")
    for slot in ("point_sign", "point_house", "point_sign_house"):
        entries = overrides.get(slot)
        if not isinstance(entries, dict):
            raise AstroNatalReadingConfigError(f"overrides.{slot} 必须是对象")
        for key, entry in entries.items():
            _check_entry(entry, f"overrides.{slot}.{key}")

    layout_text = templates.get("layout_text")
    if not isinstance(layout_text, dict):
        raise AstroNatalReadingConfigError("本命解读模板必须包含 layout_text 对象")
    for rule_id, entry in layout_text.items():
        _check_entry(entry, f"layout_text.{rule_id}")

    labels = templates.get("labels")
    if not isinstance(labels, dict):
        raise AstroNatalReadingConfigError("本命解读模板必须包含 labels 对象")
    for group in ("hemisphere", "quadrant", "element", "modality", "aspect", "phase"):
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


def _house_label(house):
    return f"第{house}宫" if isinstance(house, int) and 1 <= house <= 12 else "落宫未定"


def _join(names):
    return "、".join(name for name in names if name)


def _block(slot, rule_id, entry, **extra):
    return {"slot": slot, "rule_id": rule_id, "revision": entry["revision"],
            "text": entry["text"], **extra}


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
        "point_names": _join(point_names),
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
            ruler_house_text=_house_label(evidence.get("ruler_house")),
        )
    # chart_ruler_placement 的证据直接来自 layout.core.chart_ruler，字段名是 point_name/sign_name/house。
    if signal.get("signal_type") == "chart_ruler_placement":
        values.update(
            ruler_name=evidence.get("point_name"),
            ruler_sign_name=evidence.get("sign_name") or sign_names.get(evidence.get("sign_id")),
            ruler_house_text=_house_label(evidence.get("house")),
        )
    return values


def _fact_index(facts):
    """把逐点位事实整理成按点位索引的字典，供卡片组合使用。"""
    sign_facts, house_facts = {}, {}
    for fact in facts:
        evidence = fact.get("evidence") or {}
        if fact.get("type") == "point_in_sign" and evidence.get("point_id"):
            sign_facts[evidence["point_id"]] = fact
        elif fact.get("type") == "point_in_house" and evidence.get("point_id"):
            house_facts[evidence["point_id"]] = fact
    retrograde = {point_id for fact in facts if fact.get("type") == "retrograde_point"
                  for point_id in fact.get("point_ids") or []}
    return sign_facts, house_facts, retrograde


def _point_names(facts):
    names = {}
    for fact in facts:
        evidence = fact.get("evidence") or {}
        if fact.get("type") == "point_in_sign" and evidence.get("point_id"):
            names[evidence["point_id"]] = evidence.get("point_name") or evidence["point_id"]
    return names


def _points(layout, facts, templates, sign_names, signals, uncovered):
    sign_facts, house_facts, retrograde = _fact_index(facts)
    order = [point_id for point_id in POINT_ORDER if point_id in sign_facts]
    order += [point_id for point_id in sign_facts if point_id not in order]
    entries = []
    for point_id in order:
        sign_evidence = sign_facts[point_id].get("evidence") or {}
        house_evidence = (house_facts.get(point_id) or {}).get("evidence") or {}
        sign_id = sign_evidence.get("sign_id")
        house = house_evidence.get("house")
        point_name = sign_evidence.get("point_name") or point_id
        core = templates["planet_core"].get(point_id)
        style = templates["sign_style"].get(sign_id)
        field = templates["house_field"].get(str(house)) if house else None
        if core is None:
            uncovered.append({"signal_id": f"point_card:{point_id}", "rule_id": None,
                              "reason": "no_template"})
            continue
        override_both = templates["overrides"]["point_sign_house"].get(f"{point_id}:{sign_id}:{house}")
        override_sign = templates["overrides"]["point_sign"].get(f"{point_id}:{sign_id}")
        override_house = templates["overrides"]["point_house"].get(f"{point_id}:{house}")
        blocks = [_block("planet_core", f"template.planet_core.{point_id}", core, title=core["title"])]
        applied = []
        if override_both is not None:
            blocks.append(_block("point_sign_house",
                                 f"override.point_sign_house.{point_id}:{sign_id}:{house}", override_both))
            applied.append("point_sign_house")
        else:
            if override_sign is not None:
                blocks.append(_block("point_sign", f"override.point_sign.{point_id}:{sign_id}", override_sign))
                applied.append("point_sign")
            elif style is not None:
                blocks.append(_block("sign_style", f"template.sign_style.{sign_id}", style, lead=style["lead"]))
            else:
                uncovered.append({"signal_id": f"sign_style:{sign_id}", "rule_id": None,
                                  "reason": "no_template"})
            if override_house is not None:
                blocks.append(_block("point_house", f"override.point_house.{point_id}:{house}", override_house))
                applied.append("point_house")
            elif field is not None:
                blocks.append(_block("house_field", f"template.house_field.{house}", field, lead=field["lead"]))
            elif house:
                uncovered.append({"signal_id": f"house_field:{house}", "rule_id": None,
                                  "reason": "no_template"})
        sign_name = sign_evidence.get("sign_name") or sign_names.get(sign_id)
        summary_values = {
            "point_name": point_name,
            "sign_name": sign_name,
            "house_label": _house_label(house),
            "sign_short": (override_both or override_sign or style or {}).get("short") or sign_name,
            "house_short": (override_both or override_house or field or {}).get("short") or _house_label(house),
        }
        related = [signal["signal_id"] for signal in signals
                   if point_id in (signal.get("point_ids") or [])]
        markers = [signal["signal_id"] for signal in signals
                   if point_id in (signal.get("point_ids") or [])
                   and signal.get("signal_type") in MARKER_SIGNAL_TYPES]
        entries.append({
            "point_id": point_id,
            "point_name": point_name,
            "sign_id": sign_id,
            "sign_name": sign_name,
            "house": house,
            "retrograde": point_id in retrograde,
            "title": f"{point_name} · {sign_name} · {_house_label(house)}" if house
                     else f"{point_name} · {sign_name}",
            "summary": _render(templates["summary"]["point"], summary_values),
            "blocks": blocks,
            "overrides": applied,
            "markers": markers,
            "signal_ids": related,
            "evidence": {
                "longitude": sign_evidence.get("longitude"),
                "degree_in_sign": sign_evidence.get("degree_in_sign"),
                "house": house,
                "house_cusp": house_evidence.get("house_cusp"),
                "house_system": house_evidence.get("house_system"),
            },
        })
    return entries


def _houses(layout, facts, templates, sign_names, signals, uncovered):
    _, house_facts, _ = _fact_index(facts)
    rulers = {}
    for fact in facts:
        evidence = fact.get("evidence") or {}
        if fact.get("type") == "house_ruler_placement" and evidence.get("house"):
            rulers[evidence["house"]] = evidence
    occupied = {}
    for point_id, fact in house_facts.items():
        occupied.setdefault((fact.get("evidence") or {}).get("house"), []).append(point_id)
    point_names = _point_names(facts)
    entries = []
    for item in ((layout.get("house_occupancy") or {}).get("items")) or []:
        number = item.get("house")
        sign_id = item.get("sign_id")
        sign_name = item.get("sign_name") or sign_names.get(sign_id)
        field = templates["house_field"].get(str(number))
        ruler_entry = templates["house_ruler"].get(str(number))
        ruler = rulers.get(number) or {}
        planet_ids = [point_id for point_id in item.get("point_ids") or []]
        virtual_ids = [point_id for point_id in occupied.get(number, [])
                       if point_id not in DISTRIBUTION_POINTS and point_id not in planet_ids]
        blocks = []
        if field is not None:
            blocks.append(_block("house_field", f"template.house_field.{number}", field, lead=field["lead"]))
        if ruler_entry is not None:
            blocks.append({
                "slot": "house_ruler",
                "rule_id": f"template.house_ruler.{number}",
                "revision": ruler_entry["revision"],
                "text": _render(ruler_entry["text"], {
                    "sign_name": sign_name,
                    "ruler_name": ruler.get("ruler_name"),
                    "ruler_sign_name": ruler.get("ruler_sign_name"),
                    "ruler_house_text": _house_label(ruler.get("ruler_house")),
                }),
            })
        values = {"house_label": _house_label(number), "sign_name": sign_name}
        planet_names = _join(point_names.get(point_id, point_id) for point_id in planet_ids)
        virtual_names = _join(point_names.get(point_id, point_id) for point_id in virtual_ids)
        if planet_ids and virtual_ids:
            summary = _render(templates["summary"]["house_planets_virtual"],
                              {**values, "point_names": planet_names, "virtual_names": virtual_names})
        elif planet_ids:
            summary = _render(templates["summary"]["house_planets"],
                              {**values, "point_names": planet_names})
        elif virtual_ids:
            summary = _render(templates["summary"]["house_virtual_only"],
                              {**values, "point_names": virtual_names})
        else:
            summary = _render(templates["summary"]["house_empty"], values)
        related = [signal["signal_id"] for signal in signals
                   if (signal.get("evidence") or {}).get("house") == number]
        entries.append({
            "house": number,
            "sign_id": sign_id,
            "sign_name": sign_name,
            "cusp": item.get("cusp"),
            "title": f"第{number}宫 · {sign_name}",
            "summary": summary,
            "point_ids": planet_ids + virtual_ids,
            "virtual_point_ids": virtual_ids,
            "empty_of_planets": not planet_ids,
            "ruler": {
                "point_id": ruler.get("ruler_id"),
                "point_name": ruler.get("ruler_name"),
                "sign_id": ruler.get("ruler_sign_id"),
                "sign_name": ruler.get("ruler_sign_name"),
                "house": ruler.get("ruler_house"),
                "ruler_system": ruler.get("ruler_system"),
            },
            "blocks": blocks,
            "signal_ids": related,
            "evidence": {"cusp": item.get("cusp"), "house_system": ruler.get("house_system")},
        })
    return entries


def _aspects(layout, templates, point_names, signals, uncovered):
    tight = {signal["signal_id"] for signal in signals if signal.get("signal_type") == "tight_aspect"}
    entries = []
    for item in ((layout.get("aspect_network") or {}).get("items")) or []:
        style = templates["aspect_style"].get(item.get("type"))
        source_id, target_id = item.get("source_id"), item.get("target_id")
        source_name = point_names.get(source_id, source_id)
        target_name = point_names.get(target_id, target_id)
        if style is None:
            uncovered.append({"signal_id": f"aspect_style:{item.get('type')}", "rule_id": None,
                              "reason": "no_template"})
            continue
        signal_id = f"tight_aspect:{source_id}:{target_id}:{item.get('type')}"
        phase = item.get("phase")
        entries.append({
            "source_id": source_id,
            "target_id": target_id,
            "source_name": source_name,
            "target_name": target_name,
            "type": item.get("type"),
            "label": style["label"],
            "tone": style["tone"],
            "orb": _round(item.get("orb"), 4),
            "phase": phase,
            "phase_label": templates["labels"]["phase"].get(phase, phase),
            "title": f"{source_name} {style['label']} {target_name}",
            "summary": _render(templates["summary"]["aspect"], {
                "pair_text": f"{source_name}与{target_name}",
                "aspect_label": style["label"],
                "orb": _round(item.get("orb"), 2),
                "phase_label": templates["labels"]["phase"].get(phase, phase),
                "aspect_short": style["short"],
            }),
            "tight": signal_id in tight,
            "blocks": [_block("aspect_style", f"template.aspect_style.{item.get('type')}", style,
                              label=style["label"], tone=style["tone"])],
            "signal_ids": [signal_id] if signal_id in tight else [],
            "evidence": {
                "orb": item.get("orb"),
                "phase": phase,
                "exact_angle": item.get("exact_angle"),
                "actual_angle": item.get("actual_angle"),
            },
        })
    return entries


def _core_item(slot, layout, templates, sign_names, signals):
    core = (layout or {}).get("core") or {}
    source = core.get("chart_ruler") if slot == "chart_ruler" else core.get(slot)
    if not source:
        return None
    fact = templates["core_text"][slot]
    if slot == "ascendant":
        sign_id = source.get("sign_id")
        sign_name = source.get("sign_name") or sign_names.get(sign_id)
        special = templates["ascendant_sign"].get(sign_id)
        values = {"sign_name": sign_name, "degree_in_sign": _round(source.get("degree_in_sign"), 2)}
        title = f"上升 {sign_name}"
        point_ids = ["ascendant"]
        blocks = [_block("ascendant_sign", f"template.ascendant_sign.{sign_id}", special)] if special else []
    elif slot in ("sun", "moon"):
        sign_id = source.get("sign_id")
        house = source.get("house")
        sign_name = source.get("sign_name") or sign_names.get(sign_id)
        special = templates[f"{slot}_sign"].get(sign_id)
        field = templates["house_field"].get(str(house)) if house else None
        values = {
            "point_name": source.get("point_name"),
            "sign_name": sign_name,
            "house_text": _house_label(house),
            "longitude": _round(source.get("longitude"), 4),
        }
        title = f"{source.get('point_name')} {sign_name} · {_house_label(house)}"
        point_ids = [source.get("point_id")]
        blocks = []
        if special is not None:
            blocks.append(_block(f"{slot}_sign", f"template.{slot}_sign.{sign_id}", special))
        if field is not None:
            blocks.append(_block("house_field", f"template.house_field.{house}", field, lead=field["lead"]))
    else:
        sign_id = (core.get("ascendant") or {}).get("sign_id")
        sign_name = (core.get("ascendant") or {}).get("sign_name") or sign_names.get(sign_id)
        ruler_entry = templates["house_ruler"].get("1")
        values = {
            "sign_name": sign_name,
            "ruler_name": source.get("point_name"),
            "ruler_sign_name": source.get("sign_name") or sign_names.get(source.get("sign_id")),
            "ruler_house_text": _house_label(source.get("house")),
        }
        title = f"命主星 {source.get('point_name')} · {_house_label(source.get('house'))}"
        point_ids = [source.get("point_id")]
        blocks = []
        if ruler_entry is not None:
            blocks.append({
                "slot": "house_ruler",
                "rule_id": "template.house_ruler.1",
                "revision": ruler_entry["revision"],
                "text": _render(ruler_entry["text"], values),
                "house": 1,
            })
    return {
        "slot": slot,
        "point_id": source.get("point_id"),
        "angle_id": source.get("angle_id"),
        "sign_id": source.get("sign_id"),
        "sign_name": source.get("sign_name") or sign_names.get(source.get("sign_id")),
        "house": source.get("house"),
        "title": title,
        "fact": _render(fact["text"], values),
        "summary": blocks[0]["text"] if blocks else _render(fact["text"], values),
        "blocks": blocks,
        "signal_ids": [signal["signal_id"] for signal in signals
                       if set(signal.get("point_ids") or []) & set(point_ids)],
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
    facts = [fact for fact in (analysis.get("facts") or []) if isinstance(fact, dict)]
    labels = templates["labels"]
    sign_names = _sign_names(layout)
    point_names = _point_names(facts)
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

    points = _points(layout, facts, templates, sign_names, signals, uncovered)
    houses = _houses(layout, facts, templates, sign_names, signals, uncovered)
    aspects = _aspects(layout, templates, point_names, signals, uncovered)

    highlights = {slot: _core_item(slot, layout, templates, sign_names, signals) for slot in CORE_SLOTS}
    emphasis = [signal["signal_id"] for signal in signals
                if signal.get("signal_type") in ("element_emphasis", "modality_emphasis")]
    return {
        "reading_version": "astro-natal-reading/1.0",
        "templates_version": templates["schema_version"],
        "ruler_system": analysis.get("ruler_system", layout.get("ruler_system", "modern")),
        "highlights": highlights,
        "layout": entries,
        "layout_stats": layout,
        "points": points,
        "houses": houses,
        "aspects": aspects,
        "distribution": {
            "element_counts": copy.deepcopy(layout.get("elements") or {}),
            "modality_counts": copy.deepcopy(layout.get("modalities") or {}),
            "emphasis": emphasis,
        },
        "coverage": {
            "facts": len(facts),
            "matched": len(signals),
            "rendered": len(entries) + core_skipped,
            "layout_lines": len(entries),
            "points": len(points),
            "houses": len(houses),
            "aspects": len(aspects),
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