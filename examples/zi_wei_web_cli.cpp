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
    int effective_flow_month(const tyme::LunarDay& lunar_day) {
        const auto lunar_month = lunar_day.get_lunar_month();
        int month = lunar_month.get_month();
        if (lunar_month.is_leap() && lunar_day.get_day() > 15) {
            month = month % 12 + 1;
        }
        return month;
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
}

int main(int argc, char** argv) {
    try {
        if (argc != 18) {
            throw std::invalid_argument("参数数量不正确");
        }

        BirthDateTime birth{
            std::stoi(argv[1]), std::stoi(argv[2]), std::stoi(argv[3]),
            std::stoi(argv[4]), std::stoi(argv[5]), std::stoi(argv[6])
        };
        const bool is_male = std::stoi(argv[7]) != 0;
        BirthTimeOptions options{
            .mode = std::stoi(argv[8]) != 0
                ? BirthTimeMode::TrueSolarTime : BirthTimeMode::StandardTime,
            .longitude = std::stod(argv[9]),
            .standard_meridian = std::stod(argv[10]),
            .daylight_saving_minutes = std::stoi(argv[11])
        };

        const int target_year = std::stoi(argv[12]);
        const int target_month = std::stoi(argv[13]);
        const int target_day = std::stoi(argv[14]);
        const int target_hour = std::stoi(argv[15]);
        const int target_minute = std::stoi(argv[16]);
        const int current_age = std::stoi(argv[17]);

        const auto chart = pai_pan_solar(birth, is_male, options);
        json output = json::parse(export_to_json_full(chart));

        const auto target_time = tyme::SolarTime::from_ymd_hms(
            target_year, target_month, target_day, target_hour, target_minute, 0);
        const auto solar_day = target_time.get_solar_day();
        const auto lunar_day = solar_day.get_lunar_day();
        const auto cycle_day = solar_day.get_sixty_cycle_day();
        const auto year_cycle = cycle_day.get_year();
        const auto day_cycle = cycle_day.get_sixty_cycle();

        const auto year_gan = static_cast<TianGan>(year_cycle.get_heaven_stem().get_index());
        const auto year_zhi = static_cast<DiZhi>(year_cycle.get_earth_branch().get_index());
        const auto day_gan = static_cast<TianGan>(day_cycle.get_heaven_stem().get_index());
        const auto day_zhi = static_cast<DiZhi>(day_cycle.get_earth_branch().get_index());
        const auto hour_zhi = static_cast<DiZhi>(((target_hour + 1) / 2) % 12);
        const auto hour_gan = static_cast<TianGan>(
            (static_cast<int>(day_gan) % 5 * 2 + static_cast<int>(hour_zhi)) % 10);

        const int lunar_month = effective_flow_month(lunar_day);
        const int birth_lunar_month = chart.lunar_day.get_lunar_month().get_month();
        const auto liu_nian = get_liu_nian(
            target_year, year_gan, year_zhi, chart.ming_gong_index);
        const auto liu_yue = get_liu_yue(
            lunar_month, birth_lunar_month, chart.hour_pillar.zhi, year_gan, year_zhi);
        const auto liu_ri = get_liu_ri(
            lunar_day.get_day(), day_gan, day_zhi, liu_yue.gong_index);
        const auto liu_shi = get_liu_shi(
            hour_zhi, hour_gan, liu_ri.gong_index);
        const auto xiao_xian = get_xiao_xian(current_age, is_male, chart.year_pillar.zhi);

        const DaXianData* current_da_xian = nullptr;
        for (const auto& item : chart.da_xian_data) {
            if (current_age >= item.start_age && current_age <= item.end_age) {
                current_da_xian = &item;
                break;
            }
        }

        output["target"] = {
            {"solar_time", target_time.to_string()},
            {"lunar_date", lunar_day.to_string()},
            {"lunar_month", lunar_month},
            {"lunar_day", lunar_day.get_day()},
            {"age", current_age}
        };
        output["fortune"]["xiao_xian"] = {
            {"age", xiao_xian.age},
            {"palace_index", xiao_xian.gong_index},
            {"palace", std::string(to_zh(
                chart.palaces[xiao_xian.gong_index].gong_data.gong_wei))}
        };
        if (current_da_xian != nullptr) {
            output["fortune"]["da_xian"] = flow_layer(
                current_da_xian->tian_gan,
                current_da_xian->di_zhi,
                current_da_xian->gong_index,
                current_da_xian->si_hua,
                chart
            );
            output["fortune"]["da_xian"]["age_range"] =
                std::to_string(current_da_xian->start_age) + "-"
                + std::to_string(current_da_xian->end_age);
        }
        output["fortune"]["liu_nian"] = flow_layer(
            liu_nian.tian_gan, liu_nian.di_zhi, liu_nian.gong_index,
            liu_nian.si_hua, chart);
        output["fortune"]["liu_yue"] = flow_layer(
            liu_yue.tian_gan, liu_yue.di_zhi, liu_yue.gong_index,
            liu_yue.si_hua, chart);
        output["fortune"]["liu_yue"]["dou_jun_index"] = liu_yue.dou_jun_index;
        output["fortune"]["liu_yue"]["dou_jun_palace"] = std::string(to_zh(
            chart.palaces[liu_yue.dou_jun_index].gong_data.gong_wei));
        output["fortune"]["liu_ri"] = flow_layer(
            liu_ri.tian_gan, liu_ri.di_zhi, liu_ri.gong_index,
            liu_ri.si_hua, chart);
        output["fortune"]["liu_shi"] = flow_layer(
            liu_shi.tian_gan, liu_shi.di_zhi, liu_shi.gong_index,
            liu_shi.si_hua, chart);

        std::cout << output.dump();
        return 0;
    } catch (const std::exception& error) {
        std::cout << json{{"error", error.what()}}.dump();
        return 1;
    }
}
