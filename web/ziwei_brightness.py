import json
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "ziwei" / "star_brightness.json"
STAR_COLLECTIONS = (
    "zhu_xing",
    "fu_xing_detail",
    "sha_xing_detail",
    "za_yao_detail",
)


class BrightnessConfigError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def load_brightness_config(path=DEFAULT_CONFIG_PATH):
    config_path = Path(path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BrightnessConfigError("星曜亮度配置加载失败") from error

    branches = config.get("branches")
    allowed = set(config.get("allowed_values", []))
    stars = config.get("stars")
    aliases = config.get("aliases", {})
    if branches != ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]:
        raise BrightnessConfigError("亮度配置的十二地支顺序不正确")
    if not allowed or not isinstance(stars, dict) or not isinstance(aliases, dict):
        raise BrightnessConfigError("亮度配置结构不正确")
    for name, values in stars.items():
        if not isinstance(name, str) or not isinstance(values, list) or len(values) != 12:
            raise BrightnessConfigError(f"星曜 {name} 的亮度必须包含十二宫数据")
        invalid = [value for value in values if value is not None and value not in allowed]
        if invalid:
            raise BrightnessConfigError(f"星曜 {name} 包含无效亮度: {invalid}")
    for output_name, table_name in aliases.items():
        if table_name not in stars:
            raise BrightnessConfigError(f"星曜别名 {output_name} 指向不存在的表项")
    return config


def apply_star_brightness(chart, config=None):
    """Apply configured brightness by the star's physical earthly-branch palace."""
    if not isinstance(chart, dict):
        return chart
    config = config or load_brightness_config()
    branches = config["branches"]
    branch_indexes = {branch: index for index, branch in enumerate(branches)}
    aliases = config["aliases"]
    stars = config["stars"]

    for palace_index, palace in enumerate(chart.get("palaces", [])):
        if not isinstance(palace, dict):
            continue
        gan_zhi = palace.get("gan_zhi", "")
        branch = gan_zhi[-1:] if isinstance(gan_zhi, str) else ""
        branch_index = branch_indexes.get(branch, palace_index if palace_index < 12 else None)
        if branch_index is None:
            continue
        for collection in STAR_COLLECTIONS:
            for star in palace.get(collection, []):
                if not isinstance(star, dict):
                    continue
                output_name = star.get("name")
                table = stars.get(aliases.get(output_name, output_name))
                value = table[branch_index] if table else None
                if value is None:
                    star.pop("liang_du", None)
                else:
                    star["liang_du"] = value

    chart["brightness_table_version"] = config["table_version"]
    return chart


def apply_transit_star_brightness(result, config=None):
    if not isinstance(result, dict) or not isinstance(result.get("chart"), dict):
        return result
    config = config or load_brightness_config()
    chart = result["chart"]
    palaces = chart.get("palaces", [])
    branch_indexes = {branch: index for index, branch in enumerate(config["branches"])}
    aliases = config["aliases"]
    tables = config["stars"]

    for layer in result.get("fortune", {}).values():
        if not isinstance(layer, dict):
            continue
        for star in layer.get("transit_stars", []):
            if not isinstance(star, dict):
                continue
            palace_index = star.get("palace_index")
            if not isinstance(palace_index, int) or not 0 <= palace_index < len(palaces):
                continue
            gan_zhi = palaces[palace_index].get("gan_zhi", "")
            branch_index = branch_indexes.get(gan_zhi[-1:] if isinstance(gan_zhi, str) else "")
            table_name = aliases.get(star.get("name"), star.get("name"))
            table = tables.get(table_name)
            value = table[branch_index] if table and branch_index is not None else None
            if value is None:
                star.pop("liang_du", None)
            else:
                star["liang_du"] = value
    return result


def normalize_brightness_response(result):
    if not isinstance(result, dict):
        return result
    if isinstance(result.get("palaces"), list):
        apply_star_brightness(result)
    if isinstance(result.get("chart"), dict):
        apply_star_brightness(result["chart"])
        apply_transit_star_brightness(result)
    return result
