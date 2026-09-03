// 紫微斗数真太阳时校正
export module ZhouYi.ZiWei.SolarTime;

import std;
import ZhouYi.tyme;

export namespace ZhouYi::ZiWei {
    enum class BirthTimeMode {
        StandardTime,
        TrueSolarTime
    };

    struct BirthDateTime {
        int year;
        int month;
        int day;
        int hour;
        int minute = 0;
        int second = 0;
    };

    struct BirthTimeOptions {
        BirthTimeMode mode = BirthTimeMode::StandardTime;
        double longitude = 120.0;
        double standard_meridian = 120.0;
        int daylight_saving_minutes = 0;
    };

    struct SolarTimeCorrection {
        BirthTimeMode mode;
        BirthDateTime recorded_time;
        BirthDateTime standard_time;
        BirthDateTime chart_time;
        double longitude;
        double standard_meridian;
        int daylight_saving_minutes;
        int longitude_offset_seconds;
        int equation_of_time_seconds;
        int total_offset_seconds;
        bool crossed_date_boundary;
    };

    inline BirthDateTime to_birth_date_time(const tyme::SolarTime& time) {
        return BirthDateTime{
            .year = time.get_year(),
            .month = time.get_month(),
            .day = time.get_day(),
            .hour = time.get_hour(),
            .minute = time.get_minute(),
            .second = time.get_second()
        };
    }

    inline tyme::SolarTime to_solar_time(const BirthDateTime& time) {
        return tyme::SolarTime::from_ymd_hms(
            time.year, time.month, time.day,
            time.hour, time.minute, time.second
        );
    }

    inline int calculate_equation_of_time_seconds(const BirthDateTime& time) {
        static constexpr std::array<int, 12> DAYS_BEFORE_MONTH{
            0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334
        };

        const bool leap_year =
            time.year % 4 == 0 && (time.year % 100 != 0 || time.year % 400 == 0);
        int day_of_year = DAYS_BEFORE_MONTH.at(static_cast<std::size_t>(time.month - 1)) + time.day;
        if (leap_year && time.month > 2) {
            ++day_of_year;
        }

        const int days_in_year = leap_year ? 366 : 365;
        const double fractional_hour = static_cast<double>(time.hour)
            + static_cast<double>(time.minute) / 60.0
            + static_cast<double>(time.second) / 3600.0;
        const double gamma = 2.0 * std::numbers::pi / days_in_year
            * (day_of_year - 1 + (fractional_hour - 12.0) / 24.0);

        // NOAA fractional-year approximation. Positive means apparent solar time is ahead.
        const double minutes = 229.18 * (
            0.000075
            + 0.001868 * std::cos(gamma)
            - 0.032077 * std::sin(gamma)
            - 0.014615 * std::cos(2.0 * gamma)
            - 0.040849 * std::sin(2.0 * gamma)
        );
        return static_cast<int>(std::lround(minutes * 60.0));
    }

    inline SolarTimeCorrection correct_birth_time(
        const BirthDateTime& birth,
        const BirthTimeOptions& options = {}
    ) {
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

        const auto recorded = to_solar_time(birth);
        if (options.mode == BirthTimeMode::StandardTime) {
            return SolarTimeCorrection{
                .mode = options.mode,
                .recorded_time = birth,
                .standard_time = birth,
                .chart_time = birth,
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
        const auto standard_birth = to_birth_date_time(standard);
        const int longitude_offset = static_cast<int>(std::lround(
            (options.longitude - options.standard_meridian) * 240.0
        ));
        const int equation_offset = calculate_equation_of_time_seconds(standard_birth);
        const int solar_offset = longitude_offset + equation_offset;
        const auto chart = standard.next(solar_offset);
        const auto chart_birth = to_birth_date_time(chart);
        const bool crossed_date =
            birth.year != chart_birth.year ||
            birth.month != chart_birth.month ||
            birth.day != chart_birth.day;

        return SolarTimeCorrection{
            .mode = options.mode,
            .recorded_time = birth,
            .standard_time = standard_birth,
            .chart_time = chart_birth,
            .longitude = options.longitude,
            .standard_meridian = options.standard_meridian,
            .daylight_saving_minutes = options.daylight_saving_minutes,
            .longitude_offset_seconds = longitude_offset,
            .equation_of_time_seconds = equation_offset,
            .total_offset_seconds = -options.daylight_saving_minutes * 60 + solar_offset,
            .crossed_date_boundary = crossed_date
        };
    }
}
