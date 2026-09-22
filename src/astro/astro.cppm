module;

#include "swephexp.h"

export module ZhouYi.Astro;

import std;
import ZhouYi.Common.DateTime;

export namespace ZhouYi::Astro {

enum class Zodiac { Tropical, Sidereal };
enum class HouseSystem { Placidus, WholeSign };

struct ChartRequest {
    int year = 2000;
    int month = 1;
    int day = 1;
    int hour = 12;
    int minute = 0;
    int second = 0;
    int utc_offset_minutes = 0;
    double latitude = 0.0;
    double longitude = 0.0;
    double elevation_m = 0.0;
    Zodiac zodiac = Zodiac::Tropical;
    std::string ayanamsa = "none";
    HouseSystem house_system = HouseSystem::Placidus;
    std::vector<std::string> points;
    bool include_aspects = true;
    bool allow_moshier_fallback = false;
};

struct TransitRequest {
    ChartRequest natal;
    ChartRequest target;
    std::vector<std::string> transit_points;
    std::vector<std::string> natal_points;
    bool include_aspects = true;
    bool allow_moshier_fallback = false;
};

struct PlanetPosition {
    std::string id;
    std::string name;
    double longitude = 0.0;
    double latitude = 0.0;
    double distance_au = 0.0;
    double longitude_speed = 0.0;
    std::string sign;
    std::string sign_name;
    double degree_in_sign = 0.0;
    int house = 0;
    bool retrograde = false;
    bool stationary = false;
};

struct HouseCusp {
    int number = 0;
    double cusp = 0.0;
    std::string sign;
    std::string sign_name;
};

struct Aspect {
    std::string first;
    std::string second;
    std::string type;
    double exact_angle = 0.0;
    double actual_angle = 0.0;
    double orb = 0.0;
    bool applying = false;
};

struct ChartResult {
    ChartRequest request;
    double julian_day_ut = 0.0;
    std::string ephemeris = "swiss";
    std::string ephemeris_version = "swisseph-upstream";
    std::string precision_mode = "high";
    std::vector<std::string> warnings;
    double ascendant = 0.0;
    double midheaven = 0.0;
    double descendant = 0.0;
    double imum_coeli = 0.0;
    std::vector<PlanetPosition> planets;
    std::vector<HouseCusp> houses;
    std::vector<Aspect> aspects;
};

struct TransitAspect {
    std::string transit_point;
    std::string natal_point;
    std::string type;
    double exact_angle = 0.0;
    double actual_angle = 0.0;
    double orb = 0.0;
    bool applying = false;
};

struct TransitResult {
    TransitRequest request;
    ChartResult natal;
    ChartResult target;
    std::vector<PlanetPosition> transit_planets;
    std::vector<TransitAspect> aspects;
    std::string precision_mode = "high";
    std::vector<std::string> warnings;
};

class AstroError : public std::runtime_error {
public:
    AstroError(std::string code, std::string message)
        : std::runtime_error(std::move(message)), code_(std::move(code)) {}

    const std::string& code() const noexcept { return code_; }

private:
    std::string code_;
};

namespace detail {

struct PointSpec {
    const char* id;
    const char* name;
    int body;
    bool derived = false;
};

inline constexpr std::array<PointSpec, 12> point_specs{{
    {"sun", "太阳", SE_SUN}, {"moon", "月亮", SE_MOON},
    {"mercury", "水星", SE_MERCURY}, {"venus", "金星", SE_VENUS},
    {"mars", "火星", SE_MARS}, {"jupiter", "木星", SE_JUPITER},
    {"saturn", "土星", SE_SATURN}, {"uranus", "天王星", SE_URANUS},
    {"neptune", "海王星", SE_NEPTUNE}, {"pluto", "冥王星", SE_PLUTO},
    {"true_node", "北交点", SE_TRUE_NODE}, {"chiron", "凯龙星", SE_CHIRON}
}};

inline constexpr std::array<std::string_view, 12> sign_ids{
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
};
inline constexpr std::array<std::string_view, 12> sign_names{
    "白羊座", "金牛座", "双子座", "巨蟹座", "狮子座", "处女座",
    "天秤座", "天蝎座", "射手座", "摩羯座", "水瓶座", "双鱼座"
};

inline const PointSpec* find_point(std::string_view id) {
    for (const auto& spec : point_specs) {
        if (id == spec.id) return &spec;
    }
    return nullptr;
}

inline double normalize(double value) {
    value = std::fmod(value, 360.0);
    if (value < 0.0) value += 360.0;
    return value;
}

inline std::pair<std::string, std::string> sign_for(double longitude) {
    const auto normalized = normalize(longitude);
    const auto index = static_cast<std::size_t>(normalized / 30.0) % 12;
    return {std::string(sign_ids[index]), std::string(sign_names[index])};
}

inline double julian_day_ut(const ChartRequest& request) {
    int year = request.year;
    int month = request.month;
    const double local_day = static_cast<double>(request.day)
        + (request.hour * 3600.0 + request.minute * 60.0 + request.second
            - request.utc_offset_minutes * 60.0) / 86400.0;
    if (month <= 2) {
        --year;
        month += 12;
    }
    const int century = year / 100;
    const int correction = 2 - century + century / 4;
    return std::floor(365.25 * (year + 4716))
        + std::floor(30.6001 * (month + 1))
        + local_day + correction - 1524.5;
}

inline void validate(const ChartRequest& request) {
    const ZhouYi::Common::SolarDateTime date{
        request.year, request.month, request.day,
        request.hour, request.minute, request.second
    };
    if (!ZhouYi::Common::DateTime::is_valid_solar_date_time(date)) {
        throw AstroError("INVALID_REQUEST", "日期时间无效");
    }
    if (request.utc_offset_minutes < -720 || request.utc_offset_minutes > 840) {
        throw AstroError("INVALID_REQUEST", "UTC 偏移必须在 -720 到 840 分钟之间");
    }
    if (request.latitude < -90.0 || request.latitude > 90.0
        || request.longitude < -180.0 || request.longitude > 180.0) {
        throw AstroError("INVALID_REQUEST", "经纬度超出范围");
    }
    if (request.zodiac == Zodiac::Tropical && request.ayanamsa != "none") {
        throw AstroError("INVALID_REQUEST", "回归黄道的 ayanamsa 必须为 none");
    }
    if (request.zodiac == Zodiac::Sidereal && request.ayanamsa != "fagan_bradley") {
        throw AstroError("INVALID_REQUEST", "当前仅支持 fagan_bradley 岁差模型");
    }
    if (request.house_system == HouseSystem::Placidus
        && (request.latitude <= -89.999999 || request.latitude >= 89.999999)) {
        throw AstroError("HOUSE_CALCULATION_FAILED", "Placidus 不支持极点纬度");
    }
}

inline void initialize_ephemeris() {
    static std::once_flag once;
    std::call_once(once, [] {
        const char* configured = std::getenv("ZHOUYILAB_EPHEMERIS_PATH");
        swe_set_ephe_path(configured && *configured ? configured : nullptr);
        std::atexit([] { swe_close(); });
    });
}

inline const char* house_code(HouseSystem system) {
    return system == HouseSystem::WholeSign ? "W" : "P";
}

inline bool is_major(double actual, double exact, double& orb) {
    orb = std::abs(actual - exact);
    return orb <= 8.0;
}

inline int house_for_longitude(double longitude, const std::vector<HouseCusp>& houses) {
    const auto normalized = normalize(longitude);
    for (const auto& house : houses) {
        const double start = normalize(house.cusp);
        const auto next = house.number == 12 ? houses.front().cusp : houses[house.number].cusp;
        const double end = normalize(next);
        const bool contains = start <= end ? normalized >= start && normalized < end
            : normalized >= start || normalized < end;
        if (contains) return house.number;
    }
    return 0;
}

inline const PlanetPosition* find_planet(const std::vector<PlanetPosition>& planets,
                                          std::string_view id) {
    for (const auto& planet : planets) {
        if (planet.id == id) return &planet;
    }
    return nullptr;
}

inline std::optional<double> natal_point_longitude(const ChartResult& chart,
                                                   std::string_view id) {
    if (const auto* planet = find_planet(chart.planets, id)) return planet->longitude;
    if (id == "ascendant") return chart.ascendant;
    if (id == "midheaven") return chart.midheaven;
    if (id == "descendant") return chart.descendant;
    if (id == "imum_coeli") return chart.imum_coeli;
    return std::nullopt;
}

inline double natal_point_speed(const ChartResult& chart, std::string_view id) {
    if (const auto* planet = find_planet(chart.planets, id)) return planet->longitude_speed;
    return 0.0;
}

inline std::vector<std::string> default_transit_points() {
    return {"sun", "moon", "mercury", "venus", "mars"};
}

inline std::vector<std::string> default_natal_points() {
    return {"sun", "moon", "mercury", "venus", "mars", "ascendant"};
}

}  // namespace detail

inline ChartResult calculate(const ChartRequest& request) {
    detail::validate(request);
    detail::initialize_ephemeris();
    static std::mutex calculation_mutex;
    std::scoped_lock lock(calculation_mutex);

    ChartResult result;
    result.request = request;
    result.julian_day_ut = detail::julian_day_ut(request);
    if (request.zodiac == Zodiac::Sidereal) {
        swe_set_sid_mode(SE_SIDM_FAGAN_BRADLEY, 0, 0);
    }

    int flags = SEFLG_SWIEPH | SEFLG_SPEED;
    if (request.zodiac == Zodiac::Sidereal) flags |= SEFLG_SIDEREAL;
    const auto points = request.points.empty()
        ? std::vector<std::string>{"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "chiron"}
        : request.points;

    double cusps[13]{};
    double ascmc[10]{};
    const char house_system = detail::house_code(request.house_system)[0];
    const int house_status = swe_houses_ex(result.julian_day_ut, flags,
        request.latitude, request.longitude, house_system, cusps, ascmc);
    if (house_status < 0) {
        throw AstroError("HOUSE_CALCULATION_FAILED", "Swiss Ephemeris 无法计算宫位");
    }
    result.ascendant = detail::normalize(ascmc[SE_ASC]);
    result.midheaven = detail::normalize(ascmc[SE_MC]);
    result.descendant = detail::normalize(result.ascendant + 180.0);
    result.imum_coeli = detail::normalize(result.midheaven + 180.0);

    for (int i = 1; i <= 12; ++i) {
        const auto [sign, sign_name] = detail::sign_for(cusps[i]);
        result.houses.push_back({i, detail::normalize(cusps[i]), sign, sign_name});
    }

    for (const auto& id : points) {
        const auto* spec = detail::find_point(id);
        if (!spec) throw AstroError("INVALID_REQUEST", "不支持的点位: " + id);
        double xx[6]{};
        char serr[AS_MAXCH]{};
        const int returned_flags = swe_calc_ut(result.julian_day_ut, spec->body, flags, xx, serr);
        if (returned_flags < 0) {
            if (spec->body == SE_CHIRON && request.allow_moshier_fallback) {
                result.precision_mode = "moshier";
                result.warnings.emplace_back("Moshier 模式不支持凯龙星，已跳过 chiron");
                continue;
            }
            throw AstroError("CALCULATION_FAILED", serr[0] ? serr : "Swiss Ephemeris 计算失败");
        }
        if ((returned_flags & SEFLG_MOSEPH) != 0) {
            if (!request.allow_moshier_fallback) {
                throw AstroError("EPHEMERIS_UNAVAILABLE", "高精度星历文件不可用，计算退回 Moshier");
            }
            result.precision_mode = "moshier";
            if (std::ranges::find(result.warnings, "使用了 Moshier 降级模式") == result.warnings.end()) {
                result.warnings.emplace_back("使用了 Moshier 降级模式");
            }
        }
        const auto longitude = detail::normalize(xx[0]);
        const auto [sign, sign_name] = detail::sign_for(longitude);
        int house = 0;
        for (int h = 1; h <= 12; ++h) {
            const double start = detail::normalize(cusps[h]);
            const double end = detail::normalize(cusps[h == 12 ? 1 : h + 1]);
            const bool contains = start <= end ? longitude >= start && longitude < end
                : longitude >= start || longitude < end;
            if (contains) { house = h; break; }
        }
        result.planets.push_back({id, spec->name, longitude, xx[1], xx[2], xx[3], sign, sign_name,
            std::fmod(longitude, 30.0), house, xx[3] < 0.0, std::abs(xx[3]) < 0.01});
    }

    if (request.include_aspects) {
        constexpr std::array<std::pair<double, const char*>, 5> aspect_types{{
            {0.0, "conjunction"}, {60.0, "sextile"}, {90.0, "square"},
            {120.0, "trine"}, {180.0, "opposition"}
        }};
        for (std::size_t i = 0; i < result.planets.size(); ++i) {
            for (std::size_t j = i + 1; j < result.planets.size(); ++j) {
                const double raw = std::abs(result.planets[i].longitude - result.planets[j].longitude);
                const double actual = std::min(raw, 360.0 - raw);
                for (const auto [exact, name] : aspect_types) {
                    double orb = 0.0;
                    if (detail::is_major(actual, exact, orb)) {
                        const double relative_speed = result.planets[i].longitude_speed
                            - result.planets[j].longitude_speed;
                        result.aspects.push_back({result.planets[i].id, result.planets[j].id,
                            name, exact, actual, orb, relative_speed > 0.0});
                        break;
                    }
                }
            }
        }
    }
    return result;
}

inline TransitResult calculate_transit(const TransitRequest& request) {
    if (request.natal.zodiac != request.target.zodiac
        || request.natal.ayanamsa != request.target.ayanamsa
        || request.natal.house_system != request.target.house_system) {
        throw AstroError("INVALID_REQUEST", "本命盘与目标时刻必须使用相同的黄道、岁差和宫制");
    }

    TransitRequest normalized = request;
    if (normalized.transit_points.empty()) normalized.transit_points = detail::default_transit_points();
    if (normalized.natal_points.empty()) normalized.natal_points = detail::default_natal_points();
    normalized.natal.points.clear();
    for (const auto& id : normalized.natal_points) {
        if (detail::find_point(id)) normalized.natal.points.push_back(id);
    }
    const bool angle_only = normalized.natal.points.empty();
    if (angle_only) normalized.natal.points.push_back("sun");
    normalized.natal.include_aspects = false;
    normalized.natal.allow_moshier_fallback = normalized.allow_moshier_fallback;
    normalized.target.points = normalized.transit_points;
    normalized.target.include_aspects = false;
    normalized.target.allow_moshier_fallback = normalized.allow_moshier_fallback;

    for (const auto& id : normalized.natal_points) {
        if (id != "ascendant" && id != "midheaven" && id != "descendant" && id != "imum_coeli"
            && !detail::find_point(id)) {
            throw AstroError("INVALID_REQUEST", "不支持的本命点位: " + id);
        }
    }

    TransitResult result;
    result.request = normalized;
    result.natal = calculate(normalized.natal);
    if (angle_only) {
        result.natal.planets.clear();
    }
    result.target = calculate(normalized.target);
    result.transit_planets = result.target.planets;
    for (auto& planet : result.transit_planets) {
        planet.house = detail::house_for_longitude(planet.longitude, result.natal.houses);
    }

    result.precision_mode = result.natal.precision_mode == "moshier"
        || result.target.precision_mode == "moshier" ? "moshier" : "high";
    result.warnings = result.natal.warnings;
    for (const auto& warning : result.target.warnings) {
        if (std::ranges::find(result.warnings, warning) == result.warnings.end()) {
            result.warnings.push_back(warning);
        }
    }

    if (normalized.include_aspects) {
        constexpr std::array<std::pair<double, const char*>, 5> aspect_types{{
            {0.0, "conjunction"}, {60.0, "sextile"}, {90.0, "square"},
            {120.0, "trine"}, {180.0, "opposition"}
        }};
        for (const auto& transit : result.transit_planets) {
            for (const auto& natal_id : normalized.natal_points) {
                const auto natal_longitude = detail::natal_point_longitude(result.natal, natal_id);
                if (!natal_longitude) continue;
                const double raw = std::abs(transit.longitude - *natal_longitude);
                const double actual = std::min(raw, 360.0 - raw);
                for (const auto [exact, name] : aspect_types) {
                    double orb = 0.0;
                    if (detail::is_major(actual, exact, orb)) {
                        const double relative_speed = transit.longitude_speed
                            - detail::natal_point_speed(result.natal, natal_id);
                        result.aspects.push_back({transit.id, natal_id, name, exact, actual,
                            orb, relative_speed > 0.0});
                        break;
                    }
                }
            }
        }
    }
    return result;
}

}  // namespace ZhouYi::Astro
