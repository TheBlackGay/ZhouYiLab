import std;
import ZhouYi.LiuYaoController;
import ZhouYi.BaZiBase;
import nlohmann.json;

using json = nlohmann::json;

namespace {
json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}
void validate_date(int year, int month, int day, int hour, bool lunar) {
    if (year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > (lunar ? 30 : 31))
        throw std::invalid_argument("日期范围无效");
    if (!lunar) {
        const auto calendarDate = std::chrono::year{year} / std::chrono::month{static_cast<unsigned>(month)} / std::chrono::day{static_cast<unsigned>(day)};
        if (!calendarDate.ok()) throw std::invalid_argument("公历日期无效");
    }
    if (hour < 0 || hour > 23) throw std::invalid_argument("小时必须在 0 到 23 之间");
}
}

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto calendar = request.value("calendar", std::string("solar"));
        const bool lunar = calendar == "lunar";
        if (!lunar && calendar != "solar") throw std::invalid_argument("calendar 必须是 solar 或 lunar");
        const auto& date = request.at("date");
        const int year = date.at("year"), month = date.at("month"), day = date.at("day"), hour = date.value("hour", 0);
        validate_date(year, month, day, hour, lunar);
        const auto code = request.value("hexagram_code", std::string("111111"));
        std::vector<int> changing;
        if (request.contains("changing_lines")) changing = request.at("changing_lines").get<std::vector<int>>();
        ZhouYi::BaZiBase::BaZi bazi = lunar
            ? ZhouYi::BaZiBase::BaZi::from_lunar(year, date.value("leap_month", false) ? -month : month, day, hour)
            : ZhouYi::BaZiBase::BaZi::from_solar(year, month, day, hour, date.value("minute", 0));
        auto result = ZhouYi::LiuYaoController::calculate_liu_yao(code, bazi, changing, true);
        std::cout << result.json_data.dump();
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump(); return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump(); return 1;
    }
}
