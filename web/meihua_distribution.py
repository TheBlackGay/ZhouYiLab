"""梅花易数卦面画像（图表数据包）：三卦六体五行 / 六卦月令旺衰 / 本卦阴阳爻。

与 astro/ziwei/六壬/八字/六爻 画像同构，复用 build_package 通用构建器。
数据源为 meihua-plate/1.0 事实盘既有字段（本互变三卦的上下卦五行、六爻卦码、
月令），零新增算法、零口径发明：
* 点集 12 点 = 六卦（五行/旺衰两图）+ 本卦六爻（阴阳图），各图分母自释；
* 旺衰用与内核一致的五态表（DEF-4 修复后口径），且**运行时交叉自检**：
  本卦上/下卦两点的画像值必须等于事实盘 ti_yong 的内核值，不一致即拒绝出图——
  月令表若与内核漂移，画像层第一时间爆炸而不是静默错图；
* 文案全部为"卦面气象"描写，禁吉凶断语——梅花 calibration=pending（D13 已拍板
  的仅是起卦口径，断语层押后至 M3 案例校准）。
"""
import json
from pathlib import Path

from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    build_package,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "meihua" / "distribution_reading.json"

SCHEMA_VERSION = "meihua-distribution/1.0"
READING_SCHEMA = "meihua-distribution-reading/1.0"

DIMENSIONS = ("signs", "states", "polarity")

# 与内核 WuXingUtils.branchFiveElements 一致（tests 交叉锁定）
BRANCH_ELEMENT = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
                  "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
GEN_ORDER = ["木", "火", "土", "金", "水"]  # 相生循环；相克为 +2
WUXING_KEYS = set(GEN_ORDER)
STATES_KEYS = {"旺", "相", "休", "囚", "死"}
YAO_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}

GUA_FIELDS = (("ben_gua", "本卦"), ("hu_gua", "互卦"), ("bian_gua", "变卦"))


def wang_shuai(element, month_branch):
    """月令五态（《翼氏大典》通行表，DEF-4 修复后内核同口径的画像侧实现）。"""
    if element not in WUXING_KEYS or month_branch not in BRANCH_ELEMENT:
        raise AstroDistributionRequestError(f"无法归类：{element!r} @ {month_branch!r}")
    month = BRANCH_ELEMENT[month_branch]
    ei, mi = GEN_ORDER.index(element), GEN_ORDER.index(month)
    if ei == mi:
        return "旺"
    if ei == (mi + 1) % 5:
        return "相"   # 月令生卦
    if ei == (mi + 4) % 5:
        return "休"   # 卦生月令
    if ei == (mi + 3) % 5:
        return "囚"   # 卦克月令
    return "死"       # 月令克卦


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取梅花分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("梅花分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"梅花分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    tables = {"signs": WUXING_KEYS, "states": STATES_KEYS, "polarity": {"positive", "negative"}}
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


def collect_points(plate):
    if not isinstance(plate, dict) or plate.get("schema_version") != "meihua-plate/1.0":
        raise AstroDistributionRequestError("不是 meihua-plate/1.0 事实盘")
    ba_zi = plate.get("ba_zi") or {}
    month_branch = ba_zi.get("month_command")
    if month_branch not in BRANCH_ELEMENT:
        raise AstroDistributionRequestError(f"月令 {month_branch!r} 无法归类")
    ti_yong = plate.get("ti_yong") or {}
    points = []
    for gua_key, gua_label in GUA_FIELDS:
        gua = plate.get(gua_key) or {}
        for side, side_zh, element_field, name_field in (
                ("outer", "上卦", "outer_element", "outer"),
                ("inner", "下卦", "inner_element", "inner")):
            element = gua.get(element_field)
            name = gua.get(name_field)
            if element not in WUXING_KEYS or not name:
                raise AstroDistributionRequestError(f"{gua_label}{side_zh}五行缺失或非法：{element!r}")
            points.append({
                "point_id": f"{gua_key}_{side}",
                "point_name": f"{gua_label}{side_zh}{name}",
                "kind": "trigram",
                "attributes": {"signs": element, "states": wang_shuai(element, month_branch)},
            })
    # 运行时交叉锁：本卦上下卦的画像旺衰必须等于内核体用字段
    ben = plate.get("ben_gua") or {}
    yao_code = ben.get("code")
    if (not isinstance(yao_code, str) or len(yao_code) != 6
            or any(c not in "01" for c in yao_code)):
        raise AstroDistributionRequestError("本卦卦码缺失或非法")
    engine_by_pos = {"upper": ti_yong.get("ti_wang_shuai") if ti_yong.get("ti") == "upper" else ti_yong.get("yong_wang_shuai"),
                     "lower": ti_yong.get("yong_wang_shuai") if ti_yong.get("ti") == "upper" else ti_yong.get("ti_wang_shuai")}
    for pos, side in (("upper", "outer"), ("lower", "inner")):
        point = next(p for p in points if p["point_id"] == f"ben_gua_{side}")
        if point["attributes"]["states"] != engine_by_pos[pos]:
            raise AstroDistributionRequestError(
                f"画像旺衰与内核交叉锁失败（{pos}：画像 {point['attributes']['states']}"
                f" vs 内核 {engine_by_pos[pos]}）——月令表漂移，拒绝出图")
    for position, bit in enumerate(yao_code, start=1):
        points.append({
            "point_id": f"ben_yao_{position}",
            "point_name": YAO_NAMES[position],
            "kind": "yao",
            "attributes": {"polarity": "positive" if bit == "1" else "negative"},
        })
    return points


def compute_meihua_distribution(plate, reading_config, label=None):
    points = collect_points(plate)
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "six_trigrams_plus_six_yao",
         "description_zh": "本互变三卦上下六卦（五行/旺衰图）+ 本卦六爻（阴阳图），共 12 观测点；各图分母自释"},
        SCHEMA_VERSION)
