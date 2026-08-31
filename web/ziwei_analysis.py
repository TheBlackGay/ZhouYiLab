import json
from pathlib import Path

from ziwei_pattern_engine import PatternConfigError, load_pattern_catalog, match_patterns


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SYMBOLISM_PATH = PROJECT_ROOT / "config" / "ziwei" / "symbolism_dictionary.json"
DEFAULT_CASES_PATH = PROJECT_ROOT / "config" / "ziwei" / "analysis_cases.json"
DEFAULT_SHEN_SHA_PATH = PROJECT_ROOT / "config" / "ziwei" / "shen_sha_dictionary.json"
DEFAULT_PATTERN_DIR = PROJECT_ROOT / "config" / "ziwei" / "patterns"

STAR_FIELDS = (
    ("zhu_xing", "major"),
    ("fu_xing_detail", "benefic"),
    ("sha_xing_detail", "malefic"),
    ("za_yao_detail", "miscellaneous"),
)
RELATION_OFFSETS = (("self", 0), ("triad", 4), ("triad", 8), ("opposite", 6))
SUPPORTED_FRAGMENT_TYPES = (
    "palace_symbolism",
    "star_in_palace",
    "four_directions",
    "transformation",
    "combination",
    "pattern",
    "shen_sha_in_palace",
    "unconfigured_star",
)

SECTION_KEYS = (
    "palace_symbolism", "self_stars", "triad_stars", "opposite_stars",
    "transformations", "palace_rules", "combinations", "patterns", "shen_sha",
    "unconfigured",
)
SHEN_SHA_SYSTEMS = (
    "chang_sheng_12", "bo_shi_12", "sui_qian_12", "jiang_qian_12",
)


class AnalysisConfigError(ValueError):
    pass


class AnalysisRequestError(ValueError):
    pass


def _read_json(path):
    try:
        with Path(path).open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise AnalysisConfigError(f"无法读取分析配置 {path}: {error}") from error


def load_analysis_resources(
    symbolism_path=DEFAULT_SYMBOLISM_PATH,
    cases_path=DEFAULT_CASES_PATH,
    shen_sha_path=DEFAULT_SHEN_SHA_PATH,
    pattern_dir=DEFAULT_PATTERN_DIR,
):
    symbolism = _read_json(symbolism_path)
    cases = _read_json(cases_path)
    shen_sha = _read_json(shen_sha_path)
    _validate_symbolism(symbolism)
    _validate_cases(cases, Path(symbolism_path), symbolism["schema_version"])
    _validate_shen_sha(shen_sha)
    try:
        patterns = load_pattern_catalog(
            pattern_dir, {entry["name"] for entry in symbolism.get("stars", [])}
        )
    except PatternConfigError as error:
        raise AnalysisConfigError(str(error)) from error
    return symbolism, cases, shen_sha, patterns


def _validate_symbolism(symbolism):
    if not symbolism.get("schema_version") or not symbolism.get("dictionary_version"):
        raise AnalysisConfigError("象义词典缺少 schema_version 或 dictionary_version")
    entries = [*symbolism.get("palaces", []), *symbolism.get("stars", [])]
    entry_ids = set()
    entry_names = set()
    for entry in entries:
        entry_id = entry.get("id")
        entry_name = entry.get("name")
        if not entry_id or not entry_name:
            raise AnalysisConfigError("象义条目缺少 id 或 name")
        if not isinstance(entry.get("entry_revision"), int) or entry["entry_revision"] < 1:
            raise AnalysisConfigError(f"{entry_id} 的 entry_revision 必须是正整数")
        if entry_id in entry_ids or entry_name in entry_names:
            raise AnalysisConfigError(f"象义条目重复: {entry_id}/{entry_name}")
        entry_ids.add(entry_id)
        entry_names.add(entry_name)

        original_ids = set()
        for original in entry.get("original_definitions", []):
            if not all(original.get(field) for field in ("id", "concept", "definition")):
                raise AnalysisConfigError(f"{entry_id} 存在不完整的原始定义")
            if original["id"] in original_ids:
                raise AnalysisConfigError(f"{entry_id} 原始定义 ID 重复: {original['id']}")
            original_ids.add(original["id"])
        if not original_ids:
            raise AnalysisConfigError(f"{entry_id} 缺少原始定义")

        derived_ids = set()
        for derived in entry.get("derived_definitions", []):
            if not all(derived.get(field) for field in (
                "id", "scenario", "meaning", "derived_from", "boundary"
            )):
                raise AnalysisConfigError(f"{entry_id} 存在不完整的衍生定义")
            if derived["id"] in derived_ids:
                raise AnalysisConfigError(f"{entry_id} 衍生定义 ID 重复: {derived['id']}")
            derived_ids.add(derived["id"])
            unknown = set(derived["derived_from"]) - original_ids
            if unknown:
                raise AnalysisConfigError(
                    f"{derived['id']} 引用了不存在的原始定义: {sorted(unknown)}"
                )

    if len(symbolism.get("palaces", [])) != 12:
        raise AnalysisConfigError("象义词典必须配置完整十二宫")
    coverage = symbolism.get("coverage", {})
    if coverage.get("palaces", {}).get("configured") != len(symbolism["palaces"]):
        raise AnalysisConfigError("象义词典的宫位覆盖数量与实际条目不一致")
    configured_stars = sum(
        coverage.get(group, {}).get("configured", 0)
        for group in ("major_stars", "core_auxiliary_stars", "miscellaneous_stars")
    )
    if configured_stars != len(symbolism.get("stars", [])):
        raise AnalysisConfigError("象义词典的星曜覆盖数量与实际条目不一致")


def _validate_shen_sha(dictionary):
    if not dictionary.get("schema_version") or not dictionary.get("dictionary_version"):
        raise AnalysisConfigError("十二神词典缺少 schema_version 或 dictionary_version")
    systems = dictionary.get("systems", {})
    if set(systems) != set(SHEN_SHA_SYSTEMS):
        raise AnalysisConfigError("十二神词典必须包含长生、博士、岁前、将前四套系统")
    for system_id, system in systems.items():
        entries = system.get("entries", {})
        if len(entries) != 12:
            raise AnalysisConfigError(f"{system_id} 必须配置完整十二神")
        for name, entry in entries.items():
            if not entry.get("id") or not entry.get("key_effect") or not entry.get("boundary"):
                raise AnalysisConfigError(f"{system_id}.{name} 配置不完整")


def _version_tuple(value):
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError) as error:
        raise AnalysisConfigError(f"无效的配置版本号: {value}") from error


def _validate_cases(cases, symbolism_path, symbolism_schema_version):
    if not cases.get("schema_version") or not cases.get("ruleset"):
        raise AnalysisConfigError("案例规则缺少 schema_version 或 ruleset")
    reference = cases.get("symbolism_dictionary", {})
    configured_path = reference.get("path")
    if not configured_path:
        raise AnalysisConfigError("案例规则未声明 symbolism_dictionary.path")
    expected = (PROJECT_ROOT / configured_path).resolve()
    if expected != symbolism_path.resolve():
        raise AnalysisConfigError("案例规则引用的象义词典与实际加载路径不一致")
    minimum_version = reference.get("minimum_schema_version")
    if minimum_version and _version_tuple(symbolism_schema_version) < _version_tuple(minimum_version):
        raise AnalysisConfigError("象义词典 schema_version 不满足案例规则要求")

    case_ids = set()
    for case in cases.get("cases", []):
        case_id = case.get("id")
        if not case_id or case_id in case_ids:
            raise AnalysisConfigError(f"案例规则 ID 缺失或重复: {case_id}")
        case_ids.add(case_id)


def analyze_natal_chart(
    chart, scope=None, symbolism=None, cases=None, shen_sha=None, patterns=None
):
    if symbolism is None or cases is None or shen_sha is None or patterns is None:
        loaded_symbolism, loaded_cases, loaded_shen_sha, loaded_patterns = load_analysis_resources()
        symbolism = symbolism or loaded_symbolism
        cases = cases or loaded_cases
        shen_sha = shen_sha or loaded_shen_sha
        patterns = patterns or loaded_patterns
    scope = scope or {}
    layers = scope.get("layers", ["natal"])
    if layers != ["natal"] and set(layers) != {"natal"}:
        raise AnalysisRequestError("analysis 1.4.1 仅支持 natal 本命层")

    palaces = chart.get("palaces")
    if not isinstance(palaces, list) or len(palaces) != 12:
        raise AnalysisRequestError("chart.palaces 必须包含十二宫")

    palace_entries = {entry["name"]: entry for entry in symbolism["palaces"]}
    star_entries = {entry["name"]: entry for entry in symbolism["stars"]}
    chart_names = [palace.get("name") for palace in palaces]
    if len(set(chart_names)) != 12 or set(chart_names) != set(palace_entries):
        raise AnalysisRequestError("chart.palaces 宫名必须与象义词典中的十二宫完整对应")

    focus_names = scope.get("focus_palaces", chart_names)
    if not isinstance(focus_names, list) or not focus_names:
        raise AnalysisRequestError("scope.focus_palaces 必须是非空数组")
    if len(focus_names) != len(set(focus_names)):
        raise AnalysisRequestError("scope.focus_palaces 不能包含重复宫位")
    unknown_focus = set(focus_names) - set(chart_names)
    if unknown_focus:
        raise AnalysisRequestError(f"不支持的焦点宫: {sorted(unknown_focus)}")

    scenarios = scope.get("scenarios")
    if scenarios is not None and (
        not isinstance(scenarios, list) or not scenarios
        or not all(isinstance(item, str) and item for item in scenarios)
    ):
        raise AnalysisRequestError("scope.scenarios 必须是非空字符串数组")
    scenario_set = set(scenarios) if scenarios else None

    palace_results = []
    all_fragments = []
    for focus_name in focus_names:
        focus_index = chart_names.index(focus_name)
        result = _analyze_palace(
            palaces, focus_index, palace_entries[focus_name], star_entries,
            cases, patterns, shen_sha, scenario_set
        )
        palace_results.append(result)
        all_fragments.extend(result["fragments"])

    fragment_ids = {fragment["fragment_id"] for fragment in all_fragments}
    ai_palaces = []
    for palace in palace_results:
        summary = palace["signal_summary"]
        evidence_ids = summary["core"] + summary["supporting"] + summary["tensions"]
        ai_palaces.append({
            "palace": palace["palace"],
            "effect_subject": palace["fragments"][0]["effect_subject"],
            "core_signal_ids": summary["core"],
            "supporting_signal_ids": summary["supporting"],
            "tension_signal_ids": summary["tensions"],
            "evidence_fragment_ids": list(dict.fromkeys(evidence_ids)),
        })
    assert all(
        fragment_id in fragment_ids
        for palace in ai_palaces
        for key in ("core_signal_ids", "supporting_signal_ids", "tension_signal_ids", "evidence_fragment_ids")
        for fragment_id in palace[key]
    )
    return {
        "analysis_version": "1.4.1",
        "layer": "natal",
        "scope": {
            "layers": ["natal"],
            "focus_palaces": focus_names,
            "scenarios": scenarios or [],
            "scenario_mode": "filtered" if scenario_set else "all_candidates",
        },
        "config": {
            "symbolism_schema_version": symbolism["schema_version"],
            "symbolism_dictionary_version": symbolism["dictionary_version"],
            "analysis_rules_schema_version": cases["schema_version"],
            "analysis_ruleset": cases["ruleset"],
            "pattern_schema_version": patterns["schema_version"],
            "pattern_dictionary_version": patterns["dictionary_version"],
            "pattern_ruleset": patterns["ruleset"],
            "pattern_count": len(patterns["patterns"]),
            "shen_sha_schema_version": shen_sha["schema_version"],
            "shen_sha_dictionary_version": shen_sha["dictionary_version"],
        },
        "fragment_contract": {
            "types": list(SUPPORTED_FRAGMENT_TYPES),
            "principle": "程序输出可追溯分析碎片；AI 只能组织表达，不得改写命盘事实。",
        },
        "palaces": palace_results,
        "fragments": all_fragments,
        "pattern_engine": {
            "engine": "declarative_rule_engine",
            "authoritative_for_structured_analysis": True,
            "legacy_cpp_ge_ju": {
                "present": bool(chart.get("ge_ju")),
                "authoritative_for_structured_analysis": False,
                "reason": "旧 C++ 格局结果不包含逐宫归属和完整匹配证据，仅保留接口兼容。",
            },
        },
        "ai_packet": {
            "schema_version": "1.0.0",
            "input_kind": "ziwei_natal_structured_signals",
            "facts_are_authoritative": True,
            "palaces": ai_palaces,
            "allowed_actions": ["summarize", "connect_scenarios", "simplify_language"],
            "forbidden_actions": [
                "recalculate_chart", "change_palace", "change_star",
                "invent_pattern", "merge_distinct_shen_sha_systems",
            ],
        },
        "ai_context": {
            "input_kind": "ziwei_analysis_fragments",
            "facts_are_authoritative": True,
            "allowed_actions": ["summarize", "connect_scenarios", "simplify_language"],
            "forbidden_actions": ["recalculate_chart", "change_palace", "change_star", "invent_pattern"],
            "fragment_ids": [fragment["fragment_id"] for fragment in all_fragments],
        },
    }


def _analyze_palace(
    palaces, focus_index, palace_entry, star_entries, cases, patterns, shen_sha, scenarios
):
    focus = palaces[focus_index]
    directions = []
    for relation, offset in RELATION_OFFSETS:
        physical_index = (focus_index + offset) % 12
        physical = palaces[physical_index]
        directions.append({
            "relation": relation,
            "palace_index": physical_index,
            "palace": physical["name"],
            "gan_zhi": physical.get("gan_zhi"),
        })

    fragments = [_palace_fragment(focus_index, focus, palace_entry, scenarios)]
    configured_star_count = 0
    unconfigured_stars = []
    for direction in directions:
        physical = palaces[direction["palace_index"]]
        for star in _palace_stars(physical):
            star_entry = star_entries.get(star["name"])
            if not star_entry:
                unconfigured = {
                    "name": star["name"],
                    "physical_palace": physical["name"],
                    "relation": direction["relation"],
                }
                unconfigured_stars.append(unconfigured)
                fragments.append(_unconfigured_fragment(
                    focus_index, focus, palace_entry, direction, star
                ))
                continue
            configured_star_count += 1
            fragments.append(_star_fragment(
                focus_index, focus, palace_entry, direction, star, star_entry, scenarios
            ))
            if star.get("si_hua"):
                fragments.append(_transformation_fragment(
                    focus_index, focus, palace_entry, direction, star, star_entry
                ))

    for system_id in SHEN_SHA_SYSTEMS:
        name = focus.get("shen_sha", {}).get(system_id)
        if name:
            fragments.append(_shen_sha_fragment(
                focus_index, focus, palace_entry, system_id,
                shen_sha["systems"][system_id], name,
            ))

    context = _rule_context(palaces, focus_index, palace_entry, directions)
    fragments.extend(_rule_fragments(cases, context))
    fragments.extend(_pattern_fragments(patterns, context, palace_entry))
    sections = _group_sections(fragments)
    signal_summary = _build_signal_summary(fragments, sections, unconfigured_stars)
    return {
        "layer": "natal",
        "palace": focus["name"],
        "palace_index": focus_index,
        "gan_zhi": focus.get("gan_zhi"),
        "four_directions": {
            "self": directions[0],
            "triads": directions[1:3],
            "opposite": directions[3],
        },
        "facts": {
            "is_ming_palace": focus.get("is_ming_palace", False),
            "is_body_palace": focus.get("is_body_palace", False),
            "primary_stars": [star["name"] for star in _palace_stars(focus)
                              if star["source_field"] == "zhu_xing"],
            "configured_four_direction_stars": configured_star_count,
            "unconfigured_stars": unconfigured_stars,
        },
        "sections": sections,
        "signal_summary": signal_summary,
        "fragments": fragments,
    }


def _selected_derived(entry, scenarios):
    values = entry.get("derived_definitions", [])
    if scenarios is None:
        return values
    return [value for value in values if value["scenario"] in scenarios]


def _palace_fragment(focus_index, focus, entry, scenarios):
    return {
        "fragment_id": f"natal.{entry['id']}.palace_symbolism",
        "type": "palace_symbolism",
        "source_layer": "natal",
        "effect_palace": focus["name"],
        "effect_subject": [item["concept"] for item in entry["original_definitions"]],
        "facts": {
            "palace_index": focus_index,
            "palace": focus["name"],
            "gan_zhi": focus.get("gan_zhi"),
        },
        "original_meanings": entry["original_definitions"],
        "derived_meanings": _selected_derived(entry, scenarios),
        "modifiers": [],
        "evidence": [{
            "source": "symbolism_dictionary",
            "entry_id": entry["id"],
            "entry_revision": entry["entry_revision"],
        }],
        "confidence": {"level": "baseline", "reason": "完整匹配宫位象义配置"},
    }


def _star_fragment(focus_index, focus, palace_entry, direction, star, entry, scenarios):
    relation = direction["relation"]
    fragment_type = "star_in_palace" if relation == "self" else "four_directions"
    modifiers = []
    if star.get("liang_du"):
        modifiers.append({"type": "brightness", "value": star["liang_du"]})
    related_fragment_ids = []
    if star.get("si_hua"):
        related_fragment_ids.append(_transformation_fragment_id(
            palace_entry, direction, star, entry
        ))
    return {
        "fragment_id": (
            f"natal.{palace_entry['id']}.{fragment_type}."
            f"{relation}.{entry['id']}.{direction['palace_index']}"
        ),
        "type": fragment_type,
        "source_layer": "natal",
        "effect_palace": focus["name"],
        "effect_subject": [item["concept"] for item in palace_entry["original_definitions"]],
        "facts": {
            "focus_palace_index": focus_index,
            "focus_palace": focus["name"],
            "physical_palace_index": direction["palace_index"],
            "physical_palace": direction["palace"],
            "relation": relation,
            "star": star["name"],
            "star_category": entry.get("category"),
            "brightness": star.get("liang_du"),
            "transformation": star.get("si_hua"),
        },
        "palace_original_meanings": palace_entry["original_definitions"],
        "star_original_meanings": entry["original_definitions"],
        "star_derived_meanings": _selected_derived(entry, scenarios),
        "meaning_formula": "焦点宫作用对象 × 星曜作用机制 × 宫位关系 × 修正因素",
        "modifiers": modifiers,
        "related_fragment_ids": related_fragment_ids,
        "evidence": [
            {"source": "chart", "path": f"palaces[{direction['palace_index']}]", "relation": relation},
            {"source": "symbolism_dictionary", "entry_id": palace_entry["id"],
             "entry_revision": palace_entry["entry_revision"]},
            {"source": "symbolism_dictionary", "entry_id": entry["id"],
             "entry_revision": entry["entry_revision"]},
        ],
        "confidence": {"level": "baseline", "reason": "命盘事实与宫位、星曜象义均可追溯"},
    }


def _transformation_fragment(focus_index, focus, palace_entry, direction, star, star_entry):
    return {
        "fragment_id": _transformation_fragment_id(palace_entry, direction, star, star_entry),
        "type": "transformation",
        "source_layer": "natal",
        "effect_palace": focus["name"],
        "effect_subject": [item["concept"] for item in palace_entry["original_definitions"]],
        "facts": {
            "focus_palace_index": focus_index,
            "focus_palace": focus["name"],
            "physical_palace_index": direction["palace_index"],
            "physical_palace": direction["palace"],
            "relation": direction["relation"],
            "star": star["name"],
            "transformation": star["si_hua"],
        },
        "modifiers": [{"type": "transformation", "value": star["si_hua"]}],
        "boundary": "四化修正星曜的作用方式，不改变星曜实际落宫和焦点宫归属。",
        "evidence": [{
            "source": "chart",
            "path": f"palaces[{direction['palace_index']}].{star['source_field']}",
            "source_layer": "natal",
        }],
        "confidence": {"level": "fact", "reason": "直接来自本命盘星曜四化字段"},
    }


def _transformation_fragment_id(palace_entry, direction, star, star_entry):
    return (
        f"natal.{palace_entry['id']}.transformation."
        f"{star_entry['id']}.{direction['palace_index']}.{star['si_hua']}"
    )


def _shen_sha_fragment(focus_index, focus, palace_entry, system_id, system, name):
    entry = system["entries"].get(name)
    if entry is None:
        raise AnalysisConfigError(f"十二神词典 {system_id} 缺少命盘值: {name}")
    return {
        "fragment_id": f"natal.{palace_entry['id']}.shen_sha.{system_id}.{entry['id']}",
        "type": "shen_sha_in_palace",
        "source_layer": "natal",
        "effect_palace": focus["name"],
        "effect_subject": [item["concept"] for item in palace_entry["original_definitions"]],
        "facts": {
            "focus_palace_index": focus_index,
            "focus_palace": focus["name"],
            "physical_palace_index": focus_index,
            "physical_palace": focus["name"],
            "relation": "self",
            "system": system_id,
            "system_label": system["label"],
            "nature": system["nature"],
            "shen_sha": name,
        },
        "summary": entry["key_effect"],
        "boundary": entry["boundary"],
        "modifiers": [],
        "evidence": [
            {"source": "chart", "path": f"palaces[{focus_index}].shen_sha.{system_id}"},
            {"source": "shen_sha_dictionary", "system": system_id, "entry_id": entry["id"]},
        ],
        "confidence": {"level": "baseline", "reason": "命盘十二神事实与独立系统词典均可追溯"},
    }


def _unconfigured_fragment(focus_index, focus, palace_entry, direction, star):
    return {
        "fragment_id": (
            f"natal.{palace_entry['id']}.unconfigured.{direction['relation']}."
            f"{direction['palace_index']}.{star['source_field']}.{star['name']}"
        ),
        "type": "unconfigured_star",
        "source_layer": "natal",
        "effect_palace": focus["name"],
        "effect_subject": [item["concept"] for item in palace_entry["original_definitions"]],
        "facts": {
            "focus_palace_index": focus_index,
            "focus_palace": focus["name"],
            "physical_palace_index": direction["palace_index"],
            "physical_palace": direction["palace"],
            "relation": direction["relation"],
            "star": star["name"],
            "source_field": star["source_field"],
        },
        "summary": "命盘中存在该星曜，但静态象义尚未校订，因此不进入推理结论。",
        "modifiers": [],
        "evidence": [{
            "source": "chart",
            "path": f"palaces[{direction['palace_index']}].{star['source_field']}",
        }],
        "confidence": {"level": "unconfigured", "reason": "仅保留命盘事实，不生成象义"},
    }


def _group_sections(fragments):
    sections = {key: [] for key in SECTION_KEYS}
    for fragment in fragments:
        fragment_type = fragment["type"]
        relation = fragment.get("facts", {}).get("relation")
        if fragment_type == "palace_symbolism":
            section = "palace_symbolism"
        elif fragment_type in ("star_in_palace", "four_directions") and fragment.get("facts", {}).get("star"):
            section = {"self": "self_stars", "triad": "triad_stars", "opposite": "opposite_stars"}[relation]
        elif fragment_type == "transformation":
            section = "transformations"
        elif fragment_type == "four_directions":
            section = "palace_rules"
        elif fragment_type == "combination":
            section = "combinations"
        elif fragment_type == "pattern":
            section = "patterns"
        elif fragment_type == "shen_sha_in_palace":
            section = "shen_sha"
        elif fragment_type == "unconfigured_star":
            section = "unconfigured"
        else:
            continue
        sections[section].append(fragment["fragment_id"])
    return sections


def _build_signal_summary(fragments, sections, unconfigured_stars):
    core = []
    supporting = []
    tensions = []
    for fragment in fragments:
        fragment_id = fragment["fragment_id"]
        facts = fragment.get("facts", {})
        fragment_type = fragment["type"]
        category = facts.get("star_category")
        relation = facts.get("relation")
        if fragment_type in ("combination", "pattern"):
            core.append(fragment_id)
            if facts.get("status") in ("weakened", "broken"):
                tensions.append(fragment_id)
        elif fragment_type in ("star_in_palace", "four_directions"):
            if relation == "self" and category == "major":
                core.append(fragment_id)
            else:
                supporting.append(fragment_id)
            if category == "malefic":
                tensions.append(fragment_id)
        elif fragment_type == "transformation":
            (core if relation == "self" else supporting).append(fragment_id)
            if facts.get("transformation") == "化忌":
                tensions.append(fragment_id)
        elif fragment_type == "shen_sha_in_palace":
            supporting.append(fragment_id)
    return {
        "core": list(dict.fromkeys(core)),
        "supporting": list(dict.fromkeys(supporting)),
        "tensions": list(dict.fromkeys(tensions)),
        "coverage": {
            "configured_fragments": sum(
                len(sections[key]) for key in SECTION_KEYS if key != "unconfigured"
            ),
            "unconfigured_occurrences": len(unconfigured_stars),
            "has_unconfigured_content": bool(unconfigured_stars),
        },
    }


def _palace_stars(palace):
    result = []
    for field, fallback_category in STAR_FIELDS:
        values = palace.get(field, [])
        if not isinstance(values, list):
            continue
        for value in values:
            star = {"name": value} if isinstance(value, str) else dict(value)
            if not star.get("name"):
                continue
            star["source_field"] = field
            star["fallback_category"] = fallback_category
            result.append(star)
    return result


def _rule_context(palaces, focus_index, palace_entry, directions):
    def stars_at(index):
        return _palace_stars(palaces[index])

    def pattern_stars(index, relation):
        return [{
            "name": star["name"],
            "category": star["fallback_category"],
            "brightness": star.get("liang_du"),
            "transformation": star.get("si_hua"),
            "source_layer": "natal",
            "physical_palace": palaces[index]["name"],
            "physical_palace_index": index,
            "relation": relation,
        } for star in stars_at(index)]

    primary = [star for star in stars_at(focus_index) if star["source_field"] == "zhu_xing"]
    direction_stars = []
    for direction in directions:
        direction_stars.extend(stars_at(direction["palace_index"]))
    transformations = [star["si_hua"] for star in direction_stars if star.get("si_hua")]
    left_index = (focus_index - 1) % 12
    right_index = (focus_index + 1) % 12
    opposite_index = (focus_index + 6) % 12
    triad_indices = [
        direction["palace_index"] for direction in directions
        if direction["relation"] == "triad"
    ]
    opposite_primary = [
        star for star in stars_at(opposite_index) if star["source_field"] == "zhu_xing"
    ]
    return {
        "layer": {"id": "natal", "name": "本命"},
        "focus": {
            "name": palaces[focus_index]["name"],
            "index": focus_index,
            "primary_stars": primary,
            "primary_star_names": [star["name"] for star in primary],
            "entry": palace_entry,
            "effect_subject": [
                item["concept"] for item in palace_entry["original_definitions"]
            ],
            "relation": "self",
        },
        "opposite": {
            "name": palaces[opposite_index]["name"],
            "index": opposite_index,
            "primary_stars": opposite_primary,
            "primary_star_names": [star["name"] for star in opposite_primary],
        },
        "four_directions": {
            "all_stars": direction_stars,
            "all_star_names": [star["name"] for star in direction_stars],
            "transformations": transformations,
            "transformation_source_layers": ["natal"] * len(transformations),
        },
        "adjacent": {
            "left": {"all_star_names": [star["name"] for star in stars_at(left_index)]},
            "right": {"all_star_names": [star["name"] for star in stars_at(right_index)]},
        },
        "scopes": {
            "self": {"stars": pattern_stars(focus_index, "self")},
            "triads": {"stars": [
                star for index in triad_indices for star in pattern_stars(index, "triad")
            ]},
            "opposite": {"stars": pattern_stars(opposite_index, "opposite")},
            "four_directions": {"stars": [
                star
                for direction in directions
                for star in pattern_stars(
                    direction["palace_index"], direction["relation"]
                )
            ]},
            "adjacent_left": {"stars": pattern_stars(left_index, "adjacent_left")},
            "adjacent_right": {"stars": pattern_stars(right_index, "adjacent_right")},
        },
    }


def _pattern_fragments(catalog, context, palace_entry):
    fragments = []
    for matched in match_patterns(catalog, context):
        fragments.append({
            "fragment_id": (
                f"natal.{palace_entry['id']}.{matched['pattern_id']}"
            ),
            "type": "pattern",
            "source_layer": "natal",
            "effect_palace": matched["effect_palace"],
            "effect_subject": matched["effect_subject"],
            "facts": {
                "rule_id": matched["pattern_id"],
                "rule_name": matched["name"],
                "pattern_category": matched["category"],
                "school": matched["school"],
                "status": matched["status"],
                "nature": matched["nature"],
                "focus_palace": matched["focus_palace"],
            },
            "summary": matched["summary"],
            "interpretation_template": matched["interpretation_template"],
            "condition_trace": {
                "required": matched["required_trace"],
                "tendency": matched["tendency_trace"],
                "matched_conditions": matched["matched_conditions"],
                "missing_conditions": matched["missing_conditions"],
            },
            "modifiers": {
                "enhancers": matched["enhancers"],
                "weakeners": matched["weakeners"],
                "breakers": matched["breakers"],
            },
            "evidence": [{
                "source": "pattern_catalog",
                "path": matched["source_file"],
                "rule_id": matched["pattern_id"],
                "rule_revision": matched["pattern_revision"],
            }],
            "confidence": {
                "level": "rule_match",
                "reason": (
                    "显式倾向条件已匹配"
                    if matched["status"] == "tendency"
                    else "必要条件已匹配，状态由增强、减弱和破格条件确定"
                ),
            },
        })
    return fragments


PATH_ALIASES = {
    "$focus.primary_stars": ("focus", "primary_stars"),
    "$focus.primary_stars.names": ("focus", "primary_star_names"),
    "$opposite.primary_stars": ("opposite", "primary_stars"),
    "$opposite.primary_stars.names": ("opposite", "primary_star_names"),
    "$four_directions.all_stars.names": ("four_directions", "all_star_names"),
    "$four_directions.transformations.types": ("four_directions", "transformations"),
    "$four_directions.transformations.source_layer": (
        "four_directions", "transformation_source_layers"
    ),
    "$adjacent.left.all_stars.names": ("adjacent", "left", "all_star_names"),
    "$adjacent.right.all_stars.names": ("adjacent", "right", "all_star_names"),
    "$layer.id": ("layer", "id"),
}


def _resolve_path(context, path):
    keys = PATH_ALIASES.get(path)
    if keys is None:
        raise AnalysisConfigError(f"首版规则引擎不支持路径: {path}")
    value = context
    for key in keys:
        value = value[key]
    return value


def _condition_matches(condition, context):
    if "all" in condition:
        return all(_condition_matches(item, context) for item in condition["all"])
    if "any" in condition:
        return any(_condition_matches(item, context) for item in condition["any"])
    actual = _resolve_path(context, condition["path"])
    expected = (_resolve_path(context, condition["value_from"])
                if "value_from" in condition else condition.get("value"))
    operator = condition["operator"]
    if operator == "equals":
        return actual == expected
    if operator == "all_equal":
        return bool(actual) and all(value == expected for value in actual)
    if operator == "contains":
        candidates = expected if isinstance(expected, list) else [expected]
        matches = [value in actual for value in candidates]
        return all(matches) if condition.get("match_mode") == "all" else any(matches)
    if operator == "contains_all":
        return all(value in actual for value in expected)
    if operator == "count_equals":
        return len(actual) == expected
    if operator == "greater_or_equal":
        actual_value = len(actual) if isinstance(actual, (list, tuple, set, dict)) else actual
        return actual_value >= expected
    raise AnalysisConfigError(f"首版规则引擎不支持操作符: {operator}")


def _rule_fragments(cases, context):
    fragments = []
    for case in cases.get("cases", []):
        if not case.get("enabled", False) or case.get("kind") in ("overlay_rule", "pattern"):
            continue
        if "natal" not in case.get("applicable_layers", []):
            continue
        applicable = case.get("applicable_focus_palaces", [])
        if "*" not in applicable and context["focus"]["name"] not in applicable:
            continue
        if not _condition_matches(case["match"], context):
            continue

        enhancers = [item["name"] for item in case.get("enhancers", [])
                     if _condition_matches(item, context)]
        breakers = [item for item in case.get("breakers", [])
                    if _condition_matches(item, context)]
        status = case["result"]["status"]
        if breakers:
            status = breakers[0].get("effect", status)
        kind = case["kind"]
        fragment_type = "combination" if kind == "star_combination" else "pattern"
        if kind == "palace_rule":
            fragment_type = "four_directions"
        subject_map = cases.get("attribution_policy", {}).get("subject_by_palace", {})
        fragments.append({
            "fragment_id": f"natal.{context['focus']['entry']['id']}.rule.{case['id']}",
            "type": fragment_type,
            "source_layer": "natal",
            "effect_palace": context["focus"]["name"],
            "effect_subject": subject_map.get(context["focus"]["name"]),
            "facts": {
                "rule_id": case["id"],
                "rule_name": case["name"],
                "status": status,
                "nature": case["result"].get("nature"),
                "focus_primary_stars": context["focus"]["primary_star_names"],
                "opposite_primary_stars": context["opposite"]["primary_star_names"],
            },
            "summary": case["result"]["summary"],
            "interpretation_template": case["result"].get("interpretation_template"),
            "modifiers": {
                "enhancers": enhancers,
                "breakers": [item["name"] for item in breakers],
            },
            "evidence": [{
                "source": "analysis_cases",
                "rule_id": case["id"],
                "rule_revision": case["revision"],
                "paths": case.get("evidence", []),
            }],
            "confidence": {"level": "rule_match", "reason": "满足静态案例规则的全部必要条件"},
        })
    return fragments
