"""Render the A2 transit signals into a score-free daily reading packet."""

import copy
import json
from datetime import date
from pathlib import Path

try:
    from astro_transit_analysis import (
        DIMENSIONS,
        AstroTransitAnalysisConfigError,
        AstroTransitAnalysisRequestError,
        analyze_transit,
    )
except ImportError:
    from web.astro_transit_analysis import (
        DIMENSIONS,
        AstroTransitAnalysisConfigError,
        AstroTransitAnalysisRequestError,
        analyze_transit,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATES_PATH = PROJECT_ROOT / "config" / "astro" / "daily_reading_templates.json"
DIMENSION_ORDER = {dimension: index for index, dimension in enumerate(DIMENSIONS)}
INTENSITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class AstroDailyReadingRequestError(ValueError):
    pass


class AstroDailyReadingConfigError(ValueError):
    pass


def load_templates(path=DEFAULT_TEMPLATES_PATH):
    try:
        templates = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDailyReadingConfigError(f"无法读取日运模板配置: {error}") from error
    if not isinstance(templates, dict) or templates.get("schema_version") != "astro-daily-templates/1.0":
        raise AstroDailyReadingConfigError("日运模板配置的 schema_version 必须为 astro-daily-templates/1.0")
    dimensions = templates.get("dimensions")
    signals = templates.get("signals")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise AstroDailyReadingConfigError("日运模板必须覆盖全部生活领域")
    if not isinstance(signals, dict):
        raise AstroDailyReadingConfigError("日运模板必须包含 signals 对象")
    for dimension in DIMENSIONS:
        entry = dimensions[dimension]
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key] for key in ("label", "empty_label", "empty_text")):
            raise AstroDailyReadingConfigError(f"生活领域 {dimension} 的空状态模板无效")
    for signal_id, entry in signals.items():
        if not isinstance(signal_id, str) or not isinstance(entry, dict):
            raise AstroDailyReadingConfigError("每条日运信号模板必须是对象")
        for key in ("label", "summary", "focus"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise AstroDailyReadingConfigError(f"日运信号模板 {signal_id} 缺少 {key}")
        for key in ("actions", "avoid"):
            if not isinstance(entry.get(key), list) or any(not isinstance(item, str) or not item for item in entry[key]):
                raise AstroDailyReadingConfigError(f"日运信号模板 {signal_id} 的 {key} 无效")
    return templates


def _target_date(facts):
    if not isinstance(facts, dict):
        return None
    target = (facts.get("input") or {}).get("target")
    if not isinstance(target, dict):
        target = (facts.get("transit") or {}).get("input")
    date_value = target.get("date") if isinstance(target, dict) else None
    if not isinstance(date_value, dict):
        return None
    try:
        return date(date_value["year"], date_value["month"], date_value["day"]).isoformat()
    except (KeyError, TypeError, ValueError):
        return None


def _unique(items):
    return list(dict.fromkeys(item for item in items if item))


def _signal_template(signal, templates):
    signal_id = signal.get("rule_id")
    entry = templates["signals"].get(signal_id)
    if entry is None:
        raise AstroDailyReadingConfigError(f"缺少规则 {signal_id} 的日运模板")
    return entry


def _signal_evidence(signal):
    return {
        "signal_id": signal["signal_id"],
        "rule_id": signal["rule_id"],
        "revision": signal["revision"],
        "dimension": signal["dimension"],
        "observation_code": signal["observation_code"],
        "point_ids": copy.deepcopy(signal["point_ids"]),
        "evidence": copy.deepcopy(signal["evidence"]),
        "boundary": signal["boundary"],
    }


def _dimension_reading(dimension, signals, templates):
    meta = templates["dimensions"][dimension]
    if not signals:
        return {
            "index": None,
            "label": meta["empty_label"],
            "text": meta["empty_text"],
            "signal_ids": [],
            "actions": [],
            "avoid": [],
            "evidence": [],
        }
    entries = [_signal_template(signal, templates) for signal in signals]
    return {
        "index": None,
        "label": "、".join(_unique(entry["label"] for entry in entries)),
        "text": "；".join(_unique(entry["summary"] for entry in entries)),
        "signal_ids": [signal["signal_id"] for signal in signals],
        "actions": _unique(item for entry in entries for item in entry["actions"])[:3],
        "avoid": _unique(item for entry in entries for item in entry["avoid"])[:3],
        "evidence": [_signal_evidence(signal) for signal in signals],
    }


def _priority(signal):
    return (
        INTENSITY_ORDER.get(signal.get("intensity"), 99),
        DIMENSION_ORDER.get(signal.get("dimension"), 99),
        signal.get("signal_id", ""),
    )


def _reading_date(facts, requested_date):
    if requested_date is None:
        return _target_date(facts)
    if not isinstance(requested_date, str):
        raise AstroDailyReadingRequestError("date 必须是 YYYY-MM-DD 字符串")
    try:
        return date.fromisoformat(requested_date).isoformat()
    except ValueError as error:
        raise AstroDailyReadingRequestError("date 必须是 YYYY-MM-DD 字符串") from error


def render_daily_reading(analysis, facts=None, requested_date=None, templates=None):
    if not isinstance(analysis, dict) or analysis.get("analysis_version") != "astro-transit-analysis/1.0":
        raise AstroDailyReadingRequestError("analysis 必须是 astro-transit-analysis/1.0 分析包")
    signals = analysis.get("signals")
    if not isinstance(signals, list):
        raise AstroDailyReadingRequestError("analysis 缺少 signals 数组")
    templates = load_templates() if templates is None else templates
    grouped = {dimension: [] for dimension in DIMENSIONS}
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("dimension") not in grouped:
            raise AstroDailyReadingRequestError("analysis 包含无效的生活领域信号")
        grouped[signal["dimension"]].append(signal)
    dimensions = {
        dimension: _dimension_reading(dimension, grouped[dimension], templates)
        for dimension in DIMENSIONS
    }
    ordered_signals = sorted(signals, key=_priority)
    evidence = [_signal_evidence(signal) for signal in ordered_signals]
    if ordered_signals:
        focus_signal = ordered_signals[0]
        focus_template = _signal_template(focus_signal, templates)
        focus_dimension = focus_signal["dimension"]
        focus = {
            "dimension": focus_dimension,
            "title": f"{templates['dimensions'][focus_dimension]['label']}提醒",
            "text": focus_template["focus"],
            "signal_ids": dimensions[focus_dimension]["signal_ids"],
        }
        summary = "；".join(_unique(_signal_template(signal, templates)["summary"] for signal in ordered_signals[:3]))
        actions = dimensions[focus_dimension]["actions"]
        avoid = dimensions[focus_dimension]["avoid"]
        overall_label = "今天有几个生活主题值得留意"
    else:
        focus = {
            "dimension": None,
            "title": "暂无重点领域",
            "text": "当前日期没有命中已配置的生活领域规则。",
            "signal_ids": [],
        }
        summary = "当前日期没有命中已配置的生活领域规则。"
        actions = []
        avoid = []
        overall_label = "今天暂无已配置的生活领域信号"
    return {
        "date": _reading_date(facts, requested_date),
        "scope": "day",
        "overall": {
            "label": overall_label,
            "index": None,
            "index_semantics": "A3 不计算关注度，也不表示现实结果概率。",
            "signal_ids": [signal["signal_id"] for signal in ordered_signals],
        },
        "dimensions": dimensions,
        "summary": summary,
        "focus": focus,
        "actions": actions,
        "avoid": avoid,
        "lucky": {},
        "evidence": evidence,
        "versions": {
            "transit_schema": analysis["source_schema_versions"].get("transit"),
            "analysis_schema": analysis["analysis_version"],
            "reading_schema": "astro-daily-reading/1.0",
            "rules": analysis["rules_version"],
            "templates": templates["schema_version"],
        },
    }


def analyze_and_render(facts, scope=None, dimensions=None, requested_date=None, templates=None):
    try:
        analysis = analyze_transit(facts, scope=scope, dimensions=dimensions)
    except (AstroTransitAnalysisRequestError, AstroTransitAnalysisConfigError) as error:
        raise AstroDailyReadingRequestError(str(error)) from error
    return render_daily_reading(analysis, facts=facts, requested_date=requested_date, templates=templates)
