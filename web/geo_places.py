#!/usr/bin/env python3
"""地名解析与时区推导内核（出生地点交互优化方案 G1）。

纯 Python、本地数据、不联网：地名检索、坐标解析、IANA 时区与夏令时推导、
软校验。契约与边界见 docs/product/西洋占星出生地点交互优化方案.md §4/§6/§7。

- 数据目录：``data/geo/``（curated.json + index.json），启动时一次性载入内存。
- 时区数据：Python 标准库 ``zoneinfo``；若安装了 pip 包 ``tzdata``，用
  ``reset_tzpath`` 固定到该包，保证开发机/CI/容器读到同一份数据（§6.4）。
- 本模块不产生任何命理结论，只陈述民用地名与时区法规事实（§3.8）。
"""
import bisect
import hashlib
import json
import math
import re
import struct
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:  # 可选依赖：把时区数据固定到 pip tzdata 包（§6.4）
    import tzdata as _tzdata_pkg  # type: ignore
except ImportError:  # pragma: no cover - 环境缺包时走系统数据
    _tzdata_pkg = None

import zoneinfo
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GEO_DATA_ROOT = PROJECT_ROOT / "data" / "geo"

MIN_YEAR = 1800
MAX_YEAR = 2200
MAX_QUERY_LENGTH = 64
DEFAULT_LIMIT = 20
MAX_LIMIT = 50
NEAREST_DEFAULT_RADIUS_KM = 300.0

_EPOCH = datetime(1970, 1, 1)


class GeoError(Exception):
    code = "GEO_ERROR"

    def user_message(self):
        return str(self) or self.code


class GeoConfigError(GeoError):
    """data/geo/ 缺失或 schema 不符（GEO_CONFIG_ERROR）。"""
    code = "GEO_CONFIG_ERROR"


class GeoNotFoundError(GeoError):
    """query / place_id 无匹配（PLACE_NOT_FOUND）。"""
    code = "PLACE_NOT_FOUND"


class GeoInvalidRequest(GeoError):
    """参数非法（INVALID_REQUEST）。"""
    code = "INVALID_REQUEST"


# ---------------------------------------------------------------------------
# 时区库版本固定与可用性探测（§6.4）
# ---------------------------------------------------------------------------

_TZ_ENV = None


def tz_environment():
    """(tzdata_version, tz_source, tz_available, tz_path)。只探测一次。"""
    global _TZ_ENV
    if _TZ_ENV is not None:
        return _TZ_ENV
    version, source = "unknown:runtime", "runtime"
    available = False
    try:
        if _tzdata_pkg is not None:
            package_dir = Path(_tzdata_pkg.__file__).resolve().parent / "zoneinfo"
            if package_dir.is_dir():
                # 固定到 pip tzdata 包，让开发机/CI/容器读到同一份数据
                zoneinfo.reset_tzpath([str(package_dir), *zoneinfo.TZPATH])
                version = (
                    getattr(_tzdata_pkg, "IANA_VERSION", None)
                    or getattr(_tzdata_pkg, "__version__", None)
                    or f"unknown:{package_dir}"
                )
                source = "tzdata-package"
        if source == "runtime":
            for root in zoneinfo.TZPATH:
                version_file = Path(root) / "+VERSION"
                if version_file.is_file():
                    text = version_file.read_text(encoding="utf-8").strip()
                    version = text or f"unknown:{root}"
                    source = "system"
                    break
            else:
                first = zoneinfo.TZPATH[0] if zoneinfo.TZPATH else "none"
                version = f"unknown:{first}"
                source = "system"
        available = True
        try:
            ZoneInfo("Asia/Shanghai").utcoffset(datetime(2000, 1, 1))
        except Exception:
            available = False
    except Exception:  # pragma: no cover - 极端环境
        available = False
    _TZ_ENV = (version, source, available, list(zoneinfo.TZPATH))
    return _TZ_ENV


def _zone(tz_name):
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# TZif 转换表解析：取切换点列表，用于夏令时区间与 LMT 判定（§4.4）
# ---------------------------------------------------------------------------

_TZIFF_CACHE = {}


def _find_zone_file(tz_name):
    if not re.fullmatch(r"[A-Za-z0-9_+./-]+", tz_name or ""):
        return None
    for root in zoneinfo.TZPATH:
        candidate = Path(root) / tz_name
        if candidate.is_file():
            return candidate
    return None


def _parse_tzif_transitions(data):
    """返回按 UTC 秒排序的 (transition_utc_seconds, utoff_seconds, isdst) 列表。

    优先解析 64 位（version 2/3）数据块；无切换点的时区返回 []。
    布局见 RFC 8536：header(44) + times + type_ids + ttinfos + leaps + std/ut + chars。
    """
    if len(data) < 44 or data[:4] != b"TZif":
        return []
    version = data[4:5]

    def block(pos, wide, counts):
        isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt = counts
        times = struct.unpack_from(f">{timecnt}{'q' if wide else 'i'}", data, pos) if timecnt else ()
        pos += timecnt * (8 if wide else 4)
        type_ids = data[pos:pos + timecnt]
        pos += timecnt
        ttinfos = []
        for _ in range(typecnt):
            utoff, isdst, _dstidx = struct.unpack_from(">lBB", data, pos)
            ttinfos.append((utoff, bool(isdst)))
            pos += 6
        pos += leapcnt * (12 if wide else 8) + isstdcnt + isutcnt + charcnt
        result = []
        for index, moment in enumerate(times):
            type_id = type_ids[index]
            if type_id < len(ttinfos):
                utoff, isdst = ttinfos[type_id]
                result.append((int(moment), int(utoff), isdst))
        return result, pos

    try:
        counts = struct.unpack_from(">6I", data, 20)
        v1, after_v1 = block(44, wide=False, counts=counts)
        if version and version >= b"2":
            # 精简版构建可能把全部切换点只放在 64 位块（v1 块 0 条），
            # v2 块前有独立的 44 字节头部与自己的计数。
            if data[after_v1:after_v1 + 4] != b"TZif" or len(data) < after_v1 + 64:
                return v1
            counts2 = struct.unpack_from(">6I", data, after_v1 + 20)
            v2, _ = block(after_v1 + 44, wide=True, counts=counts2)
            return v2 or v1
        return v1
    except (struct.error, IndexError, ValueError):
        return []


def _zone_transitions(tz_name):
    if tz_name in _TZIFF_CACHE:
        return _TZIFF_CACHE[tz_name]
    parsed = []
    path = _find_zone_file(tz_name)
    if path is not None:
        try:
            parsed = _parse_tzif_transitions(path.read_bytes())
        except OSError:
            parsed = []
    _TZIFF_CACHE[tz_name] = parsed
    return parsed


# ---------------------------------------------------------------------------
# 时刻偏移推导（§4.4）：A = utcoffset()，D = dst()，S = A − D
# ---------------------------------------------------------------------------

def _minutes(td):
    if td is None:
        return 0
    return int(td.total_seconds() // 60)


def offset_info(tz_name, when_local):
    """按本地墙钟时刻推导 {utc_offset_minutes, std_offset_minutes, dst_minutes, dst_active}。"""
    zone = _zone(tz_name)
    if zone is None or when_local is None:
        return None
    naive = when_local.replace(tzinfo=None)
    local = naive.replace(tzinfo=zone)
    actual = _minutes(local.utcoffset())
    dst_delta = _minutes(local.dst())
    return {
        "utc_offset_minutes": actual,
        "std_offset_minutes": actual - dst_delta,
        "dst_minutes": dst_delta,
        "dst_active": dst_delta > 0,
    }


def _birth_utc_seconds(when_local, offset_minutes):
    """本地墙钟 → UTC epoch 秒（近似；不处理折返小时的歧义，对推导区间足够）。"""
    return int((when_local.replace(tzinfo=None) - _EPOCH).total_seconds()) - offset_minutes * 60


def _utc_moment_to_local_date(moment, utoff_seconds):
    return (_EPOCH + timedelta(seconds=moment + utoff_seconds)).date()


def offset_window(tz_name, when_local):
    """返回该时刻所处偏移区间的本地 (start_date, resume_date)。

    start：当前规则段生效的本地日期；resume：下一切换点恢复的本地日期（可 None）。
    夏令时止日 = resume 前一天（方案 §4.2 文案规则，不把切换日当成夏令时结束日）。
    """
    info = offset_info(tz_name, when_local)
    transitions = _zone_transitions(tz_name)
    if info is None or not transitions:
        return None, None
    birth_utc = _birth_utc_seconds(when_local, info["utc_offset_minutes"])
    instants = [moment for moment, _utoff, _isdst in transitions]
    index = bisect.bisect_right(instants, birth_utc) - 1
    start = None
    if 0 <= index < len(transitions):
        moment, utoff, _ = transitions[index]
        start = _utc_moment_to_local_date(moment, utoff)
    resume = None
    if 0 <= index + 1 < len(transitions):
        moment, utoff, _ = transitions[index + 1]
        resume = _utc_moment_to_local_date(moment, utoff)
    return start, resume


def is_lmt_era(tz_name, birth_day):
    """出生日早于该时区首个切换点（本地日期）→ 地方平时（LMT）段。

    判定是数据驱动的，不写死年份（§4.4）：对 Asia/Shanghai 首切换点是
    1901-01-01（之前 +8:05:43），各时区不同。无切换记录视为固定偏移，不算 LMT。
    """
    transitions = _zone_transitions(tz_name)
    if not transitions:
        return False
    moment, utoff, _ = transitions[0]
    first_local_day = _utc_moment_to_local_date(moment, utoff)
    return birth_day < first_local_day


# ---------------------------------------------------------------------------
# 地名库载入与检索（§6.3）
# ---------------------------------------------------------------------------

def normalize_text(text):
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return "".join(ch for ch in folded if not ch.isspace())


def _is_cjk(text):
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def _slug_ascii(text):
    return "".join(ch for ch in normalize_text(text) if ch.isascii() and ch.isalnum())


class PlacesIndex:
    def __init__(self, places, revision, groups, source="curated"):
        self.places = places
        self.revision = revision
        self.groups = groups
        self.source = source
        self.by_id = {place["id"]: place for place in places}
        self._search_forms = []
        for place in places:
            zh_forms = {normalize_text(place["name_zh"])}
            trimmed = place["name_zh"].rstrip("市")
            if trimmed:
                zh_forms.add(normalize_text(trimmed))
            ascii_forms = set()
            for field in (place["name_en"], *place.get("aliases", [])):
                slug = _slug_ascii(field)
                if slug:
                    ascii_forms.add(slug)
            self._search_forms.append({
                "id": place["id"],
                "zh": zh_forms,
                "ascii": ascii_forms,
            })

    def meta(self):
        return {
            "revision": self.revision,
            "count": len(self.places),
            "groups": dict(self.groups),
            "source": self.source,
        }


def load_places(path=GEO_DATA_ROOT):
    root = Path(path)
    curated_file = root / "curated.json"
    index_file = root / "index.json"
    if not curated_file.is_file() or not index_file.is_file():
        raise GeoConfigError(f"地名库缺失：{root} 下需要 curated.json 与 index.json")
    try:
        index = json.loads(index_file.read_text(encoding="utf-8"))
        places = json.loads(curated_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GeoConfigError(f"地名库读取失败：{error}") from error
    shard = (index.get("shards") or {}).get("curated") or {}
    revision = shard.get("revision") or index.get("revision")
    if not revision:
        raise GeoConfigError("地名库 index.json 缺少 revision")
    body = curated_file.read_text(encoding="utf-8")
    checksum = shard.get("sha256")
    if checksum and hashlib.sha256(body.encode("utf-8")).hexdigest() != checksum:
        raise GeoConfigError("地名库校验和不匹配（curated.json 与 index.json 不同版）")
    if not isinstance(places, list) or not places:
        raise GeoConfigError("地名库 curated.json 为空或非数组")
    required = ("id", "name_zh", "name_en", "aliases", "admin1", "country_zh",
                "country_code", "lat", "lon", "approx_radius_km", "tz", "level", "source")
    for place in places:
        if not isinstance(place, dict) or any(key not in place for key in required):
            pid = place.get("id") if isinstance(place, dict) else place
            raise GeoConfigError(f"地名库条目不符合 schema：{pid}")
        if not (-90 <= place["lat"] <= 90 and -180 <= place["lon"] <= 180):
            raise GeoConfigError(f"地名库条目坐标越界：{place['id']}")
    groups = {}
    for place in places:
        groups[place.get("group", "?")] = groups.get(place.get("group", "?"), 0) + 1
    return PlacesIndex(places, revision, groups)


_DEFAULT_INDEX = None


def default_index():
    global _DEFAULT_INDEX
    if _DEFAULT_INDEX is None:
        # 在调用时刻读取 GEO_DATA_ROOT（而非 def 时绑定），便于测试与部署覆盖
        _DEFAULT_INDEX = load_places(GEO_DATA_ROOT)
    return _DEFAULT_INDEX


def place_hit(place, score=None, distance_km=None, matched_via=None):
    hit = {
        "id": place["id"],
        "display": place["name_zh"] or place["name_en"],
        "name_zh": place["name_zh"],
        "name_en": place["name_en"],
        "admin1": place["admin1"],
        "country_zh": place["country_zh"],
        "country_code": place["country_code"],
        "lat": place["lat"],
        "lon": place["lon"],
        "tz": place["tz"],
        "level": place["level"],
        "approx_radius_km": place["approx_radius_km"],
        "population": place.get("population"),
    }
    if score is not None:
        hit["score"] = round(score, 2)
    if distance_km is not None:
        hit["distance_km"] = round(distance_km, 1)
    if matched_via is not None:
        hit["matched_via"] = matched_via
    return hit


def _population_bonus(place):
    population = place.get("population") or 0
    if population <= 0:
        return 0.0
    return max(0.0, (math.log10(population + 1) - 5) * 8)


def search_places(index, query, limit=DEFAULT_LIMIT, country=None):
    query = (query or "").strip()
    normalized = normalize_text(query)
    if not normalized:
        raise GeoInvalidRequest("搜索词 q 不能为空")
    if len(normalized) > MAX_QUERY_LENGTH:
        raise GeoInvalidRequest(f"搜索词 q 超过 {MAX_QUERY_LENGTH} 字符上限")
    limit = int(limit)
    if not 1 <= limit <= MAX_LIMIT:
        raise GeoInvalidRequest(f"limit 必须在 1 到 {MAX_LIMIT} 之间")
    query_is_cjk = _is_cjk(normalized)
    query_ascii = "" if query_is_cjk else "".join(ch for ch in normalized if ch.isascii() and ch.isalnum())
    if not query_is_cjk and len(query_ascii) < 2:
        # 拼音/英文需 2 个字符才触发（§4.1：中文 1 个字即可）
        return []
    country_filter = (country or "").strip().upper() or None
    scored = []
    for forms in index._search_forms:
        place = index.by_id[forms["id"]]
        if country_filter and place["country_code"] != country_filter:
            continue
        best = 0.0
        via = None
        for form in forms["zh"]:
            if normalized == form:
                best, via = 100.0, "zh_exact"
                break
            if query_is_cjk:
                if form.startswith(normalized) and 85.0 > best:
                    best, via = 85.0, "zh_prefix"
                elif normalized in form and 55.0 > best:
                    best, via = 55.0, "zh_substring"
        if best < 100.0 and query_ascii:
            for form in forms["ascii"]:
                if form == query_ascii:
                    best, via = 100.0, "ascii_exact"
                    break
                if form.startswith(query_ascii):
                    # 前缀命中 > 子串命中；全拼/英文名权重高于首字母缩写（§6.3）
                    weight = 80.0 if len(form) > 4 else 70.0
                    if weight > best:
                        best, via = weight, "ascii_prefix"
        if best > 0:
            scored.append((best + _population_bonus(place), place, via))
    scored.sort(key=lambda item: (-item[0], -_population_bonus(item[1]), item[1]["id"]))
    return [place_hit(place, score=score, matched_via=via) for score, place, via in scored[:limit]]


def _haversine_km(lat1, lon1, lat2, lon2):
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    chord = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(chord)))


def nearest_place(index, lat, lon, radius_km=NEAREST_DEFAULT_RADIUS_KM):
    """坐标反查最近城市；仅作提示，不改变状态机（§4.7）。"""
    best = None
    best_distance = None
    for place in index.places:
        distance = _haversine_km(lat, lon, place["lat"], place["lon"])
        if best_distance is None or distance < best_distance:
            best, best_distance = place, distance
    if best is None or best_distance > radius_km:
        return None
    return place_hit(best, distance_km=best_distance)


# ---------------------------------------------------------------------------
# 软校验（§4.6，不阻断；⚠ 只在证据区呈现）
# ---------------------------------------------------------------------------

def _fmt_offset_label(minutes):
    total = int(minutes)
    sign = "-" if total < 0 else "+"
    value = abs(total)
    hours, rest = divmod(value, 60)
    label = f"UTC{sign}{hours}" if rest == 0 else f"UTC{sign}{hours}:{rest:02d}"
    return f"{label}（{total} 分钟）"


def _wrap180(degrees):
    return (degrees + 180) % 360 - 180


def check_location_consistency(*, utc_offset_minutes=None, lat=None, lon=None,
                               house_system=None, auto_info=None, approx_radius_km=None):
    """五条软校验（§4.6）。只提醒，不阻断提交。"""
    warnings = []
    if utc_offset_minutes is not None and lon is not None:
        expected = utc_offset_minutes / 60 * 15
        if abs(_wrap180(expected - lon)) > 30:
            typical = round(lon / 15)
            typical_label = f"{'UTC+' if typical >= 0 else 'UTC-'}{abs(typical)}"
            current_label = f"{'UTC+' if utc_offset_minutes / 60 >= 0 else 'UTC-'}{abs(utc_offset_minutes) / 60:g}"
            warnings.append({
                "code": "offset_longitude_mismatch",
                "level": "warning",
                "text": f"经度 {abs(lon):.1f}°{'E' if lon >= 0 else 'W'} 通常对应 "
                        f"{typical_label}，当前为 {current_label}，请确认。",
            })
    if lat is not None and lon is not None and abs(lat) < 0.5 and abs(lon) < 0.5:
        warnings.append({
            "code": "near_zero_coordinates",
            "level": "warning",
            "text": "该坐标位于几内亚湾近海，通常是坐标未填写。",
        })
    if lat is not None and abs(lat) > 66 and (house_system or "").lower() == "placidus":
        warnings.append({
            "code": "polar_placidus",
            "level": "warning",
            "text": "Placidus 宫制在极区可能无法计算，建议改用 Whole Sign。",
        })
    if auto_info and utc_offset_minutes is not None:
        actual = auto_info["utc_offset_minutes"]
        std = auto_info["std_offset_minutes"]
        if auto_info["dst_minutes"] > 0 and std != actual and utc_offset_minutes == std:
            warnings.append({
                "code": "dst_not_applied",
                "level": "warning",
                "text": f"该日期当地处于夏令时（+{auto_info['dst_minutes']} 分钟），"
                        f"当前按标准时 {_fmt_offset_label(utc_offset_minutes)} 计算。",
            })
    if approx_radius_km is not None and approx_radius_km > 50:
        warnings.append({
            "code": "city_level_radius",
            "level": "notice",
            "text": "该地点为城市级代表点，范围较大，建议微调到出生区县。",
        })
    return warnings


# ---------------------------------------------------------------------------
# 解析入口（§6.5）
# ---------------------------------------------------------------------------

def _parse_birth_date(date_obj):
    if not isinstance(date_obj, dict):
        raise GeoInvalidRequest("必须提供 date（含 year/month/day）")
    try:
        year = int(date_obj["year"])
        month = int(date_obj["month"])
        day = int(date_obj["day"])
        hour = int(date_obj.get("hour") if date_obj.get("hour") is not None else 12)
        minute = int(date_obj.get("minute") if date_obj.get("minute") is not None else 0)
    except (KeyError, TypeError, ValueError) as error:
        raise GeoInvalidRequest(f"date 字段非法：{error}") from error
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise GeoInvalidRequest(f"年份必须在 {MIN_YEAR}-{MAX_YEAR} 之间")
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise GeoInvalidRequest("hour/minute 越界")
    try:
        when_local = datetime(year, month, day, hour, minute)
    except ValueError as error:
        raise GeoInvalidRequest(f"日期非法：{error}") from error
    return when_local


def resolve_place(index, *, place_id=None, query=None, lat=None, lon=None,
                  birth_date=None, utc_offset_minutes=None, house_system=None):
    """地名/坐标 → PlaceResolution（§6.5 结构）。warnings 始终返回（§7）。"""
    when_local = _parse_birth_date(birth_date)
    sources = [
        place_id is not None and str(place_id).strip() != "",
        query is not None and str(query).strip() != "",
        lat is not None and lon is not None,
    ]
    if sum(1 for flag in sources if flag) != 1:
        raise GeoInvalidRequest("place_id、query、latitude/longitude 必须且只能提供一种")

    place = None
    confidence = None
    derived_from = None
    if sources[0]:
        place = index.by_id.get(str(place_id).strip())
        if place is None:
            raise GeoNotFoundError(f"未收录地点：{place_id}")
        confidence = "exact" if place["level"] == "district" else "city"
        derived_from = "place"
    elif sources[1]:
        hits = search_places(index, query, limit=1)
        if not hits:
            raise GeoNotFoundError(f"没有找到「{query}」")
        place = index.by_id[hits[0]["id"]]
        confidence = "exact" if place["level"] == "district" else "city"
        derived_from = "query"
    else:
        lat = float(lat)
        lon = float(lon)
        if not -90 <= lat <= 90:
            raise GeoInvalidRequest("latitude 必须在 -90 到 90 之间")
        if not -180 <= lon <= 180:
            raise GeoInvalidRequest("longitude 必须在 -180 到 180 之间")
        nearest = nearest_place(index, lat, lon)
        if nearest is not None:
            place = index.by_id[nearest["id"]]
            confidence = "approximate"
            derived_from = "nearest"
        else:
            confidence = "approximate"
            derived_from = "coordinate_only"

    # 坐标优先取用户显式输入（手动路径），否则取地点代表点
    effective_lat = float(lat) if lat is not None else place["lat"]
    effective_lon = float(lon) if lon is not None else place["lon"]
    tz_name = place["tz"] if place else None

    version, source, tz_available, _tz_path = tz_environment()
    info = offset_info(tz_name, when_local) if (tz_name and tz_available) else None

    time_block = {
        "utc_offset_minutes": None,
        "std_offset_minutes": None,
        "dst_minutes": 0,
        "dst_active": False,
        "dst_transition": None,
        "confidence": confidence,
        "tz_available": bool(info),
        "tz_name": tz_name,
    }
    warnings = []
    provenance = {
        "dataset": index.source,
        "dataset_revision": index.revision,
        "derived_from": derived_from,
        "tzdata_version": version,
        "tz_source": source,
        "rule": None,
        "birth_date": when_local.strftime("%Y-%m-%d"),
        "birth_time_used": when_local.strftime("%H:%M"),
    }
    if info is not None:
        time_block.update({
            "utc_offset_minutes": info["utc_offset_minutes"],
            "std_offset_minutes": info["std_offset_minutes"],
            "dst_minutes": info["dst_minutes"],
            "dst_active": info["dst_active"],
        })
        provenance["rule"] = f"zoneinfo:{tz_name}"
        start, resume = offset_window(tz_name, when_local)
        if start or resume:
            time_block["dst_transition"] = {
                "start": start.isoformat() if start else None,
                "end": (resume - timedelta(days=1)).isoformat() if resume else None,
                "resume": resume.isoformat() if resume else None,
            }
        if is_lmt_era(tz_name, when_local.date()):
            time_block["confidence"] = "uncertain"
            warnings.append({
                "code": "lmt_uncertain",
                "level": "warning",
                "text": "该日期当地使用地方平时（LMT），偏移含秒级成分，引擎按整数分钟取整"
                        "（误差 ≤30 秒），无法用整数分钟精确表达，请确认。",
            })
    elif tz_name:
        warnings.append({
            "code": "tz_unavailable",
            "level": "warning",
            "text": "时区数据不可用，偏移未能自动推导，请手动选择时区（不影响坐标解析）。",
        })

    effective_offset = utc_offset_minutes
    if effective_offset is not None:
        effective_offset = int(effective_offset)
        if not -720 <= effective_offset <= 840:
            raise GeoInvalidRequest("utc_offset_minutes 必须在 -720 到 840 之间（引擎口径）")
    warnings.extend(check_location_consistency(
        utc_offset_minutes=effective_offset if effective_offset is not None else (
            info["utc_offset_minutes"] if info else None),
        lat=effective_lat,
        lon=effective_lon,
        house_system=house_system,
        auto_info=info,
        approx_radius_km=place["approx_radius_km"] if place is not None else None,
    ))

    place_block = None
    if place is not None:
        place_block = place_hit(place)
        if derived_from == "nearest":
            place_block["display"] = f"约：{place_block['display']}"
    return {
        "place": place_block,
        "location": {"latitude": effective_lat, "longitude": effective_lon},
        "time": time_block,
        "provenance": provenance,
        "warnings": warnings,
    }


def geo_meta(index=None):
    version, source, tz_available, tz_path = tz_environment()
    try:
        meta = (index or default_index()).meta()
    except GeoError as error:
        meta = {"revision": None, "count": 0, "groups": {}, "source": None,
                "config_error": error.code}
    meta.update({
        "tzdata_version": version,
        "tz_source": source,
        "tz_available": tz_available,
        "tz_path": tz_path,
    })
    return meta
