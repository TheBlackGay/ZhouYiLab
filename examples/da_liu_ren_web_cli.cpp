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
        // D2 月将取法：默认中气过宫；guifa_suicha 为古法歌诀对照口径。前台不暴露，接口可用。
        const auto yuejiang_name = request.value("yuejiang_method", std::string("zhongqi"));
        ZhouYi::DaLiuRen::YueJiangMethod yuejiang;
        if (yuejiang_name == "zhongqi") yuejiang = ZhouYi::DaLiuRen::YueJiangMethod::Zhongqi;
        else if (yuejiang_name == "guifa_suicha") yuejiang = ZhouYi::DaLiuRen::YueJiangMethod::GuifaSuicha;
        else throw std::invalid_argument("yuejiang_method 必须是 zhongqi 或 guifa_suicha");
        const auto& date = request.at("date");
        const int year = date.at("year"), month = date.at("month"), day = date.at("day"), hour = date.value("hour", 0);
        if (calendar == "solar") {
            std::cout << ZhouYi::DaLiuRen::DaLiuRenEngine::pai_pan(year, month, day, hour, yuejiang).to_json().dump();
        } else if (calendar == "lunar") {
            const int lunar_month = date.value("leap_month", false) ? -month : month;
            std::cout << ZhouYi::DaLiuRen::DaLiuRenEngine::pai_pan_lunar(year, lunar_month, day, hour, yuejiang).to_json().dump();
        } else throw std::invalid_argument("calendar 必须是 solar 或 lunar");
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump(); return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump(); return 1;
    }
}
