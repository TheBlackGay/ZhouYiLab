"""六爻分布画像（图表数据包）：六亲重心 / 爻之五行 / 月令旺衰五态。

与 astro/ziwei/六壬/八字 画像同构，复用 build_package 通用构建器。
数据源为排盘既有字段（本卦六爻的 mainRelative/mainElement/wangShuai），
零新增算法、零口径发明：
* 三图共用同一 6 点集（本卦六爻），各图分母恒为六爻；
* 旺衰五态直接取内核 wangShuai——其月令映射已于 2026-09-20 按《翼氏大典》
  通行表修正（DEF-4，tests/test_wang_shuai_contract.py 锁表）；
* 文案全部为"卦面气象"描写（直发/上行/蓄力……），禁吉凶断语——
  六爻 calibration 仍为 pending（D1 范围已收窄至伏神/进退神等真流派项），
  画像只作结构化转译与情绪价值。
"""
import json
from pathlib import Path

from astro_distribution import (
    AstroDistributionConfigError,
    AstroDistributionRequestError,
    build_package,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "liuyao" / "distribution_reading.json"

SCHEMA_VERSION = "liuyao-distribution/1.0"
READING_SCHEMA = "liuyao-distribution-reading/1.0"

DIMENSIONS = ("rels", "signs", "states")

RELS_KEYS = {"父母", "兄弟", "子孙", "妻财", "官鬼"}
WUXING_KEYS = {"木", "火", "土", "金", "水"}
STATES_KEYS = {"旺", "相", "休", "囚", "死"}
YAO_POSITION_NAMES_ZH = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取六爻分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("六爻分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"六爻分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    tables = {"rels": RELS_KEYS, "signs": WUXING_KEYS, "states": STATES_KEYS}
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
        if chart_id == "rels" and not chart.get("summary_template_zh"):
            raise AstroDistributionConfigError("rels.summary_template_zh 缺失（summary 模板取自首图）")
    return raw


def collect_points(chart):
    """本卦六爻逐爻一点；三图属性=六亲/地支五行/月令旺衰。"""
    yao = chart.get("yao") if isinstance(chart, dict) else None
    if not isinstance(yao, list) or len(yao) != 6:
        raise AstroDistributionRequestError("chart 缺少完整六爻 yao 列表，不是六爻排盘结果")
    points = []
    for item in sorted(yao, key=lambda y: y.get("position", 0)):
        position = item.get("position")
        rel = item.get("mainRelative")
        element = item.get("mainElement")
        state = item.get("wangShuai")
        if rel not in RELS_KEYS:
            raise AstroDistributionRequestError(f"{position} 爻六亲 {rel!r} 无法归类")
        if element not in WUXING_KEYS:
            raise AstroDistributionRequestError(f"{position} 爻五行 {element!r} 无法归类")
        if state not in STATES_KEYS:
            raise AstroDistributionRequestError(f"{position} 爻旺衰 {state!r} 无法归类（DEF-4 修复后应仅含五态）")
        branch = (item.get("mainPillar") or {}).get("branch", "")
        points.append({
            "point_id": f"yao{position}",
            "point_name": f"{YAO_POSITION_NAMES_ZH.get(position, position)}爻{branch}",
            "kind": "ben_gua_yao",
            "attributes": {"rels": rel, "signs": element, "states": state},
        })
    return points


def compute_liuyao_distribution(chart, reading_config, label=None):
    points = collect_points(chart)
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "ben_gua_yao6",
         "description_zh": "本卦六爻纳甲既有字段（六亲/地支五行/月令旺衰），三图共用同一 6 点"},
        SCHEMA_VERSION)
