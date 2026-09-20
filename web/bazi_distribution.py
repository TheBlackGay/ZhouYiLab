"""八字分布画像（图表数据包）：干支五行 / 十神五类 / 干之阴阳。

与 astro/ziwei/六壬 画像同构，复用 build_package 通用构建器。
数据源为排盘既有字段（pillars 四天干 + 各地支藏干），零新增算法、零口径发明：
* 天干五行/阴阳用与内核一致的标准表（甲木乙木……甲阳乙阴……），
  并与内核输出逐字交叉校验（tests 锁表）；
* 十神逐字取内核 ten_god 标注，按比劫/食伤/财/官/印五类归组；
  日干自身为命主、不入十神图分母（五行/阴阳图仍计）；
* 文案全部为"命局底色"气质描写，summary_join 配为"×"合成箴言式跨图底色；
* 八字旺衰/喜忌/格局（D3 三步走）未上线，画像不依赖、不暗示任何喜忌结论。
"""
import json
from pathlib import Path

from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    build_package,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "bazi" / "distribution_reading.json"

SCHEMA_VERSION = "bazi-distribution/1.0"
READING_SCHEMA = "bazi-distribution-reading/1.0"

DIMENSIONS = ("signs", "gods", "polarity")
PILLAR_ORDER = ("year", "month", "day", "hour")
PILLAR_NAMES_ZH = {"year": "年", "month": "月", "day": "日", "hour": "时"}

# 与内核天干五行/阴阳表一致（tests 与 CLI 输出逐字交叉锁定）
STEM_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
STEM_YINYANG = {"甲": "positive", "丙": "positive", "戊": "positive", "庚": "positive", "壬": "positive",
                "乙": "negative", "丁": "negative", "己": "negative", "辛": "negative", "癸": "negative"}
WUXING_KEYS = {"木", "火", "土", "金", "水"}
GODS_KEYS = {"bijie", "shishang", "cai", "guan", "yin"}
POLARITY_KEYS = {"positive", "negative"}

# 内核 ten_god 全称 → 五类；出现表外值即报错，防止内核口径漂移被静默吞掉
TEN_GOD_GROUP = {
    "比肩": "bijie", "劫财": "bijie",
    "食神": "shishang", "伤官": "shishang",
    "正财": "cai", "偏财": "cai",
    "正官": "guan", "七杀": "guan", "偏官": "guan",
    "正印": "yin", "偏印": "yin", "枭神": "yin",
}


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取八字分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("八字分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"八字分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    tables = {"signs": WUXING_KEYS, "gods": GODS_KEYS, "polarity": POLARITY_KEYS}
    for chart_id, chart in charts.items():
        keys = tables[chart_id]
        for field in ("labels_zh", "tags_zh", "dominant_templates_zh"):
            if set(chart.get(field, {})) != keys:
                raise AstroDistributionConfigError(f"{chart_id}.{field} 必须覆盖 {sorted(keys)}")
        if set(chart.get("order", [])) != keys or len(chart["order"]) != len(keys):
            raise AstroDistributionConfigError(f"{chart_id}.order 必须恰好是 {sorted(keys)}")
        if not keys.issubset(set(chart.get("readings_zh", {}))) or "balanced" not in chart["readings_zh"]:
            raise AstroDistributionConfigError(f"{chart_id}.readings_zh 覆盖不全")
        if not keys.issubset(set(chart.get("summary_phrases_zh", {}))) or "balanced" not in chart["summary_phrases_zh"]:
            raise AstroDistributionConfigError(f"{chart_id}.summary_phrases_zh 覆盖不全")
        for field in ("title_zh", "basis_zh", "balanced_template_zh"):
            if not chart.get(field):
                raise AstroDistributionConfigError(f"{chart_id} 缺少 {field}")
        if chart_id == "signs" and not chart.get("summary_template_zh"):
            raise AstroDistributionConfigError("signs.summary_template_zh 缺失（summary 模板取自首图）")
    return raw


def _classify_group(ten_god, where):
    group = TEN_GOD_GROUP.get(ten_god)
    if group is None:
        raise AstroDistributionRequestError(f"{where} 十神 {ten_god!r} 无法归组")
    return group


def collect_points(chart):
    """天干 4 点 + 全部地支藏干逐字一点；十神图不含日干自身（attributes 置 None）。"""
    pillars = chart.get("pillars") if isinstance(chart, dict) else None
    if not isinstance(pillars, dict) or set(pillars) != set(PILLAR_ORDER):
        raise AstroDistributionRequestError("chart 缺少完整四柱 pillars，不是八字排盘结果")
    points = []
    for position in PILLAR_ORDER:
        pillar = pillars[position]
        stem = pillar.get("stem")
        if stem not in STEM_ELEMENT:
            raise AstroDistributionRequestError(f"{position} 柱天干 {stem!r} 无法归类")
        element = pillar.get("stem_element")
        if element != STEM_ELEMENT[stem]:
            raise AstroDistributionRequestError(
                f"{position} 柱内核五行 {element!r} 与标准表 {STEM_ELEMENT[stem]!r} 不符")
        ten_god = None if position == "day" else _classify_group(
            pillar.get("stem_ten_god"), f"{position} 柱天干")
        points.append({
            "point_id": f"{position}_stem", "point_name": f"{PILLAR_NAMES_ZH[position]}干{stem}",
            "kind": "stem",
            "attributes": {"signs": element, "gods": ten_god,
                           "polarity": STEM_YINYANG[stem]},
        })
        for index, hidden in enumerate(pillar.get("hidden_stems") or [], start=1):
            h_stem, h_element = hidden.get("stem"), hidden.get("element")
            if h_stem not in STEM_ELEMENT:
                raise AstroDistributionRequestError(f"{position} 柱藏干 {h_stem!r} 无法归类")
            if h_element != STEM_ELEMENT[h_stem]:
                raise AstroDistributionRequestError(
                    f"{position} 柱藏干 {h_stem} 内核五行 {h_element!r} 与标准表不符")
            points.append({
                "point_id": f"{position}_hidden_{index}",
                "point_name": f"{PILLAR_NAMES_ZH[position]}支{pillar.get('branch', '')}藏{h_stem}",
                "kind": "hidden_stem",
                "attributes": {"signs": h_element,
                               "gods": _classify_group(hidden.get("ten_god"),
                                                       f"{position} 柱藏干{h_stem}"),
                               "polarity": STEM_YINYANG[h_stem]},
            })
    return points


def compute_bazi_distribution(chart, reading_config, label=None):
    points = collect_points(chart)
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "stems_plus_hidden",
         "description_zh": "四柱天干+地支藏干逐字计点（五行/阴阳图全计；十神图分母不含日干自身）"},
        SCHEMA_VERSION)
