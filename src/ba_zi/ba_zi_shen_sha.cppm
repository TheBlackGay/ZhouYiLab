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
};

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
};

struct Result {
    std::array<PillarResult, 4> pillars;
    DeXiuDetail de_xiu;
    TongZiDetail tong_zi;
    LuoWangDetail luo_wang;
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

constexpr TianGan yue_de_he(DiZhi month) {
    using enum DiZhi;
    if (in(month, {Yin, Wu, Xu})) return TianGan::Xin;
    if (in(month, {Shen, Zi, Chen})) return TianGan::Ding;
    if (in(month, {Hai, Mao, Wei})) return TianGan::Ji;
    return TianGan::Yi;
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

    constexpr std::array guo_yin{Xu, Hai, Chou, Yin, Chou, Yin, Chen, Si, Wei, Shen};
    constexpr std::array fei_ren{You, Xu, Zi, Chou, Zi, Chou, Mao, Chen, Wu, Wei};
    constexpr std::array hong_yan{Wu, Wu, Yin, Wei, Chen, Chen, Xu, You, Zi, Shen};
    constexpr std::array jin_yu{Chen, Si, Wei, Shen, Wei, Shen, Xu, Hai, Chou, Yin};
    constexpr std::array wen_chang{Si, Wu, Shen, You, Shen, You, Hai, Zi, Yin, Mao};
    constexpr std::array tian_chu{Si, Wu, Si, Wu, Shen, You, Hai, Zi, Yin, Mao};
    constexpr std::array lu_shen{Yin, Mao, Si, Wu, Si, Wu, Shen, You, Hai, Zi};
    constexpr std::array liu_xia{You, Xu, Wei, Shen, Si, Wu, Chen, Mao, Hai, Yin};

    const auto day_void = GanZhi::get_kong_wang(day_stem, day_branch);
    for (const TianGan stem : stems) {
        if (is_de_stem(month_branch, stem)) result.de_xiu.de_stems.push_back(stem);
        if (is_xiu_stem(month_branch, stem)) result.de_xiu.xiu_stems.push_back(stem);
    }
    std::ranges::sort(result.de_xiu.de_stems, {}, [](TianGan value) { return static_cast<int>(value); });
    std::ranges::sort(result.de_xiu.xiu_stems, {}, [](TianGan value) { return static_cast<int>(value); });
    result.de_xiu.de_stems.erase(std::unique(result.de_xiu.de_stems.begin(), result.de_xiu.de_stems.end()), result.de_xiu.de_stems.end());
    result.de_xiu.xiu_stems.erase(std::unique(result.de_xiu.xiu_stems.begin(), result.de_xiu.xiu_stems.end()), result.de_xiu.xiu_stems.end());
    result.de_xiu.matched = !result.de_xiu.de_stems.empty() && !result.de_xiu.xiu_stems.empty();

    const TianGan month_de_he = yue_de_he(month_branch);
    for (std::size_t i = 0; i < branches.size(); ++i) {
        auto& names = result.pillars[i].names;
        const auto branch = branches[i];
        const auto stem = stems[i];
        if (stem_matches_branch(year_stem, branch, guo_yin) || stem_matches_branch(day_stem, branch, guo_yin)) add_unique(names, "国印贵人");
        if (tai_ji(year_stem, branch) || tai_ji(day_stem, branch)) add_unique(names, "太极贵人");
        if (fu_xing(year_stem, branch) || fu_xing(day_stem, branch)) add_unique(names, "福星贵人");
        if (result.de_xiu.matched && (is_de_stem(month_branch, stem) || is_xiu_stem(month_branch, stem))) add_unique(names, "德秀贵人");
        if (branch == day_void[0] || branch == day_void[1]) add_unique(names, "空亡");
        if (stem_matches_branch(day_stem, branch, fei_ren)) add_unique(names, "飞刃");
        if (branch == zai_sha(year_branch) || branch == zai_sha(day_branch)) add_unique(names, "灾煞");
        if (branch == year_branch + 2) add_unique(names, "丧门");
        if (branch == jiang_xing(year_branch) || branch == jiang_xing(day_branch)) add_unique(names, "将星");
        if (stem_matches_branch(day_stem, branch, hong_yan)) add_unique(names, "红艳煞");
        if (stem_matches_branch(year_stem, branch, jin_yu) || stem_matches_branch(day_stem, branch, jin_yu)) add_unique(names, "金舆");
        if (stem_matches_branch(year_stem, branch, wen_chang) || stem_matches_branch(day_stem, branch, wen_chang)) add_unique(names, "文昌贵人");
        if (stem_matches_branch(year_stem, branch, tian_chu) || stem_matches_branch(day_stem, branch, tian_chu)) add_unique(names, "天厨贵人");
        if (tian_de(stem, branch, month_branch)) add_unique(names, "天德贵人");
        if (stem == month_de_he) add_unique(names, "月德合");
        if (stem_matches_branch(day_stem, branch, lu_shen)) add_unique(names, "禄神");
        if (stem_matches_branch(day_stem, branch, liu_xia)) add_unique(names, "流霞");
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
    for (std::size_t i = 0; i < branches.size(); ++i) {
        if (result.luo_wang.tian_luo && in(branches[i], {Xu, Hai})) add_unique(result.pillars[i].names, "天罗");
        if (result.luo_wang.di_wang && in(branches[i], {Chen, Si})) add_unique(result.pillars[i].names, "地网");
    }
    for (auto& pillar : result.pillars) {
        std::ranges::stable_sort(pillar.names, {}, [](const std::string& name) {
            return display_rank(name);
        });
    }

    return result;
}

}  // namespace ZhouYi::BaZi::ShenSha
