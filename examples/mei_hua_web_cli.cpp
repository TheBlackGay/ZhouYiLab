/**
 * @brief 梅花易数网页 JSON CLI（内核桥接，meihua-plate/1.0）
 *
 * 请求：{ "mode": "time" | "numbers"（默认 time）,
 *         "calendar": "solar" | "lunar"（默认 solar）,
 *         "date": { year, month, day, hour, minute?, leap_month? },
 *         "numbers": [n1, n2(, n3)]   // 仅 mode=numbers }
 * 输出：内核事实盘 + meta.rule_profile（meihua-rules/0.1，calibration=pending）。
 */
import std;
import ZhouYi.MeiHua;
import ZhouYi.BaZiBase;
import ZhouYi.Common.Calendar;
import ZhouYi.Common.DateTime;
import nlohmann.json;

using json = nlohmann::json;

namespace {
json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}

void validate_date(int year, int month, int day, int hour, bool lunar) {
    const auto valid = lunar
        ? ZhouYi::Common::DateTime::is_valid_lunar_date(
            ZhouYi::Common::LunarDateTime{year, month, day, hour, 0, 0})
        : ZhouYi::Common::DateTime::is_valid_solar_date_time(
            ZhouYi::Common::SolarDateTime{year, month, day, hour, 0, 0});
    if (!valid) throw std::invalid_argument("日期时间无效");
}

/**
 * @brief 规则口径标识（大六壬 DLR-205 样板同款，新模块 pending 起步）
 */
json rule_profile() {
    return {
        {"profile_version", "meihua-rules/0.1"},
        {"calibration_status", "pending"},
        {"rules", {
            {"casting_method",
                "时间起卦取《梅花易数》年月日时法：年支序（子1…亥12，年柱地支、立春为岁首）、"
                "农历月数、农历日数、时支序（时柱地支）；上卦=(年+月+日) mod 8、"
                "下卦=(年+月+日+时) mod 8、动爻=总数 mod 6，余 0 一律作满数（8/6）；"
                "先天卦数乾1兑2离3震4巽5坎6艮7坤8"},
            {"leap_month_rule",
                "闰月取数用十五分界（D13.1 已拍板 2026-09-20，与紫微 D12 同一把尺）："
                "闰 M 月初十五日（含）前作 M 月、十六日起作 M+1 月，闰十二下半月回绕作正月；"
                "前台不暴露选项，如需改口径另行登记参数"},
            {"numbers_mode",
                "报数起卦（D13.3 同批）：两数 n1,n2 → 上卦=n1%8、下卦=n2%8、动爻=(n1+n2)%6；"
                "三数另以 (n1+n2+n3)%6 定动爻；报数须正整数，余 0 作满数；"
                "月令旺衰仍取请求时间的四柱，时间上下文不可缺"},
            {"ti_yong_basis",
                "动爻所临之经卦为用、另一为体（动在上卦则上为用）；互卦取本卦二三四爻为下体、"
                "三四五爻为上体，为事之中程；变卦=动爻阴阳翻转，为事之终结；"
                "三卦皆输出卦码/卦名/八宫归属与上下体卦名五行"},
            {"wang_shuai_basis",
                "体用卦五行按月令判旺相休囚死五态，辰戌丑未月视作土令；"
                "与六爻内核共用 DEF-4 修复后的《翼氏大典》月令五态通行表（tests 双向锁表），"
                "梅花为该函数六爻之外的第一实战消费方"},
            {"gua_name_lookup",
                "卦名与八宫查表复用六爻内核（京房八宫 64 卦表），仅作盘面结构信息输出，"
                "不据宫位附加断语"},
            {"calendar_context",
                "公历/农历转换、干支四柱与时辰归支复用统一八字历法层（tyme），与 D2 月将口径自洽；"
                "农历输入闰月以 leap_month 标志表示"},
            {"judgment_scope",
                "仅输出盘面事实与体用生克五态关系判词（体用比和/用生体/用克体/体生用/体克用），"
                "不输出吉凶、应期与事类断语；断语层待案例校准（仿 D3 三步走）后另行评审接入"}
        }}
    };
}
} // namespace

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto mode = request.value("mode", std::string("time"));
        const auto calendar = request.value("calendar", std::string("solar"));
        const bool lunar = calendar == "lunar";
        if (!lunar && calendar != "solar") throw std::invalid_argument("calendar 必须是 solar 或 lunar");
        if (mode != "time" && mode != "numbers")
            throw std::invalid_argument("mode 必须是 time 或 numbers");
        const auto& date = request.at("date");
        const int year = date.at("year"), month = date.at("month"), day = date.at("day");
        const int hour = date.value("hour", 0), minute = date.value("minute", 0);
        validate_date(year, month, day, hour, lunar);

        ZhouYi::BaZiBase::BaZi bazi = lunar
            ? ZhouYi::BaZiBase::BaZi::from_lunar(year, date.value("leap_month", false) ? -month : month, day, hour)
            : ZhouYi::BaZiBase::BaZi::from_solar(year, month, day, hour, minute);

        json plate = [&] {
            if (mode == "numbers") {
                const auto numbers = request.at("numbers").get<std::vector<int>>();
                return ZhouYi::MeiHua::numbers_plate(numbers, bazi);
            }
            int signed_lunar_month;
            int lunar_day;
            if (lunar) {
                signed_lunar_month = date.value("leap_month", false) ? -month : month;
                lunar_day = day;
            } else {
                const auto lunar_dt = ZhouYi::Common::Calendar::solar_to_lunar(
                    ZhouYi::Common::SolarDateTime{year, month, day, hour, minute, 0});
                signed_lunar_month = lunar_dt.month;  // 历法层约定：负数=闰月
                lunar_day = lunar_dt.day;
            }
            const int year_order = static_cast<int>(bazi.year.zhi) + 1;
            const int hour_order = static_cast<int>(bazi.hour.zhi) + 1;
            return ZhouYi::MeiHua::time_plate(year_order, signed_lunar_month, lunar_day,
                                              hour_order, bazi);
        }();

        plate["meta"] = {{"rule_profile", rule_profile()}};
        std::cout << plate.dump();
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump(); return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump(); return 1;
    }
    return 0;
}
