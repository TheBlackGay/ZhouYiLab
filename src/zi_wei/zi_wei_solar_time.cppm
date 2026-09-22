// 紫微斗数真太阳时校正
export module ZhouYi.ZiWei.SolarTime;

import std;
import ZhouYi.Common.Calendar;
import ZhouYi.tyme;

export namespace ZhouYi::ZiWei {
    // 保留原有名称，底层统一使用公共公历时间结构。
    using BirthDateTime = ZhouYi::Common::SolarDateTime;

    // 保留旧 API 名称，实际类型和算法统一由公共日历组件提供。
    using BirthTimeMode = ZhouYi::Common::Calendar::SolarTimeMode;
    using BirthTimeOptions = ZhouYi::Common::Calendar::SolarTimeOptions;
    using SolarTimeCorrection = ZhouYi::Common::Calendar::SolarTimeCorrection;

    inline BirthDateTime to_birth_date_time(const tyme::SolarTime& time) {
        return ZhouYi::Common::Calendar::from_solar_time(time);
    }

    inline tyme::SolarTime to_solar_time(const BirthDateTime& time) {
        return ZhouYi::Common::Calendar::to_solar_time(time);
    }

    inline int calculate_equation_of_time_seconds(const BirthDateTime& time) {
        return ZhouYi::Common::Calendar::calculate_equation_of_time_seconds(time);
    }

    inline SolarTimeCorrection correct_birth_time(
        const BirthDateTime& birth,
        const BirthTimeOptions& options = {}
    ) {
        return ZhouYi::Common::Calendar::correct_solar_time(birth, options);
    }
}
