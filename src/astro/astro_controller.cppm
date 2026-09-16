export module ZhouYi.Astro.Controller;

import std;
import nlohmann.json;
import ZhouYi.Astro;

export namespace ZhouYi::Astro::Controller {

using json = nlohmann::json;

inline std::string sign_element(std::string_view sign) {
    if (sign == "aries" || sign == "leo" || sign == "sagittarius") return "fire";
    if (sign == "taurus" || sign == "virgo" || sign == "capricorn") return "earth";
    if (sign == "gemini" || sign == "libra" || sign == "aquarius") return "air";
    return "water";
}

inline std::string sign_modality(std::string_view sign) {
    if (sign == "aries" || sign == "cancer" || sign == "libra" || sign == "capricorn") return "cardinal";
    if (sign == "taurus" || sign == "leo" || sign == "scorpio" || sign == "aquarius") return "fixed";
    return "mutable";
}

inline json derived_signals_json(const ChartResult& result) {
    constexpr int emphasis_threshold = 4;
    constexpr int stellium_threshold = 3;
    constexpr double tight_aspect_orb = 3.0;
    json signals = json::array();
    std::map<std::string, int> element_counts{{"fire", 0}, {"earth", 0}, {"air", 0}, {"water", 0}};
    std::map<std::string, int> modality_counts{{"cardinal", 0}, {"fixed", 0}, {"mutable", 0}};
    std::map<std::string, std::vector<std::string>> sign_points;
    std::map<int, std::vector<std::string>> house_points;
    for (const auto& value : result.planets) {
        const auto element = sign_element(value.sign);
        const auto modality = sign_modality(value.sign);
        ++element_counts[element];
        ++modality_counts[modality];
        sign_points[value.sign].push_back(value.id);
        if (value.house > 0) house_points[value.house].push_back(value.id);
        if (value.house == 1 || value.house == 4 || value.house == 7 || value.house == 10) {
            signals.push_back({
                {"signal_id", "angular_planet:" + value.id}, {"type", "angular_planet"},
                {"point_ids", {value.id}},
                {"evidence", {{"house", value.house}, {"angularity", "angular"}}}
            });
        }
        if (value.retrograde) {
            signals.push_back({
                {"signal_id", "retrograde_point:" + value.id}, {"type", "retrograde_point"},
                {"point_ids", {value.id}},
                {"evidence", {{"longitude_speed", value.longitude_speed}}}
            });
        }
    }
    for (const auto& [element, count] : element_counts) {
        if (count >= emphasis_threshold) {
            signals.push_back({
                {"signal_id", "element_emphasis:" + element}, {"type", "element_emphasis"},
                {"point_ids", json::array()},
                {"evidence", {{"element", element}, {"count", count}, {"threshold", emphasis_threshold}}}
            });
        }
    }
    for (const auto& [modality, count] : modality_counts) {
        if (count >= emphasis_threshold) {
            signals.push_back({
                {"signal_id", "modality_emphasis:" + modality}, {"type", "modality_emphasis"},
                {"point_ids", json::array()},
                {"evidence", {{"modality", modality}, {"count", count}, {"threshold", emphasis_threshold}}}
            });
        }
    }
    for (const auto& [sign, point_ids] : sign_points) {
        if (static_cast<int>(point_ids.size()) >= stellium_threshold) {
            signals.push_back({
                {"signal_id", "sign_stellium:" + sign}, {"type", "sign_stellium"},
                {"point_ids", point_ids},
                {"evidence", {{"sign_id", sign}, {"count", point_ids.size()}, {"threshold", stellium_threshold}}}
            });
        }
    }
    for (const auto& [house, point_ids] : house_points) {
        if (static_cast<int>(point_ids.size()) >= stellium_threshold) {
            signals.push_back({
                {"signal_id", "house_stellium:" + std::to_string(house)}, {"type", "house_stellium"},
                {"point_ids", point_ids},
                {"evidence", {{"house", house}, {"count", point_ids.size()}, {"threshold", stellium_threshold}}}
            });
        }
    }
    for (const auto& value : result.aspects) {
        if (value.orb <= tight_aspect_orb) {
            signals.push_back({
                {"signal_id", "tight_aspect:" + value.first + ":" + value.second + ":" + value.type},
                {"type", "tight_aspect"}, {"point_ids", {value.first, value.second}},
                {"evidence", {{"aspect_type", value.type}, {"orb", value.orb},
                    {"threshold", tight_aspect_orb}, {"phase", value.applying ? "applying" : "separating"}}}
            });
        }
    }
    return {{"schema_version", "astro-derived-signals/1.0"}, {"signals", std::move(signals)}};
}

inline json structured_json(const ChartResult& result) {
    json points = json::array();
    json element_counts = { {"fire", 0}, {"earth", 0}, {"air", 0}, {"water", 0} };
    json modality_counts = { {"cardinal", 0}, {"fixed", 0}, {"mutable", 0} };
    json house_counts = json::object();
    for (const auto& value : result.planets) {
        const auto element = sign_element(value.sign);
        const auto modality = sign_modality(value.sign);
        element_counts[element] = element_counts[element].get<int>() + 1;
        modality_counts[modality] = modality_counts[modality].get<int>() + 1;
        if (value.house > 0) {
            const auto house_key = std::to_string(value.house);
            house_counts[house_key] = house_counts.value(house_key, 0) + 1;
        }
        points.push_back({
            {"id", value.id}, {"kind", "celestial_point"}, {"name", value.name},
            {"longitude", value.longitude}, {"latitude", value.latitude},
            {"distance_au", value.distance_au}, {"degree_in_sign", value.degree_in_sign},
            {"sign_id", value.sign}, {"house", value.house},
            {"motion", {{"longitude_speed", value.longitude_speed},
                {"direction", value.retrograde ? "retrograde" : "direct"},
                {"retrograde", value.retrograde}, {"stationary", value.stationary}}},
            {"classification", {{"element", element}, {"modality", modality}}}
        });
    }
    json angles = json::array();
    const std::array<std::pair<std::string_view, double>, 4> angle_values{{
        {"ascendant", result.ascendant}, {"midheaven", result.midheaven},
        {"descendant", result.descendant}, {"imum_coeli", result.imum_coeli}
    }};
    for (const auto& [id, longitude] : angle_values) {
        const auto normalized = detail::normalize(longitude);
        const auto [sign, sign_name] = detail::sign_for(normalized);
        angles.push_back({{"id", id}, {"longitude", normalized}, {"sign_id", sign},
            {"sign_name", sign_name}, {"degree_in_sign", std::fmod(normalized, 30.0)}});
    }
    json houses = json::array();
    for (const auto& value : result.houses) {
        houses.push_back({{"number", value.number}, {"cusp", value.cusp},
            {"sign_id", value.sign}, {"sign_name", value.sign_name},
            {"element", sign_element(value.sign)}, {"modality", sign_modality(value.sign)}});
    }
    json aspects = json::array();
    for (const auto& value : result.aspects) {
        aspects.push_back({{"source_id", value.first}, {"target_id", value.second},
            {"type", value.type}, {"exact_angle", value.exact_angle},
            {"actual_angle", value.actual_angle}, {"orb", value.orb},
            {"phase", value.applying ? "applying" : "separating"}});
    }
    return {
        {"schema_version", "astro-structured/1.0"},
        {"coordinate_frame", "geocentric_apparent"},
        {"points", std::move(points)}, {"angles", std::move(angles)},
        {"houses", std::move(houses)}, {"aspects", std::move(aspects)},
        {"derived_signals", derived_signals_json(result)},
        {"aggregates", {{"element_counts", std::move(element_counts)},
            {"modality_counts", std::move(modality_counts)},
            {"house_counts", std::move(house_counts)}}}
    };
}

inline ChartRequest parse_request(const json& input) {
    const auto& date = input.at("date");
    const auto& location = input.at("location");
    ChartRequest request{
        .year = date.at("year").get<int>(),
        .month = date.at("month").get<int>(),
        .day = date.at("day").get<int>(),
        .hour = date.value("hour", 0),
        .minute = date.value("minute", 0),
        .second = date.value("second", 0),
        .utc_offset_minutes = input.at("utc_offset_minutes").get<int>(),
        .latitude = location.at("latitude").get<double>(),
        .longitude = location.at("longitude").get<double>(),
        .elevation_m = location.value("elevation_m", 0.0),
        .zodiac = input.value("zodiac", std::string("tropical")) == "sidereal"
            ? Zodiac::Sidereal : Zodiac::Tropical,
        .ayanamsa = input.value("ayanamsa", std::string("none")),
        .house_system = input.value("house_system", std::string("placidus")) == "whole_sign"
            ? HouseSystem::WholeSign : HouseSystem::Placidus,
        .points = input.value("points", std::vector<std::string>{}),
        .include_aspects = input.value("include_aspects", true),
        .allow_moshier_fallback = input.value("allow_moshier_fallback", false)
    };
    const auto zodiac = input.value("zodiac", std::string("tropical"));
    if (zodiac != "tropical" && zodiac != "sidereal") {
        throw AstroError("INVALID_REQUEST", "zodiac 必须是 tropical 或 sidereal");
    }
    const auto house_system = input.value("house_system", std::string("placidus"));
    if (house_system != "placidus" && house_system != "whole_sign") {
        throw AstroError("INVALID_REQUEST", "house_system 必须是 placidus 或 whole_sign");
    }
    return request;
}

inline json chart_to_json(const ChartResult& result) {
    const auto utc_seconds = static_cast<long long>(
        (result.julian_day_ut - 2440587.5) * 86400.0 + 0.5);
    const auto utc_time = std::chrono::system_clock::time_point{std::chrono::seconds{utc_seconds}};
    const auto utc_date = std::chrono::floor<std::chrono::days>(utc_time);
    const auto utc_day = std::chrono::year_month_day{utc_date};
    const auto utc_clock = std::chrono::hh_mm_ss{utc_time - utc_date};
    const auto utc_datetime = std::format("{:%Y-%m-%d}T{:02d}:{:02d}:{:02d}Z",
        utc_day, utc_clock.hours().count(), utc_clock.minutes().count(), utc_clock.seconds().count());
    json planets = json::array();
    for (const auto& value : result.planets) {
        planets.push_back({
            {"id", value.id}, {"name", value.name},
            {"longitude", value.longitude}, {"latitude", value.latitude},
            {"distance_au", value.distance_au}, {"longitude_speed", value.longitude_speed},
            {"sign", value.sign}, {"sign_name", value.sign_name},
            {"degree_in_sign", value.degree_in_sign}, {"house", value.house},
            {"retrograde", value.retrograde}, {"stationary", value.stationary}
        });
    }
    json houses = json::array();
    for (const auto& value : result.houses) {
        houses.push_back({
            {"number", value.number}, {"cusp", value.cusp},
            {"sign", value.sign}, {"sign_name", value.sign_name}
        });
    }
    json aspects = json::array();
    for (const auto& value : result.aspects) {
        aspects.push_back({
            {"first", value.first}, {"second", value.second}, {"type", value.type},
            {"exact_angle", value.exact_angle}, {"actual_angle", value.actual_angle},
            {"orb", value.orb}, {"applying", value.applying}
        });
    }
    return {
        {"chart_type", "natal"},
        {"input", {
            {"utc_datetime", utc_datetime},
            {"date", {{"year", result.request.year}, {"month", result.request.month}, {"day", result.request.day}, {"hour", result.request.hour}, {"minute", result.request.minute}, {"second", result.request.second}}},
            {"utc_offset_minutes", result.request.utc_offset_minutes},
            {"latitude", result.request.latitude}, {"longitude", result.request.longitude},
            {"zodiac", result.request.zodiac == Zodiac::Sidereal ? "sidereal" : "tropical"},
            {"ayanamsa", result.request.ayanamsa},
            {"house_system", result.request.house_system == HouseSystem::WholeSign ? "whole_sign" : "placidus"}
        }},
        {"calculation", {
            {"julian_day_ut", result.julian_day_ut}, {"ephemeris", result.ephemeris},
            {"ephemeris_version", result.ephemeris_version},
            {"precision_mode", result.precision_mode}, {"warnings", result.warnings}
        }},
        {"angles", {
            {"ascendant", result.ascendant}, {"midheaven", result.midheaven},
            {"descendant", result.descendant}, {"imum_coeli", result.imum_coeli}
        }},
        {"planets", std::move(planets)}, {"houses", std::move(houses)},
        {"aspects", std::move(aspects)},
        {"structured", structured_json(result)}
    };
}

inline json calculate_json(const json& input) {
    return chart_to_json(calculate(parse_request(input)));
}

inline json meta_json() {
    return {
        {"api_version", "v1"},
        {"algorithm_version", "zhouyilab-astro/0.1.0"},
        {"ephemeris", "swiss"},
        {"supported_points", {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "true_node", "chiron"}},
        {"zodiacs", {"tropical", "sidereal"}},
        {"ayanamsas", {"none", "fagan_bradley"}},
        {"house_systems", {"placidus", "whole_sign"}},
        {"aspect_types", {"conjunction", "sextile", "square", "trine", "opposition"}},
        {"structured_schema_version", "astro-structured/1.0"},
        {"derived_signals_schema_version", "astro-derived-signals/1.0"}
    };
}

}  // namespace ZhouYi::Astro::Controller
