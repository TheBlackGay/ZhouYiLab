export module ZhouYi.BaZi.ShenSha;

import std;
import ZhouYi.GanZhi;

export namespace ZhouYi::BaZi::ShenSha {

using GanZhi::DiZhi;
using GanZhi::TianGan;
using GanZhi::WuXing;

struct PillarResult {
    std::vector<std::string> names;
};

struct DeXiuDetail {
    bool matched = false;
    std::vector<TianGan> de_stems;
    std::vector<TianGan> xiu_stems;
    std::vector<std::string> sub_tags;
};
struct TaiJiOccurrence { std::size_t pillar_index = 0; std::vector<std::string> sources; };
struct SourceOccurrence { std::size_t pillar_index = 0; std::string name; std::vector<std::string> sources; std::vector<std::string> sub_tags; };
struct LuMaPattern { std::string pattern_key; std::vector<std::size_t> involved_pillars; std::string trigger_basis; bool hit = true; };

struct TongZiDetail {
    bool matched = false;
    bool month_rule = false;
    bool na_yin_rule = false;
    int match_count = 0;
};

struct LuoWangDetail {
    bool tian_luo = false;
    bool di_wang = false;
    std::string gender_note;
    std::vector<std::string> sub_tags;
};

struct LuShenOccurrence {
    std::size_t pillar_index = 0;
    std::string position;
    std::string ganzhi;
    std::string variant;
    std::string nature;
};

struct JinYuOccurrence {
    std::size_t pillar_index = 0;
    std::string position;
};

struct YiMaOccurrence {
    std::size_t pillar_index = 0;
    std::string source;
};

struct TianYiOccurrence {
    std::size_t pillar_index = 0;
    std::string method;
};

struct SanQiOccurrence {
    std::string type;
    std::string positions;
};
struct XueGuanOccurrence { std::size_t pillar_index = 0; std::string id; bool is_zheng = false; };

struct TianYueDeResult {
    bool tiande = false;
    bool yuede = false;
    bool tiandehe = false;
    bool yuedehe = false;
};

struct AuxiliaryDetail {
    bool guchen = false;
    bool guaxiu = false;
    bool gejiao = false;
    bool goushen = false;
    bool jiaoshen = false;
    bool yangren = false;
    bool feiren = false;
    bool yuanchen = false;
    std::vector<std::string> yuanchen_alias;
    bool kongwang = false;
    std::vector<std::string> sub_tags;
    std::vector<std::string> an_jin_sources;
    std::vector<std::string> an_jin_sub_tags;
};

struct RelationRecord {
    std::string type;
    std::vector<std::size_t> pillars;
    std::vector<std::string> symbols;
    std::string detail;
};

struct StemCombineRecord {
    std::vector<std::size_t> pillars;
    std::vector<std::string> stems;
    std::string combine_element;
};

struct WangShuaiTable {
    std::array<std::array<int, 5>, 12> ranks{};
};

struct Result {
    std::array<PillarResult, 4> pillars;
    DeXiuDetail de_xiu;
    std::vector<TaiJiOccurrence> tai_ji;
    std::vector<SourceOccurrence> source_occurrences;
    std::vector<LuMaPattern> lu_ma_patterns;
    TongZiDetail tong_zi;
    LuoWangDetail luo_wang;
    std::vector<LuShenOccurrence> lu_shen;
    std::vector<JinYuOccurrence> jin_yu;
    std::vector<YiMaOccurrence> yi_ma;
    std::vector<TianYiOccurrence> tian_yi;
    std::vector<SanQiOccurrence> san_qi;
    TianYueDeResult tian_yue_de;
    AuxiliaryDetail auxiliary;
    std::vector<RelationRecord> branch_relations;
    std::vector<StemCombineRecord> stem_relations;
    std::vector<RelationRecord> interchanges;
    std::vector<RelationRecord> sanhe_ju;
    std::vector<XueGuanOccurrence> xue_guan;
};

namespace detail {

constexpr bool in(DiZhi value, std::initializer_list<DiZhi> values) {
    return std::ranges::find(values, value) != values.end();
}

constexpr bool in(TianGan value, std::initializer_list<TianGan> values) {
    return std::ranges::find(values, value) != values.end();
}

void add_unique(std::vector<std::string>& target, std::string_view name) {
    if (std::ranges::find(target, name) == target.end()) target.emplace_back(name);
}

constexpr bool stem_matches_branch(TianGan stem, DiZhi branch,
                                   const std::array<DiZhi, 10>& table) {
    return table[static_cast<std::size_t>(stem)] == branch;
}

struct LuVariant {
    std::string_view name;
    std::string_view nature;
};

constexpr LuVariant lu_variant(TianGan day_stem, TianGan pillar_stem) {
    using enum TianGan;
    switch (day_stem) {
        case Jia:
            switch (pillar_stem) {
                case Bing: return {"福星禄", "吉"}; case Wu: return {"伏马禄", "吉"};
                case Geng: return {"破禄", "半吉半凶"}; case Ren: return {"正禄", "不吉"};
                case Jia: return {"长生禄", "吉"}; default: break;
            }
            break;
        case Yi:
            switch (pillar_stem) {
                case Yi: return {"喜神旺", "禄吉"}; case Ding: return {"截路空亡", "凶"};
                case Ji: return {"进神禄", "吉"}; case Xin: return {"破禄", "半吉半凶"};
                case Gui: return {"死禄", "凶"}; default: break;
            }
            break;
        case Bing:
            switch (pillar_stem) {
                case Ji: return {"九天库禄", "吉"}; case Xin: return {"截路空亡", "凶"};
                case Gui: return {"伏贵神禄", "半吉"}; case Yi: return {"旺马禄", "吉"};
                case Ding: return {"库禄", "吉"}; default: break;
            }
            break;
        case Ding:
            switch (pillar_stem) {
                case Geng: return {"截路空亡", "凶"}; case Ren: return {"德合禄", "吉"};
                case Jia: return {"进神禄", "吉"}; case Bing: return {"喜神禄", "半吉"};
                case Wu: return {"伏羊刃禄", "凶"}; default: break;
            }
            break;
        case Wu:
            switch (pillar_stem) {
                case Ji: return {"九天库禄", "吉"}; case Xin: return {"截路空亡", "凶"};
                case Gui: return {"贵神禄", "吉"}; case Yi: return {"驿马同乡禄", "吉"};
                case Ding: return {"旺库禄", "吉"}; default: break;
            }
            break;
        case Ji:
            switch (pillar_stem) {
                case Geng: return {"截路空亡", "凶"}; case Ren: return {"死鬼禄", "吉"};
                case Jia: return {"进神合禄", "吉"}; case Bing: return {"喜神禄", "半吉"};
                case Wu: return {"伏羊刃禄", "凶"}; default: break;
            }
            break;
        case Geng:
            switch (pillar_stem) {
                case Ren: return {"大败禄", "凶"}; case Jia: return {"截路空亡", "凶"};
                case Bing: return {"大败禄", "半吉"}; case Wu: return {"伏马禄", "吉"};
                case Geng: return {"长生禄", "吉"}; default: break;
            }
            break;
        case Xin:
            switch (pillar_stem) {
                case Gui: return {"伏神禄", "凶"}; case Yi: return {"破禄", "凶"};
                case Ding: return {"空亡贵神禄", "凶"}; case Ji: return {"进神禄", "吉"};
                case Xin: return {"正禄", "吉"}; default: break;
            }
            break;
        case Ren:
            switch (pillar_stem) {
                case Ding: return {"贵神合禄", "吉"}; case Yi: return {"天德禄", "吉"};
                case Ji: return {"旺禄", "吉"}; case Xin: return {"同马乡禄", "吉"};
                case Gui: return {"大败禄", "凶"}; default: break;
            }
            break;
        case Gui:
            switch (pillar_stem) {
                case Jia: return {"进神禄", "吉"}; case Bing: return {"羊刃禄", "吉"};
                case Wu: return {"伏羊刃合贵", "半吉"}; case Geng: return {"卯禄", "吉"};
                case Ren: return {"正羊刃禄", "凶"}; default: break;
            }
            break;
    }
    return {"", ""};
}

constexpr bool tai_ji(TianGan stem, DiZhi branch) {
    using enum DiZhi;
    switch (stem) {
        case TianGan::Jia: case TianGan::Yi: return in(branch, {Zi, Wu});
        case TianGan::Bing: case TianGan::Ding: return in(branch, {Mao, You});
        case TianGan::Wu: case TianGan::Ji: return in(branch, {Chen, Xu, Chou, Wei});
        case TianGan::Geng: case TianGan::Xin: return in(branch, {Yin, Hai});
        case TianGan::Ren: case TianGan::Gui: return in(branch, {Si, Shen});
    }
    return false;
}

constexpr bool fu_xing(TianGan stem, DiZhi branch) {
    using enum DiZhi;
    switch (stem) {
        case TianGan::Jia: case TianGan::Bing: return in(branch, {Yin, Zi});
        case TianGan::Yi: case TianGan::Gui: return in(branch, {Chou, Mao});
        case TianGan::Ding: return branch == Hai;
        case TianGan::Wu: return branch == Shen;
        case TianGan::Ji: return branch == Wei;
        case TianGan::Geng: return branch == Wu;
        case TianGan::Xin: return branch == Si;
        case TianGan::Ren: return branch == Chen;
    }
    return false;
}

constexpr DiZhi jiang_xing(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Yin, Wu, Xu})) return Wu;
    if (in(origin, {Shen, Zi, Chen})) return Zi;
    if (in(origin, {Si, You, Chou})) return You;
    return Mao;
}

constexpr DiZhi zai_sha(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Yin, Wu, Xu})) return Zi;
    if (in(origin, {Shen, Zi, Chen})) return Wu;
    if (in(origin, {Si, You, Chou})) return Mao;
    return You;
}

constexpr DiZhi san_he_target(DiZhi origin, DiZhi yin_wu_xu, DiZhi shen_zi_chen,
                              DiZhi si_you_chou, DiZhi hai_mao_wei) {
    using enum DiZhi;
    if (in(origin, {Yin, Wu, Xu})) return yin_wu_xu;
    if (in(origin, {Shen, Zi, Chen})) return shen_zi_chen;
    if (in(origin, {Si, You, Chou})) return si_you_chou;
    return hai_mao_wei;
}

constexpr DiZhi jie_sha(DiZhi origin) {
    using enum DiZhi;
    return san_he_target(origin, Hai, Si, Yin, Shen);
}

constexpr DiZhi wang_shen(DiZhi origin) {
    using enum DiZhi;
    return san_he_target(origin, Si, Hai, Shen, Yin);
}

constexpr DiZhi liu_e(DiZhi origin) {
    using enum DiZhi;
    return san_he_target(origin, You, Mao, Zi, Wu);
}

constexpr DiZhi yi_ma(DiZhi origin) {
    using enum DiZhi;
    return san_he_target(origin, Shen, Yin, Hai, Si);
}

constexpr bool san_qi_match(TianGan a, TianGan b, TianGan c, std::string_view& type) {
    using enum TianGan;
    if (a == Jia && b == Wu && c == Geng) { type = "天上三奇"; return true; }
    if (a == Yi && b == Bing && c == Ding) { type = "地下三奇"; return true; }
    if (a == Ren && b == Gui && c == Xin) { type = "人中三奇"; return true; }
    return false;
}

constexpr bool pair(DiZhi a, DiZhi b, DiZhi x, DiZhi y) { return (a == x && b == y) || (a == y && b == x); }
constexpr bool pair(TianGan a, TianGan b, TianGan x, TianGan y) { return (a == x && b == y) || (a == y && b == x); }
constexpr std::string_view wx_name(WuXing value) {
    switch (value) { case WuXing::Mu: return "木"; case WuXing::Huo: return "火"; case WuXing::Tu: return "土"; case WuXing::Jin: return "金"; case WuXing::Shui: return "水"; }
    return "";
}
constexpr std::string_view branch_name(DiZhi value) { return GanZhi::Mapper::to_zh(value); }

constexpr WangShuaiTable build_wang_shuai_table() {
    WangShuaiTable table;
    // columns: 木、火、土、金、水; ranks: 旺4、相3、休2、囚1、死0
    constexpr std::array<std::array<int, 5>, 5> groups{{
        {{4, 3, 0, 1, 2}}, {{2, 4, 3, 0, 1}}, {{0, 1, 2, 4, 3}},
        {{3, 0, 1, 2, 4}}, {{1, 2, 4, 3, 0}}
    }};
    for (const auto branch : {DiZhi::Yin, DiZhi::Mao}) table.ranks[static_cast<int>(branch)] = groups[0];
    for (const auto branch : {DiZhi::Si, DiZhi::Wu}) table.ranks[static_cast<int>(branch)] = groups[1];
    for (const auto branch : {DiZhi::Shen, DiZhi::You}) table.ranks[static_cast<int>(branch)] = groups[2];
    for (const auto branch : {DiZhi::Hai, DiZhi::Zi}) table.ranks[static_cast<int>(branch)] = groups[3];
    for (const auto branch : {DiZhi::Chen, DiZhi::Wei, DiZhi::Xu, DiZhi::Chou}) table.ranks[static_cast<int>(branch)] = groups[4];
    return table;
}

constexpr auto WANG_SHUAI_TABLE = build_wang_shuai_table();

constexpr int wx_rank(DiZhi month, WuXing element) {
    return WANG_SHUAI_TABLE.ranks[static_cast<int>(month)][static_cast<int>(element) - 1];
}

constexpr bool shi_e_da_bai(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Jia && branch == DiZhi::Chen) || (stem == TianGan::Yi && branch == DiZhi::Si)
        || (stem == TianGan::Bing && branch == DiZhi::Shen) || (stem == TianGan::Ding && branch == DiZhi::Hai)
        || (stem == TianGan::Wu && branch == DiZhi::Xu) || (stem == TianGan::Ji && branch == DiZhi::Chou)
        || (stem == TianGan::Geng && branch == DiZhi::Chen) || (stem == TianGan::Xin && branch == DiZhi::Si)
        || (stem == TianGan::Ren && branch == DiZhi::Shen) || (stem == TianGan::Gui && branch == DiZhi::Hai);
}

constexpr DiZhi yuan_chen(DiZhi origin, bool forward) {
    return origin + (forward ? 7 : 5);
}

constexpr DiZhi gu_chen(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Yin, Mao, Chen})) return Si;
    if (in(origin, {Si, Wu, Wei})) return Shen;
    if (in(origin, {Shen, You, Xu})) return Hai;
    return Yin;
}

constexpr DiZhi gua_su(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Yin, Mao, Chen})) return Chou;
    if (in(origin, {Si, Wu, Wei})) return Chen;
    if (in(origin, {Shen, You, Xu})) return Wei;
    return Xu;
}

constexpr DiZhi ge_jiao(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Hai, Mao, Wei})) return Chou;
    if (in(origin, {Yin, Wu, Xu})) return Chen;
    if (in(origin, {Si, You, Chou})) return Wei;
    return Xu;
}

constexpr DiZhi an_jin(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Zi, Mao, Wu, You})) return Si;
    if (in(origin, {Yin, Si, Shen, Hai})) return You;
    return Chou;
}

constexpr DiZhi xue_tang(WuXing element) {
    using enum DiZhi;
    switch (element) { case WuXing::Jin: return Si; case WuXing::Mu: return Hai;
        case WuXing::Shui: case WuXing::Tu: return Shen; case WuXing::Huo: return Yin; }
    return Zi;
}

constexpr DiZhi ci_guan(WuXing element) {
    using enum DiZhi;
    switch (element) { case WuXing::Jin: return Shen; case WuXing::Mu: return Yin;
        case WuXing::Shui: case WuXing::Tu: return Hai; case WuXing::Huo: return Si; }
    return Zi;
}

constexpr bool zheng_yin(WuXing element, TianGan stem, DiZhi branch) {
    if (element == WuXing::Jin) return stem == TianGan::Yi && branch == DiZhi::Chou;
    if (element == WuXing::Mu) return stem == TianGan::Gui && branch == DiZhi::Wei;
    if (element == WuXing::Huo) return stem == TianGan::Jia && branch == DiZhi::Xu;
    if (element == WuXing::Shui || element == WuXing::Tu) {
        return (stem == TianGan::Ren && branch == DiZhi::Chen)
            || (stem == TianGan::Bing && branch == DiZhi::Chen);
    }
    return false;
}

constexpr bool yin_cha_yang_cuo(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Bing && branch == DiZhi::Zi) || (stem == TianGan::Ding && branch == DiZhi::Chou)
        || (stem == TianGan::Wu && branch == DiZhi::Yin) || (stem == TianGan::Xin && branch == DiZhi::Mao)
        || (stem == TianGan::Ren && branch == DiZhi::Chen) || (stem == TianGan::Gui && branch == DiZhi::Si)
        || (stem == TianGan::Bing && branch == DiZhi::Wu) || (stem == TianGan::Ding && branch == DiZhi::Wei)
        || (stem == TianGan::Wu && branch == DiZhi::Shen) || (stem == TianGan::Xin && branch == DiZhi::You)
        || (stem == TianGan::Ren && branch == DiZhi::Xu) || (stem == TianGan::Gui && branch == DiZhi::Hai);
}

constexpr bool ba_zhuan(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Jia && branch == DiZhi::Yin) || (stem == TianGan::Yi && branch == DiZhi::Mao)
        || (stem == TianGan::Ji && branch == DiZhi::Wei) || (stem == TianGan::Ding && branch == DiZhi::Wei)
        || (stem == TianGan::Geng && branch == DiZhi::Shen) || (stem == TianGan::Xin && branch == DiZhi::You)
        || (stem == TianGan::Wu && branch == DiZhi::Xu) || (stem == TianGan::Gui && branch == DiZhi::Chou);
}

constexpr bool jiu_chou(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Ren && (branch == DiZhi::Zi || branch == DiZhi::Wu))
        || (stem == TianGan::Wu && (branch == DiZhi::Zi || branch == DiZhi::Wu))
        || (stem == TianGan::Ji && (branch == DiZhi::Si || branch == DiZhi::Mao))
        || (stem == TianGan::Yi && branch == DiZhi::Mao)
        || (stem == TianGan::Xin && (branch == DiZhi::You || branch == DiZhi::Mao));
}

constexpr bool gu_luan_day(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Jia && branch == DiZhi::Yin)
        || (stem == TianGan::Yi && branch == DiZhi::Si)
        || (stem == TianGan::Bing && branch == DiZhi::Wu)
        || (stem == TianGan::Ding && branch == DiZhi::Si)
        || (stem == TianGan::Wu && (branch == DiZhi::Wu || branch == DiZhi::Shen))
        || (stem == TianGan::Xin && branch == DiZhi::Hai)
        || (stem == TianGan::Ren && branch == DiZhi::Zi);
}

constexpr bool yin_yang_sha(TianGan stem, DiZhi branch, bool male) {
    return male ? (stem == TianGan::Bing && branch == DiZhi::Zi)
                : (stem == TianGan::Wu && branch == DiZhi::Wu);
}

constexpr bool tian_huo(const std::array<TianGan, 4>& stems,
                        const std::array<DiZhi, 4>& branches) {
    const bool san_he = std::ranges::all_of(std::array{DiZhi::Yin, DiZhi::Wu, DiZhi::Xu},
        [&](DiZhi value) { return std::ranges::find(branches, value) != branches.end(); });
    const bool fire_stems = std::ranges::find(stems, TianGan::Bing) != stems.end()
        && std::ranges::find(stems, TianGan::Ding) != stems.end();
    const bool no_water = std::ranges::find(stems, TianGan::Ren) == stems.end()
        && std::ranges::find(stems, TianGan::Gui) == stems.end()
        && std::ranges::none_of(branches, [](DiZhi value) { return value == DiZhi::Zi || value == DiZhi::Hai; });
    return san_he && fire_stems && no_water;
}

constexpr bool tian_tu(DiZhi day, DiZhi hour) {
    return (day == DiZhi::Chou && hour == DiZhi::Hai) || (day == DiZhi::Hai && hour == DiZhi::Chou)
        || (day == DiZhi::Yin && hour == DiZhi::Xu) || (day == DiZhi::Xu && hour == DiZhi::Yin)
        || (day == DiZhi::Mao && hour == DiZhi::You) || (day == DiZhi::You && hour == DiZhi::Mao)
        || (day == DiZhi::Chen && hour == DiZhi::Shen) || (day == DiZhi::Shen && hour == DiZhi::Chen)
        || (day == DiZhi::Si && hour == DiZhi::Wei) || (day == DiZhi::Wei && hour == DiZhi::Si);
}

constexpr bool tun_xian(const std::array<DiZhi, 4>& branches) {
    const auto has = [&](DiZhi value) { return std::ranges::find(branches, value) != branches.end(); };
    return (has(DiZhi::Hai) || has(DiZhi::Xu) || has(DiZhi::Wei)) && has(DiZhi::Yin)
        || has(DiZhi::Shen) && has(DiZhi::Si)
        || has(DiZhi::Mao) && has(DiZhi::Xu)
        || has(DiZhi::Wu) && (has(DiZhi::Chou) || has(DiZhi::Zi));
}

constexpr bool di_zhi_po(DiZhi left, DiZhi right) {
    return (left == DiZhi::Mao && right == DiZhi::Wu) || (left == DiZhi::Wu && right == DiZhi::Mao)
        || (left == DiZhi::Chou && right == DiZhi::Chen) || (left == DiZhi::Chen && right == DiZhi::Chou)
        || (left == DiZhi::Zi && right == DiZhi::You) || (left == DiZhi::You && right == DiZhi::Zi)
        || (left == DiZhi::Wei && right == DiZhi::Xu) || (left == DiZhi::Xu && right == DiZhi::Wei);
}

constexpr bool tian_xing(DiZhi year, TianGan hour) {
    using enum DiZhi;
    if (in(year, {Zi, Chou})) return hour == TianGan::Yi;
    if (year == Yin) return hour == TianGan::Geng;
    if (in(year, {Mao, Chen})) return hour == TianGan::Xin;
    if (year == Si) return hour == TianGan::Ren;
    if (in(year, {Wu, Wei})) return hour == TianGan::Gui;
    if (year == Shen) return hour == TianGan::Bing;
    if (in(year, {You, Xu})) return hour == TianGan::Ding;
    return hour == TianGan::Wu;
}

constexpr bool zhen_chang_sheng(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Jia && branch == DiZhi::Shen)
        || (stem == TianGan::Ji && branch == DiZhi::Si)
        || (stem == TianGan::Xin && branch == DiZhi::Si)
        || (stem == TianGan::Bing && branch == DiZhi::Yin);
}

constexpr bool jin_shen(TianGan stem, DiZhi branch) {
    return (stem == TianGan::Jia && (branch == DiZhi::Zi || branch == DiZhi::Wu))
        || (stem == TianGan::Ji && (branch == DiZhi::Mao || branch == DiZhi::You));
}

constexpr int jia_zi_index(TianGan stem, DiZhi branch) {
    for (int index = 0; index < 60; ++index) {
        if (static_cast<int>(stem) == index % 10 && static_cast<int>(branch) == index % 12) return index;
    }
    return -1;
}

constexpr bool ri_xing(TianGan day_stem, DiZhi day_branch, TianGan stem, DiZhi branch) {
    const int index = jia_zi_index(day_stem, day_branch);
    if (index < 0) return false;
    const int offset = static_cast<int>(day_stem);
    const int target = (index + ((static_cast<int>(day_stem) % 2 == 0) ? offset : -offset) + 60) % 60;
    return static_cast<int>(stem) == target % 10 && static_cast<int>(branch) == target % 12;
}

constexpr bool liu_xue(TianGan year_stem, DiZhi year_branch,
                       TianGan month_stem, DiZhi month_branch,
                       TianGan stem, DiZhi branch) {
    const int year_index = jia_zi_index(year_stem, year_branch);
    const int month_index = jia_zi_index(month_stem, month_branch);
    if (year_index < 0 || month_index < 0) return false;
    const int target = (year_index + month_index) % 60;
    return static_cast<int>(stem) == target % 10 && static_cast<int>(branch) == target % 12;
}

constexpr bool fu_chen(DiZhi year_branch, DiZhi month_branch, DiZhi candidate) {
    // The surviving transcriptions use 戌起 and 子起 variants; accept both
    // target palace positions while preserving the source ambiguity.
    const int xu_to_month = (static_cast<int>(DiZhi::Xu) - static_cast<int>(month_branch) + 12) % 12;
    const int zi_to_year = (static_cast<int>(DiZhi::Zi) - static_cast<int>(year_branch) + 12) % 12;
    return candidate == year_branch + xu_to_month || candidate == year_branch + zi_to_year;
}

constexpr bool lei_ting(DiZhi month, DiZhi hour) {
    // 正七、二八子寅；三九、四十卯巳；五十一午申；六十二酉亥。
    const int month_no = (static_cast<int>(month) - static_cast<int>(DiZhi::Yin) + 12) % 12 + 1;
    if (month_no == 1 || month_no == 2 || month_no == 7 || month_no == 8)
        return hour == DiZhi::Zi || hour == DiZhi::Yin;
    if (month_no == 3 || month_no == 4 || month_no == 9 || month_no == 10)
        return hour == DiZhi::Mao || hour == DiZhi::Si;
    if (month_no == 5 || month_no == 11)
        return hour == DiZhi::Wu || hour == DiZhi::Shen;
    return hour == DiZhi::You || hour == DiZhi::Hai;
}

static_assert(ri_xing(TianGan::Ren, DiZhi::Chen, TianGan::Geng, DiZhi::Zi));
static_assert(liu_xue(TianGan::Bing, DiZhi::Zi, TianGan::Gui, DiZhi::Si, TianGan::Yi, DiZhi::Si));

constexpr bool jian_feng(TianGan day_stem, DiZhi day_branch, DiZhi candidate) {
    const DiZhi start = day_branch + -((static_cast<int>(day_stem) * 5) % 12);
    // Six 甲旬 tables from the chapter: sword and edge oppose each other.
    if (start == DiZhi::Zi) return candidate == DiZhi::Chen || candidate == DiZhi::Xu;
    if (start == DiZhi::Wu) return candidate == DiZhi::Xu || candidate == DiZhi::Chen;
    if (start == DiZhi::Yin) return candidate == DiZhi::Wu || candidate == DiZhi::Zi;
    if (start == DiZhi::Shen) return candidate == DiZhi::Zi || candidate == DiZhi::Wu;
    if (start == DiZhi::Chen) return candidate == DiZhi::Yin || candidate == DiZhi::Shen;
    if (start == DiZhi::Xu) return candidate == DiZhi::Shen || candidate == DiZhi::Yin;
    return false;
}

constexpr bool ji_feng(DiZhi month, TianGan stem) {
    using enum DiZhi;
    constexpr std::array targets{TianGan::Jia, TianGan::Yi, TianGan::Wu, TianGan::Bing,
        TianGan::Ding, TianGan::Ji, TianGan::Geng, TianGan::Xin, TianGan::Wu,
        TianGan::Ren, TianGan::Gui, TianGan::Ji};
    return targets[static_cast<std::size_t>(month)] == stem;
}

constexpr DiZhi tao_hua(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Hai, Mao, Wei})) return Zi;
    if (in(origin, {Si, You, Chou})) return Wu;
    if (in(origin, {Yin, Wu, Xu})) return Mao;
    return You;
}

constexpr DiZhi hua_gai(DiZhi origin) {
    using enum DiZhi;
    if (in(origin, {Yin, Wu, Xu})) return Xu;
    if (in(origin, {Shen, Zi, Chen})) return Chen;
    if (in(origin, {Si, You, Chou})) return Chou;
    return Wei;
}

constexpr bool tian_de(TianGan stem, DiZhi branch, DiZhi month) {
    using enum DiZhi;
    switch (month) {
        case Yin: return stem == TianGan::Ding;
        case Mao: return branch == Shen;
        case Chen: return stem == TianGan::Ren;
        case Si: return stem == TianGan::Xin;
        case Wu: return branch == Hai;
        case Wei: return stem == TianGan::Jia;
        case Shen: return stem == TianGan::Gui;
        case You: return branch == Yin;
        case Xu: return stem == TianGan::Bing;
        case Hai: return stem == TianGan::Yi;
        case Zi: return branch == Si;
        case Chou: return stem == TianGan::Geng;
    }
    return false;
}

constexpr TianGan he_gan(TianGan stem) {
    using enum TianGan;
    switch (stem) {
        case Jia: return Ji; case Yi: return Geng; case Bing: return Xin;
        case Ding: return Ren; case Wu: return Gui; case Ji: return Jia;
        case Geng: return Yi; case Xin: return Bing; case Ren: return Ding;
        case Gui: return Wu;
    }
    return Jia;
}

constexpr TianGan yue_de_he(DiZhi month) {
    using enum DiZhi;
    if (in(month, {Yin, Wu, Xu})) return TianGan::Xin;
    if (in(month, {Shen, Zi, Chen})) return TianGan::Ding;
    if (in(month, {Hai, Mao, Wei})) return TianGan::Ji;
    return TianGan::Yi;
}

constexpr std::optional<TianGan> tian_de_gan(DiZhi month) {
    using enum DiZhi;
    switch (month) {
        case Yin: return TianGan::Ding; case Chen: return TianGan::Ren;
        case Si: return TianGan::Xin; case Wei: return TianGan::Jia;
        case Shen: return TianGan::Gui; case Xu: return TianGan::Bing;
        case Hai: return TianGan::Yi; case Chou: return TianGan::Geng;
        default: return std::nullopt;
    }
}

constexpr bool is_de_stem(DiZhi month, TianGan stem) {
    using enum DiZhi;
    if (in(month, {Yin, Wu, Xu})) return in(stem, {TianGan::Bing, TianGan::Ding});
    if (in(month, {Shen, Zi, Chen})) return in(stem, {TianGan::Ren, TianGan::Gui, TianGan::Wu, TianGan::Ji});
    if (in(month, {Si, You, Chou})) return in(stem, {TianGan::Geng, TianGan::Xin});
    return in(stem, {TianGan::Jia, TianGan::Yi});
}

constexpr bool is_xiu_stem(DiZhi month, TianGan stem) {
    using enum DiZhi;
    if (in(month, {Yin, Wu, Xu})) return in(stem, {TianGan::Wu, TianGan::Gui});
    if (in(month, {Shen, Zi, Chen})) return in(stem, {TianGan::Bing, TianGan::Xin, TianGan::Jia, TianGan::Ji});
    if (in(month, {Si, You, Chou})) return in(stem, {TianGan::Yi, TianGan::Geng});
    return in(stem, {TianGan::Ding, TianGan::Ren});
}

constexpr bool tong_zi_month_rule(DiZhi month, DiZhi candidate) {
    using enum DiZhi;
    const bool spring_autumn = in(month, {Yin, Mao, Chen, Shen, You, Xu});
    return spring_autumn ? in(candidate, {Yin, Zi}) : in(candidate, {Mao, Wei, Chen});
}

constexpr bool tong_zi_na_yin_rule(WuXing na_yin, DiZhi candidate) {
    using enum DiZhi;
    switch (na_yin) {
        case WuXing::Jin:
        case WuXing::Mu: return in(candidate, {Wu, Mao});
        case WuXing::Shui:
        case WuXing::Huo: return in(candidate, {You, Xu});
        case WuXing::Tu: return in(candidate, {Chen, Si});
    }
    return false;
}

constexpr std::size_t display_rank(std::string_view name) {
    using namespace std::string_view_literals;
    constexpr std::array order{
        "国印贵人"sv, "太极贵人"sv, "福星贵人"sv, "德秀贵人"sv, "空亡"sv,
        "飞刃"sv, "灾煞"sv, "丧门"sv, "将星"sv,
        "红艳煞"sv, "童子煞"sv, "金舆"sv, "文昌贵人"sv, "天厨贵人"sv,
        "天德贵人"sv, "天罗"sv, "地网"sv, "月德合"sv, "禄神"sv, "流霞"sv
    };
    const auto found = std::ranges::find(order, name);
    return found == order.end() ? order.size() : static_cast<std::size_t>(found - order.begin());
}

}  // namespace detail

Result calculate(const std::array<TianGan, 4>& stems,
                 const std::array<DiZhi, 4>& branches,
                 WuXing year_na_yin,
                 bool male) {
    using namespace detail;
    using enum DiZhi;

    Result result;
    const TianGan year_stem = stems[0];
    const TianGan day_stem = stems[2];
    const DiZhi year_branch = branches[0];
    const DiZhi month_branch = branches[1];
    const DiZhi day_branch = branches[2];
    const bool yuan_chen_forward = (static_cast<int>(year_stem) % 2 == 0) == male;

    constexpr std::array guo_yin{Xu, Hai, Chou, Yin, Chou, Yin, Chen, Si, Wei, Shen};
    constexpr std::array fei_ren{You, Xu, Zi, Chou, Zi, Chou, Mao, Chen, Wu, Wei};
    constexpr std::array hong_yan{Wu, Wu, Yin, Wei, Chen, Chen, Xu, You, Zi, Shen};
    constexpr std::array jin_yu{Chen, Si, Wei, Shen, Wei, Shen, Xu, Hai, Chou, Yin};
    constexpr std::array wen_chang{Si, Wu, Shen, You, Shen, You, Hai, Zi, Yin, Mao};
    constexpr std::array tian_chu{Si, Wu, Si, Wu, Shen, You, Hai, Zi, Yin, Mao};
    constexpr std::array lu_shen{Yin, Mao, Si, Wu, Si, Wu, Shen, You, Hai, Zi};
    constexpr std::array liu_xia{You, Xu, Wei, Shen, Si, Wu, Chen, Mao, Hai, Yin};
    constexpr std::array yang_ren{Mao, Chen, Wu, Wei, You, Xu, Zi, Chou, Zi, Chou};
    constexpr std::array tian_yi_a{Chou, Zi, You, You, Chou, Zi, Yin, Yin, Mao, Mao};
    constexpr std::array tian_yi_b{Wei, Shen, Hai, Hai, Wei, Shen, Wu, Wu, Si, Si};
    constexpr std::array tian_yi_guang_a{Chou, Zi, You, You, Chou, Zi, Chou, Yin, Mao, Mao};
    constexpr std::array tian_yi_guang_b{Wei, Shen, Hai, Hai, Wei, Shen, Wei, Wu, Si, Si};

    const auto day_void = GanZhi::get_kong_wang(day_stem, day_branch);
    const DiZhi guan_fu_branch = year_branch + 1;
    const DiZhi bing_fu_branch = year_branch + 11;
    const DiZhi si_fu_branch = bing_fu_branch + 6;
    const DiZhi diao_ke_branch = year_branch + 10;
    const DiZhi zhai_branch = year_branch + 5;
    const DiZhi mu_branch = year_branch + 7;
    const bool has_tian_huo = tian_huo(stems, branches);
    const bool gu_luan_pair = gu_luan_day(day_stem, day_branch)
        && gu_luan_day(stems[3], branches[3]);
    const bool has_tian_tu = tian_tu(day_branch, branches[3]);
    const bool has_tian_xing = tian_xing(year_branch, stems[3]);
    const bool has_lei_ting = lei_ting(month_branch, branches[3]);
    const bool has_lu = std::ranges::any_of(branches, [&](DiZhi branch) {
        return stem_matches_branch(day_stem, branch, lu_shen);
    });
    const bool has_ma = std::ranges::any_of(branches, [&](DiZhi branch) {
        return branch == yi_ma(year_branch) || branch == yi_ma(day_branch);
    });
    const bool same_lu_ma = std::ranges::any_of(branches, [&](DiZhi branch) {
        return stem_matches_branch(day_stem, branch, lu_shen)
            && (branch == yi_ma(year_branch) || branch == yi_ma(day_branch));
    });
    const bool has_tian_yi = std::ranges::any_of(branches, [&](DiZhi branch) {
        const auto index = static_cast<std::size_t>(day_stem);
        return branch == tian_yi_a[index] || branch == tian_yi_b[index];
    });
    const TianGan food_stem = static_cast<TianGan>((static_cast<int>(day_stem) + 2) % 10);
    const bool has_food = std::ranges::find(stems, food_stem) != stems.end();
    const bool has_tun_xian = tun_xian(branches);
    const bool has_po = std::ranges::any_of(branches, [&](DiZhi left) {
        return std::ranges::any_of(branches, [&](DiZhi right) { return left != right && di_zhi_po(left, right); });
    });
    const bool has_fan_ben = std::ranges::any_of(std::array{stems[2], stems[3]}, [&](TianGan stem) {
        return GanZhi::wu_xing_ke(GanZhi::get_wu_xing(stem), year_na_yin);
    });
    const bool has_water_sha_day =
        (day_stem == TianGan::Bing && day_branch == DiZhi::Zi)
        || (day_stem == TianGan::Gui && (day_branch == DiZhi::Wei || day_branch == DiZhi::Chou));
    const bool has_hang_jian = std::ranges::all_of(
        std::array{DiZhi::Si, DiZhi::You, DiZhi::Chou},
        [&](DiZhi value) { return std::ranges::find(branches, value) != branches.end(); })
        && std::ranges::find(branches, DiZhi::Shen) != branches.end();
    const bool has_self_hang = std::ranges::find(stems, TianGan::Wu) != stems.end()
        && std::ranges::find(stems, TianGan::Ji) != stems.end()
        && ((std::ranges::find(branches, DiZhi::Chen) != branches.end()
             && std::ranges::find(branches, DiZhi::Hai) != branches.end())
            || (std::ranges::find(branches, DiZhi::Yin) != branches.end()
                && std::ranges::find(branches, DiZhi::Wei) != branches.end())
            || (std::ranges::find(branches, DiZhi::Mao) != branches.end()
                && std::ranges::find(branches, DiZhi::Shen) != branches.end())
            || (std::ranges::find(branches, DiZhi::Wu) != branches.end()
                && std::ranges::find(branches, DiZhi::Chou) != branches.end())
            || (std::ranges::find(branches, DiZhi::Zi) != branches.end()
                && std::ranges::find(branches, DiZhi::You) != branches.end()));
    for (const TianGan stem : stems) {
        if (is_de_stem(month_branch, stem)) result.de_xiu.de_stems.push_back(stem);
        if (is_xiu_stem(month_branch, stem)) result.de_xiu.xiu_stems.push_back(stem);
    }
    std::ranges::sort(result.de_xiu.de_stems, {}, [](TianGan value) { return static_cast<int>(value); });
    std::ranges::sort(result.de_xiu.xiu_stems, {}, [](TianGan value) { return static_cast<int>(value); });
    result.de_xiu.de_stems.erase(std::unique(result.de_xiu.de_stems.begin(), result.de_xiu.de_stems.end()), result.de_xiu.de_stems.end());
    result.de_xiu.xiu_stems.erase(std::unique(result.de_xiu.xiu_stems.begin(), result.de_xiu.xiu_stems.end()), result.de_xiu.xiu_stems.end());
    result.de_xiu.matched = !result.de_xiu.de_stems.empty() && !result.de_xiu.xiu_stems.empty();
    if (result.de_xiu.matched) {
        constexpr std::array<std::pair<DiZhi, DiZhi>, 6> chong_pairs{{{DiZhi::Zi, DiZhi::Wu}, {DiZhi::Chou, DiZhi::Wei}, {DiZhi::Yin, DiZhi::Shen}, {DiZhi::Mao, DiZhi::You}, {DiZhi::Chen, DiZhi::Xu}, {DiZhi::Si, DiZhi::Hai}}};
        const bool has_chong = std::ranges::any_of(chong_pairs, [&](const auto& p) {
            return std::ranges::find(branches, p.first) != branches.end() && std::ranges::find(branches, p.second) != branches.end();
        });
        if (has_chong) result.de_xiu.sub_tags.push_back("chongkejiaya");
    }

    const TianGan month_de_he = yue_de_he(month_branch);
    const auto month_tian_de = tian_de_gan(month_branch);
    for (std::size_t i = 0; i < branches.size(); ++i) {
        auto& names = result.pillars[i].names;
        const auto branch = branches[i];
        const auto stem = stems[i];
        const bool tiande = tian_de(stem, branch, month_branch);
        const bool yuede = is_de_stem(month_branch, stem);
        const bool yuedehe = stem == month_de_he;
        const bool tiandehe = month_tian_de.has_value() && stem == he_gan(*month_tian_de);
        if (tiande) { result.tian_yue_de.tiande = true; add_unique(names, "天德贵人"); }
        if (yuede) { result.tian_yue_de.yuede = true; add_unique(names, "月德贵人"); }
        if (yuedehe) { result.tian_yue_de.yuedehe = true; add_unique(names, "月德合"); }
        if (tiandehe) { result.tian_yue_de.tiandehe = true; add_unique(names, "天德合"); }
        if (stem_matches_branch(year_stem, branch, guo_yin) || stem_matches_branch(day_stem, branch, guo_yin)) add_unique(names, "国印贵人");
        if (tai_ji(year_stem, branch) || tai_ji(day_stem, branch)) {
            add_unique(names, "太极贵人");
            add_unique(names, "太极贵");
            TaiJiOccurrence occurrence{i, {}};
            if (tai_ji(year_stem, branch)) occurrence.sources.push_back("year_stem");
            if (tai_ji(day_stem, branch)) occurrence.sources.push_back("day_stem");
            result.tai_ji.push_back(std::move(occurrence));
        }
        if (fu_xing(year_stem, branch) || fu_xing(day_stem, branch)) add_unique(names, "福星贵人");
        if (result.de_xiu.matched && (is_de_stem(month_branch, stem) || is_xiu_stem(month_branch, stem))) {
            add_unique(names, "德秀贵人");
            add_unique(names, "德秀");
        }
        if (branch == day_void[0] || branch == day_void[1]) { add_unique(names, "空亡"); result.auxiliary.kongwang = true; }
        if (stem_matches_branch(day_stem, branch, fei_ren)) { add_unique(names, "飞刃"); result.auxiliary.feiren = true; }
        if (stem_matches_branch(day_stem, branch, yang_ren)) { add_unique(names, "羊刃"); result.auxiliary.yangren = true; }
        const auto day_index = static_cast<std::size_t>(day_stem);
        const bool tian_yi_common = branch == tian_yi_a[day_index] || branch == tian_yi_b[day_index];
        const bool tian_yi_guang = branch == tian_yi_guang_a[day_index] || branch == tian_yi_guang_b[day_index];
        if (tian_yi_common || tian_yi_guang) {
            add_unique(names, "天乙贵人");
            add_unique(names, "贵人");
            if (tian_yi_common) result.tian_yi.push_back({i, "tianyige_common"});
            if (tian_yi_guang) result.tian_yi.push_back({i, "tianyige_guanglu"});
        }
        if (branch == zai_sha(year_branch) || branch == zai_sha(day_branch)) add_unique(names, "灾煞");
        if (branch == jie_sha(year_branch) || branch == jie_sha(day_branch)) {
            add_unique(names, "劫煞");
        }
        if (branch == wang_shen(year_branch) || branch == wang_shen(day_branch)) {
            add_unique(names, "亡神");
        }
        if (branch == liu_e(year_branch) || branch == liu_e(day_branch)) add_unique(names, "六厄");
        if (branch == yi_ma(year_branch) || branch == yi_ma(day_branch)) {
            add_unique(names, "驿马");
            add_unique(names, "禄马");
            if (branch == yi_ma(year_branch)) result.yi_ma.push_back({i, "yearBranch"});
            if (branch == yi_ma(day_branch)) result.yi_ma.push_back({i, "dayBranch"});
        }
        if (branch == yuan_chen(year_branch, yuan_chen_forward)) {
            add_unique(names, "元辰");
            add_unique(names, "大耗");
            result.auxiliary.yuanchen = true;
            if (std::ranges::find(result.auxiliary.yuanchen_alias, "大耗") == result.auxiliary.yuanchen_alias.end())
                result.auxiliary.yuanchen_alias.push_back("大耗");
        }
        if (branch == gu_chen(year_branch)) { add_unique(names, "孤辰"); result.auxiliary.guchen = true; }
        if (branch == gua_su(year_branch)) { add_unique(names, "寡宿"); result.auxiliary.guaxiu = true; }
        if (branch == ge_jiao(year_branch)) { add_unique(names, "隔角煞"); result.auxiliary.gejiao = true; }
        if (branch == an_jin(year_branch) || branch == an_jin(day_branch)) {
            add_unique(names, "暗金的煞");
            add_unique(names, "吟呻");
            add_unique(names, "破碎");
            add_unique(names, "白衣");
            if (branch == an_jin(year_branch)) result.auxiliary.an_jin_sources.push_back("year_branch");
            if (branch == an_jin(day_branch)) result.auxiliary.an_jin_sources.push_back("day_branch");
            result.auxiliary.an_jin_sub_tags = {"yinshen", "posui", "baiyi"};
        }
        const bool forward_gou = ((static_cast<int>(year_stem) % 2 == 0) == male);
        const auto gou_branch = year_branch + (forward_gou ? 3 : 9);
        const auto jiao_branch = year_branch + (forward_gou ? 9 : 3);
        if (branch == gou_branch) { add_unique(names, "勾神"); result.auxiliary.goushen = true; result.auxiliary.sub_tags.push_back("爪牙煞"); }
        if (branch == jiao_branch) { add_unique(names, "绞神"); result.auxiliary.jiaoshen = true; result.auxiliary.sub_tags.push_back("爪牙煞"); }
        if (branch == xue_tang(year_na_yin)) {
            add_unique(names, "学堂词馆"); add_unique(names, "学堂");
            const auto pillar_na_yin = GanZhi::LiuShiJiaZi(stem, branch).get_na_yin();
            result.xue_guan.push_back({i, "xuetang_nayin", pillar_na_yin == year_na_yin});
        }
        if (branch == ci_guan(year_na_yin)) {
            add_unique(names, "学堂词馆"); add_unique(names, "词馆");
            const auto pillar_na_yin = GanZhi::LiuShiJiaZi(stem, branch).get_na_yin();
            result.xue_guan.push_back({i, "ciguan_nayin", pillar_na_yin == year_na_yin});
        }
        const auto day_element = GanZhi::get_wu_xing(day_stem);
        if (branch == xue_tang(day_element)) {
            add_unique(names, "学堂词馆"); add_unique(names, "学堂");
            result.xue_guan.push_back({i, "xuetang_ri", false});
        }
        if (branch == ci_guan(day_element)) {
            add_unique(names, "学堂词馆"); add_unique(names, "词馆");
            result.xue_guan.push_back({i, "ciguan_ri", false});
        }
        if (branch == tao_hua(year_branch) || branch == tao_hua(day_branch)) {
            add_unique(names, "桃花煞");
            add_unique(names, "桃花");
            add_unique(names, "咸池");
            SourceOccurrence occurrence{i, "桃花", {}};
            if (branch == tao_hua(year_branch)) occurrence.sources.push_back("year_branch");
            if (branch == tao_hua(day_branch)) occurrence.sources.push_back("day_branch");
            result.source_occurrences.push_back(std::move(occurrence));
        }
        if (branch == hua_gai(year_branch) || branch == hua_gai(day_branch)) {
            add_unique(names, "华盖"); SourceOccurrence occurrence{i, "华盖", {}};
            if (branch == hua_gai(year_branch)) occurrence.sources.push_back("year_branch");
            if (branch == hua_gai(day_branch)) occurrence.sources.push_back("day_branch");
            result.source_occurrences.push_back(std::move(occurrence));
        }
        if (in(branch, {Chen, Xu, Chou, Wei})) {
            add_unique(names, "四库");
            add_unique(names, "四墓");
        }
        if (zhen_chang_sheng(stem, branch)) add_unique(names, "长生");
        if (jin_shen(stem, branch)) add_unique(names, "进神");
        const bool is_lu_branch = stem_matches_branch(day_stem, branch, lu_shen);
        const bool is_ma_branch = branch == yi_ma(year_branch) || branch == yi_ma(day_branch);
        auto add_lu_ma = [&](std::string key, std::string basis) {
            std::vector<std::size_t> pillars;
            for (std::size_t p = 0; p < branches.size(); ++p) if (stem_matches_branch(day_stem, branches[p], lu_shen) || branches[p] == yi_ma(year_branch) || branches[p] == yi_ma(day_branch)) pillars.push_back(p);
            result.lu_ma_patterns.push_back({std::move(key), std::move(pillars), std::move(basis), true});
        };
        if (same_lu_ma && is_lu_branch && is_ma_branch) add_lu_ma("禄马同乡", "日干禄位与年支或日支驿马同支");
        if (has_lu && has_ma && (is_lu_branch || is_ma_branch)) {
            add_lu_ma("天禄天马", "命局同时见日干禄与驿马");
            add_lu_ma("禄马交驰", "命局禄神与驿马同见");
        }
        if (has_lu && is_lu_branch) add_lu_ma("生旺禄", "日干禄位出现在四柱");
        if (has_lu && is_lu_branch) {
            add_lu_ma("名位禄", "日干禄位命中");
            add_lu_ma("真禄", "日干禄位命中");
        }
        if (has_lu && has_ma && !same_lu_ma && (is_lu_branch || is_ma_branch)) add_lu_ma("夹禄夹马", "禄位与驿马分列命局");
        if (has_lu && std::ranges::count_if(branches, [&](DiZhi value) {
                return stem_matches_branch(day_stem, value, lu_shen);
            }) > 1)
            add_lu_ma("进退真禄", "四柱重复出现日干禄位");
        if (has_lu && has_food && is_lu_branch) add_lu_ma("食神合禄", "食神与日干禄同见");
        if (has_lu && has_tian_yi && is_lu_branch) add_lu_ma("天禄贵神", "日干禄与天乙贵人同见");
        if (branch == year_branch + 8) add_unique(names, "白虎");
        if (yin_cha_yang_cuo(stem, branch)) {
            add_unique(names, "阴差阳错煞"); add_unique(names, "阴错阳差");
            result.source_occurrences.push_back({i, "阴差阳错煞", {"fixed_ganzhi"}, {"阴错阳差"}});
        }
        if (ba_zhuan(stem, branch) || jiu_chou(stem, branch)) {
            add_unique(names, "淫欲妨害煞");
            result.source_occurrences.push_back({i, "淫欲妨害煞", {"fixed_ganzhi"}, {"组合条件仅作备注"}});
        }
        if (shi_e_da_bai(stem, branch)) {
            add_unique(names, "十恶大败");
            add_unique(names, "无禄日");
        }
        if (zheng_yin(year_na_yin, stem, branch)) add_unique(names, "正印");
        if (branch == year_branch + 2) { add_unique(names, "丧门"); result.source_occurrences.push_back({i, "丧门", {"year_branch"}, {}}); }
        if (branch == guan_fu_branch) { add_unique(names, "官符煞"); result.source_occurrences.push_back({i, "官符煞", {"year_branch"}, {}}); }
        if (branch == bing_fu_branch) { add_unique(names, "病符煞"); result.source_occurrences.push_back({i, "病符煞", {"year_branch"}, {}}); }
        if (branch == si_fu_branch) { add_unique(names, "死符煞"); result.source_occurrences.push_back({i, "死符煞", {"year_branch"}, {}}); }
        if (branch == diao_ke_branch) {
            add_unique(names, "吊客");
            add_unique(names, "丧吊煞");
            result.source_occurrences.push_back({i, "丧吊煞", {"year_branch"}, {"吊客"}});
        }
        if (branch == zhai_branch || branch == mu_branch) { add_unique(names, "宅墓煞"); result.source_occurrences.push_back({i, "宅墓煞", {"year_branch"}, {}}); }
        const bool self_hang_branch = has_self_hang &&
            ((branch == Chen && std::ranges::find(branches, Hai) != branches.end())
             || (branch == Hai && std::ranges::find(branches, Chen) != branches.end())
             || (branch == Yin && std::ranges::find(branches, Wei) != branches.end())
             || (branch == Wei && std::ranges::find(branches, Yin) != branches.end())
             || (branch == Mao && std::ranges::find(branches, Shen) != branches.end())
             || (branch == Shen && std::ranges::find(branches, Mao) != branches.end())
             || (branch == Wu && std::ranges::find(branches, Chou) != branches.end())
             || (branch == Chou && std::ranges::find(branches, Wu) != branches.end())
             || (branch == Zi && std::ranges::find(branches, You) != branches.end())
             || (branch == You && std::ranges::find(branches, Zi) != branches.end()));
        if (self_hang_branch) add_unique(names, "自缢煞");
        if (has_water_sha_day && i == 2 && (branch == tao_hua(year_branch) || branch == tao_hua(day_branch))) add_unique(names, "水溺煞");
        if (has_hang_jian && in(branch, {Si, You, Chou, Shen})) add_unique(names, "挂剑煞");
        if (has_tian_tu && (i == 2 || i == 3)) add_unique(names, "天屠煞");
        if (has_tian_xing && i == 3) add_unique(names, "天刑煞");
        if (has_lei_ting && i == 3) add_unique(names, "雷霆煞");
        if (has_tun_xian && (in(branch, {Hai, Xu, Wei, Yin, Shen, Si, Mao, Wu, Chou, Zi}))) add_unique(names, "吞陷煞");
        if (has_po && (i == 2 || i == 3)) add_unique(names, "破煞");
        if (has_fan_ben && (i == 2 || i == 3)) add_unique(names, "返本煞");
        if (ri_xing(day_stem, day_branch, stem, branch)) add_unique(names, "日刑煞");
        if (liu_xue(year_stem, year_branch, stems[1], month_branch, stem, branch)) add_unique(names, "流血煞");
        if (fu_chen(year_branch, month_branch, branch)) add_unique(names, "浮沉煞");
        if (jian_feng(day_stem, day_branch, branch)) add_unique(names, "剑锋煞");
        if (ji_feng(month_branch, stem)) add_unique(names, "戟锋煞");
        if (branch == jiang_xing(year_branch) || branch == jiang_xing(day_branch)) {
            add_unique(names, "将星"); SourceOccurrence occurrence{i, "将星", {}};
            if (branch == jiang_xing(year_branch)) occurrence.sources.push_back("year_branch");
            if (branch == jiang_xing(day_branch)) occurrence.sources.push_back("day_branch");
            result.source_occurrences.push_back(std::move(occurrence));
        }
        if (stem_matches_branch(day_stem, branch, hong_yan)) add_unique(names, "红艳煞");
        if ((branch == tao_hua(year_branch) || branch == tao_hua(day_branch))
            && stem_matches_branch(day_stem, branch, hong_yan)) add_unique(names, "桃花红艳煞");
        if (yin_yang_sha(day_stem, day_branch, male) && i == 2) add_unique(names, "阴阳煞");
        if (gu_luan_day(stem, branch)) {
            add_unique(names, "孤鸾寡鹄煞");
            result.source_occurrences.push_back({i, "孤鸾寡鹄煞", {"fixed_ganzhi"}, {male ? "男命释义备注" : "女命释义备注"}});
        }
        if (has_tian_huo && in(branch, {Yin, Wu, Xu})) add_unique(names, "天火煞");
        if (branch == jin_yu[static_cast<std::size_t>(day_stem)]) {
            add_unique(names, "金舆");
            constexpr std::array<std::string_view, 4> positions{"年柱", "月柱", "日柱", "时柱"};
            result.jin_yu.push_back({i, std::string(positions[i])});
        }
        if (stem_matches_branch(year_stem, branch, wen_chang) || stem_matches_branch(day_stem, branch, wen_chang)) {
            add_unique(names, "文昌贵人"); SourceOccurrence occurrence{i, "文昌贵人", {}};
            if (stem_matches_branch(year_stem, branch, wen_chang)) occurrence.sources.push_back("year_stem");
            if (stem_matches_branch(day_stem, branch, wen_chang)) occurrence.sources.push_back("day_stem");
            result.source_occurrences.push_back(std::move(occurrence));
        }
        if (stem_matches_branch(year_stem, branch, tian_chu) || stem_matches_branch(day_stem, branch, tian_chu)) {
            add_unique(names, "天厨贵人"); SourceOccurrence occurrence{i, "天厨贵人", {}};
            if (stem_matches_branch(year_stem, branch, tian_chu)) occurrence.sources.push_back("year_stem");
            if (stem_matches_branch(day_stem, branch, tian_chu)) occurrence.sources.push_back("day_stem");
            result.source_occurrences.push_back(std::move(occurrence));
        }
        if (tian_de(stem, branch, month_branch)) {
            add_unique(names, "天德贵人");
            add_unique(names, "天月德");
        }
        if (stem == month_de_he) {
            add_unique(names, "月德合");
            add_unique(names, "月德贵人");
            add_unique(names, "天月德");
        }
        if (stem_matches_branch(day_stem, branch, lu_shen)) {
            add_unique(names, "禄神");
            constexpr std::array<std::string_view, 4> positions{"岁禄", "建禄", "专禄", "归禄"};
            const auto variant = lu_variant(day_stem, stem);
            result.lu_shen.push_back({
                .pillar_index = i,
                .position = std::string(positions[i]),
                .ganzhi = std::string(GanZhi::Mapper::to_zh(stem)) + std::string(GanZhi::Mapper::to_zh(branch)),
                .variant = std::string(variant.name),
                .nature = std::string(variant.nature),
            });
        }
        if (stem_matches_branch(day_stem, branch, liu_xia)) { add_unique(names, "流霞"); result.source_occurrences.push_back({i, "流霞", {"day_stem"}}); }
        if (in(stem, {TianGan::Jia, TianGan::Bing, TianGan::Ding, TianGan::Ren}) || branch == Chen)
            add_unique(names, "平头煞");
        if (in(stem, {TianGan::Jia, TianGan::Gui}) || in(branch, {Wei, Shen, You}))
            add_unique(names, "破字煞");
        if (in(stem, {TianGan::Jia, TianGan::Xin}) || in(branch, {Mao, Wu, Shen})) {
            add_unique(names, "悬针煞");
            add_unique(names, "悬针");
        }
        if (in(stem, {TianGan::Wu, TianGan::Geng}) || branch == Xu)
            add_unique(names, "杖刑煞");
        if (in(stem, {TianGan::Yi, TianGan::Ji}) || branch == Chou)
            add_unique(names, "曲脚煞");
    }

    for (const auto [a, b, c, positions] : std::array{
        std::tuple{stems[0], stems[1], stems[2], std::string_view{"年-月-日"}},
        std::tuple{stems[1], stems[2], stems[3], std::string_view{"月-日-时"}}}) {
        std::string_view type;
        if (san_qi_match(a, b, c, type)) {
            result.san_qi.push_back({std::string(type), std::string(positions)});
            for (auto& pillar : result.pillars) add_unique(pillar.names, "三奇贵人");
        }
    }

    for (const std::size_t i : {std::size_t{2}, std::size_t{3}}) {
        const bool month_hit = tong_zi_month_rule(month_branch, branches[i]);
        const bool na_yin_hit = tong_zi_na_yin_rule(year_na_yin, branches[i]);
        if (month_hit || na_yin_hit) add_unique(result.pillars[i].names, "童子煞");
        result.tong_zi.month_rule = result.tong_zi.month_rule || month_hit;
        result.tong_zi.na_yin_rule = result.tong_zi.na_yin_rule || na_yin_hit;
    }
    result.tong_zi.match_count = static_cast<int>(result.tong_zi.month_rule) + static_cast<int>(result.tong_zi.na_yin_rule);
    result.tong_zi.matched = result.tong_zi.match_count > 0;

    const bool has_xu = std::ranges::contains(branches, Xu);
    const bool has_hai = std::ranges::contains(branches, Hai);
    const bool has_chen = std::ranges::contains(branches, Chen);
    const bool has_si = std::ranges::contains(branches, Si);
    result.luo_wang.tian_luo = year_na_yin == WuXing::Huo && has_xu && has_hai;
    result.luo_wang.di_wang = (year_na_yin == WuXing::Shui || year_na_yin == WuXing::Tu) && has_chen && has_si;
    result.luo_wang.gender_note = male ? "男命尤忌天罗" : "女命尤忌地网";
    if (result.luo_wang.tian_luo) result.luo_wang.sub_tags.push_back("龙蛇混杂");
    if (result.luo_wang.di_wang) result.luo_wang.sub_tags.push_back("猪犬侵凌");
    for (std::size_t i = 0; i < branches.size(); ++i) {
        if (result.luo_wang.tian_luo && in(branches[i], {Xu, Hai})) {
            add_unique(result.pillars[i].names, "天罗");
            add_unique(result.pillars[i].names, "天罗地网");
        }
        if (result.luo_wang.di_wang && in(branches[i], {Chen, Si})) {
            add_unique(result.pillars[i].names, "地网");
            add_unique(result.pillars[i].names, "天罗地网");
        }
    }
    for (auto& pillar : result.pillars) {
        std::ranges::stable_sort(pillar.names, {}, [](const std::string& name) {
            return display_rank(name);
        });
    }

    constexpr std::array<std::pair<DiZhi, DiZhi>, 6> chongs{{{Zi, Wu}, {Chou, Wei}, {Yin, Shen}, {Mao, You}, {Chen, Xu}, {Si, Hai}}};
    constexpr std::array<std::pair<DiZhi, DiZhi>, 6> pos{{{Zi, You}, {Chou, Chen}, {Yin, Hai}, {Mao, Wu}, {Si, Shen}, {Wei, Xu}}};
    constexpr std::array<std::pair<DiZhi, DiZhi>, 6> liuhe{{{Zi, Chou}, {Yin, Hai}, {Mao, Xu}, {Chen, You}, {Si, Shen}, {Wu, Wei}}};
    for (std::size_t a = 0; a < 4; ++a) for (std::size_t b = a + 1; b < 4; ++b) {
        const auto x = branches[a], y = branches[b];
        auto add_relation = [&](std::string type, std::string detail) { result.branch_relations.push_back({std::move(type), {a, b}, {std::string(branch_name(x)), std::string(branch_name(y))}, std::move(detail)}); };
        for (const auto& [l, r] : chongs) if (pair(x, y, l, r)) add_relation("chong", std::string(branch_name(x)) + std::string(branch_name(y)) + "冲");
        for (const auto& [l, r] : pos) if (pair(x, y, l, r)) add_relation("po", std::string(branch_name(x)) + std::string(branch_name(y)) + "破");
        for (const auto& [l, r] : liuhe) if (pair(x, y, l, r)) add_relation("he", std::string(branch_name(x)) + std::string(branch_name(y)) + "合");
        if (x == y && in(x, {Chen, Wu, You, Hai})) add_relation("xing", std::string(branch_name(x)) + "自刑");
        if (pair(x, y, Zi, Mao)) add_relation("xing", "子卯刑");
    }
    const std::array<std::pair<std::array<DiZhi, 3>, std::string_view>, 2> xing_groups{{
        {std::array<DiZhi, 3>{Yin, Si, Shen}, "寅巳申无恩刑"},
        {std::array<DiZhi, 3>{Chou, Xu, Wei}, "丑戌未恃势刑"}
    }};
    for (const auto& group : xing_groups) {
        std::vector<std::size_t> hits;
        for (std::size_t i = 0; i < 4; ++i) if (in(branches[i], {group.first[0], group.first[1], group.first[2]})) hits.push_back(i);
        if (hits.size() == 3) result.branch_relations.push_back({"xing", hits, {}, std::string(group.second)});
    }
    constexpr std::array<std::tuple<DiZhi, DiZhi, DiZhi, WuXing>, 4> sanhes{{{Shen, Zi, Chen, WuXing::Shui}, {Hai, Mao, Wei, WuXing::Mu}, {Yin, Wu, Xu, WuXing::Huo}, {Si, You, Chou, WuXing::Jin}}};
    for (const auto& [l, m, r, element] : sanhes) {
        std::vector<std::size_t> hits;
        for (std::size_t i = 0; i < 4; ++i) if (in(branches[i], {l, m, r})) hits.push_back(i);
        if (hits.size() == 3) result.sanhe_ju.push_back({"sanhe", hits, {std::string(branch_name(l)), std::string(branch_name(m)), std::string(branch_name(r))}, std::string(wx_name(element))});
    }
    constexpr std::array<std::pair<TianGan, TianGan>, 5> gan_he{{{TianGan::Jia, TianGan::Ji}, {TianGan::Yi, TianGan::Geng}, {TianGan::Bing, TianGan::Xin}, {TianGan::Ding, TianGan::Ren}, {TianGan::Wu, TianGan::Gui}}};
    constexpr std::array<WuXing, 5> he_elements{WuXing::Tu, WuXing::Jin, WuXing::Shui, WuXing::Mu, WuXing::Huo};
    for (std::size_t a = 0; a < 4; ++a) for (std::size_t b = a + 1; b < 4; ++b) for (std::size_t i = 0; i < gan_he.size(); ++i)
        if (pair(stems[a], stems[b], gan_he[i].first, gan_he[i].second)) result.stem_relations.push_back({{a, b}, {std::string(GanZhi::Mapper::to_zh(stems[a])), std::string(GanZhi::Mapper::to_zh(stems[b]))}, std::string(wx_name(he_elements[i]))});

    for (std::size_t a = 0; a < 4; ++a) for (std::size_t b = a + 1; b < 4; ++b) {
        if (stem_matches_branch(stems[b], branches[a], lu_shen)
            && stem_matches_branch(stems[a], branches[b], lu_shen))
            result.interchanges.push_back({"hulu", {a, b}, {}, "两柱互换禄"});
        const auto ia = static_cast<std::size_t>(stems[a]);
        const auto ib = static_cast<std::size_t>(stems[b]);
        const bool a_gui = (branches[b] == tian_yi_a[ia] || branches[b] == tian_yi_b[ia]);
        const bool b_gui = (branches[a] == tian_yi_a[ib] || branches[a] == tian_yi_b[ib]);
        if (a_gui && b_gui) result.interchanges.push_back({"hugui", {a, b}, {}, "两柱互换贵人"});
        if (branches[a] == yi_ma(branches[b]) && branches[b] == yi_ma(branches[a]))
            result.interchanges.push_back({"huma", {a, b}, {}, "两柱互换驿马"});
    }

    return result;
}

}  // namespace ZhouYi::BaZi::ShenSha
