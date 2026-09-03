import json
from copy import deepcopy
from pathlib import Path


SUPPORTED_LAYERS = {"natal", "decade", "annual", "monthly", "daily", "hourly"}
SUPPORTED_SCOPES = {
    "self", "triads", "opposite", "four_directions",
    "adjacent_left", "adjacent_right", "chart", "wealth_career",
}
SUPPORTED_PREDICATES = {
    "star.contains",
    "star.contains_all",
    "star.count",
    "star.same_palace",
    "star.in_triad",
    "star.in_opposite",
    "star.flanks",
    "star.contains_in_scopes",
    "star.complete_pair_count",
    "star.one_each_across_branches",
    "star.at_physical_branch",
    "palace.is_empty",
    "brightness.in",
    "transformation.contains",
    "transformation.contains_all",
    "transformation.contains_in_palaces",
    "transformation.contains_in_scopes",
    "transformation.not_contains",
    "transformation.flanks",
    "transformation.flanking_count",
    "transformation.san_ji_distribution",
    "birth.year_stem_in",
    "birth.is_daytime",
    "focus.branch_in",
    "focus.role_in",
    "focus.name_in",
    "input.pattern_flag",
    "chart.ming_shen_lucun_template",
    "relation.equals",
    "layer.equals",
    "limit.is_auspicious",
    "annual.lu_kong_dao_ma",
    "star.lu_ma_same_palace_good_place",
    "star.sun_moon_reverse",
    "transformation.sun_moon_good",
}
SUPPORTED_STATUSES = {"formed", "strengthened", "weakened", "broken", "tendency"}
SUPPORTED_OPERATORS = {"equals", "greater_or_equal", "less_or_equal"}


class PatternConfigError(ValueError):
    pass


def _read_json(path):
    try:
        with Path(path).open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        raise PatternConfigError(f"无法读取格局配置 {path}: {error}") from error


def load_pattern_catalog(directory, known_star_names=None):
    directory = Path(directory)
    manifest_path = directory / "_manifest.json"
    manifest = _read_json(manifest_path)
    if not manifest.get("schema_version") or not manifest.get("ruleset"):
        raise PatternConfigError(f"{manifest_path} 缺少 schema_version 或 ruleset")

    patterns = []
    pattern_ids = set()
    source_files = {}
    for path in sorted(directory.glob("*.json")):
        if path.name.startswith("_") or path.name == "pattern.schema.json":
            continue
        pattern = _read_json(path)
        _validate_pattern(pattern, path, known_star_names)
        pattern_id = pattern["id"]
        if pattern_id in pattern_ids:
            raise PatternConfigError(f"格局 ID 重复: {pattern_id} ({path})")
        pattern_ids.add(pattern_id)
        patterns.append(pattern)
        try:
            source_files[pattern_id] = str(path.relative_to(directory.parent.parent.parent))
        except ValueError:
            source_files[pattern_id] = path.name

    declared_count = manifest.get("pattern_count")
    if declared_count is not None and declared_count != len(patterns):
        raise PatternConfigError(
            f"格局清单数量不一致: manifest={declared_count}, files={len(patterns)}"
        )
    return {
        "schema_version": manifest["schema_version"],
        "ruleset": manifest["ruleset"],
        "dictionary_version": manifest.get("dictionary_version", "1.0.0"),
        "patterns": patterns,
        "source_files": source_files,
    }


def _validate_pattern(pattern, path, known_star_names):
    required_fields = (
        "schema_version", "id", "revision", "enabled", "name", "category",
        "school", "strictness", "applicable_layers", "applicable_focus_palaces",
        "required", "status_policy", "result",
    )
    missing = [field for field in required_fields if field not in pattern]
    if missing:
        raise PatternConfigError(f"{path} 缺少字段: {missing}")
    if not isinstance(pattern["revision"], int) or pattern["revision"] < 1:
        raise PatternConfigError(f"{path} revision 必须是正整数")
    if not isinstance(pattern["enabled"], bool):
        raise PatternConfigError(f"{path} enabled 必须是布尔值")
    if not pattern["applicable_layers"] or not set(pattern["applicable_layers"]) <= SUPPORTED_LAYERS:
        raise PatternConfigError(f"{path} applicable_layers 包含不支持的盘层")
    if not pattern["applicable_focus_palaces"]:
        raise PatternConfigError(f"{path} applicable_focus_palaces 不能为空")
    result = pattern["result"]
    if not all(result.get(field) for field in ("nature", "summary", "interpretation_template")):
        raise PatternConfigError(f"{path} result 缺少 nature、summary 或 interpretation_template")

    condition_ids = set()
    _validate_condition(pattern["required"], path, "required", condition_ids, known_star_names)
    if pattern.get("tendency_conditions"):
        _validate_condition(
            pattern["tendency_conditions"], path, "tendency_conditions",
            condition_ids, known_star_names,
        )
    for group in ("enhancers", "weakeners", "breakers"):
        values = pattern.get(group, [])
        if not isinstance(values, list):
            raise PatternConfigError(f"{path} {group} 必须是数组")
        for index, condition in enumerate(values):
            _validate_condition(
                condition, path, f"{group}[{index}]", condition_ids, known_star_names
            )
    observations = pattern.get("observations", [])
    if not isinstance(observations, list):
        raise PatternConfigError(f"{path} observations 必须是数组")
    for index, condition in enumerate(observations):
        _validate_condition(
            condition, path, f"observations[{index}]", condition_ids, known_star_names
        )
    ordinary_observations = pattern.get("ordinary_palace_observations", [])
    if not isinstance(ordinary_observations, list):
        raise PatternConfigError(f"{path} ordinary_palace_observations 必须是数组")
    for index, condition in enumerate(ordinary_observations):
        if not condition.get("note_template"):
            raise PatternConfigError(
                f"{path} ordinary_palace_observations[{index}] 缺少 note_template"
            )
        _validate_condition(
            condition, path, f"ordinary_palace_observations[{index}]",
            condition_ids, known_star_names,
        )
    snapshot_stars = pattern.get("snapshot_stars", [])
    if not isinstance(snapshot_stars, list):
        raise PatternConfigError(f"{path} snapshot_stars 必须是数组")
    if known_star_names:
        unknown = set(snapshot_stars) - set(known_star_names)
        if unknown:
            raise PatternConfigError(f"{path} snapshot_stars 引用了未知星曜: {sorted(unknown)}")

    output_star_positions = pattern.get("output_star_positions", {})
    if not isinstance(output_star_positions, dict) or any(
        not isinstance(field, str) or not field
        or not isinstance(star_name, str) or not star_name
        for field, star_name in output_star_positions.items()
    ):
        raise PatternConfigError(f"{path} output_star_positions 配置无效")
    if known_star_names:
        unknown = set(output_star_positions.values()) - set(known_star_names)
        if unknown:
            raise PatternConfigError(f"{path} output_star_positions 引用了未知星曜: {sorted(unknown)}")

    break_check = pattern.get("break_check")
    if break_check is not None and (
        not isinstance(break_check, dict)
        or not isinstance(break_check.get("break_star"), list)
        or not all(isinstance(item, str) and item for item in break_check.get("break_star", []))
        or not isinstance(break_check.get("scan_scope"), str)
        or not break_check["scan_scope"]
        or not isinstance(break_check.get("note"), str)
        or not break_check["note"]
    ):
        raise PatternConfigError(f"{path} break_check 配置无效")

    policy = pattern["status_policy"]
    for key, status in policy.items():
        if status not in SUPPORTED_STATUSES:
            raise PatternConfigError(f"{path} status_policy.{key} 状态无效: {status}")

    variant_policy = pattern.get("required_variant_policy")
    if variant_policy is not None:
        if not isinstance(variant_policy, dict):
            raise PatternConfigError(f"{path} required_variant_policy 必须是对象")
        minimum = variant_policy.get("minimum_matches")
        if not isinstance(minimum, int) or minimum < 2:
            raise PatternConfigError(
                f"{path} required_variant_policy.minimum_matches 必须是至少为 2 的整数"
            )
        if variant_policy.get("status") not in SUPPORTED_STATUSES:
            raise PatternConfigError(f"{path} required_variant_policy.status 状态无效")
        if "any" not in pattern["required"]:
            raise PatternConfigError(
                f"{path} required_variant_policy 只能用于顶层 required.any 变体"
            )

    grade_rules = pattern.get("grade_rules", [])
    if not isinstance(grade_rules, list):
        raise PatternConfigError(f"{path} grade_rules 必须是数组")
    if grade_rules and not isinstance(pattern.get("default_grade"), str):
        raise PatternConfigError(f"{path} 使用 grade_rules 时必须提供 default_grade")
    for index, grade_rule in enumerate(grade_rules):
        if not isinstance(grade_rule, dict) or not isinstance(grade_rule.get("grade"), str):
            raise PatternConfigError(f"{path} grade_rules[{index}] 缺少 grade")
        condition = grade_rule.get("when")
        if not isinstance(condition, dict):
            raise PatternConfigError(f"{path} grade_rules[{index}] 缺少 when 条件")
        _validate_condition(
            condition, path, f"grade_rules[{index}].when", condition_ids, known_star_names
        )

    examples = pattern.get("examples", [])
    if not examples:
        raise PatternConfigError(f"{path} 至少需要一个正例或反例")
    for index, example in enumerate(examples):
        if not example.get("name") or not isinstance(example.get("context"), dict):
            raise PatternConfigError(f"{path} examples[{index}] 缺少 name 或 context")
        expected = example.get("expected")
        if not isinstance(expected, dict) or "matched" not in expected:
            raise PatternConfigError(f"{path} examples[{index}].expected 缺少 matched")


def _validate_condition(condition, path, location, condition_ids, known_star_names):
    if not isinstance(condition, dict):
        raise PatternConfigError(f"{path} {location} 必须是对象")
    logic_keys = [key for key in ("all", "any", "not") if key in condition]
    if logic_keys:
        if len(logic_keys) != 1:
            raise PatternConfigError(f"{path} {location} 只能使用一种逻辑组合")
        key = logic_keys[0]
        children = condition[key]
        if key == "not":
            children = [children]
        if not isinstance(children, list) or not children:
            raise PatternConfigError(f"{path} {location}.{key} 必须包含条件")
        condition_id = condition.get("id")
        if condition_id:
            if condition_id in condition_ids:
                raise PatternConfigError(f"{path} 条件 ID 重复: {condition_id}")
            condition_ids.add(condition_id)
        for index, child in enumerate(children):
            _validate_condition(
                child, path, f"{location}.{key}[{index}]", condition_ids, known_star_names
            )
        return

    condition_id = condition.get("id")
    predicate = condition.get("predicate")
    if not condition_id or not predicate:
        raise PatternConfigError(f"{path} {location} 缺少 id 或 predicate")
    if condition_id in condition_ids:
        raise PatternConfigError(f"{path} 条件 ID 重复: {condition_id}")
    condition_ids.add(condition_id)
    if predicate not in SUPPORTED_PREDICATES:
        raise PatternConfigError(f"{path} 不支持谓词: {predicate}")
    scope = condition.get("scope")
    if scope is not None and scope not in SUPPORTED_SCOPES:
        raise PatternConfigError(f"{path} {condition_id} scope 无效: {scope}")
    operator = condition.get("operator")
    if operator is not None and operator not in SUPPORTED_OPERATORS:
        raise PatternConfigError(f"{path} {condition_id} operator 无效: {operator}")
    if predicate == "transformation.flanking_count":
        if (
            not isinstance(condition.get("minimum"), int)
            or condition["minimum"] < 1
            or not isinstance(condition.get("require_both_sides", True), bool)
            or not set(condition.get("values", [])) <= {"化禄", "化权", "化科"}
        ):
            raise PatternConfigError(f"{path} {condition_id} 四化夹宫计数配置无效")
    if predicate == "birth.year_stem_in" and not set(condition.get("values", [])) <= set(
        "甲乙丙丁戊己庚辛壬癸"
    ):
        raise PatternConfigError(f"{path} {condition_id} 出生年干配置无效")
    if predicate == "birth.is_daytime" and not isinstance(condition.get("value"), bool):
        raise PatternConfigError(f"{path} {condition_id} 白天出生布尔配置无效")
    if predicate == "focus.branch_in" and not set(condition.get("values", [])) <= set(
        "子丑寅卯辰巳午未申酉戌亥"
    ):
        raise PatternConfigError(f"{path} {condition_id} 目标地支配置无效")
    if predicate == "focus.role_in" and not set(condition.get("values", [])) <= {"ming", "body"}:
        raise PatternConfigError(f"{path} {condition_id} 目标角色配置无效")
    if predicate == "focus.name_in" and not set(condition.get("values", [])) <= {
        "命宫", "兄弟宫", "夫妻宫", "子女宫", "财帛宫", "疾厄宫",
        "迁移宫", "仆役宫", "官禄宫", "田宅宫", "福德宫", "父母宫",
    }:
        raise PatternConfigError(f"{path} {condition_id} 功能宫配置无效")
    if predicate == "input.pattern_flag" and (
        not isinstance(condition.get("pattern_id"), str)
        or not condition["pattern_id"].startswith("pattern.")
        or not isinstance(condition.get("key"), str)
        or not condition["key"]
        or not isinstance(condition.get("value", True), bool)
    ):
        raise PatternConfigError(f"{path} {condition_id} 外部格局布尔输入配置无效")
    if predicate == "star.one_each_across_branches" and (
        len(condition.get("branches", [])) != 2
        or len(set(condition.get("branches", []))) != 2
        or not set(condition.get("branches", [])) <= set("子丑寅卯辰巳午未申酉戌亥")
        or len(condition.get("values", [])) != 2
        or len(set(condition.get("values", []))) != 2
    ):
        raise PatternConfigError(f"{path} {condition_id} 两宫分占配置无效")
    if predicate == "star.complete_pair_count" and (
        not isinstance(condition.get("pairs"), list)
        or not condition["pairs"]
        or any(
            not isinstance(pair, list) or len(pair) != 2 or len(set(pair)) != 2
            for pair in condition["pairs"]
        )
        or not isinstance(condition.get("value"), int)
    ):
        raise PatternConfigError(f"{path} {condition_id} 完整星对计数配置无效")
    if predicate == "star.at_physical_branch" and (
        not isinstance(condition.get("star"), str)
        or not condition["star"]
        or condition.get("branch") not in set("子丑寅卯辰巳午未申酉戌亥")
    ):
        raise PatternConfigError(f"{path} {condition_id} 星曜地支配置无效")
    if predicate == "transformation.contains_in_palaces" and (
        not isinstance(condition.get("palaces"), list)
        or not condition["palaces"]
        or not all(isinstance(item, str) and item for item in condition["palaces"])
        or ("scopes" in condition and (
            not isinstance(condition["scopes"], list)
            or not condition["scopes"]
            or not set(condition["scopes"]) <= SUPPORTED_SCOPES
        ))
        or not set(condition.get("values", [])) <= {"化禄", "化权", "化科", "化忌"}
    ):
        raise PatternConfigError(f"{path} {condition_id} 四化功能宫位配置无效")
    if predicate == "transformation.contains_in_scopes" and (
        not isinstance(condition.get("scopes"), list)
        or not condition["scopes"]
        or not set(condition["scopes"]) <= SUPPORTED_SCOPES
        or not set(condition.get("values", [])) <= {"化禄", "化权", "化科", "化忌"}
    ):
        raise PatternConfigError(f"{path} {condition_id} 四化范围配置无效")
    if predicate == "chart.ming_shen_lucun_template":
        templates = condition.get("templates")
        if not isinstance(templates, list) or not templates or any(
            set(template) != {"year_stem", "lu_branch", "flank_branches"}
            or template["year_stem"] not in set("甲乙丙丁戊己庚辛壬癸")
            or template["lu_branch"] not in set("子丑寅卯辰巳午未申酉戌亥")
            or not isinstance(template["flank_branches"], list)
            or len(template["flank_branches"]) != 2
            or len(set(template["flank_branches"])) != 2
            for template in templates
        ):
            raise PatternConfigError(f"{path} {condition_id} 命身夹禄存模板无效")
    if known_star_names and predicate.startswith(("star.", "brightness.")):
        configured_names = set(condition.get("stars", []))
        if predicate.startswith("star."):
            configured_names |= set(condition.get("values", []))
            configured_names |= {
                star_name
                for pair in condition.get("pairs", [])
                for star_name in pair
            }
        if condition.get("star"):
            configured_names.add(condition["star"])
        if predicate == "star.flanks":
            configured_names |= set(condition.get("values", []))
        unknown = configured_names - set(known_star_names) - {"天空"}
        if unknown:
            raise PatternConfigError(f"{path} {condition_id} 引用了未知星曜: {sorted(unknown)}")


def match_patterns(catalog, context):
    results = []
    for pattern in catalog.get("patterns", []):
        if not pattern.get("enabled", False):
            continue
        if context["layer"]["id"] not in pattern["applicable_layers"]:
            continue
        focus_name = context["focus"]["name"]
        applicable = pattern["applicable_focus_palaces"]
        if "*" not in applicable and focus_name not in applicable:
            continue
        result = match_pattern(pattern, context)
        if result is not None:
            result["source_file"] = catalog.get("source_files", {}).get(pattern["id"])
            results.append(result)
    return results


def match_pattern(pattern, context):
    required_trace = _evaluate_condition(pattern["required"], context)
    tendency_trace = None
    if not required_trace["matched"]:
        if not pattern.get("tendency_conditions"):
            return None
        tendency_trace = _evaluate_condition(pattern["tendency_conditions"], context)
        if not tendency_trace["matched"]:
            return None
        status = pattern["status_policy"].get("tendency_matched", "tendency")
    else:
        status = pattern["status_policy"].get("required_matched", "formed")

    matched_variant_count = _matched_required_variant_count(required_trace)
    variant_policy = pattern.get("required_variant_policy")
    if (
        required_trace["matched"]
        and variant_policy
        and matched_variant_count >= variant_policy["minimum_matches"]
    ):
        status = variant_policy["status"]
    base_status = status

    modifier_traces = {}
    for group in ("enhancers", "weakeners", "breakers"):
        modifier_traces[group] = [
            _evaluate_condition(condition, context) for condition in pattern.get(group, [])
        ]
    triggered = {
        group: [trace for trace in traces if trace["matched"]]
        for group, traces in modifier_traces.items()
    }
    observation_traces = [
        _evaluate_condition(condition, context)
        for condition in pattern.get("observations", [])
    ]
    if triggered["breakers"]:
        status = pattern["status_policy"].get("breaker_matched", "broken")
    elif triggered["weakeners"]:
        status = pattern["status_policy"].get("weakener_matched", "weakened")
    elif triggered["enhancers"] and required_trace["matched"]:
        status = pattern["status_policy"].get("enhancer_matched", "strengthened")

    leaves = _leaf_traces(required_trace)
    if tendency_trace:
        leaves.extend(_leaf_traces(tendency_trace))
    return {
        "pattern_id": pattern["id"],
        "pattern_revision": pattern["revision"],
        "name": pattern["name"],
        "category": pattern["category"],
        "school": pattern["school"],
        "strictness": pattern["strictness"],
        "status": status,
        "base_status": base_status,
        "nature": pattern["result"]["nature"],
        "focus_palace": context["focus"]["name"],
        "effect_palace": context["focus"]["name"],
        "effect_subject": context["focus"].get("effect_subject"),
        "summary": pattern["result"]["summary"],
        "interpretation_template": pattern["result"]["interpretation_template"],
        "required_trace": required_trace,
        "tendency_trace": tendency_trace,
        "matched_conditions": [trace for trace in leaves if trace["matched"]],
        "missing_conditions": [trace for trace in leaves if not trace["matched"]],
        "matched_variant_count": matched_variant_count,
        "matched_variants": _matched_required_variants(required_trace),
        "enhancers": triggered["enhancers"],
        "weakeners": triggered["weakeners"],
        "breakers": triggered["breakers"],
        "observations": observation_traces,
        "matched_observations": [
            trace for trace in observation_traces if trace["matched"]
        ],
        "pattern_snapshot": _pattern_snapshot(context, pattern.get("snapshot_stars", [])),
        "named_star_positions": _named_star_positions(
            context, pattern.get("output_star_positions", {})
        ),
    "textual_variants": deepcopy(pattern.get("textual_variants", [])),
        "flags": _pattern_flags(pattern, required_trace, modifier_traces, observation_traces),
        "break_check": _pattern_break_check(pattern, triggered["breakers"]),
        "rule_notes": deepcopy(pattern.get("result", {}).get("notes", [])),
        "status_message": pattern.get("result", {}).get("status_messages", {}).get(status),
        "tags": deepcopy(pattern.get("result", {}).get("tags", [])),
        "grade": _matched_grade(pattern, required_trace, context),
    }


def match_pattern_observations(pattern, context):
    if context.get("focus", {}).get("roles") and not pattern.get("allow_role_observations", False):
        return []
    results = []
    for condition in pattern.get("ordinary_palace_observations", []):
        if set(context.get("focus", {}).get("roles", [])) & set(condition.get("exclude_roles", [])):
            continue
        trace = _evaluate_condition(condition, context)
        if trace["matched"]:
            results.append({
                "condition_id": condition["id"],
                "name": condition.get("name", condition["id"]),
                "note": condition["note_template"].format(
                    focus_palace=context["focus"]["name"]
                ),
                "trace": trace,
            })
    return results


def _matched_grade(pattern, trace, context):
    for grade_rule in pattern.get("grade_rules", []):
        if _evaluate_condition(grade_rule["when"], context)["matched"]:
            return grade_rule["grade"]
    if pattern.get("grade_rules"):
        return pattern.get("default_grade")
    grade_by_variant = pattern.get("grade_by_variant", {})
    if trace.get("logic") != "any" or not grade_by_variant:
        return None
    for child in trace.get("children", []):
        if child.get("matched") and child.get("condition_id") in grade_by_variant:
            return grade_by_variant[child["condition_id"]]
    return None


def _evaluate_condition(condition, context):
    for logic in ("all", "any", "not"):
        if logic not in condition:
            continue
        children = condition[logic]
        if logic == "not":
            child = _evaluate_condition(children, context)
            return {"logic": "not", "matched": not child["matched"], "children": [child]}
        traces = [_evaluate_condition(child, context) for child in children]
        matched = all(trace["matched"] for trace in traces) if logic == "all" else any(
            trace["matched"] for trace in traces
        )
        return {
            "logic": logic,
            "condition_id": condition.get("id"),
            "name": condition.get("name"),
            "matched": matched,
            "children": traces,
        }

    matched, actual, evidence = _evaluate_predicate(condition, context)
    return {
        "condition_id": condition["id"],
        "name": condition.get("name", condition["id"]),
        "predicate": condition["predicate"],
        "scope": condition.get("scope"),
        "matched": matched,
        "expected": deepcopy(
            condition.get(
                "values",
                condition.get("value", condition.get("templates", condition.get("operator"))),
            )
        ),
        "actual": actual,
        "evidence": evidence,
    }


def _scope_stars(context, scope):
    if scope == "chart":
        return [
            star
            for palace in context.get("chart", {}).get("palaces", [])
            for star in palace.get("stars", [])
        ]
    scope_data = context.get("scopes", {}).get(scope, {})
    if isinstance(scope_data, list):
        return scope_data
    return scope_data.get("stars", [])


def _pattern_flags(pattern, required_trace, modifier_traces, observation_traces):
    traces = [required_trace]
    traces.extend(_leaf_traces(required_trace))
    traces.extend([trace for group in modifier_traces.values() for trace in group])
    traces.extend(observation_traces)
    flags = {}
    for flag, condition_id in pattern.get("output_flags", {}).items():
        flags[flag] = any(_trace_has_condition(trace, condition_id) for trace in traces)
    for flag, enum_config in pattern.get("output_enums", {}).items():
        if enum_config.get("multiple"):
            matched_values = []
            for enum_value, condition_ids in enum_config.get("values", {}).items():
                ids = condition_ids if isinstance(condition_ids, list) else [condition_ids]
                if any(_trace_has_condition(trace, condition_id) for condition_id in ids for trace in traces):
                    matched_values.append(enum_value)
            flags[flag] = matched_values or enum_config.get("default", [])
            continue
        value = enum_config.get("default")
        for enum_value, condition_ids in enum_config.get("values", {}).items():
            ids = condition_ids if isinstance(condition_ids, list) else [condition_ids]
            if any(_trace_has_condition(trace, condition_id) for condition_id in ids for trace in traces):
                value = enum_value
                break
        flags[flag] = value
    for flag, output_config in pattern.get("output_values", {}).items():
        if isinstance(output_config, str):
            condition_id, path = output_config, None
        else:
            condition_id, path = output_config.get("condition_id"), output_config.get("path")
        matching = [
            matched_trace
            for trace in traces
            for matched_trace in _matching_condition_traces(trace, condition_id)
        ]
        if matching:
            value = matching[0].get("actual")
            if path:
                for part in path.split("."):
                    value = value.get(part) if isinstance(value, dict) else None
            flags[flag] = value
    return flags


def _pattern_break_check(pattern, triggered_breakers):
    config = pattern.get("break_check")
    if not config:
        return None
    evidence = [
        evidence_item
        for trace in triggered_breakers
        for leaf in _leaf_traces(trace)
        if leaf.get("matched")
        for evidence_item in leaf.get("evidence", [])
    ]
    seen = set()
    break_star_list = []
    for item in evidence:
        key = (
            item.get("star"), item.get("transformation"),
            item.get("physical_palace"), item.get("physical_branch"),
        )
        if key in seen:
            continue
        seen.add(key)
        entry = {
            "star": item.get("star"),
            "palace": item.get("physical_palace"),
            "branch": item.get("physical_branch"),
        }
        if item.get("transformation"):
            entry["transformation"] = item["transformation"]
        break_star_list.append(entry)
    return {
        "status": "broken" if triggered_breakers else "normal",
        "break_star": deepcopy(config.get("break_star", [])),
        "break_star_list": break_star_list,
        "scan_scope": config.get("scan_scope"),
        "note": config.get("note"),
    }


def _named_star_positions(context, configured_fields):
    current_layer = context.get("layer", {}).get("id")
    positions = {}
    chart_stars = _scope_stars(context, "chart")
    for field, star_name in configured_fields.items():
        star = next((item for item in chart_stars if (
            item.get("name") == star_name
            and item.get("source_layer") == current_layer
        )), None)
        positions[field] = star.get("physical_branch") if star else None
    return positions


def _trace_has_condition(trace, condition_id):
    if trace.get("condition_id") == condition_id and trace.get("matched"):
        return True
    return any(
        _trace_has_condition(child, condition_id)
        for child in trace.get("children", [])
    )


def _matching_condition_traces(trace, condition_id):
    matches = []
    if trace.get("condition_id") == condition_id and trace.get("matched"):
        matches.append(trace)
    for child in trace.get("children", []):
        matches.extend(_matching_condition_traces(child, condition_id))
    return matches


def _filter_stars(stars, condition, current_layer=None):
    category = condition.get("category")
    names = set(condition.get("stars", []))
    result = stars
    if category:
        result = [star for star in result if star.get("category") == category]
    if names:
        result = [star for star in result if star.get("name") in names]
    source_layer = condition.get("source_layer")
    if source_layer == "$current_layer":
        source_layer = current_layer
    if source_layer:
        result = [star for star in result if star.get("source_layer") == source_layer]
    return result


def _star_evidence(stars):
    return [{
        "star": star.get("name"),
        "brightness": star.get("brightness"),
        "transformation": star.get("transformation"),
        "physical_palace": star.get("physical_palace"),
        "physical_palace_index": star.get("physical_palace_index"),
        "physical_branch": star.get("physical_branch"),
        "relation": star.get("relation"),
        "source_layer": star.get("source_layer"),
    } for star in stars]


def _pattern_snapshot(context, snapshot_stars=None):
    scopes = context.get("scopes", {})

    def malefics(scope):
        return _star_evidence([
            star for star in _scope_stars(context, scope)
            if star.get("category") == "malefic"
        ])

    def transformations(scope):
        return _star_evidence([
            star for star in _scope_stars(context, scope)
            if star.get("transformation") in {"化禄", "化权", "化科"}
        ])

    chart = context.get("chart", {})
    snapshot_names = set(snapshot_stars or [])
    def scope_meta(name):
        value = scopes.get(name, {})
        return value if isinstance(value, dict) else {}
    return {
        "target": {
            "functional_palace": context.get("focus", {}).get("name"),
            "roles": deepcopy(context.get("focus", {}).get("roles", [])),
            "branch": context.get("focus", {}).get("branch"),
            "index": context.get("focus", {}).get("index"),
        },
        "adjacent_palaces": {
            "left": deepcopy(scope_meta("adjacent_left").get("palace")),
            "right": deepcopy(scope_meta("adjacent_right").get("palace")),
        },
        "transformation_distribution": {
            "left": transformations("adjacent_left"),
            "right": transformations("adjacent_right"),
        },
        "lu_cun_positions": [
            {
                "palace": palace.get("name"),
                "branch": palace.get("branch"),
                "index": palace.get("index"),
            }
            for palace in chart.get("palaces", [])
            if any(star.get("name") == "禄存" for star in palace.get("stars", []))
        ],
        "star_positions": [
            evidence
            for palace in chart.get("palaces", [])
            for evidence in _star_evidence([
                star for star in palace.get("stars", [])
                if star.get("name") in snapshot_names
            ])
        ],
        "malefic_notes": {
            "target": malefics("self"),
            "adjacent": malefics("adjacent_left") + malefics("adjacent_right"),
            "four_directions": malefics("four_directions"),
        },
    }


def _evaluate_predicate(condition, context):
    predicate = condition["predicate"]
    scope = condition.get("scope", "four_directions")
    current_layer = context["layer"]["id"]
    stars = _filter_stars(_scope_stars(context, scope), condition, current_layer)
    names = [star.get("name") for star in stars]
    values = condition.get("values", [])

    if predicate in {"star.contains", "star.contains_all", "star.same_palace", "star.in_triad", "star.in_opposite"}:
        if predicate == "star.same_palace":
            stars = _filter_stars(
                _scope_stars(context, condition.get("scope", "self")),
                condition,
                current_layer,
            )
        elif predicate == "star.in_triad":
            stars = _filter_stars(_scope_stars(context, "triads"), condition)
        elif predicate == "star.in_opposite":
            stars = _filter_stars(_scope_stars(context, "opposite"), condition)
        names = [star.get("name") for star in stars]
        candidates = values or [condition.get("value")]
        if predicate in {"star.contains_all", "star.same_palace"}:
            matched = all(value in names for value in candidates)
        else:
            flags = [value in names for value in candidates]
            matched = all(flags) if condition.get("match_mode") == "all" else any(flags)
        evidence = [star for star in stars if star.get("name") in candidates]
        return matched, names, _star_evidence(evidence)

    if predicate == "star.contains_in_scopes":
        scope_names = condition.get("scopes", [])
        scoped_stars = [
            star
            for scope_name in scope_names
            for star in _scope_stars(context, scope_name)
        ]
        scoped_stars = _filter_stars(scoped_stars, condition, current_layer)
        names = [star.get("name") for star in scoped_stars]
        matched = all(value in names for value in values) if condition.get("match_mode") == "all" else any(value in names for value in values)
        evidence = [star for star in scoped_stars if star.get("name") in values]
        return matched, names, _star_evidence(evidence)

    if predicate == "star.complete_pair_count":
        unique_names = set(names)
        pairs = condition.get("pairs", [])
        found_pairs = [pair for pair in pairs if set(pair) <= unique_names]
        configured_names = {name for pair in pairs for name in pair}
        found_list = sorted(unique_names & configured_names)
        pair_total = len(found_pairs)
        expected = condition.get("value", 0)
        operator = condition.get("operator", "equals")
        matched = {
            "equals": pair_total == expected,
            "greater_or_equal": pair_total >= expected,
            "less_or_equal": pair_total <= expected,
        }[operator]
        evidence = [star for star in stars if star.get("name") in configured_names]
        return matched, {
            "found_list": found_list,
            "minister_count": len(found_list),
            "found_pairs": found_pairs,
            "pair_total": pair_total,
        }, _star_evidence(evidence)

    if predicate == "star.one_each_across_branches":
        branches = condition.get("branches", [])
        candidates = set(values)
        distribution = {branch: [] for branch in branches}
        evidence = []
        for palace in context.get("chart", {}).get("palaces", []):
            branch = palace.get("branch")
            if branch not in distribution:
                continue
            for original_star in palace.get("stars", []):
                if original_star.get("name") not in candidates:
                    continue
                if (
                    condition.get("source_layer") == "$current_layer"
                    and original_star.get("source_layer") != current_layer
                ):
                    continue
                star = dict(original_star)
                star.setdefault("physical_palace", palace.get("name"))
                star.setdefault("physical_branch", branch)
                distribution[branch].append(star.get("name"))
                evidence.append(star)
        actual_names = {
            name for branch_names in distribution.values() for name in branch_names
        }
        matched = (
            actual_names == candidates
            and all(len(branch_names) == 1 for branch_names in distribution.values())
        )
        return matched, distribution, _star_evidence(evidence)

    if predicate == "star.at_physical_branch":
        candidate = condition.get("star")
        branch = condition.get("branch")
        scope_names = condition.get("scopes") or [condition.get("scope", "chart")]
        stars = [
            star
            for scope_name in scope_names
            for star in _scope_stars(context, scope_name)
        ]
        stars = _filter_stars(stars, condition, current_layer)
        evidence = [
            star for star in stars
            if star.get("name") == candidate
            and (star.get("physical_branch") or star.get("branch")) == branch
        ]
        return bool(evidence), {"star": candidate, "branch": branch}, _star_evidence(evidence)

    if predicate == "transformation.contains_in_palaces":
        palace_names = set(condition.get("palaces", []))
        if condition.get("scopes"):
            scoped_stars = [
                item
                for scope_name in condition["scopes"]
                for item in _scope_stars(context, scope_name)
            ]
            scoped_stars = _filter_stars(scoped_stars, condition, current_layer)
        else:
            scoped_stars = stars
        scoped_stars = [
            star for star in scoped_stars
            if star.get("physical_palace") in palace_names
            and star.get("transformation") in values
        ]
        actual = sorted({star.get("transformation") for star in scoped_stars})
        matched = any(value in actual for value in values)
        return matched, {
            "palaces": sorted(palace_names),
            "transformations": actual,
        }, _star_evidence(scoped_stars)

    if predicate == "star.count":
        actual = len(stars)
        expected = condition.get("value", 0)
        operator = condition.get("operator", "equals")
        matched = {
            "equals": actual == expected,
            "greater_or_equal": actual >= expected,
            "less_or_equal": actual <= expected,
        }[operator]
        return matched, actual, _star_evidence(stars)

    if predicate == "star.flanks":
        left = _filter_stars(
            _scope_stars(context, "adjacent_left"), condition, current_layer
        )
        right = _filter_stars(
            _scope_stars(context, "adjacent_right"), condition, current_layer
        )
        left_names = {star.get("name") for star in left}
        right_names = {star.get("name") for star in right}
        matched = len(values) == 2 and (
            (values[0] in left_names and values[1] in right_names)
            or (values[1] in left_names and values[0] in right_names)
        )
        evidence = [star for star in left + right if star.get("name") in values]
        return matched, {"left": sorted(left_names), "right": sorted(right_names)}, _star_evidence(evidence)

    if predicate == "transformation.flanks":
        source_layer = condition.get("source_layer")
        if source_layer == "$current_layer":
            source_layer = context["layer"]["id"]
        left = [
            star for star in _scope_stars(context, "adjacent_left")
            if star.get("transformation")
            and (source_layer is None or star.get("source_layer") == source_layer)
        ]
        right = [
            star for star in _scope_stars(context, "adjacent_right")
            if star.get("transformation")
            and (source_layer is None or star.get("source_layer") == source_layer)
        ]
        left_values = {star["transformation"] for star in left}
        right_values = {star["transformation"] for star in right}
        matched = len(values) == 2 and (
            (values[0] in left_values and values[1] in right_values)
            or (values[1] in left_values and values[0] in right_values)
        )
        evidence = [
            star for star in left + right if star.get("transformation") in values
        ]
        return matched, {
            "left": sorted(left_values), "right": sorted(right_values)
        }, _star_evidence(evidence)

    if predicate == "transformation.contains_in_scopes":
        scoped_stars = [
            item
            for scope_name in condition.get("scopes", [])
            for item in _scope_stars(context, scope_name)
        ]
        scoped_stars = _filter_stars(scoped_stars, condition, current_layer)
        evidence = [star for star in scoped_stars if star.get("transformation") in values]
        return bool(evidence), [star.get("transformation") for star in scoped_stars], _star_evidence(evidence)

    if predicate == "transformation.flanking_count":
        source_layer = condition.get("source_layer")
        if source_layer == "$current_layer":
            source_layer = context["layer"]["id"]
        allowed = set(values)

        def qualifying(scope_name):
            return [
                star for star in _scope_stars(context, scope_name)
                if star.get("transformation") in allowed
                and (source_layer is None or star.get("source_layer") == source_layer)
            ]

        left = qualifying("adjacent_left")
        right = qualifying("adjacent_right")
        left_values = {star["transformation"] for star in left}
        right_values = {star["transformation"] for star in right}
        distinct = left_values | right_values
        minimum = condition.get("minimum", 1)
        both_sides = condition.get("require_both_sides", True)
        matched = len(distinct) >= minimum and (
            not both_sides or (bool(left_values) and bool(right_values))
        )
        return matched, {
            "left": sorted(left_values),
            "right": sorted(right_values),
            "distinct_count": len(distinct),
        }, _star_evidence(left + right)

    if predicate == "transformation.san_ji_distribution":
        allowed = set(values or ["化禄", "化权", "化科"])

        def qualifying(scope_name):
            return [
                star for star in _scope_stars(context, scope_name)
                if star.get("transformation") in allowed
                and (condition.get("source_layer") not in (None, "$current_layer")
                     or star.get("source_layer") == current_layer)
            ]

        target = qualifying("self")
        wealth = qualifying("wealth_career")
        triad = qualifying("triads")
        target_values = {star["transformation"] for star in target}
        wealth_values = {star["transformation"] for star in wealth}
        triad_values = {star["transformation"] for star in triad}
        all_values = target_values | wealth_values | triad_values
        matched = (
            allowed <= all_values
            and bool(target_values)
            and bool(wealth_values)
            and bool(triad_values)
        )
        return matched, {
            "all": sorted(all_values),
            "target": sorted(target_values),
            "wealth_career": sorted(wealth_values),
            "triads": sorted(triad_values),
            "target_has_one": bool(target_values),
            "wealth_career_has_one": bool(wealth_values),
            "triad_has_one": bool(triad_values),
        }, _star_evidence(target + wealth + triad)

    if predicate == "annual.lu_kong_dao_ma":
        annual = context.get("annual") or context.get("chart", {}).get("annual") or context.get("chart", {})
        palaces = annual.get("palaces", [])
        branches = "子丑寅卯辰巳午未申酉戌亥"
        by_branch = {palace.get("branch"): palace for palace in palaces}
        lu_palaces = [p for p in palaces if any(s.get("name") == "禄存" for s in p.get("stars", []))]
        ma_palaces = [p for p in palaces if any(s.get("name") == "天马" for s in p.get("stars", []))]
        tai_sui = annual.get("tai_sui_palace_code") or annual.get("year_branch")
        tai_index = branches.find(tai_sui) if tai_sui in branches else -1
        candidates = []
        for lu in lu_palaces:
            lu_index = branches.find(lu.get("branch"))
            for ma in ma_palaces:
                ma_index = branches.find(ma.get("branch"))
                if lu_index < 0 or ma_index < 0:
                    continue
                distance = (ma_index - lu_index) % 12
                if distance not in (0, 6):
                    continue
                state_palaces = [lu] if distance == 0 else [lu, ma]
                state_ok = any(p.get("chang_sheng") in ("沐浴", "绝") or p.get("is_kong_wang") is True for p in state_palaces)
                if not state_ok or tai_index < 0:
                    continue
                lu_index = branches.find(lu.get("branch"))
                relation_distance = (tai_index - lu_index) % 12
                if relation_distance == 0:
                    meet_type = "同宫"
                elif relation_distance in (4, 8):
                    meet_type = "三合"
                elif relation_distance == 6:
                    meet_type = "对宫"
                else:
                    continue
                tai_palace = by_branch.get(tai_sui, {})
                tai_has_kong_jie = any(s.get("name") in ("地劫", "天空") for s in tai_palace.get("stars", []))
                if not tai_has_kong_jie:
                    continue
                candidates.append({
                    "lu_ma_palace_code": lu.get("branch"),
                    "lu_ma_relation": "同宫" if distance == 0 else "对宫",
                    "lu_ma_state": {
                        "chang_sheng": [p.get("chang_sheng") for p in state_palaces if p.get("chang_sheng") in ("沐浴", "绝")],
                        "is_kong_wang": any(p.get("is_kong_wang") is True for p in state_palaces),
                    },
                    "tai_sui_palace_code": tai_sui,
                    "tai_sui_have_kong_jie": True,
                    "meet_type": meet_type,
                    "tai_sui_stars": [s.get("name") for s in tai_palace.get("stars", []) if s.get("name") in ("地劫", "天空")],
                })
        return bool(candidates), candidates, []

    if predicate == "star.lu_ma_same_palace_good_place":
        chart = context.get("chart", {})
        current_layer = context["layer"]["id"]
        candidates = []
        for palace in chart.get("palaces", []):
            stars_in_palace = [
                star for star in palace.get("stars", [])
                if star.get("source_layer") in (None, current_layer)
            ]
            ma_stars = [star for star in stars_in_palace if star.get("name") == "天马"]
            lu_stars = [
                star for star in stars_in_palace
                if star.get("transformation") == "化禄" and star.get("name") != "天马"
            ]
            if not ma_stars or not lu_stars:
                continue
            ma = ma_stars[0]
            ma_brightness = ma.get("brightness") or ma.get("liang_du")
            for lu_star in lu_stars:
                lu_brightness = lu_star.get("brightness") or lu_star.get("liang_du")
                candidate = {
                    "occur_pal": palace.get("name") or palace.get("branch"),
                    "lu_ma_palace_code": palace.get("branch"),
                    "debug_brightness": {
                        "hualu_star": lu_star.get("name"),
                        "hualu_brightness": lu_brightness,
                        "tianma_brightness": ma_brightness,
                    },
                }
                candidates.append(candidate)
                if all(value is not None and value != "陷" for value in (lu_brightness, ma_brightness)):
                    return True, candidate, _star_evidence([lu_star, ma])
        return False, {"candidates": candidates}, []

    if predicate == "star.sun_moon_reverse":
        chart = context.get("chart", {})
        stars = [star for palace in chart.get("palaces", []) for star in palace.get("stars", [])]
        stars = _filter_stars(stars, condition, current_layer)
        sun_branches = {p.get("branch") for p in chart.get("palaces", []) if any(s.get("name") == "太阳" and s in stars for s in p.get("stars", []))}
        moon_branches = {p.get("branch") for p in chart.get("palaces", []) if any(s.get("name") == "太阴" and s in stars for s in p.get("stars", []))}
        matched = bool(sun_branches & set("申酉戌亥子")) and bool(moon_branches & set("寅卯辰巳午"))
        return matched, {"sun_branches": sorted(sun_branches), "moon_branches": sorted(moon_branches)}, []

    if predicate == "transformation.sun_moon_good":
        chart = context.get("chart", {})
        branches = "子丑寅卯辰巳午未申酉戌亥"
        star_branch = {}
        for palace in chart.get("palaces", []):
            for star in palace.get("stars", []):
                if star.get("name") in ("太阳", "太阴") and (condition.get("source_layer") != "$current_layer" or star.get("source_layer") == current_layer):
                    star_branch[star.get("name")] = palace.get("branch")
        allowed = set()
        for branch in star_branch.values():
            if branch in branches:
                index = branches.index(branch)
                allowed.update({branch, branches[(index + 4) % 12], branches[(index + 8) % 12]})
        evidence = []
        for palace in chart.get("palaces", []):
            if palace.get("branch") not in allowed:
                continue
            for star in palace.get("stars", []):
                if star.get("transformation") in {"化禄", "化权", "化科"} and (condition.get("source_layer") != "$current_layer" or star.get("source_layer") == current_layer):
                    evidence.append(star)
        return bool(evidence), sorted(allowed), _star_evidence(evidence)

    if predicate == "birth.year_stem_in":
        actual = context.get("chart", {}).get("birth_year_stem")
        return actual in values, actual, []

    if predicate == "birth.is_daytime":
        actual = context.get("birth", {}).get("is_daytime")
        if actual is None:
            actual = context.get("chart", {}).get("is_daytime")
        expected = condition.get("value")
        return actual is expected, actual, []

    if predicate == "focus.branch_in":
        actual = context.get("focus", {}).get("branch")
        return actual in values, actual, []

    if predicate == "focus.role_in":
        actual = context.get("focus", {}).get("roles", [])
        matched_roles = [role for role in actual if role in values]
        return bool(matched_roles), actual, [{"role": role} for role in matched_roles]

    if predicate == "focus.name_in":
        actual = context.get("focus", {}).get("name")
        return actual in values, actual, []

    if predicate == "input.pattern_flag":
        pattern_id = condition["pattern_id"]
        key = condition["key"]
        actual = context.get("pattern_inputs", {}).get(pattern_id, {}).get(key)
        expected = condition.get("value", True)
        return isinstance(actual, bool) and actual is expected, actual, []

    if predicate == "chart.ming_shen_lucun_template":
        chart = context.get("chart", {})
        actual = {
            "year_stem": chart.get("birth_year_stem"),
            "ming_branch": chart.get("ming", {}).get("branch"),
            "shen_branch": chart.get("body", {}).get("branch"),
        }
        lu_palaces = [
            palace for palace in chart.get("palaces", [])
            if any(star.get("name") == "禄存" for star in palace.get("stars", []))
        ]
        actual["lu_cun_branches"] = [palace.get("branch") for palace in lu_palaces]
        matched_template = next((template for template in condition.get("templates", []) if (
            actual["year_stem"] == template.get("year_stem")
            and {actual["ming_branch"], actual["shen_branch"]}
                == set(template.get("flank_branches", []))
            and template.get("lu_branch") in actual["lu_cun_branches"]
        )), None)
        evidence = []
        if matched_template:
            lu_branch = matched_template["lu_branch"]
            for palace in lu_palaces:
                if palace.get("branch") == lu_branch:
                    evidence.extend(_star_evidence([
                        star for star in palace.get("stars", [])
                        if star.get("name") == "禄存"
                    ]))
        actual["matched_template"] = deepcopy(matched_template)
        return matched_template is not None, actual, evidence

    if predicate == "palace.is_empty":
        primary = _filter_stars(
            _scope_stars(context, "self"), {"category": "major"}, current_layer
        )
        expected = condition.get("value", True)
        return (len(primary) == 0) == expected, len(primary) == 0, _star_evidence(primary)

    if predicate == "brightness.in":
        brightness_values = set(values)
        matching = [star for star in stars if star.get("brightness") in brightness_values]
        matched = bool(matching)
        if condition.get("match_mode") == "all" and stars:
            matched = len(matching) == len(stars)
        return matched, [star.get("brightness") for star in stars], _star_evidence(matching)

    if predicate.startswith("transformation."):
        source_layer = condition.get("source_layer")
        if source_layer == "$current_layer":
            source_layer = context["layer"]["id"]
        transformations = [
            star for star in stars
            if star.get("transformation")
            and (source_layer is None or star.get("source_layer") == source_layer)
        ]
        actual = [star["transformation"] for star in transformations]
        if predicate == "transformation.contains_all":
            matched = all(value in actual for value in values)
        elif predicate == "transformation.not_contains":
            matched = all(value not in actual for value in values)
        else:
            matched = any(value in actual for value in values)
        evidence = [star for star in transformations if star["transformation"] in values]
        return matched, actual, _star_evidence(evidence)

    if predicate == "relation.equals":
        actual = context["focus"].get("relation", "self")
        expected = condition.get("value")
        return actual == expected, actual, []

    if predicate == "layer.equals":
        actual = context["layer"]["id"]
        expected = condition.get("value")
        return actual == expected, actual, []

    if predicate == "limit.is_auspicious":
        actual = bool(context.get("layer", {}).get("is_auspicious_limit", False))
        return actual, actual, []

    raise PatternConfigError(f"不支持谓词: {predicate}")


def _leaf_traces(trace):
    if "children" not in trace:
        return [trace]
    result = []
    for child in trace["children"]:
        result.extend(_leaf_traces(child))
    return result


def _matched_required_variant_count(trace):
    if trace.get("logic") == "any":
        return sum(1 for child in trace.get("children", []) if child["matched"])
    return 0


def _matched_required_variants(trace):
    if trace.get("logic") != "any":
        return []
    candidates = trace.get("children", [])
    return [{
        "id": candidate.get("condition_id"),
        "name": candidate.get("name"),
    } for candidate in candidates if candidate.get("matched")]


def run_catalog_examples(catalog):
    results = []
    for pattern in catalog.get("patterns", []):
        for example in pattern.get("examples", []):
            matched = match_pattern(pattern, example["context"])
            expected = example["expected"]
            errors = []
            if (matched is not None) != expected["matched"]:
                errors.append(f"matched 期望 {expected['matched']}")
            if matched:
                for field in ("status", "effect_palace", "effect_subject"):
                    if field in expected and matched.get(field) != expected[field]:
                        errors.append(f"{field} 期望 {expected[field]}，实际 {matched.get(field)}")
            results.append({
                "pattern_id": pattern["id"],
                "example": example["name"],
                "passed": not errors,
                "errors": errors,
            })
    return results
