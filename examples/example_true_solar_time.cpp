import std;
import ZhouYi.ZiWei;
import ZhouYi.ZiWei.Controller;
import fmt;

using namespace ZhouYi::ZiWei;

namespace {
    void require(bool condition, std::string_view message) {
        if (!condition) {
            throw std::runtime_error(std::string(message));
        }
    }

    bool same_date_time(const BirthDateTime& lhs, const BirthDateTime& rhs) {
        return lhs.year == rhs.year && lhs.month == rhs.month && lhs.day == rhs.day
            && lhs.hour == rhs.hour && lhs.minute == rhs.minute && lhs.second == rhs.second;
    }
}

int main() {
    const BirthDateTime birth{1994, 12, 8, 9, 5, 0};

    const auto uncorrected = correct_birth_time(birth);
    require(same_date_time(uncorrected.recorded_time, uncorrected.chart_time),
        "关闭真太阳时时不得修改出生时间");
    require(uncorrected.total_offset_seconds == 0,
        "关闭真太阳时时总校正量必须为0");

    BirthTimeOptions hangzhou{
        .mode = BirthTimeMode::TrueSolarTime,
        .longitude = 120.3
    };
    const auto hangzhou_time = correct_birth_time(birth, hangzhou);
    require(hangzhou_time.longitude_offset_seconds == 72,
        "杭州经度校正应为+72秒");
    require(std::abs(hangzhou_time.equation_of_time_seconds) < 1200,
        "均时差应处于合理范围");

    BirthTimeOptions chengdu{
        .mode = BirthTimeMode::TrueSolarTime,
        .longitude = 104.066
    };
    const auto chengdu_time = correct_birth_time(birth, chengdu);
    require(chengdu_time.longitude_offset_seconds == -3824,
        "成都经度校正应约为-63分44秒");

    BirthTimeOptions urumqi{
        .mode = BirthTimeMode::TrueSolarTime,
        .longitude = 87.617
    };
    const auto urumqi_time = correct_birth_time(
        BirthDateTime{1994, 12, 8, 22, 50, 0}, urumqi);
    require(urumqi_time.longitude_offset_seconds == -7772,
        "乌鲁木齐经度校正应约为-129分32秒");
    require(urumqi_time.chart_time.hour == 20,
        "乌鲁木齐22:50应校正到20点附近");

    BirthTimeOptions daylight_saving{
        .mode = BirthTimeMode::TrueSolarTime,
        .longitude = 120.0,
        .daylight_saving_minutes = 60
    };
    const auto daylight_time = correct_birth_time(birth, daylight_saving);
    require(daylight_time.standard_time.hour == 8 && daylight_time.standard_time.minute == 5,
        "夏令时应先还原为标准时间");

    BirthTimeOptions western_location{
        .mode = BirthTimeMode::TrueSolarTime,
        .longitude = 73.0
    };
    const auto crossed = correct_birth_time(
        BirthDateTime{2000, 1, 1, 0, 10, 0}, western_location);
    require(crossed.crossed_date_boundary,
        "极西地区午夜附近应能跨到前一日");
    require(crossed.chart_time.year == 1999 && crossed.chart_time.month == 12
        && crossed.chart_time.day == 31,
        "跨日后日期必须正确归一化");

    const auto legacy = pai_pan_solar(1994, 12, 8, 9, true);
    const auto explicit_standard = pai_pan_solar(
        BirthDateTime{1994, 12, 8, 9, 0, 0}, true);
    require(legacy.hour_pillar.to_string() == explicit_standard.hour_pillar.to_string(),
        "旧接口与显式标准时间接口的时柱必须一致");
    require(legacy.ming_gong_index == explicit_standard.ming_gong_index,
        "旧接口与显式标准时间接口的命宫必须一致");

    const auto corrected_chart = pai_pan_solar(birth, true, chengdu);
    require(corrected_chart.time_correction.chart_time.minute != birth.minute
        || corrected_chart.time_correction.chart_time.hour != birth.hour,
        "启用真太阳时后结果必须保存校正时间");
    const auto json = export_to_json(corrected_chart);
    require(json.find("true_solar_time") != std::string::npos,
        "JSON必须标明真太阳时模式");
    require(json.find("longitude_offset_seconds") != std::string::npos,
        "JSON必须包含经度校正明细");

    fmt::print("真太阳时校验通过\n");
    fmt::print("杭州：总校正 {:+d} 秒\n", hangzhou_time.total_offset_seconds);
    fmt::print("成都：总校正 {:+d} 秒\n", chengdu_time.total_offset_seconds);
    fmt::print("乌鲁木齐：{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}\n",
        urumqi_time.chart_time.year, urumqi_time.chart_time.month,
        urumqi_time.chart_time.day, urumqi_time.chart_time.hour,
        urumqi_time.chart_time.minute, urumqi_time.chart_time.second);
    return 0;
}
