"""大六壬分布画像（图表数据包）：上神五行 / 遁干五行 / 上神阴阳。

与 astro/ziwei 画像同构，复用 build_package 通用构建器。
数据源为盘面既有字段（tian_di_pan 十二位），零新增算法、零口径发明：
* 地支五行/阴阳用与内核一致的标准表（子水丑土寅木……；阳支子寅辰午申戌）；
* 遁干五行取甲乙木丙丁火戊己土庚辛金壬癸水；旬空位无遁干、不入该图分母；
* 文案全部为"课面气象"描写（升发/升腾/稳重……），不含吉凶断语——
  大六壬算法 calibration 仍为 pending，画像只作结构化转译与情绪价值。
"""
import json
from pathlib import Path

from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    build_package,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "daliuren" / "distribution_reading.json"

SCHEMA_VERSION = "dlr-distribution/1.0"
READING_SCHEMA = "dlr-distribution-reading/1.0"

DIMENSIONS = ("signs", "stems", "polarity")

# 与内核 WuXingUtils.branchFiveElements 一致（tests 交叉锁定）
BRANCH_ELEMENT = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
                  "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
# 阳支：子寅辰午申戌；阴支：丑卯巳未酉亥
YANG_BRANCHES = {"子", "寅", "辰", "午", "申", "戌"}
STEM_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
                "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WUXING_KEYS = {"木", "火", "土", "金", "水"}


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取六壬分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("六壬分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"六壬分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    for chart_id, chart in charts.items():
        keys = WUXING_KEYS if chart_id in ("signs", "stems") else {"positive", "negative"}
        for field in ("labels_zh", "tags_zh", "dominant_templates_zh"):
            if set(chart.get(field, {})) != keys:
                raise AstroDistributionConfigError(f"{chart_id}.{field} 必须覆盖 {sorted(keys)}")
        if set(chart.get("order", [])) != keys or len(chart["order"]) != len(keys):
            raise AstroDistributionConfigError(f"{chart_id}.order 必须恰好是 {sorted(keys)}")
        if not keys.issubset(set(chart.get("readings_zh", {}))) or "balanced" not in chart["readings_zh"]:
            raise AstroDistributionConfigError(f"{chart_id}.readings_zh 覆盖不全")
        if not keys.issubset(set(chart.get("summary_phrases_zh", {}))) or "balanced" not in chart["summary_phrases_zh"]:
            raise AstroDistributionConfigError(f"{chart_id}.summary_phrases_zh 覆盖不全")
        for field in ("title_zh", "basis_zh", "balanced_template_zh", "summary_template_zh"):
            if not chart.get(field):
                raise AstroDistributionConfigError(f"{chart_id} 缺少 {field}")
    return raw


def collect_plate_points(chart):
    plate = chart.get("tian_di_pan") if isinstance(chart, dict) else None
    if not isinstance(plate, list) or len(plate) != 12:
        raise AstroDistributionRequestError("chart 缺少完整的 tian_di_pan 十二位，不是六壬课盘")
    points = []
    for slot in plate:
        upper = slot.get("tian_pan")
        if upper not in BRANCH_ELEMENT:
            raise AstroDistributionRequestError(f"位 {slot.get('position')} 上神 {upper!r} 无法归类")
        attributes = {
            "signs": BRANCH_ELEMENT[upper],
            "polarity": "positive" if upper in YANG_BRANCHES else "negative",
        }
        stem = slot.get("dun_gan") or ""
        if stem:
            if stem not in STEM_ELEMENT:
                raise AstroDistributionRequestError(f"位 {slot.get('position')} 遁干 {stem!r} 无法归类")
            attributes["stems"] = STEM_ELEMENT[stem]
        points.append({"point_id": slot.get("position") or upper,
                       "point_name": f"{slot.get('position', '')}宫上神{upper}",
                       "kind": "plate_slot", "attributes": attributes})
    return points


def compute_dlr_distribution(chart, reading_config, label=None):
    points = collect_plate_points(chart)
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "plate12",
         "description_zh": "十二宫天盘上神与遁干（课盘既有字段，零新增算法；遁干图分母为有干之宫）"},
        SCHEMA_VERSION)
