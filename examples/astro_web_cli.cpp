import std;
import nlohmann.json;
import ZhouYi.Astro.Controller;
import ZhouYi.Astro;

using json = nlohmann::json;

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto operation = request.value("operation", std::string("chart"));
        if (operation == "meta") {
            std::cout << ZhouYi::Astro::Controller::meta_json().dump() << '\n';
            return 0;
        }
        if (operation == "transit") {
            std::cout << ZhouYi::Astro::Controller::calculate_transit_json(request).dump() << '\n';
            return 0;
        }
        std::cout << ZhouYi::Astro::Controller::calculate_json(request).dump() << '\n';
        return 0;
    } catch (const ZhouYi::Astro::AstroError& error) {
        std::cout << json{{"error", {{"code", error.code()}, {"message", error.what()}}}}.dump() << '\n';
    } catch (const std::exception& error) {
        std::cout << json{{"error", {{"code", "INVALID_REQUEST"}, {"message", error.what()}}}}.dump() << '\n';
    }
    return 1;
}
