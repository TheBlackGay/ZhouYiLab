import std;
import ZhouYi.BaZiController;
import ZhouYi.BaZiBase;
import ZhouYi.BaZi.ShenSha;
import ZhouYi.GanZhi;
import ZhouYi.tyme;
import ZhouYi.ZiWei.SolarTime;
import nlohmann.json;

using json = nlohmann::json;

namespace {

json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}

std::string format_date_time(const ZhouYi::ZiWei::BirthDateTime& value) {
    return std::format("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}",
        value.year, value.month, value.day, value.hour, value.minute, value.second);
}

json correction_json(const ZhouYi::ZiWei::SolarTimeCorrection& correction) {
    using ZhouYi::ZiWei::BirthTimeMode;
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

ZhouYi::ZiWei::BirthTimeOptions parse_time_options(const json& request) {
    using namespace ZhouYi::ZiWei;
    const auto options = request.value("time_correction", json::object());
    const auto mode = options.value("mode", std::string("standard_time"));
    if (mode != "standard_time" && mode != "true_solar_time") {
        throw std::invalid_argument("time_correction.mode 必须是 standard_time 或 true_solar_time");
    }
    return BirthTimeOptions{
        .mode = mode == "true_solar_time" ? BirthTimeMode::TrueSolarTime : BirthTimeMode::StandardTime,
        .longitude = options.value("longitude", 120.0),
        .standard_meridian = options.value("standard_meridian", 120.0),
        .daylight_saving_minutes = options.value("daylight_saving_minutes", 0)
    };
}

void validate_date_time(int year, int month, int day, int hour, int minute, bool lunar) {
    if (year < 1 || year > 9999) throw std::invalid_argument("年份必须在 1 到 9999 之间");
    if (month < 1 || month > 12) throw std::invalid_argument("月份必须在 1 到 12 之间");
    if (day < 1 || day > (lunar ? 30 : 31)) {
        throw std::invalid_argument(lunar ? "农历日期必须在 1 到 30 之间" : "日期必须在 1 到 31 之间");
    }
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) {
        throw std::invalid_argument("时间必须在 00:00 到 23:59 之间");
    }
}

json pillar_detail(
    const ZhouYi::BaZiBase::Pillar& pillar,
    ZhouYi::GanZhi::TianGan day_stem,
    std::string_view stem_ten_god
) {
    using namespace ZhouYi::GanZhi;
    const LiuShiJiaZi cycle(pillar.gan, pillar.zhi);
    const auto void_branches = get_kong_wang(pillar.gan, pillar.zhi);
    json hidden = json::array();
    for (const auto stem : get_cang_gan(pillar.zhi)) {
        hidden.push_back({
            {"stem", std::string(Mapper::to_zh(stem))},
            {"element", std::string(Mapper::to_zh(get_wu_xing(stem)))},
            {"ten_god", std::string(shi_shen_to_zh(get_shi_shen(day_stem, stem)))}
        });
    }
    return {
        {"stem", pillar.stem()},
        {"branch", pillar.branch()},
        {"stem_element", std::string(Mapper::to_zh(get_wu_xing(pillar.gan)))},
        {"branch_element", std::string(Mapper::to_zh(get_wu_xing(pillar.zhi)))},
        {"stem_yin_yang", std::string(Mapper::to_zh(get_yin_yang(pillar.gan)))},
        {"branch_yin_yang", std::string(Mapper::to_zh(get_yin_yang(pillar.zhi)))},
        {"stem_ten_god", std::string(stem_ten_god)},
        {"star_fortune", std::string(ShiErChangShengMapper::to_zh(
            get_shi_er_chang_sheng(day_stem, pillar.zhi)))},
        {"self_sitting", std::string(ShiErChangShengMapper::to_zh(
            get_shi_er_chang_sheng(pillar.gan, pillar.zhi)))},
        {"void_branches", json::array({
            std::string(Mapper::to_zh(void_branches[0])),
            std::string(Mapper::to_zh(void_branches[1]))
        })},
        {"na_yin", std::string(cycle.get_na_yin_name())},
        {"na_yin_element", std::string(Mapper::to_zh(cycle.get_na_yin()))},
        {"hidden_stems", std::move(hidden)}
    };
}

}  // namespace

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto calendar = request.value("calendar", std::string("solar"));
        if (calendar != "solar" && calendar != "lunar") {
            throw std::invalid_argument("calendar 必须是 solar 或 lunar");
        }
        const auto gender = request.value("gender", std::string("male"));
        if (gender != "male" && gender != "female") {
            throw std::invalid_argument("gender 必须是 male 或 female");
        }

        const auto& date = request.at("date");
        const int year = date.at("year").get<int>();
        const int month = date.at("month").get<int>();
        const int day = date.at("day").get<int>();
        const int hour = date.value("hour", 0);
        const int minute = date.value("minute", 0);
        const bool lunar = calendar == "lunar";
        validate_date_time(year, month, day, hour, minute, lunar);

        tyme::SolarTime recorded_solar = lunar
            ? tyme::LunarHour::from_ymd_hms(
                year, date.value("leap_month", false) ? -month : month,
                day, hour, minute, 0).get_solar_time()
            : tyme::SolarTime::from_ymd_hms(year, month, day, hour, minute, 0);
        const auto recorded = ZhouYi::ZiWei::to_birth_date_time(recorded_solar);
        const auto correction = ZhouYi::ZiWei::correct_birth_time(recorded, parse_time_options(request));
        const auto& chart = correction.chart_time;
        auto result = ZhouYi::BaZiController::pai_pan_solar(
            chart.year, chart.month, chart.day, chart.hour, chart.minute, gender == "male");

        auto output = result.to_json();
        output["calendar"] = calendar;
        output["gender"] = gender;
        output["birth_date"] = {
            {"year", recorded.year}, {"month", recorded.month}, {"day", recorded.day},
            {"hour", recorded.hour}, {"minute", recorded.minute},
            {"display", format_date_time(recorded)}
        };
        output["birth_time"] = correction_json(correction);
        output["solar_date"] = recorded_solar.to_string();
        output["lunar_date"] = recorded_solar.get_lunar_hour().to_string();
        output["chart_lunar_date"] = ZhouYi::ZiWei::to_solar_time(chart).get_lunar_hour().to_string();

        const auto ten_gods = result.get_si_zhu_shi_shen();
        const auto& bazi = result.ba_zi;
        output["pillars"] = {
            {"year", pillar_detail(bazi.year, bazi.day.gan, ZhouYi::GanZhi::shi_shen_to_zh(ten_gods[0]))},
            {"month", pillar_detail(bazi.month, bazi.day.gan, ZhouYi::GanZhi::shi_shen_to_zh(ten_gods[1]))},
            {"day", pillar_detail(bazi.day, bazi.day.gan, ZhouYi::GanZhi::shi_shen_to_zh(ten_gods[2]))},
            {"hour", pillar_detail(bazi.hour, bazi.day.gan, ZhouYi::GanZhi::shi_shen_to_zh(ten_gods[3]))}
        };
        const std::array stems{bazi.year.gan, bazi.month.gan, bazi.day.gan, bazi.hour.gan};
        const std::array branches{bazi.year.zhi, bazi.month.zhi, bazi.day.zhi, bazi.hour.zhi};
        const auto shen_sha = ZhouYi::BaZi::ShenSha::calculate(
            stems, branches,
            ZhouYi::GanZhi::LiuShiJiaZi(bazi.year.gan, bazi.year.zhi).get_na_yin(),
            gender == "male");
        constexpr std::array<std::string_view, 4> pillar_keys{"year", "month", "day", "hour"};
        for (std::size_t i = 0; i < pillar_keys.size(); ++i) {
            output["pillars"][pillar_keys[i]]["shen_sha"] = shen_sha.pillars[i].names;
        }
        const auto stems_to_json = [](const std::vector<ZhouYi::GanZhi::TianGan>& values) {
            json result = json::array();
            for (const auto value : values) {
                result.push_back(std::string(ZhouYi::GanZhi::Mapper::to_zh(value)));
            }
            return result;
        };
        output["shen_sha_summary"] = {
            {"source", "渊海子平·三命通会口径"},
            {"de_xiu", {
                {"matched", shen_sha.de_xiu.matched},
                {"de_stems", stems_to_json(shen_sha.de_xiu.de_stems)},
                {"xiu_stems", stems_to_json(shen_sha.de_xiu.xiu_stems)}
            }},
            {"tong_zi", {
                {"matched", shen_sha.tong_zi.matched},
                {"month_rule", shen_sha.tong_zi.month_rule},
                {"na_yin_rule", shen_sha.tong_zi.na_yin_rule},
                {"match_count", shen_sha.tong_zi.match_count},
                {"is_double", shen_sha.tong_zi.match_count == 2},
                {"source_note", "后世民间兼容规则，非两部原书完整神煞口诀"}
            }},
            {"tian_luo_di_wang", {
                {"tian_luo", shen_sha.luo_wang.tian_luo},
                {"di_wang", shen_sha.luo_wang.di_wang},
                {"gender_note", shen_sha.luo_wang.gender_note}
            }}
        };
        output["day_master"] = {
            {"stem", bazi.day.stem()},
            {"element", std::string(ZhouYi::GanZhi::Mapper::to_zh(ZhouYi::GanZhi::get_wu_xing(bazi.day.gan)))},
            {"yin_yang", std::string(ZhouYi::GanZhi::Mapper::to_zh(ZhouYi::GanZhi::get_yin_yang(bazi.day.gan)))}
        };
        const auto child_limit = result.get_child_limit_detail();
        output["da_yun"]["start_detail"] = {
            {"nominal_start_age", child_limit.start_age},
            {"years", child_limit.year_count},
            {"months", child_limit.month_count},
            {"days", child_limit.day_count},
            {"hours", child_limit.hour_count},
            {"minutes", child_limit.minute_count},
            {"birth_time", child_limit.start_time.to_string()},
            {"start_time", child_limit.end_time.to_string()}
        };
        output["xun_kong"] = json::array({bazi.xun_kong_1, bazi.xun_kong_2});

        std::cout << output.dump();
        return 0;
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump();
        return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump();
        return 1;
    }
}
