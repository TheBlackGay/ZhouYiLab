import std;
import ZhouYi.QiMen;
import ZhouYi.QiMen.Controller;
import nlohmann.json;

using json = nlohmann::json;

namespace {

json error_response(std::string code, std::string message) {
    return {
        {"error", {
            {"code", std::move(code)},
            {"message", std::move(message)}
        }}
    };
}

void validate_date_time(int year, int month, int day, int hour, int minute, bool lunar) {
    if (year < 1 || year > 9999) {
        throw std::invalid_argument("年份必须在 1 到 9999 之间");
    }
    const int max_day = lunar ? 30 : 31;
    if (month < 1 || month > 12) {
        throw std::invalid_argument("月份必须在 1 到 12 之间");
    }
    if (day < 1 || day > max_day) {
        throw std::invalid_argument(lunar ? "农历日期必须在 1 到 30 之间" : "日期必须在 1 到 31 之间");
    }
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
        throw std::invalid_argument("时间必须在 00:00 到 23:59 之间");
    }
}

}  // namespace

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto calendar = request.value("calendar", std::string("solar"));
        if (calendar != "solar" && calendar != "lunar") {
            throw std::invalid_argument("calendar 必须是 solar 或 lunar");
        }

        const auto& date = request.at("date");
        const int year = date.at("year").get<int>();
        const int month = date.at("month").get<int>();
        const int day = date.at("day").get<int>();
        const int hour = date.value("hour", 0);
        const int minute = date.value("minute", 0);
        const bool lunar = calendar == "lunar";
        validate_date_time(year, month, day, hour, minute, lunar);

        auto result = lunar
            ? ZhouYi::QiMen::QiMenController::pai_pan_lunar(
                year, date.value("leap_month", false) ? -month : month, day, hour, minute)
            : ZhouYi::QiMen::QiMenController::pai_pan_solar(year, month, day, hour, minute);
        if (!result) {
            std::cout << error_response("CALCULATION_FAILED", result.error()).dump();
            return 2;
        }

        std::cout << ZhouYi::QiMen::QiMenController::get_pan_json_ordered(result.value());
        return 0;
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump();
        return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump();
        return 1;
    }
}
