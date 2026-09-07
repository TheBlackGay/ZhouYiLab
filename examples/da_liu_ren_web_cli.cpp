import std;
import ZhouYi.DaLiuRen;
import nlohmann.json;

using json = nlohmann::json;

namespace {
json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}
}

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto calendar = request.value("calendar", std::string("solar"));
        const auto& date = request.at("date");
        const int year = date.at("year"), month = date.at("month"), day = date.at("day"), hour = date.value("hour", 0);
        if (calendar == "solar") {
            std::cout << ZhouYi::DaLiuRen::DaLiuRenEngine::pai_pan(year, month, day, hour).to_json().dump();
        } else if (calendar == "lunar") {
            const int lunar_month = date.value("leap_month", false) ? -month : month;
            std::cout << ZhouYi::DaLiuRen::DaLiuRenEngine::pai_pan_lunar(year, lunar_month, day, hour).to_json().dump();
        } else throw std::invalid_argument("calendar 必须是 solar 或 lunar");
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump(); return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump(); return 1;
    }
}
