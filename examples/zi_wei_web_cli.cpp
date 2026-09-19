import std;
import ZhouYi.GanZhi;
import ZhouYi.ZhMapper;
import ZhouYi.tyme;
import ZhouYi.ZiWei;
import ZhouYi.ZiWei.Controller;
import ZhouYi.ZiWei.Horoscope;
import ZhouYi.ZiWei.Constants;
import ZhouYi.ZiWei.StarDocument;
import ZhouYi.Common.DateTime;
import ZhouYi.Common.Calendar;
import nlohmann.json;

using json = nlohmann::json;
using namespace ZhouYi::GanZhi;
using namespace ZhouYi::ZiWei;
using namespace ZhouYi::Mapper;

namespace {
    constexpr std::array<std::string_view, 6> ALL_LAYERS{
        "decade", "minor", "annual", "monthly", "daily", "hourly"
    };

    int effective_flow_month(const tyme::LunarDay& lunar_day) {
        const auto lunar_month = lunar_day.get_lunar_month();
        int month = lunar_month.get_month();
        if (lunar_month.is_leap() && lunar_day.get_day() > 15) {
            month = month % 12 + 1;
        }
        return month;
    }

    json correction_json(const SolarTimeCorrection& correction) {
        return {
            {"mode", correction.mode == BirthTimeMode::TrueSolarTime
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

    BirthDateTime parse_date_time(const json& value) {
        return BirthDateTime{
            .year = value.at("year").get<int>(),
            .month = value.at("month").get<int>(),
            .day = value.at("day").get<int>(),
            .hour = value.value("hour", 0),
            .minute = value.value("minute", 0),
            .second = value.value("second", 0)
        };
    }

    BirthTimeOptions parse_time_options(const json& request) {
        const auto options = request.value("time_correction", json::object());
        const auto mode = options.value("mode", std::string("standard_time"));
        if (mode != "standard_time" && mode != "true_solar_time") {
            throw std::invalid_argument(
                "time_correction.mode 必须是 standard_time 或 true_solar_time");
        }
        return BirthTimeOptions{
            .mode = mode == "true_solar_time"
                ? BirthTimeMode::TrueSolarTime : BirthTimeMode::StandardTime,
            .longitude = options.value("longitude", 120.0),
            .standard_meridian = options.value("standard_meridian", 120.0),
            .daylight_saving_minutes = options.value("daylight_saving_minutes", 0)
        };
    }

    bool parse_gender(const json& birth) {
        const auto gender = birth.at("gender").get<std::string>();
        if (gender == "male") return true;
        if (gender == "female") return false;
        throw std::invalid_argument("birth.gender 必须是 male 或 female");
    }

    std::set<std::string> parse_layers(const json& target) {
        std::set<std::string> layers;
        if (!target.contains("layers")) {
            for (const auto layer : ALL_LAYERS) layers.emplace(layer);
            return layers;
        }
        for (const auto& item : target.at("layers")) {
            const auto layer = item.get<std::string>();
            if (std::ranges::find(ALL_LAYERS, layer) == ALL_LAYERS.end()) {
                throw std::invalid_argument("target.layers 包含不支持的层级: " + layer);
            }
            layers.emplace(layer);
        }
        if (layers.empty()) {
            throw std::invalid_argument("target.layers 不能为空");
        }
        return layers;
    }

    json four_transformations(const std::array<std::string, 4>& values) {
        static constexpr std::array<std::string_view, 4> NAMES{"禄", "权", "科", "忌"};
        json result = json::array();
        for (std::size_t i = 0; i < values.size(); ++i) {
            result.push_back({{"type", NAMES[i]}, {"star", values[i]}});
        }
        return result;
    }

    std::string transit_star_base_name(std::string_view display_name) {
        if (display_name == "年解") return "年解";
        static constexpr std::array<std::pair<std::string_view, std::string_view>, 10> NAMES{{
            {"魁", "天魁"}, {"钺", "天钺"}, {"昌", "文昌"}, {"曲", "文曲"},
            {"禄", "禄存"}, {"羊", "擎羊"}, {"陀", "陀罗"}, {"马", "天马"},
            {"鸾", "红鸾"}, {"喜", "天喜"},
        }};
        for (const auto& [suffix, name] : NAMES) {
            if (display_name.ends_with(suffix)) return std::string(name);
        }
        return std::string(display_name);
    }

    json transit_stars(
        TianGan gan,
        DiZhi zhi,
        Scope scope,
        const ZiWeiResult& chart
    ) {
        json result = json::array();
        for (const auto& palace_stars : get_horoscope_stars(gan, zhi, scope)) {
            for (const auto& display_name : palace_stars.stars) {
                result.push_back({
                    {"name", transit_star_base_name(display_name)},
                    {"display_name", display_name},
                    {"palace_index", palace_stars.gong_index},
                    {"palace", std::string(to_zh(
                        chart.palaces[palace_stars.gong_index].gong_data.gong_wei))}
                });
            }
        }
        return result;
    }

    json flow_layer(
        TianGan gan,
        DiZhi zhi,
        int palace_index,
        const std::array<std::string, 4>& transformations,
        Scope scope,
        const ZiWeiResult& chart
    ) {
        return {
            {"gan_zhi", std::string(ZhouYi::GanZhi::Mapper::to_zh(gan))
                + std::string(ZhouYi::GanZhi::Mapper::to_zh(zhi))},
            {"palace_index", palace_index},
            {"palace", std::string(to_zh(chart.palaces[palace_index].gong_data.gong_wei))},
            {"si_hua", four_transformations(transformations)},
            {"transit_stars", transit_stars(gan, zhi, scope, chart)}
        };
    }

    /**
     * @brief 规则口径标识（参照大六壬 DLR-205 样板，纯新增 meta.rule_profile 字段）
     *
     * 每条描述以当前代码行为为准（括号内为内核位置），不引入未经代码证实的古籍归属。
     */
    json rule_profile() {
        return {
            {"profile_version", "ziwei-rules/2.0"},
            {"calibration_status", "calibrated"},
            {"rules", {
                {"true_solar_time",
                    "出生时间校正与八字共用 ZhouYi.Common.Calendar：标准时间=钟表时间−夏令时分钟数；"
                    "true_solar_time 模式下真太阳时=标准时间+(出生地经度−标准经线)×4分钟/度+均时差"
                    "（NOAA 年分数近似式，四舍五入到秒），并以校正后时间排盘、记录是否跨公历日；"
                    "standard_time 模式不作任何校正；longitude 与 standard_meridian 缺省均为东经120度"},
                {"ming_gong_shen_gong",
                    "命宫身宫用寅起生月生时法：寅宫起正月顺数至生月，逆数生时为命宫、顺数生时为身宫；"
                    "五行局以命宫干支按干支取数歌诀定（非纳音查表）：干甲乙1丙丁2戊己3庚辛4壬癸5、"
                    "支子午丑未1寅申卯酉2辰戌巳亥3，和满5减5对应木三金四水二火六土五局"},
                {"zi_wei_star_method",
                    "紫微星按农历日数加借数后除局数定宫：取最小借数使(农历日+借数)整除局数，商数自寅宫起数，"
                    "借数偶数进宫、奇数退宫；天府宫按寅申轴镜像（紫微在寅申与天府同宫）；"
                    "紫微系六星自紫微逆行安天机−1、太阳−3、武曲−4、天同−5、廉贞−8；"
                    "天府系八星自天府顺行安太阴+1、贪狼+2、巨门+3、天相+4、天梁+5、七杀+6、破军+10"},
                {"si_hua",
                    "四化取代码实测十干表（禄权科忌顺序，与紫微斗数全书三合派通行表一致）："
                    "甲廉贞破军武曲太阳、乙天机天梁紫微太阴、丙天同天机文昌廉贞、丁太阴天同天机巨门、"
                    "戊贪狼太阴右弼天机、己武曲贪狼天梁文曲、庚太阳武曲天同天相、辛巨门太阳文曲文昌、"
                    "壬天梁紫微左辅武曲、癸破军巨门太阴贪狼；丙干作同机昌廉（中州派为同昌机廉，权科次序不同）；"
                    "大限流年流月流日流时四化按各层之干查同一表"},
                {"brightness",
                    "亮度仅十四主星赋格：按星曜×宫位地支固定取表，七等庙旺得平陷不利；"
                    "辅星煞星杂曜神煞在本命输出中亮度为空（实现以代码为准）"},
                {"fortune_layers",
                    "大限以五行局数为起限虚岁（水二局自2岁），每限管十年虚岁，阳男阴女顺行、阴男阳女逆行（以年支奇偶判阴阳）；"
                    "大限宫干按五虎遁以本命年干起寅宫、取限所在宫之干，宫支取本位支（D11 正统口径，"
                    "判据案例：丁年命宫辰→首限甲辰、逆行次限癸卯三限壬寅；甲年命宫寅→丙寅、顺行次限丁卯三限戊辰）；"
                    "可选项 daxian_gan_method=original 复现旧巡运伪口径仅供对照，界面不暴露；"
                    "本命闰月默认十五分界：十五日以前作本月、以后作下月（民国《斗数宣微》口径，与流月闰月规则同源；"
                    "可选项 leap_month_method=next_month 取《全书》'一律作下月'原文口径；闰M≡12−M 旧映射已废除）；"
                    "小限按年支三合起宫（寅午戌起辰、申子辰起戌、巳酉丑起未、亥卯未起丑），男顺女逆一岁一宫；"
                    "流年太岁地支入宫；流月斗君法（太岁宫起逆数生月至宫，自该宫起子时顺数生时起斗君，斗君起正月顺数至目标月），流月干由年干五虎遁；"
                    "流月闰月换算：目标时刻为闰月且日数大于15时按下一月计（effective_flow_month，与本盘控制器流月规则同源）；"
                    "流日自流月宫起初一顺数至农历日、流时自流日宫起子时顺数至时支，日干支取实际六十甲子日、时干五鼠遁（由本接口推算）；"
                    "边界：闰月本命的人生轨迹反推案例验证为后续校准任务（D12 说明），当前默认口径已在接口与规则说明中标注"},
                {"ge_ju_note",
                    "接口 ge_ju 字段仅为内核 C++ GeJuAnalyzer 评分结果（ji_ge/xiong_ge/total_score）的兼容导出，不作权威判定；"
                    "权威格局判定由网页端声明式规则引擎执行（web/ziwei_pattern_engine.py 加载 config/ziwei/patterns/ 规则配置），本接口不含其结论"}
            }}
        };
    }

    // D11/D12 口径参数：默认均为正统口径（五虎遁重排 / 闰月十五分界），
    // 旧口径保留为对照选项，供复现历史盘面，前台界面不暴露。
    DaXianGanMethod parse_daxian_method(const json& request) {
        const auto name = request.value("daxian_gan_method", std::string("resort"));
        if (name == "resort") return DaXianGanMethod::Resort;
        if (name == "original") return DaXianGanMethod::Original;
        throw std::invalid_argument("daxian_gan_method 必须是 resort 或 original");
    }

    LeapMonthMethod parse_leap_method(const json& request) {
        const auto name = request.value("leap_month_method", std::string("fifteen"));
        if (name == "fifteen") return LeapMonthMethod::FifteenBoundary;
        if (name == "next_month") return LeapMonthMethod::NextMonth;
        throw std::invalid_argument("leap_month_method 必须是 fifteen 或 next_month");
    }

    json calculate_chart(const json& request) {
        const auto& birth_json = request.at("birth");
        const auto birth = parse_date_time(birth_json);
        const auto options = parse_time_options(request);
        const auto chart = pai_pan_solar(birth, parse_gender(birth_json), options,
            parse_daxian_method(request), parse_leap_method(request));
        return json::parse(export_to_json_full(chart));
    }

    json calculate_fortune(const json& request) {
        const auto& birth_json = request.at("birth");
        const auto& target_json = request.at("target");
        const auto birth = parse_date_time(birth_json);
        const auto target = parse_date_time(target_json);
        const bool is_male = parse_gender(birth_json);
        const auto options = parse_time_options(request);
        const auto layers = parse_layers(target_json);
        const int current_age = target_json.value("age", target.year - birth.year + 1);
        if (current_age < 1 || current_age > 150) {
            throw std::invalid_argument("target.age 必须在 1 到 150 之间");
        }

        const auto chart = pai_pan_solar(birth, is_male, options,
            parse_daxian_method(request), parse_leap_method(request));
        const auto target_time = ZhouYi::Common::Calendar::to_solar_time(target);
        const auto solar_day = target_time.get_solar_day();
        const auto lunar_day = solar_day.get_lunar_day();
        const auto cycle_day = solar_day.get_sixty_cycle_day();
        const auto year_cycle = cycle_day.get_year();
        const auto day_cycle = cycle_day.get_sixty_cycle();

        const auto year_gan = static_cast<TianGan>(year_cycle.get_heaven_stem().get_index());
        const auto year_zhi = static_cast<DiZhi>(year_cycle.get_earth_branch().get_index());
        const auto day_gan = static_cast<TianGan>(day_cycle.get_heaven_stem().get_index());
        const auto day_zhi = static_cast<DiZhi>(day_cycle.get_earth_branch().get_index());
        const auto hour_zhi = static_cast<DiZhi>(((target.hour + 1) / 2) % 12);
        const auto hour_gan = static_cast<TianGan>(
            (static_cast<int>(day_gan) % 5 * 2 + static_cast<int>(hour_zhi)) % 10);

        const int lunar_month = effective_flow_month(lunar_day);
        const int birth_lunar_month = chart.lunar_day.get_lunar_month().get_month();
        const auto liu_nian = get_liu_nian(
            target.year, year_gan, year_zhi, chart.ming_gong_index);
        const auto liu_yue = get_liu_yue(
            lunar_month, birth_lunar_month, chart.hour_pillar.zhi, year_gan, year_zhi);
        const auto liu_ri = get_liu_ri(
            lunar_day.get_day(), day_gan, day_zhi, liu_yue.gong_index);
        const auto liu_shi = get_liu_shi(hour_zhi, hour_gan, liu_ri.gong_index);
        const auto xiao_xian = get_xiao_xian(current_age, is_male, chart.year_pillar.zhi);

        const DaXianData* current_da_xian = nullptr;
        for (const auto& item : chart.da_xian_data) {
            if (current_age >= item.start_age && current_age <= item.end_age) {
                current_da_xian = &item;
                break;
            }
        }

        json fortune = json::object();
        if (layers.contains("minor")) {
            fortune["xiao_xian"] = {
                {"age", xiao_xian.age},
                {"palace_index", xiao_xian.gong_index},
                {"palace", std::string(to_zh(
                    chart.palaces[xiao_xian.gong_index].gong_data.gong_wei))}
            };
        }
        if (layers.contains("decade") && current_da_xian != nullptr) {
            fortune["da_xian"] = flow_layer(
                current_da_xian->tian_gan,
                current_da_xian->di_zhi,
                current_da_xian->gong_index,
                current_da_xian->si_hua,
                Scope::Decadal,
                chart
            );
            fortune["da_xian"]["age_range"] =
                std::to_string(current_da_xian->start_age) + "-"
                + std::to_string(current_da_xian->end_age);
        }
        if (layers.contains("annual")) {
            fortune["liu_nian"] = flow_layer(
                liu_nian.tian_gan, liu_nian.di_zhi, liu_nian.gong_index,
                liu_nian.si_hua, Scope::Yearly, chart);
        }
        if (layers.contains("monthly")) {
            fortune["liu_yue"] = flow_layer(
                liu_yue.tian_gan, liu_yue.di_zhi, liu_yue.gong_index,
                liu_yue.si_hua, Scope::Monthly, chart);
            fortune["liu_yue"]["dou_jun_index"] = liu_yue.dou_jun_index;
            fortune["liu_yue"]["dou_jun_palace"] = std::string(to_zh(
                chart.palaces[liu_yue.dou_jun_index].gong_data.gong_wei));
        }
        if (layers.contains("daily")) {
            fortune["liu_ri"] = flow_layer(
                liu_ri.tian_gan, liu_ri.di_zhi, liu_ri.gong_index,
                liu_ri.si_hua, Scope::Daily, chart);
        }
        if (layers.contains("hourly")) {
            fortune["liu_shi"] = flow_layer(
                liu_shi.tian_gan, liu_shi.di_zhi, liu_shi.gong_index,
                liu_shi.si_hua, Scope::Hourly, chart);
        }

        return {
            {"chart", json::parse(export_to_json_full(chart))},
            {"target", {
                {"solar_time", target_time.to_string()},
                {"lunar_date", lunar_day.to_string()},
                {"lunar_month", lunar_month},
                {"lunar_day", lunar_day.get_day()},
                {"age", current_age},
                {"requested_layers", layers}
            }},
            {"fortune", fortune}
        };
    }

    // ===== symbols: 权威符号字典（从内核模块导出） =====

    // 枚举中文名数组；跳过 COUNT 哨兵值（无中文映射时 to_zh 回退为枚举英文名）
    template <typename E>
    std::vector<std::string> enum_zh_names() {
        std::vector<std::string> result;
        for (const auto name : ZhouYi::Mapper::get_all_zh_names<E>()) {
            if (name == "COUNT") continue;
            result.emplace_back(name);
        }
        return result;
    }

    json string_array(const std::vector<std::string>& names) {
        json result = json::array();
        for (const auto& name : names) result.push_back(name);
        return result;
    }

    // 文档名 ∪ 枚举名并集（保序去重）：类别列表以文档模块为主，
    // 枚举中文名补齐文档库未收录但可上盘的星名（如 截路/空亡），
    // 保留内核侧权威符号全集的语义。
    std::vector<std::string> merge_names(std::vector<std::string> base,
                                         const std::vector<std::string>& extra) {
        const std::set<std::string> seen(base.begin(), base.end());
        for (const auto& name : extra) {
            if (!seen.contains(name)) base.push_back(name);
        }
        return base;
    }

    json calculate_symbols() {
        // 星曜类别列表 = 文档模块 vector<string> ∪ 枚举中文名
        const auto zhu_xing = merge_names(
            ZhouYi::ZiWei::StarDoc::get_all_zhu_xing_names(), enum_zh_names<ZhuXing>());
        const auto fu_xing = merge_names(
            ZhouYi::ZiWei::StarDoc::get_all_fu_xing_names(), enum_zh_names<FuXing>());
        const auto za_yao = merge_names(
            ZhouYi::ZiWei::StarDoc::get_all_za_yao_names(), enum_zh_names<ZaYao>());
        const auto shen_sha = ZhouYi::ZiWei::StarDoc::get_all_shen_sha_names();
        // 煞星无文档模块列表，取枚举中文名
        const auto sha_xing = enum_zh_names<ShaXing>();

        // 星性档案（人性化画像数据源）：主星/辅星/六煞的性质五行、阴阳、辅星分类
        // 一律取自内核星曜文档库（StarDocument.wu_xing/yin_yang/fu_xing_category），
        // 不在配置层手编映射，保证与安星诀同源。
        json star_temperament = json::array();
        const std::vector<std::pair<const std::vector<std::string>*, const char*>> temperament_sources = {
            {&zhu_xing, "zhu_xing"}, {&fu_xing, "fu_xing"}, {&sha_xing, "sha_xing"},
        };
        for (const auto& [names, group] : temperament_sources) {
            for (const auto& name : *names) {
                auto doc = ZhouYi::ZiWei::StarDoc::get_zhu_xing_document(name);
                if (!doc.has_value()) doc = ZhouYi::ZiWei::StarDoc::get_fu_xing_document(name);
                if (!doc.has_value()) continue;
                json entry {{"name", name}, {"group", group}};
                if (doc->wu_xing.has_value()) entry["element"] = string(to_zh(*doc->wu_xing));
                if (doc->yin_yang.has_value()) entry["polarity"] = string(to_zh(*doc->yin_yang));
                if (doc->fu_xing_category.has_value())
                    entry["category"] = string(to_zh(*doc->fu_xing_category));
                if (!doc->key_trait.empty()) entry["key_trait"] = doc->key_trait;
                star_temperament.push_back(std::move(entry));
            }
        }

        std::set<std::string> all_names;
        for (const auto& names : {zhu_xing, fu_xing, za_yao, shen_sha}) {
            all_names.insert(names.begin(), names.end());
        }
        all_names.insert(sha_xing.begin(), sha_xing.end());

        // 干支/五行中文名来自 ZhouYi.GanZhi 的 ZhMap
        std::vector<std::string> heavenly_stems;
        for (int i = 0; i < 10; ++i) {
            heavenly_stems.emplace_back(
                ZhouYi::GanZhi::Mapper::to_zh(static_cast<TianGan>(i)));
        }
        std::vector<std::string> earthly_branches;
        for (int i = 0; i < 12; ++i) {
            earthly_branches.emplace_back(
                ZhouYi::GanZhi::Mapper::to_zh(static_cast<DiZhi>(i)));
        }
        std::vector<std::string> five_elements;
        for (int i = 1; i <= 5; ++i) {
            five_elements.emplace_back(
                ZhouYi::GanZhi::Mapper::to_zh(static_cast<WuXing>(i)));
        }

        return {
            {"operation", "symbols"},
            {"symbols_version", "ziwei-symbols/1.1"},
            {"stars", {
                {"zhu_xing", string_array(zhu_xing)},
                {"fu_xing", string_array(fu_xing)},
                {"za_yao", string_array(za_yao)},
                {"shen_sha", string_array(shen_sha)},
                {"sha_xing", string_array(sha_xing)}
            }},
            {"all_star_names", string_array({all_names.begin(), all_names.end()})},
            {"star_temperament", std::move(star_temperament)},
            {"brightness", string_array(enum_zh_names<LiangDu>())},
            {"si_hua", string_array(enum_zh_names<SiHua>())},
            {"palaces", string_array(enum_zh_names<GongWei>())},
            {"heavenly_stems", string_array(heavenly_stems)},
            {"earthly_branches", string_array(earthly_branches)},
            {"five_elements", string_array(five_elements)}
        };
    }

    json execute(const json& request) {
        const auto operation = request.at("operation").get<std::string>();
        json out;
        if (operation == "time_correction") {
            out = correction_json(correct_birth_time(
                parse_date_time(request.at("birth")), parse_time_options(request)));
        } else if (operation == "chart") {
            out = calculate_chart(request);
        } else if (operation == "fortune") {
            out = calculate_fortune(request);
        } else if (operation == "symbols") {
            out = calculate_symbols();
        } else {
            throw std::invalid_argument("不支持的 operation: " + operation);
        }
        // 纯增量挂载规则口径标识，不改变任何既有字段（大六壬 DLR-205 样板）。
        out["meta"]["rule_profile"] = rule_profile();
        return out;
    }

    json legacy_request(int argc, char** argv) {
        if (argc != 18) throw std::invalid_argument("参数数量不正确");
        return {
            {"operation", "fortune"},
            {"birth", {
                {"year", std::stoi(argv[1])}, {"month", std::stoi(argv[2])},
                {"day", std::stoi(argv[3])}, {"hour", std::stoi(argv[4])},
                {"minute", std::stoi(argv[5])}, {"second", std::stoi(argv[6])},
                {"gender", std::stoi(argv[7]) != 0 ? "male" : "female"}
            }},
            {"time_correction", {
                {"mode", std::stoi(argv[8]) != 0 ? "true_solar_time" : "standard_time"},
                {"longitude", std::stod(argv[9])},
                {"standard_meridian", std::stod(argv[10])},
                {"daylight_saving_minutes", std::stoi(argv[11])}
            }},
            {"target", {
                {"year", std::stoi(argv[12])}, {"month", std::stoi(argv[13])},
                {"day", std::stoi(argv[14])}, {"hour", std::stoi(argv[15])},
                {"minute", std::stoi(argv[16])}, {"second", 0},
                {"age", std::stoi(argv[17])}
            }}
        };
    }
}

int main(int argc, char** argv) {
    try {
        json request;
        if (argc == 1) {
            std::cin >> request;
        } else {
            request = legacy_request(argc, argv);
        }
        std::cout << execute(request).dump();
        return 0;
    } catch (const json::exception& error) {
        std::cout << json{{"error", {
            {"code", "INVALID_JSON"}, {"message", error.what()}
        }}}.dump();
        return 2;
    } catch (const std::invalid_argument& error) {
        std::cout << json{{"error", {
            {"code", "INVALID_ARGUMENT"}, {"message", error.what()}
        }}}.dump();
        return 2;
    } catch (const std::exception& error) {
        std::cout << json{{"error", {
            {"code", "CALCULATION_FAILED"}, {"message", error.what()}
        }}}.dump();
        return 1;
    }
}
