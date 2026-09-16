// 公共历法适配组件
// 集中管理日期互转、真太阳时校正、tyme 时间对象构造和八字提取流程。
export module ZhouYi.Common.Calendar;

export import ZhouYi.Common.DateTime;
import ZhouYi.tyme;
import std;

export namespace ZhouYi::Common::Calendar {

enum class SolarTimeMode {
    StandardTime,
    TrueSolarTime
};

struct SolarTimeOptions {
    SolarTimeMode mode = SolarTimeMode::StandardTime;
    double longitude = 120.0;
    double standard_meridian = 120.0;
    int daylight_saving_minutes = 0;
};

struct TrueSolarTimeOptions {
    double longitude = 120.0;
    double standard_meridian = 120.0;
    int daylight_saving_minutes = 0;
};

struct SolarTimeCorrection {
    SolarTimeMode mode;
    SolarDateTime recorded_time;
    SolarDateTime standard_time;
    SolarDateTime chart_time;
    double longitude;
    double standard_meridian;
    int daylight_saving_minutes;
    int longitude_offset_seconds;
    int equation_of_time_seconds;
    int total_offset_seconds;
    bool crossed_date_boundary;
};

namespace detail {

inline void validate_solar_date_time(const SolarDateTime& value) {
    if (!DateTime::is_valid_solar_date_time(value)) {
        throw std::invalid_argument("公历日期时间无效");
    }
}

inline void validate_lunar_date_time(const LunarDateTime& value) {
    if (!DateTime::is_valid_lunar_date(value)) {
        throw std::invalid_argument("农历日期时间无效");
    }
}

inline void validate_solar_time_options(const SolarTimeOptions& options) {
    if (!std::isfinite(options.longitude) ||
        options.longitude < -180.0 || options.longitude > 180.0) {
        throw std::invalid_argument("出生地经度必须在-180到180度之间");
    }
    if (!std::isfinite(options.standard_meridian) ||
        options.standard_meridian < -180.0 || options.standard_meridian > 180.0) {
        throw std::invalid_argument("标准经线必须在-180到180度之间");
    }
    if (options.daylight_saving_minutes < 0 ||
        options.daylight_saving_minutes > 180) {
        throw std::invalid_argument("夏令时校正分钟必须在0到180之间");
    }
}

} // namespace detail

inline tyme::SolarTime to_solar_time(const SolarDateTime& value) {
    detail::validate_solar_date_time(value);
    return tyme::SolarTime::from_ymd_hms(
        value.year, value.month, value.day,
        value.hour, value.minute, value.second
    );
}

inline tyme::LunarHour to_lunar_hour(const LunarDateTime& value) {
    detail::validate_lunar_date_time(value);
    return tyme::LunarHour::from_ymd_hms(
        value.year, value.month, value.day,
        value.hour, value.minute, value.second
    );
}

inline tyme::SolarTime to_solar_time(const LunarDateTime& value) {
    return to_lunar_hour(value).get_solar_time();
}

inline SolarDateTime from_solar_time(const tyme::SolarTime& value) {
    return SolarDateTime{
        .year = value.get_year(),
        .month = value.get_month(),
        .day = value.get_day(),
        .hour = value.get_hour(),
        .minute = value.get_minute(),
        .second = value.get_second()
    };
}

inline SolarDateTime from_lunar_time(const tyme::LunarHour& value) {
    return from_solar_time(value.get_solar_time());
}

/**
 * @brief 将公共公历日期时间转换为公共农历日期时间。
 *
 * 闰月用负数月份表示，例如 -4 表示闰四月。
 */
inline LunarDateTime solar_to_lunar(const SolarDateTime& value) {
    const auto lunar = to_solar_time(value).get_lunar_hour();
    const auto lunar_month = lunar.get_lunar_day().get_lunar_month();
    return LunarDateTime{
        .year = lunar.get_year(),
        .month = lunar_month.get_month_with_leap(),
        .day = lunar.get_day(),
        .hour = lunar.get_hour(),
        .minute = lunar.get_minute(),
        .second = lunar.get_second()
    };
}

/**
 * @brief 将公共农历日期时间转换为公共公历日期时间。
 */
inline SolarDateTime lunar_to_solar(const LunarDateTime& value) {
    return from_solar_time(to_solar_time(value));
}

/**
 * @brief 计算日期对应的均时差，单位为秒。
 *
 * 采用 NOAA fractional-year approximation。正值表示视太阳时领先平太阳时。
 */
inline int calculate_equation_of_time_seconds(const SolarDateTime& value) {
    detail::validate_solar_date_time(value);
    const bool leap_year = DateTime::is_leap_year(value.year);
    const int day_of_year = DateTime::day_of_year(
        value.year, value.month, value.day);
    const int days_in_year = leap_year ? 366 : 365;
    const double fractional_hour = static_cast<double>(value.hour)
        + static_cast<double>(value.minute) / 60.0
        + static_cast<double>(value.second) / 3600.0;
    const double gamma = 2.0 * std::numbers::pi / days_in_year
        * (day_of_year - 1 + (fractional_hour - 12.0) / 24.0);

    const double minutes = 229.18 * (
        0.000075
        + 0.001868 * std::cos(gamma)
        - 0.032077 * std::sin(gamma)
        - 0.014615 * std::cos(2.0 * gamma)
        - 0.040849 * std::sin(2.0 * gamma)
    );
    return static_cast<int>(std::lround(minutes * 60.0));
}

/**
 * @brief 根据标准时间、经度和均时差计算校正后的太阳时。
 *
 * 标准时间模式会原样返回输入时间；真太阳时模式按以下关系计算：
 * 真太阳时 = 标准时间 + (经度 - 标准经线) * 4分钟 + 均时差。
 */
inline SolarTimeCorrection correct_solar_time(
    const SolarDateTime& recorded_time,
    const SolarTimeOptions& options = {}
) {
    detail::validate_solar_time_options(options);
    const auto recorded = to_solar_time(recorded_time);
    if (options.mode == SolarTimeMode::StandardTime) {
        return SolarTimeCorrection{
            .mode = options.mode,
            .recorded_time = recorded_time,
            .standard_time = recorded_time,
            .chart_time = recorded_time,
            .longitude = options.longitude,
            .standard_meridian = options.standard_meridian,
            .daylight_saving_minutes = 0,
            .longitude_offset_seconds = 0,
            .equation_of_time_seconds = 0,
            .total_offset_seconds = 0,
            .crossed_date_boundary = false
        };
    }

    const auto standard = recorded.next(-options.daylight_saving_minutes * 60);
    const auto standard_time = from_solar_time(standard);
    const int longitude_offset = static_cast<int>(std::lround(
        (options.longitude - options.standard_meridian) * 240.0
    ));
    const int equation_offset = calculate_equation_of_time_seconds(standard_time);
    const int solar_offset = longitude_offset + equation_offset;
    const auto chart_time = from_solar_time(standard.next(solar_offset));
    const bool crossed_date =
        recorded_time.year != chart_time.year ||
        recorded_time.month != chart_time.month ||
        recorded_time.day != chart_time.day;

    return SolarTimeCorrection{
        .mode = options.mode,
        .recorded_time = recorded_time,
        .standard_time = standard_time,
        .chart_time = chart_time,
        .longitude = options.longitude,
        .standard_meridian = options.standard_meridian,
        .daylight_saving_minutes = options.daylight_saving_minutes,
        .longitude_offset_seconds = longitude_offset,
        .equation_of_time_seconds = equation_offset,
        .total_offset_seconds = -options.daylight_saving_minutes * 60 + solar_offset,
        .crossed_date_boundary = crossed_date
    };
}

/**
 * @brief 直接计算真太阳时。
 */
inline SolarTimeCorrection calculate_true_solar_time(
    const SolarDateTime& recorded_time,
    const TrueSolarTimeOptions& options = {}
) {
    return correct_solar_time(recorded_time, SolarTimeOptions{
        .mode = SolarTimeMode::TrueSolarTime,
        .longitude = options.longitude,
        .standard_meridian = options.standard_meridian,
        .daylight_saving_minutes = options.daylight_saving_minutes
    });
}

inline tyme::EightChar eight_char_from_solar_time(const tyme::SolarTime& value) {
    return value.get_lunar_hour().get_eight_char();
}

inline tyme::EightChar eight_char_from_lunar_time(const tyme::LunarHour& value) {
    return value.get_eight_char();
}

} // namespace ZhouYi::Common::Calendar
