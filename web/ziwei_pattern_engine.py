import json
from copy import deepcopy
from pathlib import Path


SUPPORTED_LAYERS = {"natal", "decade", "annual", "monthly", "daily", "hourly"}
SUPPORTED_SCOPES = {
    "self", "triads", "opposite", "four_directions",
    "adjacent_left", "adjacent_right",
}
SUPPORTED_PREDICATES = {
    "star.contains",
    "star.contains_all",
    "star.count",
    "star.same_palace",
    "star.in_triad",
    "star.in_opposite",
    "star.flanks",
    "palace.is_empty",
    "brightness.in",
    "transformation.contains",
    "transformation.contains_all",
    "transformation.not_contains",
    "relation.equals",
    "layer.equals",
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

    policy = pattern["status_policy"]
    for key, status in policy.items():
        if status not in SUPPORTED_STATUSES:
            raise PatternConfigError(f"{path} status_policy.{key} 状态无效: {status}")

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
    if known_star_names and predicate.startswith(("star.", "brightness.")):
        configured_names = set(condition.get("stars", []))
        if predicate.startswith("star."):
            configured_names |= set(condition.get("values", []))
        if condition.get("star"):
            configured_names.add(condition["star"])
        if predicate == "star.flanks":
            configured_names |= set(condition.get("values", []))
        unknown = configured_names - set(known_star_names)
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

    modifier_traces = {}
    for group in ("enhancers", "weakeners", "breakers"):
        modifier_traces[group] = [
            _evaluate_condition(condition, context) for condition in pattern.get(group, [])
        ]
    triggered = {
        group: [trace for trace in traces if trace["matched"]]
        for group, traces in modifier_traces.items()
    }
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
        "enhancers": triggered["enhancers"],
        "weakeners": triggered["weakeners"],
        "breakers": triggered["breakers"],
    }


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
        return {"logic": logic, "matched": matched, "children": traces}

    matched, actual, evidence = _evaluate_predicate(condition, context)
    return {
        "condition_id": condition["id"],
        "name": condition.get("name", condition["id"]),
        "predicate": condition["predicate"],
        "scope": condition.get("scope"),
        "matched": matched,
        "expected": deepcopy(
            condition.get("values", condition.get("value", condition.get("operator")))
        ),
        "actual": actual,
        "evidence": evidence,
    }


def _scope_stars(context, scope):
    return context.get("scopes", {}).get(scope, {}).get("stars", [])


def _filter_stars(stars, condition):
    category = condition.get("category")
    names = set(condition.get("stars", []))
    result = stars
    if category:
        result = [star for star in result if star.get("category") == category]
    if names:
        result = [star for star in result if star.get("name") in names]
    return result


def _star_evidence(stars):
    return [{
        "star": star.get("name"),
        "brightness": star.get("brightness"),
        "transformation": star.get("transformation"),
        "physical_palace": star.get("physical_palace"),
        "physical_palace_index": star.get("physical_palace_index"),
        "relation": star.get("relation"),
        "source_layer": star.get("source_layer"),
    } for star in stars]


def _evaluate_predicate(condition, context):
    predicate = condition["predicate"]
    scope = condition.get("scope", "four_directions")
    stars = _filter_stars(_scope_stars(context, scope), condition)
    names = [star.get("name") for star in stars]
    values = condition.get("values", [])

    if predicate in {"star.contains", "star.contains_all", "star.same_palace", "star.in_triad", "star.in_opposite"}:
        if predicate == "star.same_palace":
            stars = _filter_stars(_scope_stars(context, "self"), condition)
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
        left = _scope_stars(context, "adjacent_left")
        right = _scope_stars(context, "adjacent_right")
        left_names = {star.get("name") for star in left}
        right_names = {star.get("name") for star in right}
        matched = len(values) == 2 and (
            (values[0] in left_names and values[1] in right_names)
            or (values[1] in left_names and values[0] in right_names)
        )
        evidence = [star for star in left + right if star.get("name") in values]
        return matched, {"left": sorted(left_names), "right": sorted(right_names)}, _star_evidence(evidence)

    if predicate == "palace.is_empty":
        primary = _filter_stars(_scope_stars(context, "self"), {"category": "major"})
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

    raise PatternConfigError(f"不支持谓词: {predicate}")


def _leaf_traces(trace):
    if "children" not in trace:
        return [trace]
    result = []
    for child in trace["children"]:
        result.extend(_leaf_traces(child))
    return result


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
