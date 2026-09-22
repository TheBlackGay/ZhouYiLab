import std;
import ZhouYi.BaZiController;
import ZhouYi.BaZiBase;
import ZhouYi.BaZi.ShenSha;
import ZhouYi.GanZhi;
import ZhouYi.tyme;
import ZhouYi.Common.DateTime;
import ZhouYi.Common.Calendar;
import nlohmann.json;

using json = nlohmann::json;

namespace {

json error_response(std::string code, std::string message) {
    return {{"error", {{"code", std::move(code)}, {"message", std::move(message)}}}};
}

json correction_json(const ZhouYi::Common::Calendar::SolarTimeCorrection& correction) {
    using ZhouYi::Common::Calendar::SolarTimeMode;
    return {
        {"mode", correction.mode == SolarTimeMode::TrueSolarTime
            ? "true_solar_time" : "standard_time"},
        {"recorded_time", ZhouYi::Common::DateTime::format(correction.recorded_time)},
        {"standard_time", ZhouYi::Common::DateTime::format(correction.standard_time)},
        {"chart_time", ZhouYi::Common::DateTime::format(correction.chart_time)},
        {"longitude", correction.longitude},
        {"standard_meridian", correction.standard_meridian},
        {"daylight_saving_minutes", correction.daylight_saving_minutes},
        {"longitude_offset_seconds", correction.longitude_offset_seconds},
        {"equation_of_time_seconds", correction.equation_of_time_seconds},
        {"total_offset_seconds", correction.total_offset_seconds},
        {"crossed_date_boundary", correction.crossed_date_boundary}
    };
}

ZhouYi::Common::Calendar::SolarTimeOptions parse_time_options(const json& request) {
    using namespace ZhouYi::Common::Calendar;
    const auto options = request.value("time_correction", json::object());
    const auto mode = options.value("mode", std::string("standard_time"));
    if (mode != "standard_time" && mode != "true_solar_time") {
        throw std::invalid_argument("time_correction.mode 必须是 standard_time 或 true_solar_time");
    }
    return SolarTimeOptions{
        .mode = mode == "true_solar_time" ? SolarTimeMode::TrueSolarTime : SolarTimeMode::StandardTime,
        .longitude = options.value("longitude", 120.0),
        .standard_meridian = options.value("standard_meridian", 120.0),
        .daylight_saving_minutes = options.value("daylight_saving_minutes", 0)
    };
}

void validate_date_time(int year, int month, int day, int hour, int minute, bool lunar) {
    if (year < 1 || year > 9999) throw std::invalid_argument("年份必须在 1 到 9999 之间");
    if (month < 1 || month > 12) throw std::invalid_argument("月份必须在 1 到 12 之间");
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
 * 每条描述以 src/ba_zi、src/common 当前代码行为为准，不引入未经代码证实的古籍归属。
 */
json rule_profile() {
    return {
        {"profile_version", "bazi-rules/0.1"},
        {"calibration_status", "in_progress"},
        {"rules", {
            {"four_pillars",
                "四柱由统一历法引擎 tyme 生成：年柱以立春为界、月柱以节（立春惊蛰等十二节）为界、"
                "日柱按公历日、时柱按时辰；晚子时（23至24点）日柱算次日（tyme 默认八字算法，"
                "时柱随之按次日日干起五鼠遁）；农历输入先换公历再排"},
            {"true_solar_time",
                "真太阳时与紫微共用 ZhouYi.Common.Calendar：先减夏令时分钟得标准时间，"
                "再加（经度−标准经线）×4分钟/度与均时差（NOAA 年分数近似式，取整到秒）得排盘时间；"
                "四柱以校正后排盘时间计算，输出附校正明细与是否跨公历日；standard_time 模式不校正；"
                "经度与标准经线缺省均为东经120度"},
            {"shi_shen",
                "十神以日干为我，按五行生克与阴阳同异推定：同我比肩劫财、我生食神伤官、我克偏财正财、"
                "克我七杀正官、生我偏印正印（同性为偏、异性为正）；日柱天干十神按同干比和输出为比肩"},
            {"cang_gan",
                "地支藏干取代码固定表（本气中气余气顺序）：子癸、丑己癸辛、寅甲丙戊、卯乙、辰戊乙癸、"
                "巳丙戊庚、午丁己、未己丁乙、申庚壬戊、酉辛、戌戊辛丁、亥壬甲；藏干十神按日干推"},
            {"twelve_stages",
                "十二长生阳干顺行、阴干逆行：长生起位甲亥、乙午、丙寅、丁酉、戊寅、己酉（土同火）、"
                "庚巳、辛子、壬申、癸卯；阶段为长生沐浴冠带临官帝旺衰病死墓绝胎养；"
                "star_fortune 以日干查本支，self_sitting 以本柱干查本柱支"},
            {"xun_kong_per_pillar",
                "逐柱旬空：各柱以自身干支定旬首，取该旬所缺二地支（甲子旬戌亥空等）；"
                "顶层 xun_kong 字段为日柱旬空二支"},
            {"na_yin",
                "六十甲子纳音取固定表：甲子乙丑海中金至壬戌癸亥大海水共三十名，"
                "每柱输出纳音名（如海中金）与纳音五行"},
            {"shen_sha_basis",
                "神煞为项目首批按《渊海子平》《三命通会》口径复核的规则集（输出 source 字段即此声明）："
                "天乙贵人、禄神、金舆、三奇、学堂词馆、驿马、太极、天月德、德秀、天罗地网、"
                "孤辰寡宿隔角、劫煞亡神、空亡、元辰、羊刃飞刃、十恶大败、阴差阳错等逐柱分布；"
                "童子煞取月支法与纳音法双轨、命中计 match_count，输出明确标注为后世民间兼容规则、非两部原书完整口诀"},
            {"luck_pillars",
                "起运：阳男阴女顺数至下一节、阴男阳女逆数至上一节（tyme 童限算法），"
                "距离按 3日折1年、1日折4月、1小时折5日、1分钟折2小时、1秒折2分钟折算交运时刻；"
                "大运以年干阴阳与性别定顺逆（阳男阴女顺排、阴男阳女逆排），自月柱干支顺/逆推十步、每步十年；"
                "start_detail 输出折算年月日时与出生、交运时刻"},
            {"boundary_note",
                "边界：旺衰评分、喜忌用神与格局判定在本版本未实现且未校准（shen_sha_summary.relations 中 "
                "wangshuai_info 与干支合化 hua_success 等字段为空占位），本接口只输出排盘事实，不输出断语；"
                "八字整体处于校准中状态"}
        }}
    };
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

        const auto recorded = lunar
            ? ZhouYi::Common::Calendar::lunar_to_solar(
                ZhouYi::Common::LunarDateTime{
                    year, date.value("leap_month", false) ? -month : month,
                    day, hour, minute, 0})
            : ZhouYi::Common::SolarDateTime{year, month, day, hour, minute, 0};
        const auto recorded_solar = ZhouYi::Common::Calendar::to_solar_time(recorded);
        const auto correction = ZhouYi::Common::Calendar::correct_solar_time(
            recorded, parse_time_options(request));
        const auto& chart = correction.chart_time;
        auto result = ZhouYi::BaZiController::pai_pan_solar(
            chart.year, chart.month, chart.day, chart.hour, chart.minute, gender == "male");

        auto output = result.to_json();
        output["calendar"] = calendar;
        output["gender"] = gender;
        output["birth_date"] = {
            {"year", recorded.year}, {"month", recorded.month}, {"day", recorded.day},
            {"hour", recorded.hour}, {"minute", recorded.minute},
            {"display", ZhouYi::Common::DateTime::format(recorded)}
        };
        output["birth_time"] = correction_json(correction);
        output["solar_date"] = recorded_solar.to_string();
        output["lunar_date"] = recorded_solar.get_lunar_hour().to_string();
        output["chart_lunar_date"] = ZhouYi::Common::Calendar::to_solar_time(chart)
            .get_lunar_hour().to_string();

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
            output["pillars"][pillar_keys[i]]["shen_sha_details"] = json::array();
        }
        for (const auto& occurrence : shen_sha.lu_shen) {
            output["pillars"][pillar_keys[occurrence.pillar_index]]["shen_sha_details"].push_back({
                {"id", "lu_shen"},
                {"name", "禄神"},
                {"position", occurrence.position},
                {"ganzhi", occurrence.ganzhi},
                {"variant", occurrence.variant},
                {"nature", occurrence.nature}
            });
        }
        for (const auto& occurrence : shen_sha.jin_yu) {
            output["pillars"][pillar_keys[occurrence.pillar_index]]["shen_sha_details"].push_back({
                {"id", "jin_yu"},
                {"name", "金舆"},
                {"position", occurrence.position},
                {"priority", occurrence.pillar_index >= 2 ? "优先" : "次之"}
            });
        }
        // Every calculated name gets a stable resource id so the web layer can
        // open the matching knowledge-base entry, even when it has no bespoke
        // occurrence payload yet.
        const std::unordered_map<std::string, std::string> shen_sha_resource_ids{
            {"暗金的煞", "an_jin_de_sha"}, {"德秀贵人", "de_xiu_gui_ren"},
            {"勾绞煞", "gou_jiao_sha"}, {"空亡", "kong_wang"}, {"六厄", "liu_e"},
            {"灾煞", "zai_sha"}, {"太极贵人", "tai_ji_gui"}, {"天德贵人", "tian_yue_de"},
            {"月德合", "tian_yue_de"}, {"羊刃", "yang_ren"}, {"元辰", "yuan_chen"},
            {"孤辰", "gu_chen_gua_su"}, {"寡宿", "gu_chen_gua_su"}, {"隔角煞", "gu_chen_gua_su"},
            {"十恶大败", "shi_e_da_bai"}, {"劫煞", "jie_sha_wang_shen"},
            {"亡神", "jie_sha_wang_shen"}, {"驿马", "yi_ma"}, {"正印", "zheng_yin"},
            {"天乙贵人", "tian_yi_gui_ren"}, {"三奇贵人", "san_qi_gui_ren"},
            {"学堂词馆", "xue_tang_ci_guan"}, {"战斗伏降刑冲破合", "zhan_dou_fu_jiang_xing_chong_po_he"},
            {"国印贵人", "qi_ta_shen_sha_1"}, {"福星贵人", "qi_ta_shen_sha_1"},
            {"飞刃", "qi_ta_shen_sha_3"}, {"丧门", "qi_ta_shen_sha_2"}, {"将星", "qi_ta_shen_sha_1"},
            {"红艳煞", "qi_ta_shen_sha_3"}, {"文昌贵人", "tai_ji_gui"},
            {"天厨贵人", "qi_ta_shen_sha_1"}, {"流霞", "qi_ta_shen_sha_3"},
            {"天罗", "tian_luo_di_wang"}, {"地网", "tian_luo_di_wang"},
            {"劫煞十六般", "jie_sha_shi_liu_ban"}, {"亡神十六般", "wang_shen_shi_liu_ban"},
            {"华盖", "yin_shen_si_hai_si_gong_hu_huan_shen_sha"}, {"阴差阳错煞", "qi_ta_shen_sha_4"},
            {"淫欲妨害煞", "qi_ta_shen_sha_4"}, {"桃花煞", "qi_ta_shen_sha_3"},
            {"官符煞", "qi_ta_shen_sha_2"}, {"病符煞", "qi_ta_shen_sha_2"},
            {"死符煞", "qi_ta_shen_sha_2"}, {"吊客", "qi_ta_shen_sha_2"},
            {"丧吊煞", "qi_ta_shen_sha_2"}, {"宅墓煞", "qi_ta_shen_sha_2"}, {"桃花红艳煞", "qi_ta_shen_sha_3"},
            {"阴阳煞", "qi_ta_shen_sha_4"}, {"孤鸾寡鹄煞", "qi_ta_shen_sha_4"},
            {"天火煞", "qi_ta_shen_sha_1"}, {"自缢煞", "qi_ta_shen_sha_1"},
            {"水溺煞", "qi_ta_shen_sha_1"}, {"挂剑煞", "qi_ta_shen_sha_1"},
            {"天屠煞", "qi_ta_shen_sha_1"}, {"天刑煞", "qi_ta_shen_sha_1"}, {"雷霆煞", "qi_ta_shen_sha_1"}, {"吞陷煞", "qi_ta_shen_sha_1"},
            {"破煞", "qi_ta_shen_sha_3"}
            , {"学堂", "xue_tang_ci_guan"}, {"词馆", "xue_tang_ci_guan"}, {"桃花", "qi_ta_shen_sha_3"},
            {"咸池", "qi_ta_shen_sha_3"}, {"月德贵人", "tian_yue_de"}, {"德秀", "de_xiu_gui_ren"},
            {"平头煞", "gan_zhi_zi_za_fan"}, {"破字煞", "gan_zhi_zi_za_fan"}, {"悬针煞", "gan_zhi_zi_za_fan"},
            {"杖刑煞", "gan_zhi_zi_za_fan"}, {"曲脚煞", "gan_zhi_zi_za_fan"}
            , {"贵人", "tian_yi_gui_ren"}, {"禄马", "zong_lun_lu_ma"},
            {"四库", "chen_xu_chou_wei_si_gong_hu_huan_shen_sha"}, {"四墓", "chen_xu_chou_wei_si_gong_hu_huan_shen_sha"},
            {"龙蛇混杂", "tian_luo_di_wang"}, {"猪犬侵凌", "tian_luo_di_wang"},
            {"剑锋煞", "qi_ta_shen_sha_3"}, {"戟锋煞", "qi_ta_shen_sha_3"},
            {"短寿煞", "qi_ta_shen_sha_4"}, {"禄神", "lu_shen"}, {"童子煞", "qi_ta_shen_sha_2"},
            {"返本煞", "qi_ta_shen_sha_4"}, {"进神", "zi_wu_mao_you_si_gong_hu_huan_shen_sha"},
            {"金舆", "jin_yu"}, {"长生", "yin_shen_si_hai_si_gong_hu_huan_shen_sha"},
            {"悬针", "gan_zhi_zi_za_fan"}, {"日刑煞", "qi_ta_shen_sha_3"},
            {"流血煞", "qi_ta_shen_sha_3"}, {"浮沉煞", "qi_ta_shen_sha_3"},
            {"白虎", "qi_ta_shen_sha_1"}, {"阴错阳差", "qi_ta_shen_sha_3"}
            , {"亡神十六般格局", "wang_shen_shi_liu_ban"}, {"劫煞十六般格局", "jie_sha_shi_liu_ban"},
            {"勾绞", "gou_jiao_sha"}, {"大耗", "yuan_chen"}, {"天月德", "tian_yue_de"},
            {"天罗地网", "tian_luo_di_wang"}, {"太极贵", "tai_ji_gui"}, {"无禄日", "shi_e_da_bai"},
            {"爪牙煞", "gou_jiao_sha"}, {"吟呻", "an_jin_de_sha"}, {"破碎", "an_jin_de_sha"}, {"白衣", "an_jin_de_sha"}
            , {"隔角", "gu_chen_gua_su"}, {"天禄天马", "zong_lun_lu_ma"}, {"禄马交驰", "zong_lun_lu_ma"},
            {"禄马同乡", "zong_lun_lu_ma"}, {"生旺禄", "zong_lun_lu_ma"}, {"名位禄", "zong_lun_lu_ma"},
            {"天禄贵神", "zong_lun_lu_ma"}, {"夹禄夹马", "zong_lun_lu_ma"}, {"真禄", "zong_lun_lu_ma"},
            {"进退真禄", "zong_lun_lu_ma"}, {"食神合禄", "zong_lun_lu_ma"}
        };
        for (std::size_t i = 0; i < pillar_keys.size(); ++i) {
            for (const auto& name : shen_sha.pillars[i].names) {
                const auto found = shen_sha_resource_ids.find(name);
                if (found == shen_sha_resource_ids.end()) continue;
                auto& details = output["pillars"][pillar_keys[i]]["shen_sha_details"];
                const bool already_present = std::ranges::any_of(details, [&](const json& item) {
                    return item.value("name", "") == name;
                });
                if (!already_present) details.push_back({
                    {"id", found->second}, {"name", name}, {"position", pillar_keys[i]}
                });
            }
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
            {"relations", {
                {"branch_relations", json::array()}, {"stem_relations", json::array()},
                {"interchanges", json::array()}, {"sanhe_ju", json::array()},
                {"wangshuai_info", nullptr}
            }},
            {"xue_guan", [&] {
                json value = { {"occurrences", json::array()} };
                for (const auto& item : shen_sha.xue_guan) value["occurrences"].push_back({
                    {"pillar", pillar_keys[item.pillar_index]}, {"id", item.id}, {"is_zheng", item.is_zheng}
                });
                return value;
            }()},
            {"yi_ma", [&] {
                json value = { {"matched", !shen_sha.yi_ma.empty()}, {"occurrences", json::array()} };
                for (const auto& item : shen_sha.yi_ma) value["occurrences"].push_back({
                    {"pillar", pillar_keys[item.pillar_index]}, {"source", item.source}
                });
                return value;
            }()},
            {"tian_yi_gui_ren", [&] {
                json value = { {"matched", !shen_sha.tian_yi.empty()}, {"occurrences", json::array()} };
                for (const auto& item : shen_sha.tian_yi) value["occurrences"].push_back({
                    {"pillar", pillar_keys[item.pillar_index]}, {"method", item.method}
                });
                return value;
            }()},
            {"san_qi", [&] {
                json value = { {"matched", !shen_sha.san_qi.empty()}, {"occurrences", json::array()} };
                for (const auto& item : shen_sha.san_qi) value["occurrences"].push_back({
                    {"type", item.type}, {"positions", item.positions}
                });
                return value;
            }()},
            {"tian_yue_de", {
                {"tiande", shen_sha.tian_yue_de.tiande},
                {"yuede", shen_sha.tian_yue_de.yuede},
                {"tiandehe", shen_sha.tian_yue_de.tiandehe},
                {"yuedehe", shen_sha.tian_yue_de.yuedehe}
            }},
            {"de_xiu", {
                {"matched", shen_sha.de_xiu.matched},
                {"de_stems", stems_to_json(shen_sha.de_xiu.de_stems)},
                {"xiu_stems", stems_to_json(shen_sha.de_xiu.xiu_stems)},
                {"sub_tags", shen_sha.de_xiu.sub_tags}
            }},
            {"tai_ji", [&] {
                json value = { {"matched", !shen_sha.tai_ji.empty()}, {"occurrences", json::array()} };
                for (const auto& item : shen_sha.tai_ji) value["occurrences"].push_back({
                    {"pillar", pillar_keys[item.pillar_index]}, {"sources", item.sources}
                });
                return value;
            }()},
            {"source_occurrences", [&] {
                json value = json::array();
                for (const auto& item : shen_sha.source_occurrences) value.push_back({
                    {"pillar", pillar_keys[item.pillar_index]}, {"name", item.name}, {"source", item.sources}, {"sub_tags", item.sub_tags}
                });
                return value;
            }()},
            {"lu_ma_patterns", [&] {
                json value = json::array();
                for (const auto& item : shen_sha.lu_ma_patterns) value.push_back({
                    {"pattern_key", item.pattern_key}, {"involved_pillars", item.involved_pillars},
                    {"trigger_basis", item.trigger_basis}, {"hit", item.hit}
                });
                return value;
            }()},
            {"group1_occurrences", json::array()},
            {"group2_occurrences", json::array()},
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
                {"gender_note", shen_sha.luo_wang.gender_note},
                {"sub_tags", shen_sha.luo_wang.sub_tags}
            }},
            {"auxiliary", {
                {"guchen", shen_sha.auxiliary.guchen},
                {"guaxiu", shen_sha.auxiliary.guaxiu},
                {"gejiao", shen_sha.auxiliary.gejiao},
                {"goushen", shen_sha.auxiliary.goushen},
                {"jiaoshen", shen_sha.auxiliary.jiaoshen},
                {"yangren", shen_sha.auxiliary.yangren},
                {"feiren", shen_sha.auxiliary.feiren},
                {"kongwang", shen_sha.auxiliary.kongwang},
                {"yuanchen", shen_sha.auxiliary.yuanchen},
                {"yuanchen_alias", shen_sha.auxiliary.yuanchen_alias},
                {"sub_tags", shen_sha.auxiliary.sub_tags},
                {"an_jin_sources", shen_sha.auxiliary.an_jin_sources},
                {"an_jin_sub_tags", shen_sha.auxiliary.an_jin_sub_tags}
            }},
            {"lu_shen", {
                {"matched", !shen_sha.lu_shen.empty()},
                {"basis", "日干定禄，遍查年、月、日、时四支"},
                {"day_stem", bazi.day.stem()},
                {"occurrence_count", shen_sha.lu_shen.size()}
            }},
            {"jin_yu", {
                {"matched", !shen_sha.jin_yu.empty()},
                {"basis", "日干取禄，禄神地支顺推二辰"},
                {"day_stem", bazi.day.stem()},
                {"occurrence_count", shen_sha.jin_yu.size()}
            }}
        };
        for (const auto& item : shen_sha.branch_relations) output["shen_sha_summary"]["relations"]["branch_relations"].push_back({
            {"type", item.type}, {"pillars", item.pillars}, {"branches", item.symbols}, {"detail", item.detail}
        });
        for (const auto& item : shen_sha.stem_relations) output["shen_sha_summary"]["relations"]["stem_relations"].push_back({
            {"type", "wuhe"}, {"pillars", item.pillars}, {"stems", item.stems}, {"combine_element", item.combine_element}, {"hua_success", nullptr}
        });
        for (const auto& item : shen_sha.sanhe_ju) output["shen_sha_summary"]["relations"]["sanhe_ju"].push_back({
            {"pillars", item.pillars}, {"branches", item.symbols}, {"element", item.detail}
        });
        for (const auto& item : shen_sha.interchanges) output["shen_sha_summary"]["relations"]["interchanges"].push_back({
            {"type", item.type}, {"pillars", item.pillars}, {"detail", item.detail}
        });
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

        // 纯增量挂载规则口径标识，不改变任何既有字段（大六壬 DLR-205 样板）。
        output["meta"]["rule_profile"] = rule_profile();

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
