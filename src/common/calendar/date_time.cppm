// 公共日期时间组件
// 统一提供排盘模块使用的日期结构、边界校验和显示格式。
export module ZhouYi.Common.DateTime;

import std;

export namespace ZhouYi::Common {

/**
 * @brief 公历日期时间。
 *
 * 该结构只描述输入的民用时间，不携带时区或真太阳时语义。
 */
struct SolarDateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute = 0;
    int second = 0;
};

/**
 * @brief 农历日期时间。
 *
 * month 为负数时表示闰月，正数表示普通月份。
 */
struct LunarDateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute = 0;
    int second = 0;
};

namespace DateTime {

constexpr bool is_leap_year(int year) noexcept {
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

/**
 * @brief 获取公历月份天数。
 *
 * 非法月份返回 0，调用方可直接将结果用于日期合法性判断。
 */
constexpr int days_in_month(int year, int month) noexcept {
    constexpr std::array<int, 12> days{
        31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    };
    if (month < 1 || month > 12) return 0;
    if (month == 2) return is_leap_year(year) ? 29 : 28;
    return days[static_cast<std::size_t>(month - 1)];
}

constexpr bool is_valid_solar_date(int year, int month, int day) noexcept {
    return year >= 1 && year <= 9999
        && month >= 1 && month <= 12
        && day >= 1 && day <= days_in_month(year, month);
}

constexpr bool is_valid_clock_time(int hour, int minute = 0, int second = 0) noexcept {
    return hour >= 0 && hour <= 23
        && minute >= 0 && minute <= 59
        && second >= 0 && second <= 59;
}

constexpr bool is_valid_solar_date_time(const SolarDateTime& value) noexcept {
    return is_valid_solar_date(value.year, value.month, value.day)
        && is_valid_clock_time(value.hour, value.minute, value.second);
}

constexpr bool is_valid_lunar_date(const LunarDateTime& value) noexcept {
    return value.year >= 1 && value.year <= 9999
        && value.month != 0 && value.month >= -12 && value.month <= 12
        && value.day >= 1 && value.day <= 30
        && is_valid_clock_time(value.hour, value.minute, value.second);
}

constexpr int day_of_year(int year, int month, int day) noexcept {
    if (!is_valid_solar_date(year, month, day)) return 0;
    constexpr std::array<int, 12> days_before_month{
        0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334
    };
    const int leap_day = is_leap_year(year) && month > 2 ? 1 : 0;
    return days_before_month[static_cast<std::size_t>(month - 1)] + day + leap_day;
}

inline std::string format(const SolarDateTime& value) {
    return std::format("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}",
        value.year, value.month, value.day,
        value.hour, value.minute, value.second);
}

inline std::string format(const LunarDateTime& value) {
    if (value.month < 0) {
        // 闰月（负月约定）以"闰NN"呈现，避免 "{:02d}" 直落负数产生 "--2" 类畸形串。
        return std::format("{:04d}-闰{:02d}-{:02d} {:02d}:{:02d}:{:02d}",
            value.year, -value.month, value.day,
            value.hour, value.minute, value.second);
    }
    return std::format("{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}",
        value.year, value.month, value.day,
        value.hour, value.minute, value.second);
}

} // namespace DateTime
} // namespace ZhouYi::Common
