"""西洋占星分布画像（图表数据包）：元素 / 阴阳 / 三性质三张占比图。

设计约束（对齐平台原则）：
* 数据层自足：每个图表段自带中文 label/tag 与 percent，外部项目可直接渲染；
* 三图共用同一基准点集 `core14` = 十大行星（不含北交点 true_node）+ 四轴，
  点集与取法在 point_basis 中完整披露，保证可复现；
* 百分比用最大余数法归一，整数和恒等于 100；
* 解读文本是声明式配置 config/astro/distribution_reading.json 的模板，
  本模块只做插值，不即兴生成文案、不做吉凶断语；
* 本命盘由内核输出：行星带 sign 字符串；四轴仅给黄经，星座按 30° 区间反推。
"""
import json
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_READING_PATH = PROJECT_ROOT / "config" / "astro" / "distribution_reading.json"

SCHEMA_VERSION = "astro-distribution/1.0"
READING_SCHEMA = "astro-distribution-reading/1.0"

SIGN_ORDER = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
SIGN_ELEMENT = {
    "aries": "fire", "leo": "fire", "sagittarius": "fire",
    "taurus": "earth", "virgo": "earth", "capricorn": "earth",
    "gemini": "air", "libra": "air", "aquarius": "air",
    "cancer": "water", "scorpio": "water", "pisces": "water",
}
SIGN_MODALITY = {sign: ("cardinal", "fixed", "mutable")[index % 3]
                 for index, sign in enumerate(SIGN_ORDER)}
# 阳性=主动（白羊起交替），阴性=被动
SIGN_POLARITY = {sign: ("positive" if index % 2 == 0 else "negative")
                 for index, sign in enumerate(SIGN_ORDER)}

AXIS_ORDER = ("ascendant", "midheaven", "descendant", "imum_coeli")
AXIS_NAMES_ZH = {"ascendant": "上升", "midheaven": "天顶",
                 "descendant": "下降", "imum_coeli": "天底"}
CORE10 = ("sun", "moon", "mercury", "venus", "mars",
          "jupiter", "saturn", "uranus", "neptune", "pluto")

DIMENSIONS = ("element", "polarity", "modality")


class AstroDistributionRequestError(ValueError):
    pass


class AstroDistributionConfigError(ValueError):
    pass


def load_reading_config(path=DEFAULT_READING_PATH):
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AstroDistributionConfigError(f"无法读取分布解读配置 {path.name}: {error}") from error
    if raw.get("schema") != READING_SCHEMA:
        raise AstroDistributionConfigError("分布解读配置 schema 不符")
    charts = raw.get("charts") or {}
    if set(charts) != set(DIMENSIONS):
        raise AstroDistributionConfigError(
            f"分布解读配置必须恰好包含 {list(DIMENSIONS)}，实际 {sorted(charts)}")
    for chart_id, chart in charts.items():
        table = {"element": SIGN_ELEMENT, "polarity": SIGN_POLARITY, "modality": SIGN_MODALITY}[chart_id]
        keys = set(table.values())
        for field in ("labels_zh", "tags_zh", "dominant_templates_zh"):
            if set(chart.get(field, {})) != keys:
                raise AstroDistributionConfigError(f"{chart_id}.{field} 必须覆盖 {sorted(keys)}")
        if set(chart.get("readings_zh", {})) != keys | {"balanced"}:
            raise AstroDistributionConfigError(
                f"{chart_id}.readings_zh 必须覆盖 {sorted(keys)} 与 balanced")
        order = chart.get("order", [])
        if len(order) != len(set(order)) or set(order) != keys:
            raise AstroDistributionConfigError(f"{chart_id}.order 非法")
        if not chart.get("balanced_template_zh") or not chart.get("basis_zh"):
            raise AstroDistributionConfigError(f"{chart_id} 缺少 balanced_template_zh/basis_zh")
        if not chart.get("summary_template_zh"):
            raise AstroDistributionConfigError(f"{chart_id} 缺少 summary_template_zh")
        if set(chart.get("summary_phrases_zh", {})) != keys | {"balanced"}:
            raise AstroDistributionConfigError(
                f"{chart_id}.summary_phrases_zh 必须覆盖 {sorted(keys)} 与 balanced")
        if not chart.get("title_zh"):
            raise AstroDistributionConfigError(f"{chart_id} 缺少 title_zh")
        for key in keys | {"balanced"}:
            if not chart["readings_zh"].get(key):
                raise AstroDistributionConfigError(f"{chart_id}.readings_zh 缺 {key}")
    return raw


def _sign_from_longitude(longitude):
    if longitude is None:
        return None
    return SIGN_ORDER[int(math.floor((float(longitude) % 360.0) / 30.0)) % 12]


def collect_points(chart):
    """core14：十大行星（按内核既有顺序）+ 四轴（黄经反推星座）。"""
    if not isinstance(chart, dict):
        raise AstroDistributionRequestError("chart 必须是 JSON 对象")
    planets = chart.get("planets")
    angles = chart.get("angles")
    if not isinstance(planets, list) or not isinstance(angles, dict):
        raise AstroDistributionRequestError("chart 缺少 planets/angles，不是本命盘计算结果")
    points = []
    seen = set()
    for planet in planets:
        pid = planet.get("id")
        if pid not in CORE10 or pid in seen:
            continue
        sign = planet.get("sign")
        if sign not in SIGN_ELEMENT:
            raise AstroDistributionRequestError(f"行星 {pid} 缺少有效星座")
        seen.add(pid)
        points.append({"point_id": pid, "point_name": planet.get("name") or pid,
                       "kind": "planet", "sign": sign})
    missing = [pid for pid in CORE10 if pid not in seen]
    if missing:
        raise AstroDistributionRequestError(f"chart 缺少行星点位：{'、'.join(missing)}")
    for axis in AXIS_ORDER:
        if axis not in angles:
            raise AstroDistributionRequestError(f"chart 缺少四轴 {axis}")
        sign = _sign_from_longitude(angles[axis])
        if sign is None:
            raise AstroDistributionRequestError(f"四轴 {axis} 黄经缺失")
        points.append({"point_id": axis, "point_name": AXIS_NAMES_ZH[axis],
                       "kind": "angle", "sign": sign})
    return points


def _largest_remainder_percent(counts, total):
    """整数百分比、和恒为 100：先取 floor，再按余数从大到小补。"""
    if total <= 0:
        return [0] * len(counts)
    raw = [count * 100 / total for count in counts]
    base = [math.floor(value) for value in raw]
    remainder = 100 - sum(base)
    order = sorted(range(len(counts)),
                   key=lambda i: (-(raw[i] - base[i]), counts[i] * -1, i))
    for index in order[:remainder]:
        base[index] += 1
    return base


def _headline(chart_cfg, dominant_key, label):
    subject = f"「{label}」" if label else "这张盘"
    if dominant_key is None:
        return f"{subject}{chart_cfg['balanced_template_zh']}"
    template = chart_cfg["dominant_templates_zh"][dominant_key]
    text = template.format(tag=chart_cfg["tags_zh"][dominant_key],
                           label=chart_cfg["labels_zh"][dominant_key])
    return f"{subject}{text}"


def largest_remainder_percent(counts, total):
    """公开别名：整数百分比、和恒为 100（跨平台分布画像共用）。"""
    return _largest_remainder_percent(counts, total)


def build_package(points, dimensions, reading_config, label, basis, schema_version):
    """通用分布画像构建器。

    points: [{point_id, point_name, kind, attributes:{dimension_id: key}}]
    dimensions: [(chart_id, attr_key)]；解读文案一律来自声明式配置。
    """
    charts_out = []
    phrases = []
    global_total = len(points)
    for chart_id, attr_key in dimensions:
        chart_cfg = reading_config["charts"][chart_id]
        # 每图分母 = 具备该属性的点；亮度等只覆盖主星时，各图 basis_zh 自释分母
        counts_map = {}
        for point in points:
            key = point["attributes"].get(attr_key)
            if key is None:
                continue
            counts_map[key] = counts_map.get(key, 0) + 1
        keys = list(chart_cfg["order"])
        counts = [counts_map.get(key, 0) for key in keys]
        total = sum(counts)
        percents = _largest_remainder_percent(counts, total)
        segments = [{
            "key": key,
            "label_zh": chart_cfg["labels_zh"][key],
            "tag_zh": chart_cfg["tags_zh"][key],
            "count": count,
            "percent": percent,
        } for key, count, percent in zip(keys, counts, percents)]
        max_count = max(counts) if counts else 0
        winners = [key for key, count in zip(keys, counts) if count == max_count and count > 0]
        dominant_key = winners[0] if len(winners) == 1 else None
        reading_key = dominant_key if dominant_key is not None else "balanced"
        if dominant_key is not None:
            phrase = chart_cfg["summary_phrases_zh"][dominant_key].format(
                tag=chart_cfg["tags_zh"][dominant_key],
                label=chart_cfg["labels_zh"][dominant_key])
        else:
            phrase = chart_cfg["summary_phrases_zh"]["balanced"]
        phrases.append(phrase)
        if total <= 0:
            raise AstroDistributionRequestError(f"分布画像无可用点位：{chart_id}")
        charts_out.append({
            "id": chart_id,
            "title_zh": chart_cfg["title_zh"],
            "basis_zh": chart_cfg["basis_zh"],
            "point_total": total,
            "segments": segments,
            "dominant": None if dominant_key is None else {
                "key": dominant_key,
                "label_zh": chart_cfg["labels_zh"][dominant_key],
                "tag_zh": chart_cfg["tags_zh"][dominant_key],
                "percent": percents[keys.index(dominant_key)],
                "tied": False,
            },
            "headline_zh": _headline(chart_cfg, dominant_key, label),
            "reading_zh": chart_cfg["readings_zh"][reading_key],
        })
    summary_template = reading_config["charts"][charts_out[0]["id"]]["summary_template_zh"]
    subject = f"「{label}」" if label else "这张盘"
    return {
        "schema_version": schema_version,
        "point_basis": {**basis, "count": global_total, "points": [
            {k: point[k] for k in ("point_id", "point_name", "kind") if k in point}
            | ({"sign": point["sign"]} if "sign" in point else {})
            for point in points]},
        "label": label,
        "summary_zh": summary_template.format(subject=subject, phrases="，".join(phrases)),
        "charts": charts_out,
    }


def compute_distribution(chart, reading_config, label=None):
    points = collect_points(chart)
    tables = {"element": SIGN_ELEMENT, "polarity": SIGN_POLARITY, "modality": SIGN_MODALITY}
    for point in points:
        point["attributes"] = {dim: table[point["sign"]] for dim, table in tables.items()}
    return build_package(
        points,
        [(dim, dim) for dim in DIMENSIONS],
        reading_config, label,
        {"id": "core14",
         "description_zh": "十大行星（不含北交点）+ 上升/天顶/下降/天底四轴，三图共用同一分母"},
        SCHEMA_VERSION)
