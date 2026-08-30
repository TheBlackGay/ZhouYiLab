import std;
import ZhouYi.GanZhi;
import ZhouYi.ZhMapper;
import ZhouYi.tyme;
import ZhouYi.ZiWei;
import ZhouYi.ZiWei.Controller;
import ZhouYi.ZiWei.Horoscope;
import nlohmann.json;

using json = nlohmann::json;
using namespace ZhouYi::GanZhi;
using namespace ZhouYi::ZiWei;
using namespace ZhouYi::Mapper;

namespace {
    constexpr std::array<std::string_view, 6> ALL_LAYERS{
        "decade", "minor", "annual", "monthly", "daily", "hourly"
    };

    int effective_flow_month(const tyme::LunarDay& lunar_day) {
        const auto lunar_month = lunar_day.get_lunar_month();
        int month = lunar_month.get_month();
        if (lunar_month.is_leap() && lunar_day.get_day() > 15) {
            month = month % 12 + 1;
        }
        return month;
    }

    std::string format_date_time(const BirthDateTime& value) {
        return std::format("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}",
            value.year, value.month, value.day,
            value.hour, value.minute, value.second);
    }

    json correction_json(const SolarTimeCorrection& correction) {
        return {
            {"mode", correction.mode == BirthTimeMode::TrueSolarTime
                ? "true_solar_time" : "standard_time"},
            {"recorded_time", format_date_time(correction.recorded_time)},
            {"standard_time", format_date_time(correction.standard_time)},
            {"chart_time", format_date_time(correction.chart_time)},
            {"longitude", correction.longitude},
            {"standard_meridian", correction.standard_meridian},
            {"daylight_saving_minutes", correction.daylight_saving_minutes},
            {"longitude_offset_seconds", correction.longitude_offset_seconds},
            {"equation_of_time_seconds", correction.equation_of_time_seconds},
            {"total_offset_seconds", correction.total_offset_seconds},
            {"crossed_date_boundary", correction.crossed_date_boundary}
        };
    }

    BirthDateTime parse_date_time(const json& value) {
        return BirthDateTime{
            .year = value.at("year").get<int>(),
            .month = value.at("month").get<int>(),
            .day = value.at("day").get<int>(),
            .hour = value.value("hour", 0),
            .minute = value.value("minute", 0),
            .second = value.value("second", 0)
        };
    }

    BirthTimeOptions parse_time_options(const json& request) {
        const auto options = request.value("time_correction", json::object());
        const auto mode = options.value("mode", std::string("standard_time"));
        if (mode != "standard_time" && mode != "true_solar_time") {
            throw std::invalid_argument(
                "time_correction.mode 必须是 standard_time 或 true_solar_time");
        }
        return BirthTimeOptions{
            .mode = mode == "true_solar_time"
                ? BirthTimeMode::TrueSolarTime : BirthTimeMode::StandardTime,
            .longitude = options.value("longitude", 120.0),
            .standard_meridian = options.value("standard_meridian", 120.0),
            .daylight_saving_minutes = options.value("daylight_saving_minutes", 0)
        };
    }

    bool parse_gender(const json& birth) {
        const auto gender = birth.at("gender").get<std::string>();
        if (gender == "male") return true;
        if (gender == "female") return false;
        throw std::invalid_argument("birth.gender 必须是 male 或 female");
    }

    std::set<std::string> parse_layers(const json& target) {
        std::set<std::string> layers;
        if (!target.contains("layers")) {
            for (const auto layer : ALL_LAYERS) layers.emplace(layer);
            return layers;
        }
        for (const auto& item : target.at("layers")) {
            const auto layer = item.get<std::string>();
            if (std::ranges::find(ALL_LAYERS, layer) == ALL_LAYERS.end()) {
                throw std::invalid_argument("target.layers 包含不支持的层级: " + layer);
            }
            layers.emplace(layer);
        }
        if (layers.empty()) {
            throw std::invalid_argument("target.layers 不能为空");
        }
        return layers;
    }

    json four_transformations(const std::array<std::string, 4>& values) {
        static constexpr std::array<std::string_view, 4> NAMES{"禄", "权", "科", "忌"};
        json result = json::array();
        for (std::size_t i = 0; i < values.size(); ++i) {
            result.push_back({{"type", NAMES[i]}, {"star", values[i]}});
        }
        return result;
    }

    json flow_layer(
        TianGan gan,
        DiZhi zhi,
        int palace_index,
        const std::array<std::string, 4>& transformations,
        const ZiWeiResult& chart
    ) {
        return {
            {"gan_zhi", std::string(ZhouYi::GanZhi::Mapper::to_zh(gan))
                + std::string(ZhouYi::GanZhi::Mapper::to_zh(zhi))},
            {"palace_index", palace_index},
            {"palace", std::string(to_zh(chart.palaces[palace_index].gong_data.gong_wei))},
            {"si_hua", four_transformations(transformations)}
        };
    }

    json calculate_chart(const json& request) {
        const auto& birth_json = request.at("birth");
        const auto birth = parse_date_time(birth_json);
        const auto options = parse_time_options(request);
        const auto chart = pai_pan_solar(birth, parse_gender(birth_json), options);
        return json::parse(export_to_json_full(chart));
    }

    json calculate_fortune(const json& request) {
        const auto& birth_json = request.at("birth");
        const auto& target_json = request.at("target");
        const auto birth = parse_date_time(birth_json);
        const auto target = parse_date_time(target_json);
        const bool is_male = parse_gender(birth_json);
        const auto options = parse_time_options(request);
        const auto layers = parse_layers(target_json);
        const int current_age = target_json.value("age", target.year - birth.year + 1);
        if (current_age < 1 || current_age > 150) {
            throw std::invalid_argument("target.age 必须在 1 到 150 之间");
        }

        const auto chart = pai_pan_solar(birth, is_male, options);
        const auto target_time = tyme::SolarTime::from_ymd_hms(
            target.year, target.month, target.day,
            target.hour, target.minute, target.second);
        const auto solar_day = target_time.get_solar_day();
        const auto lunar_day = solar_day.get_lunar_day();
        const auto cycle_day = solar_day.get_sixty_cycle_day();
        const auto year_cycle = cycle_day.get_year();
        const auto day_cycle = cycle_day.get_sixty_cycle();

        const auto year_gan = static_cast<TianGan>(year_cycle.get_heaven_stem().get_index());
        const auto year_zhi = static_cast<DiZhi>(year_cycle.get_earth_branch().get_index());
        const auto day_gan = static_cast<TianGan>(day_cycle.get_heaven_stem().get_index());
        const auto day_zhi = static_cast<DiZhi>(day_cycle.get_earth_branch().get_index());
        const auto hour_zhi = static_cast<DiZhi>(((target.hour + 1) / 2) % 12);
        const auto hour_gan = static_cast<TianGan>(
            (static_cast<int>(day_gan) % 5 * 2 + static_cast<int>(hour_zhi)) % 10);

        const int lunar_month = effective_flow_month(lunar_day);
        const int birth_lunar_month = chart.lunar_day.get_lunar_month().get_month();
        const auto liu_nian = get_liu_nian(
            target.year, year_gan, year_zhi, chart.ming_gong_index);
        const auto liu_yue = get_liu_yue(
            lunar_month, birth_lunar_month, chart.hour_pillar.zhi, year_gan, year_zhi);
        const auto liu_ri = get_liu_ri(
            lunar_day.get_day(), day_gan, day_zhi, liu_yue.gong_index);
        const auto liu_shi = get_liu_shi(hour_zhi, hour_gan, liu_ri.gong_index);
        const auto xiao_xian = get_xiao_xian(current_age, is_male, chart.year_pillar.zhi);

        const DaXianData* current_da_xian = nullptr;
        for (const auto& item : chart.da_xian_data) {
            if (current_age >= item.start_age && current_age <= item.end_age) {
                current_da_xian = &item;
                break;
            }
        }

        json fortune = json::object();
        if (layers.contains("minor")) {
            fortune["xiao_xian"] = {
                {"age", xiao_xian.age},
                {"palace_index", xiao_xian.gong_index},
                {"palace", std::string(to_zh(
                    chart.palaces[xiao_xian.gong_index].gong_data.gong_wei))}
            };
        }
        if (layers.contains("decade") && current_da_xian != nullptr) {
            fortune["da_xian"] = flow_layer(
                current_da_xian->tian_gan,
                current_da_xian->di_zhi,
                current_da_xian->gong_index,
                current_da_xian->si_hua,
                chart
            );
            fortune["da_xian"]["age_range"] =
                std::to_string(current_da_xian->start_age) + "-"
                + std::to_string(current_da_xian->end_age);
        }
        if (layers.contains("annual")) {
            fortune["liu_nian"] = flow_layer(
                liu_nian.tian_gan, liu_nian.di_zhi, liu_nian.gong_index,
                liu_nian.si_hua, chart);
        }
        if (layers.contains("monthly")) {
            fortune["liu_yue"] = flow_layer(
                liu_yue.tian_gan, liu_yue.di_zhi, liu_yue.gong_index,
                liu_yue.si_hua, chart);
            fortune["liu_yue"]["dou_jun_index"] = liu_yue.dou_jun_index;
            fortune["liu_yue"]["dou_jun_palace"] = std::string(to_zh(
                chart.palaces[liu_yue.dou_jun_index].gong_data.gong_wei));
        }
        if (layers.contains("daily")) {
            fortune["liu_ri"] = flow_layer(
                liu_ri.tian_gan, liu_ri.di_zhi, liu_ri.gong_index,
                liu_ri.si_hua, chart);
        }
        if (layers.contains("hourly")) {
            fortune["liu_shi"] = flow_layer(
                liu_shi.tian_gan, liu_shi.di_zhi, liu_shi.gong_index,
                liu_shi.si_hua, chart);
        }

        return {
            {"chart", json::parse(export_to_json_full(chart))},
            {"target", {
                {"solar_time", target_time.to_string()},
                {"lunar_date", lunar_day.to_string()},
                {"lunar_month", lunar_month},
                {"lunar_day", lunar_day.get_day()},
                {"age", current_age},
                {"requested_layers", layers}
            }},
            {"fortune", fortune}
        };
    }

    json execute(const json& request) {
        const auto operation = request.at("operation").get<std::string>();
        if (operation == "time_correction") {
            return correction_json(correct_birth_time(
                parse_date_time(request.at("birth")), parse_time_options(request)));
        }
        if (operation == "chart") return calculate_chart(request);
        if (operation == "fortune") return calculate_fortune(request);
        throw std::invalid_argument("不支持的 operation: " + operation);
    }

    json legacy_request(int argc, char** argv) {
        if (argc != 18) throw std::invalid_argument("参数数量不正确");
        return {
            {"operation", "fortune"},
            {"birth", {
                {"year", std::stoi(argv[1])}, {"month", std::stoi(argv[2])},
                {"day", std::stoi(argv[3])}, {"hour", std::stoi(argv[4])},
                {"minute", std::stoi(argv[5])}, {"second", std::stoi(argv[6])},
                {"gender", std::stoi(argv[7]) != 0 ? "male" : "female"}
            }},
            {"time_correction", {
                {"mode", std::stoi(argv[8]) != 0 ? "true_solar_time" : "standard_time"},
                {"longitude", std::stod(argv[9])},
                {"standard_meridian", std::stod(argv[10])},
                {"daylight_saving_minutes", std::stoi(argv[11])}
            }},
            {"target", {
                {"year", std::stoi(argv[12])}, {"month", std::stoi(argv[13])},
                {"day", std::stoi(argv[14])}, {"hour", std::stoi(argv[15])},
                {"minute", std::stoi(argv[16])}, {"second", 0},
                {"age", std::stoi(argv[17])}
            }}
        };
    }
}

int main(int argc, char** argv) {
    try {
        json request;
        if (argc == 1) {
            std::cin >> request;
        } else {
            request = legacy_request(argc, argv);
        }
        std::cout << execute(request).dump();
        return 0;
    } catch (const json::exception& error) {
        std::cout << json{{"error", {
            {"code", "INVALID_JSON"}, {"message", error.what()}
        }}}.dump();
        return 2;
    } catch (const std::invalid_argument& error) {
        std::cout << json{{"error", {
            {"code", "INVALID_ARGUMENT"}, {"message", error.what()}
        }}}.dump();
        return 2;
    } catch (const std::exception& error) {
        std::cout << json{{"error", {
            {"code", "CALCULATION_FAILED"}, {"message", error.what()}
        }}}.dump();
        return 1;
    }
}
