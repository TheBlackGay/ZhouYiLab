import std;
import ZhouYi.Common.Calendar;
import nlohmann.json;

using json = nlohmann::json;
using namespace ZhouYi::Common;
using namespace ZhouYi::Common::Calendar;

namespace {

json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}

SolarDateTime parse_solar(const json& value) {
    return SolarDateTime{
        .year = value.at("year").get<int>(),
        .month = value.at("month").get<int>(),
        .day = value.at("day").get<int>(),
        .hour = value.value("hour", 0),
        .minute = value.value("minute", 0),
        .second = value.value("second", 0)
    };
}

LunarDateTime parse_lunar(const json& value) {
    const int month = value.at("month").get<int>();
    if (month < 1 || month > 12) {
        throw std::invalid_argument("农历月份必须在1到12之间");
    }
    return LunarDateTime{
        .year = value.at("year").get<int>(),
        .month = value.value("leap_month", false) ? -month : month,
        .day = value.at("day").get<int>(),
        .hour = value.value("hour", 0),
        .minute = value.value("minute", 0),
        .second = value.value("second", 0)
    };
}

json solar_json(const SolarDateTime& value) {
    return {
        {"year", value.year}, {"month", value.month}, {"day", value.day},
        {"hour", value.hour}, {"minute", value.minute}, {"second", value.second},
        {"display", DateTime::format(value)}
    };
}

json lunar_json(const LunarDateTime& value) {
    return {
        {"year", value.year},
        {"month", std::abs(value.month)},
        {"leap_month", value.month < 0},
        {"day", value.day},
        {"hour", value.hour},
        {"minute", value.minute},
        {"second", value.second},
        {"display", DateTime::format(value)}
    };
}

json conversion(const json& request) {
    const auto calendar = request.value("calendar", std::string("solar"));
    if (calendar != "solar" && calendar != "lunar") {
        throw std::invalid_argument("calendar 必须是 solar 或 lunar");
    }

    json result;
    if (calendar == "solar") {
        const auto solar = parse_solar(request.at("date"));
        const auto lunar = solar_to_lunar(solar);
        result["source"] = "solar";
        result["solar"] = solar_json(solar);
        result["lunar"] = lunar_json(lunar);
    } else {
        const auto lunar = parse_lunar(request.at("date"));
        const auto solar = lunar_to_solar(lunar);
        result["source"] = "lunar";
        result["solar"] = solar_json(solar);
        result["lunar"] = lunar_json(lunar);
    }
    return result;
}

json correction(const SolarTimeCorrection& value) {
    return {
        {"mode", "true_solar_time"},
        {"recorded_time", solar_json(value.recorded_time)},
        {"standard_time", solar_json(value.standard_time)},
        {"true_solar_time", solar_json(value.chart_time)},
        {"chart_time", solar_json(value.chart_time)},
        {"longitude", value.longitude},
        {"standard_meridian", value.standard_meridian},
        {"daylight_saving_minutes", value.daylight_saving_minutes},
        {"longitude_offset_seconds", value.longitude_offset_seconds},
        {"equation_of_time_seconds", value.equation_of_time_seconds},
        {"total_offset_seconds", value.total_offset_seconds},
        {"crossed_date_boundary", value.crossed_date_boundary}
    };
}

json true_solar_time(const json& request) {
    const auto birth = parse_solar(request.at("date"));
    const auto value = calculate_true_solar_time(birth, TrueSolarTimeOptions{
        .longitude = request.value("longitude", 120.0),
        .standard_meridian = request.value("standard_meridian", 120.0),
        .daylight_saving_minutes = request.value("daylight_saving_minutes", 0)
    });
    return correction(value);
}

} // namespace

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto operation = request.value("operation", std::string("convert"));
        if (operation == "convert") {
            std::cout << conversion(request).dump() << '\n';
        } else if (operation == "true_solar_time") {
            std::cout << true_solar_time(request).dump() << '\n';
        } else {
            std::cout << error_response("INVALID_OPERATION", "不支持的 operation").dump() << '\n';
            return 2;
        }
        return 0;
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_REQUEST", error.what()).dump() << '\n';
        return 2;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump() << '\n';
        return 2;
    }
}
