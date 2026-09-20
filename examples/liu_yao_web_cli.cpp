import std;
import ZhouYi.LiuYaoController;
import ZhouYi.BaZiBase;
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
 * @brief 规则口径标识（参照大六壬 DLR-205 样板，纯新增 meta.rule_profile 字段）
 *
 * 每条描述以 src/liu_yao 当前代码行为为准，不引入未经代码证实的古籍归属。
 */
json rule_profile() {
    return {
        {"profile_version", "liu-yao-rules/0.2"},
        {"calibration_status", "in_progress"},
        {"rules", {
            {"input_format",
                "入参为 hexagram_code 六位字符串（仅 0/1，第 1 位是初爻、自下而上，1 阳 0 阴）"
                "与 changing_lines 动爻位列表（1-6，1=初爻，去重升序归一）；老阴老阳不经字符串传入，"
                "6/7/8/9 爻题到 0/1+动爻的换算由调用方或摇卦模拟器完成；"
                "时间入参 date 支持 solar/lunar（闰月以 leap_month 标志），公历可给分钟、农历仅取时辰，"
                "四柱（含晚子时日柱算次日、日柱旬空）复用统一八字历法口径"},
            {"na_jia",
                "京房纳甲按内外卦分别查固定表：每宫一张六位数组，前 3 位配内卦、后 3 位配外卦，"
                "乾内甲子寅辰、外壬午申戌，坤内乙未巳卯、外癸丑亥酉，震庚、坎戊、艮丙、巽辛、离己、兑丁，"
                "阳卦支顺行、阴卦支逆行；乾坤之干取通行一套（即京房本、《增删卜易》同系；"
                "D1=A 拍板 2026-09-20，代码旧注'冬至后两说'随口径确认关闭，不另设开关）"},
            {"shi_ying",
                "世应不做算法推导，按 64 卦逐卦硬编码查表打 世/应 标记，"
                "宫名与宫五行同为查表；表序与八宫卦序标准一致（本宫世6应3，一至五世递增，"
                "游魂4应1、归魂3应6），但游魂/归魂类别字段不在 JSON 输出中"},
            {"liu_qin_basis",
                "六亲一律以本卦所属八纯卦的宫五行为我（同我兄弟、我生子孙、我克妻财、克我官鬼、生我父母），"
                "与日干、世爻无关；变爻与伏神六亲亦按本卦宫五行计算"},
            {"six_spirits",
                "六神按日干起、自初爻顺布循环：甲乙青龙、丙丁朱雀、戊勾陈、己螣蛇、庚辛白虎、壬癸玄武；"
                "六神序列青龙朱雀勾陈螣蛇白虎玄武；变卦不再布六神"},
            {"fu_shen",
                "伏神取本卦所属宫之八纯卦六爻纳甲为候选，凡某六亲在本卦六爻一处不现者，"
                "即伏于本卦同序号爻下，伏神另算月破/旬空/日合日冲/入日墓入月墓/入飞神墓状态标签；"
                "D1=A 拍板（2026-09-20）：伏神'出不出、破空可否用'以《增删卜易》伏神章为准——"
                "原文逐字校勘前引擎只标注事实状态、不下可用/不可用结论（DEF-5 余项跟踪）"},
            {"wang_shuai",
                "旺衰仅以月支对每爻地支五行判旺相休囚死五态（辰戌丑未月先视作土），日辰不并入旺衰、"
                "另以生克冲合标签标注；映射从《翼氏大典》月令五态通行表（增删卜易系与现代教材同口径）："
                "当令者旺、月令生爻者相、爻生月令者休、爻克月令者囚、月令克爻者死；"
                "2026-09-20 修复实现与自身注释及通行表间相休、囚死两组标签对调的缺陷（DEF-4），"
                "爻的 wangShuai 与暗动判定（须旺或相）随之更正，此表不再是 D1 待复核项"},
            {"bian_gua",
                "变卦按动爻位 0/1 翻转得之卦、查表输出宫名卦名，仅将动爻位对应变爻的干支五行抄回本卦，"
                "静爻无变出信息；动爻标记阳动 O、阴动 X；注意无伏神/静爻时 hiddenPillar、changedPillar "
                "因默认构造恒显示甲子，判空须看 hiddenRelative、changedElement 是否空串"},
            {"state_tags_scope",
                "每爻输出月破、旬空（日柱旬）、入日墓、日合日冲、暗动、合绊、化破化墓、进退神等状态标签"
                "与约 20 种神煞（按日干/日支三合局/月支起）；进退神按《增删卜易》只认四对"
                "（子化丑、巳化午为进，丑化子、午化巳为退；2026-09-20 随 D1=A 收窄，旧邻支对表废弃）；"
                "不输出卦身、应期与吉凶断语"}
        }}
    };
}
}

int main() {
    try {
        const auto request = json::parse(std::cin);
        const auto calendar = request.value("calendar", std::string("solar"));
        const bool lunar = calendar == "lunar";
        if (!lunar && calendar != "solar") throw std::invalid_argument("calendar 必须是 solar 或 lunar");
        const auto& date = request.at("date");
        const int year = date.at("year"), month = date.at("month"), day = date.at("day"), hour = date.value("hour", 0);
        validate_date(year, month, day, hour, lunar);
        const auto code = request.value("hexagram_code", std::string("111111"));
        std::vector<int> changing;
        if (request.contains("changing_lines")) changing = request.at("changing_lines").get<std::vector<int>>();
        ZhouYi::BaZiBase::BaZi bazi = lunar
            ? ZhouYi::BaZiBase::BaZi::from_lunar(year, date.value("leap_month", false) ? -month : month, day, hour)
            : ZhouYi::BaZiBase::BaZi::from_solar(year, month, day, hour, date.value("minute", 0));
        auto result = ZhouYi::LiuYaoController::calculate_liu_yao(code, bazi, changing, true);
        // 纯增量挂载规则口径标识，不改变任何既有字段（大六壬 DLR-205 样板）。
        result.json_data["meta"]["rule_profile"] = rule_profile();
        std::cout << result.json_data.dump();
    } catch (const json::exception& error) {
        std::cout << error_response("INVALID_JSON", error.what()).dump(); return 1;
    } catch (const std::exception& error) {
        std::cout << error_response("INVALID_ARGUMENT", error.what()).dump(); return 1;
    }
}
