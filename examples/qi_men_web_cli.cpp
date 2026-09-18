import std;
import ZhouYi.QiMen;
import ZhouYi.QiMen.Controller;
import ZhouYi.Common.DateTime;
import nlohmann.json;

using json = nlohmann::json;

namespace {

json error_response(std::string code, std::string message) {
    return {
        {"error", {
            {"code", std::move(code)},
            {"message", std::move(message)}
        }}
    };
}

void validate_date_time(int year, int month, int day, int hour, int minute, bool lunar) {
    if (year < 1 || year > 9999) {
        throw std::invalid_argument("年份必须在 1 到 9999 之间");
    }
    if (month < 1 || month > 12) {
        throw std::invalid_argument("月份必须在 1 到 12 之间");
    }
    const auto valid = lunar
        ? ZhouYi::Common::DateTime::is_valid_lunar_date(
            ZhouYi::Common::LunarDateTime{year, month, day, hour, minute, 0})
        : ZhouYi::Common::DateTime::is_valid_solar_date_time(
            ZhouYi::Common::SolarDateTime{year, month, day, hour, minute, 0});
    if (!valid) {
        throw std::invalid_argument("日期时间无效");
    }
}

/**
 * @brief 规则口径标识（参照大六壬 DLR-205 样板，纯新增 meta.rule_profile 字段）
 *
 * 每条描述以 src/qi_men 当前代码行为为准，不引入未经代码证实的古籍归属。
 */
json rule_profile() {
    return {
        {"profile_version", "qi-men-rules/1.0"},
        {"calibration_status", "calibrated"},
        {"rules", {
            {"qi_ju_method",
                "拆补法：起局节气取当日所值节气（tyme 历法），三元以日干支回推符头（甲或己日）定——"
                "符头支四仲（子午卯酉）上元、四孟（寅申巳亥）中元、四季（辰戌丑未）下元，"
                "局数查节气×三元定局表（如冬至上中下三元依次1、7、4局，夏至依次9、3、6局）；无超神接气置闰逻辑"},
            {"shichen_scope",
                "时家奇门：以排盘时刻的时辰干支定旬首与值符值使落宫；时辰按钟点数二小时一支（23-1时为子），"
                "时干按四柱日干五鼠遁（甲己起甲子至戊癸起壬子）；日干支取统一八字历法（tyme 默认晚子时日柱算次日，"
                "故23时后时干按次日日干起）；分钟不参与起局，仅体现在输出的四柱展示字段"},
            {"pan_method",
                "转盘：地盘的六仪三奇（固定顺序戊己庚辛壬癸丁丙乙）自局数宫起依九宫数阳遁顺飞、阴遁逆飞排布；"
                "天盘九星与人盘八门各自整体沿洛书外围八宫环（1→8→3→4→9→2→7→6）转动，环上相对次序不变，"
                "转宫步数由值符值使落宫决定（阴阳遁差异体现在判宫而非环序）"},
            {"zhi_fu_zhi_shi",
                "值符：时柱旬首六仪所在地盘宫之本宫星（随时干加临——旬首仪所在宫之星转至时干所落地盘宫），"
                "值使：同宫之本宫门（从旬首宫起旬首时支，阳遁顺、阴遁逆按九宫数数至当前时支，落中五寄坤二后带动八门转盘）；"
                "阴阳遁以节气切换：冬至至（不含）夏至为阳遁，夏至至（不含）冬至为阴遁"},
            {"jia_hidden",
                "六甲旬首遁藏于六仪：甲子戊、甲戌己、甲申庚、甲午辛、甲辰壬、甲寅癸（按旬查表）；"
                "三奇六仪布地盘顺序固定为戊己庚辛壬癸丁丙乙"},
            {"zhong_gong_ji_kun",
                "中五宫寄坤二宫：凡转盘判宫落中五者取坤二（值符原宫、时干定位皆如此），"
                "天禽星恒留中五宫输出但以 lodged_star 形式寄载于坤二宫、随天禽之干以 lodged_tian_gan 标注；"
                "中五宫本身不布门不布神（gate/spirit 为空），阳遁阴遁同规"},
            {"shen_sha_set",
                "盘面名单固定九星：天蓬天芮天冲天辅天禽天心天柱天任天英（本宫各配一宫）；"
                "八门：休生伤杜景死惊开（中宫无门）；八神：直符腾蛇太阴六合白虎玄武九地九天，"
                "自值符所在时宫起，阳遁沿洛书环顺布、阴遁逆布，中五宫无神"}
        }}
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

        const auto& date = request.at("date");
        const int year = date.at("year").get<int>();
        const int month = date.at("month").get<int>();
        const int day = date.at("day").get<int>();
        const int hour = date.value("hour", 0);
        const int minute = date.value("minute", 0);
        const bool lunar = calendar == "lunar";
        validate_date_time(year, month, day, hour, minute, lunar);

        auto result = lunar
            ? ZhouYi::QiMen::QiMenController::pai_pan_lunar(
                year, date.value("leap_month", false) ? -month : month, day, hour, minute)
            : ZhouYi::QiMen::QiMenController::pai_pan_solar(year, month, day, hour, minute);
        if (!result) {
            std::cout << error_response("CALCULATION_FAILED", result.error()).dump();
            return 2;
        }

        // 纯增量追加 meta.rule_profile：控制器输出的字节序列原样保留，
        // 仅在对象收尾大括号前插入 meta 成员（大六壬 DLR-205 样板，不改旧字段）。
        std::string pan_json = ZhouYi::QiMen::QiMenController::get_pan_json_ordered(result.value());
        const json meta_value = {{"rule_profile", rule_profile()}};
        std::string meta_member = "\"meta\": " + meta_value.dump(2);
        // 除首行外整体提升缩进 2 空格，匹配外层对象的成员风格。
        for (std::size_t pos = meta_member.find('\n'); pos != std::string::npos; pos = meta_member.find('\n', pos + 3)) {
            meta_member.insert(pos + 1, "  ");
        }
        pan_json.pop_back();  // 去掉收尾 '}'
        pan_json += ",\n  " + meta_member + "\n}";
        std::cout << pan_json;
        return 0;
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump();
        return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump();
        return 1;
    }
}
