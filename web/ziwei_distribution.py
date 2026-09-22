"""紫微斗数分布画像（图表数据包）：星系气质 / 阴阳星性 / 星光明暗。

与 astro_distribution 同构（复用 build_package 通用构建器），差异只在点位采集：
* presence28（`point_basis.id`，旧注释误作 core28）：全盘十四主星 + 六吉六煞二辅
  （`sha_xing` 与 `fu_xing` 文档重叠，按名去重）；
* 星性（五行、阴阳）与亮度一律来自内核 symbols 导出（安星诀文档库为唯一数据源），
  配置层不手编任何映射；
* 明暗图仅统计有亮度字段的十四主星（辅煞亮度未入档），各图 basis 自释分母。
"""
import json
from pathlib import Path

from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    build_package,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "ziwei" / "distribution_reading.json"

SCHEMA_VERSION = "ziwei-distribution/1.0"
READING_SCHEMA = "ziwei-distribution-reading/1.0"

DIMENSIONS = ("temperament", "polarity", "light")
POLARITY_MAP = {"阳": "positive", "阴": "negative"}
# 内核亮度七等：庙旺得平陷不利
LIGHT_MAP = {"庙": "bright", "旺": "bright", "得": "steady", "平": "steady",
             "陷": "dim", "不": "dim", "利": "dim"}
EXPECTED_KEYS = {
    "temperament": {"火", "木", "土", "金", "水"},
    "polarity": {"positive", "negative"},
    "light": {"bright", "steady", "dim"},
}


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取紫微分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("紫微分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"紫微分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    for chart_id, chart in charts.items():
        keys = EXPECTED_KEYS[chart_id]
        for field in ("labels_zh", "tags_zh", "dominant_templates_zh",
                      "summary_phrases_zh", "readings_zh"):
            if not keys.issubset(set(chart.get(field, {}))):
                raise AstroDistributionConfigError(f"{chart_id}.{field} 必须覆盖 {sorted(keys)}")
        if not keys == set(chart.get("order", [])):
            raise AstroDistributionConfigError(f"{chart_id}.order 必须恰好是 {sorted(keys)}")
        for field in ("title_zh", "basis_zh", "balanced_template_zh", "summary_template_zh"):
            if not chart.get(field):
                raise AstroDistributionConfigError(f"{chart_id} 缺少 {field}")
        if "balanced" not in chart["readings_zh"] or "balanced" not in chart["summary_phrases_zh"]:
            raise AstroDistributionConfigError(f"{chart_id} 缺 balanced 文案")
    return raw


def _iter_palace_stars(palaces):
    for palace in palaces:
        for entry in palace.get("zhu_xing") or []:
            if isinstance(entry, dict):
                yield entry.get("name"), entry.get("liang_du"), "zhu"
            else:
                yield entry, None, "zhu"
        for group in ("fu_xing", "sha_xing"):
            for name in palace.get(group) or []:
                entry_name = name.get("name") if isinstance(name, dict) else name
                yield entry_name, None, "fu"


def collect_star_points(chart, symbols):
    temperament = (symbols or {}).get("star_temperament")
    if not isinstance(temperament, list) or not temperament:
        raise AstroDistributionRequestError(
            "内核 symbols 无 star_temperament：请重新构建 zi_wei_web_cli（ziwei-symbols/1.1）")
    star_map = {entry["name"]: entry for entry in temperament}
    points, seen = [], set()
    palaces = chart.get("palaces") if isinstance(chart, dict) else None
    if not isinstance(palaces, list):
        raise AstroDistributionRequestError("chart 缺少 palaces，不是紫微本命盘")
    for name, liang_du, group in _iter_palace_stars(palaces):
        if not name or name in seen:
            continue
        entry = star_map.get(name)
        if entry is None:
            continue
        seen.add(name)
        attributes = {}
        if entry.get("element"):
            attributes["temperament"] = entry["element"]
        mapped_polarity = POLARITY_MAP.get(entry.get("polarity"))
        if mapped_polarity:
            attributes["polarity"] = mapped_polarity
        if group == "zhu" and liang_du and LIGHT_MAP.get(liang_du):
            attributes["light"] = LIGHT_MAP[liang_du]
        points.append({"point_id": name, "point_name": name,
                       "kind": "star", "attributes": attributes})
    if len(points) < 14:
        raise AstroDistributionRequestError(f"命盘主星不完整（识别 {len(points)} 颗），无法出画像")
    return points


def compute_ziwei_distribution(chart, symbols, reading_config, label=None):
    points = collect_star_points(chart, symbols)
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "presence28",
         "description_zh": "全盘十四主星＋六吉六煞二辅（内核星性文档为唯一数据源；明暗图分母为十四主星亮度）"},
        SCHEMA_VERSION)
