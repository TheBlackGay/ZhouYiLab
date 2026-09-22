/**
 * @module ZhouYi.MeiHua
 * @brief 梅花易数起卦引擎（M1：时间/报数双式起卦 + 体用互变事实盘）
 *
 * 平台原则（docs/product/梅花易数立项设计方案.md v0.1）：
 * * 排盘事实全部由内核产出：起卦取数、本互变推演、体用定位、月令旺衰，
 *   输出契约 meihua-plate/1.0；
 * * 零口径发明：卦名/宫位查表与变卦翻转复用六爻内核（get_hexagram_info），
 *   体用旺衰复用 DEF-4 修复后的月令五态通行表（getWangShuai），
 *   闰月取数与紫微 D12 同一把"十五分界"尺（D13.1 已拍板）；
 * * 年支以立春为岁首（统一八字历法层年柱口径），农历月日记数随输入历法；
 * * 不输出吉凶/应期断语（calibration=pending，断语押后至案例校准）。
 */
export module ZhouYi.MeiHua;

import nlohmann.json;
import ZhouYi.BaZiBase;        // BaZi / Pillar（四柱、月令、时辰地支）
import ZhouYi.GanZhi;          // DiZhi 枚举
import ZhouYi.WuXingUtils;     // getWangShuai / getElementRelationship
import ZhouYi.LiuYao;          // HexagramInfo（查表结果类型）
import ZhouYi.LiuYaoController; // get_hexagram_info：64 卦名/宫位查表复用
import std;

export namespace ZhouYi::MeiHua {

using json = nlohmann::json;
using ZhouYi::BaZiBase::BaZi;
using ZhouYi::BaZiBase::Pillar;

constexpr const char* PLATE_SCHEMA_VERSION = "meihua-plate/1.0";

// ==================== 先天卦数 ====================
/**
 * @brief 先天八卦数（乾一兑二离三震四巽五坎六艮七坤八）。
 * code 为经卦三爻自下而上（初/二/三爻），1 阳 0 阴；
 * 乾"111" 兑"110" 离"101" 震"100" 巽"011" 坎"010" 艮"001" 坤"000"。
 */
struct Trigram {
    int number;
    const char* name;
    const char* code;
    const char* element;
};

inline const Trigram& trigram_by_number(int number) {
    static constexpr Trigram table[9] = {
        {0, "", "", ""},
        {1, "乾", "111", "金"}, {2, "兑", "110", "金"},
        {3, "离", "101", "火"}, {4, "震", "100", "木"},
        {5, "巽", "011", "木"}, {6, "坎", "010", "水"},
        {7, "艮", "001", "土"}, {8, "坤", "000", "土"},
    };
    if (number < 1 || number > 8) throw std::invalid_argument("卦数须为 1-8");
    return table[number];
}

inline const Trigram& trigram_by_code(const std::string& code3) {
    for (int n = 1; n <= 8; ++n) {
        const Trigram& t = trigram_by_number(n);
        if (code3 == t.code) return t;
    }
    throw std::invalid_argument("无法识别的三爻卦码: " + code3);
}

/** 余 0 作满数（起卦通例：mod 8 余 0 即坤 8，mod 6 余 0 即上爻 6）。 */
inline int mod_or_full(int value, int modulus) {
    int r = value % modulus;
    return r == 0 ? modulus : r;
}

/**
 * @brief 闰月取数（D13.1 拍板：十五分界，与紫微 D12 同尺同源）
 * @param signed_month 农历月（负数=闰 M 月，沿用历法层通用符号约定）
 * @param day 农历日（1-30）
 * @return 参与起卦的月数：闰月初 15 日（含）作本闰月 M，16 日起作下一月 M+1（闰十二下半月回绕正月）
 */
inline int cast_lunar_month(int signed_month, int day) {
    if (signed_month > 0) return signed_month;
    const int base = -signed_month;
    if (day < 1 || day > 30) throw std::invalid_argument("农历日无效");
    return day <= 15 ? base : base % 12 + 1;
}

// ==================== 三卦推演 ====================

struct PlateGua {
    std::string code;   // 六爻码，第 0 位是初爻（自下而上，1 阳 0 阴）
    std::string name;   // 卦名（六爻查表）
    std::string palace; // 八宫归属（查表）
    Trigram upper{};    // 外卦（四五六爻）
    Trigram lower{};    // 内卦（初二三爻）
};

inline PlateGua plate_from_code(const std::string& code) {
    if (code.size() != 6 ||
        code.find_first_not_of("01") != std::string::npos) {
        throw std::invalid_argument("卦码必须是六位 0/1 字符串");
    }
    auto info = ZhouYi::LiuYaoController::get_hexagram_info(code);
    PlateGua gua;
    gua.code = code;
    gua.name = info.name;
    gua.palace = info.palaceType;
    gua.lower = trigram_by_code(code.substr(0, 3));
    gua.upper = trigram_by_code(code.substr(3, 3));
    return gua;
}

/** 互卦：本卦二三四爻为下体、三四五爻为上体（事之中程）。 */
inline std::string mutual_code(const std::string& code) {
    return code.substr(1, 3) + code.substr(2, 3);
}

/** 变卦：动爻位（1-6）阴阳翻转（事之终结）。 */
inline std::string changed_code(const std::string& code, int moving_line) {
    if (moving_line < 1 || moving_line > 6) throw std::invalid_argument("动爻须为 1-6");
    std::string out = code;
    out[moving_line - 1] = (out[moving_line - 1] == '1') ? '0' : '1';
    return out;
}

// ==================== 体用 ====================

/** 动爻在下体（初至三爻）则下为用、上为体；反之亦然。 */
inline bool yong_is_lower(int moving_line) { return moving_line <= 3; }

/** 以体为主语的用之判词：用生体/用克体/体生用/体克用/体用比和。 */
inline std::string ti_yong_phrase(const std::string& ti_element,
                                  const std::string& yong_element) {
    using ZhouYi::WuXingUtils::ElementalRelation;
    using ZhouYi::WuXingUtils::getElementRelationship;
    switch (getElementRelationship(ti_element, yong_element)) {
        case ElementalRelation::Same:         return "体用比和";
        case ElementalRelation::GeneratedBy:  return "用生体";   // 生我
        case ElementalRelation::Generates:    return "体生用";   // 我生（泄）
        case ElementalRelation::ControlledBy: return "用克体";   // 克我
        case ElementalRelation::Controls:     return "体克用";   // 我克
        default:                              return "关系无效";
    }
}

// ==================== 事实盘装配 ====================

namespace detail {

inline json gua_json(const PlateGua& gua) {
    return {
        {"code", gua.code}, {"name", gua.name}, {"palace", gua.palace},
        {"inner", gua.lower.name}, {"inner_element", gua.lower.element},
        {"outer", gua.upper.name}, {"outer_element", gua.upper.element},
    };
}

inline json trigram_json(const Trigram& t) {
    return {{"number", t.number}, {"name", t.name}, {"element", t.element}};
}

/** 三图共用装配：由上下卦数 + 动爻 + 四柱产出完整事实盘 JSON。 */
inline json assemble(int upper_number, int lower_number, int moving_line,
                     const BaZi& bazi, const json& casting) {
    const Trigram& upper = trigram_by_number(upper_number);
    const Trigram& lower = trigram_by_number(lower_number);
    const std::string code = std::string(lower.code) + upper.code;
    const PlateGua ben = plate_from_code(code);
    const PlateGua hu = plate_from_code(mutual_code(code));
    const PlateGua bian = plate_from_code(changed_code(code, moving_line));

    const bool lower_is_yong = yong_is_lower(moving_line);
    const Trigram& yao = lower_is_yong ? lower : upper;
    const Trigram& ti = lower_is_yong ? upper : lower;
    const std::string month_branch = bazi.month.branch();

    return {
        {"schema_version", PLATE_SCHEMA_VERSION},
        {"casting", casting},
        {"ba_zi", {
            {"year",  {{"stem", bazi.year.stem()},  {"branch", bazi.year.branch()}}},
            {"month", {{"stem", bazi.month.stem()}, {"branch", month_branch}}},
            {"day",   {{"stem", bazi.day.stem()},   {"branch", bazi.day.branch()}}},
            {"hour",  {{"stem", bazi.hour.stem()},  {"branch", bazi.hour.branch()}}},
            {"month_command", month_branch},
        }},
        {"ben_gua", gua_json(ben)},
        {"hu_gua", gua_json(hu)},
        {"bian_gua", gua_json(bian)},
        {"moving_line", moving_line},
        {"trigrams", {{"upper", trigram_json(upper)}, {"lower", trigram_json(lower)}}},
        {"ti_yong", {
            {"ti", lower_is_yong ? "upper" : "lower"},
            {"yong", lower_is_yong ? "lower" : "upper"},
            {"ti_element", ti.element},
            {"yong_element", yao.element},
            {"relation", ti_yong_phrase(ti.element, yao.element)},
            {"ti_wang_shuai", ZhouYi::WuXingUtils::getWangShuai(ti.element, month_branch)},
            {"yong_wang_shuai", ZhouYi::WuXingUtils::getWangShuai(yao.element, month_branch)},
        }},
    };
}

} // namespace detail

/**
 * @brief 时间起卦（《梅花易数》年月日时起卦法）
 * @param year_branch_order 年支序（子1…亥12，取年柱地支，立春为岁首）
 * @param signed_lunar_month 农历月（负数=闰，先经 cast_lunar_month 折算）
 * @param lunar_day 农历日（1-30）
 * @param hour_branch_order 时支序（子1…亥12，取时柱地支）
 * @param bazi 该时刻四柱（提供年支/时支/月令）
 *
 * 上卦 =（年+月+日）mod 8；下卦 =（年+月+日+时）mod 8；动爻 =（年+月+日+时）mod 6，
 * 余 0 各作满数。
 */
inline json time_plate(int year_branch_order, int signed_lunar_month, int lunar_day,
                       int hour_branch_order, const BaZi& bazi) {
    if (year_branch_order < 1 || year_branch_order > 12)
        throw std::invalid_argument("年支序须为 1-12");
    if (hour_branch_order < 1 || hour_branch_order > 12)
        throw std::invalid_argument("时支序须为 1-12");
    const int month = cast_lunar_month(signed_lunar_month, lunar_day);
    const int day = lunar_day;
    const int upper_sum = year_branch_order + month + day;
    const int full_sum = upper_sum + hour_branch_order;
    const int upper = mod_or_full(upper_sum, 8);
    const int lower = mod_or_full(full_sum, 8);
    const int moving = mod_or_full(full_sum, 6);

    json casting = {
        {"method", "time"},
        {"year_branch_order", year_branch_order},
        {"lunar_month_input_signed", signed_lunar_month},
        {"lunar_month_used", month},
        {"lunar_day", day},
        {"hour_branch_order", hour_branch_order},
        {"upper_sum", upper_sum},
        {"lower_sum", full_sum},
        {"leap_month_rule", "fifteen_boundary"},
        {"formula", "上卦=(年+月+日)%8，下卦=(年+月+日+时)%8，动爻=总数%6，余0作满数"},
    };
    return detail::assemble(upper, lower, moving, bazi, std::move(casting));
}

/**
 * @brief 报数起卦（D13.3 拍板：与时间起卦同批；两数/三数）
 * 两数：上卦=n1%8，下卦=n2%8，动爻=(n1+n2)%6；
 * 三数：上卦=n1%8，下卦=n2%8，动爻=(n1+n2+n3)%6。余 0 作满数。
 * 月令旺衰仍取请求时间的四柱（时间上下文不可缺）。
 */
inline json numbers_plate(const std::vector<int>& numbers, const BaZi& bazi) {
    if (numbers.size() != 2 && numbers.size() != 3)
        throw std::invalid_argument("报数起卦须为 2 或 3 个正整数");
    for (int n : numbers) {
        if (n < 1) throw std::invalid_argument("报数须为正整数");
    }
    const int upper = mod_or_full(numbers[0], 8);
    const int lower = mod_or_full(numbers[1], 8);
    const int sum = numbers[0] + numbers[1];
    const int moving = mod_or_full(numbers.size() == 3 ? sum + numbers[2] : sum, 6);

    json casting = {
        {"method", "numbers"},
        {"reported", numbers},
        {"upper_sum", numbers[0]},
        {"lower_sum", sum},
        {"formula", "两数：上卦=n1%8，下卦=n2%8，动爻=(n1+n2)%6；三数动爻=(n1+n2+n3)%6；余0作满数"},
    };
    return detail::assemble(upper, lower, moving, bazi, std::move(casting));
}

} // namespace ZhouYi::MeiHua
