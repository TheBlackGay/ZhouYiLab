import std;
import ZhouYi.LiuYaoController;
import ZhouYi.BaZiBase;
import ZhouYi.Common.DateTime;
import nlohmann.json;

using json = nlohmann::json;

namespace {
json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}
void validate_date(int year, int month, int day, int hour, bool lunar) {
    const auto valid = lunar
        ? ZhouYi::Common::DateTime::is_valid_lunar_date(
            ZhouYi::Common::LunarDateTime{year, month, day, hour, 0, 0})
        : ZhouYi::Common::DateTime::is_valid_solar_date_time(
            ZhouYi::Common::SolarDateTime{year, month, day, hour, 0, 0});
    if (!valid) throw std::invalid_argument("日期时间无效");
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
