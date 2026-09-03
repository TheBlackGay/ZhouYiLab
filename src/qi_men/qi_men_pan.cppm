// 奇门遁甲排盘算法实现
// 实现完整的排盘逻辑

export module ZhouYi.QiMen.Pan;

import ZhouYi.QiMen;
import ZhouYi.GanZhi;
import fmt;
import std;

/**
 * @brief 奇门排盘算法实现
 */
export namespace ZhouYi::QiMen {

/**
 * @brief 排盘器类
 * 
 * 负责生成完整的奇门盘
 */
class QiMenPanGenerator {
public:
    /**
     * @brief 生成奇门盘
     * 
     * @param solar_term 节气
     * @param tian_gan_day 日天干（0-9）
     * @param di_zhi_day 日地支（0-11）
     * @param tian_gan_hour 时天干（0-9）
     * @param di_zhi_hour 时地支（0-11）
     * @return 生成的奇门盘
     */
    [[nodiscard]] static auto generate_pan(
        SolarTerm solar_term,
        std::uint8_t tian_gan_day,
        std::uint8_t di_zhi_day,
        std::uint8_t tian_gan_hour,
        std::uint8_t di_zhi_hour
    ) -> std::expected<QiMenPan, std::string> {
        
        // 参数验证
        if (tian_gan_day >= 10) {
            return std::unexpected("日天干必须在 0-9 之间");
        }
        if (di_zhi_day >= 12) {
            return std::unexpected("日地支必须在 0-11 之间");
        }
        if (tian_gan_hour >= 10) {
            return std::unexpected("时天干必须在 0-9 之间");
        }
        if (di_zhi_hour >= 12) {
            return std::unexpected("时地支必须在 0-11 之间");
        }
        
        QiMenPan pan{};
        
        // 1. 确定阴阳遁
        pan.dun = get_dun_from_solar_term(solar_term);
        
        // 2. 拆补法按日干支回推符头并确定三元
        pan.yuan = get_yuan_from_gan_zhi(tian_gan_day, di_zhi_day);
        
        // 3. 确定局数
        pan.ju = get_ju_from_solar_term_and_yuan(solar_term, pan.yuan);
        
        // 4. 记录节气
        pan.solar_term = solar_term;
        
        // 5. 排布地盘（地盘天干）
        arrange_di_pan(pan, pan.ju);
        
        // 6. 确定直符和直使
        determine_zhi_fu_and_zhi_shi(pan, tian_gan_hour, di_zhi_hour);
        
        // 7. 排布天盘（天盘天干）
        arrange_tian_pan(pan, tian_gan_hour, di_zhi_hour);
        
        // 7.5. 排布九星（转盘）
        arrange_jiu_xing(pan, tian_gan_hour);
        
        // 8. 排布人盘（人盘八门）
        arrange_ren_pan(pan, tian_gan_hour, di_zhi_hour);
        
        // 9. 排布神盘（八神）
        arrange_shen_pan(pan);
        
        return pan;
    }

private:
    /**
     * @brief 排布地盘天干
     * 
     * 地盘天干按照戊己庚辛壬癸丁丙乙的顺序排列
     * 阳遁从局数宫按九宫数字顺飞，阴遁按九宫数字逆飞
     */
    static void arrange_di_pan(QiMenPan& pan, std::uint8_t ju) {
        // 地盘干固定顺序：戊己庚辛壬癸丁丙乙
        auto gan_seq = get_tian_gan_sequence();
        
        // 初始化所有宫位的基本信息
        for (std::uint8_t i = 1; i <= 9; ++i) {
            Palace p = get_palace_from_number(i);
            auto& palace_info = pan.palaces[i - 1];
            palace_info.palace = p;
            palace_info.star = get_star_at_palace(p);
            palace_info.gate = get_gate_at_palace(p);
            palace_info.di_gan = 0;  // 先初始化
            palace_info.tian_gan = 0;
            palace_info.ren_gan = 0;
            palace_info.lodged_tian_gan.reset();
            palace_info.tian_qin_lodged = false;
        }
        
        int current_gong = ju;
        for (std::size_t i = 0; i < 9; ++i) {
            pan.palaces[static_cast<std::size_t>(current_gong - 1)].di_gan = gan_seq[i];
            current_gong += pan.dun == Dun::Yang ? 1 : -1;
            if (current_gong == 10) current_gong = 1;
            if (current_gong == 0) current_gong = 9;
        }
    }
    
    static constexpr std::uint8_t effective_rotating_palace(
        std::uint8_t palace
    ) noexcept {
        return palace == 5 ? 2 : palace;
    }

    static std::uint8_t find_di_gan_palace(
        const QiMenPan& pan,
        std::uint8_t stem
    ) noexcept {
        for (const auto& palace : pan.palaces) {
            if (palace.di_gan == stem) {
                return effective_rotating_palace(get_number_from_palace(palace.palace));
            }
        }
        return 2;
    }

    static std::size_t ring_index(std::uint8_t palace) noexcept {
        const auto order = get_luo_shu_order();
        for (std::size_t i = 0; i < order.size(); ++i) {
            if (order[i] == palace) return i;
        }
        return 0;
    }
    
    /**
     * @brief 确定直符和直使
     */
    static void determine_zhi_fu_and_zhi_shi(
        QiMenPan& pan,
        std::uint8_t tian_gan_hour,
        std::uint8_t di_zhi_hour
    ) {
        // 时家奇门以时柱所在六甲旬确定旬首六仪
        JiaXun jia_xun = get_jia_xun_from_gan_zhi(tian_gan_hour, di_zhi_hour);
        
        // 获取旬首对应的六仪
        std::uint8_t liu_yi = get_liu_yi_from_jia_xun(jia_xun);
        
        // 在地盘上查找六仪的位置 = 值符宫
        std::uint8_t zhi_fu_gong = 0;
        for (std::size_t i = 0; i < 9; ++i) {
            if (pan.palaces[i].di_gan == liu_yi) {
                // 找到了旬首六仪在地盘上的位置
                zhi_fu_gong = effective_rotating_palace(
                    get_number_from_palace(pan.palaces[i].palace)
                );
                const auto effective_palace = get_palace_from_number(zhi_fu_gong);
                
                // 值符星 = 该宫位原位的九星
                pan.zhi_fu_star = get_star_at_palace(effective_palace);
                
                // 值使门 = 该宫位原位的八门
                pan.zhi_shi_gate = get_gate_at_palace(effective_palace);
                
                pan.zhi_fu_palace = effective_palace;
                pan.zhi_fu_origin_palace = effective_palace;
                pan.zhi_shi_palace = effective_palace;
                break;
            }
        }
        
        // 如果没找到（理论上不应该发生），默认寄坤2宫
        if (zhi_fu_gong == 0) {
            zhi_fu_gong = 2;
            pan.zhi_fu_palace = Palace::SouthWest;
            pan.zhi_fu_origin_palace = Palace::SouthWest;
            pan.zhi_fu_star = get_star_at_palace(Palace::SouthWest);
            pan.zhi_shi_gate = get_gate_at_palace(Palace::SouthWest);
            pan.zhi_shi_palace = Palace::SouthWest;
        }
    }
    
    /**
     * @brief 根据天干地支确定旬首
     * 
     * 六十甲子分六旬：
     * - 甲子旬：甲子～癸酉（10个）
     * - 甲戌旬：甲戌～癸未（10个）
     * - 甲申旬：甲申～癸己（10个）
     * - 甲午旬：甲午～癸卯（10个）
     * - 甲辰旬：甲辰～癸丑（10个）
     * - 甲寅旬：甲寅～癸亥（10个）
     */
    static constexpr JiaXun get_jia_xun_from_gan_zhi(
        std::uint8_t tian_gan,
        std::uint8_t di_zhi
    ) noexcept {
        const auto xun_head_branch = static_cast<std::uint8_t>(
            (di_zhi + 12 - tian_gan) % 12
        );
        switch (xun_head_branch) {
            case 0: return JiaXun::JiaZi;
            case 10: return JiaXun::JiaXu;
            case 8: return JiaXun::JiaShen;
            case 6: return JiaXun::JiaWu;
            case 4: return JiaXun::JiaChen;
            case 2: return JiaXun::JiaYin;
            default:
                return JiaXun::JiaZi;
        }
    }

    static constexpr std::uint8_t get_xun_head_branch(JiaXun xun) noexcept {
        switch (xun) {
            case JiaXun::JiaZi: return 0;
            case JiaXun::JiaXu: return 10;
            case JiaXun::JiaShen: return 8;
            case JiaXun::JiaWu: return 6;
            case JiaXun::JiaChen: return 4;
            case JiaXun::JiaYin: return 2;
        }
        return 0;
    }
    
    /**
     * @brief 排布天盘天干（转盘法）
     * 
     * 天盘整体转动，使值符星落到时干所在宫
     */
    static void arrange_tian_pan(QiMenPan& pan, std::uint8_t tian_gan_hour, std::uint8_t di_zhi_hour) {
        const auto jia_xun = get_jia_xun_from_gan_zhi(tian_gan_hour, di_zhi_hour);
        const auto effective_hour_stem = tian_gan_hour == 0
            ? get_liu_yi_from_jia_xun(jia_xun)
            : tian_gan_hour;
        const auto source_gong = get_number_from_palace(pan.zhi_fu_origin_palace);
        const auto target_gong = find_di_gan_palace(pan, effective_hour_stem);
        const auto steps = (ring_index(target_gong) - ring_index(source_gong) + 8) % 8;
        const auto luo_shu = get_luo_shu_order();
        
        // 4. 天盘整体转动
        // 天盘干就是地盘干整体移动
        std::array<std::uint8_t, 9> temp_tian_gan{};
        
        for (std::size_t i = 0; i < 8; ++i) {
            std::uint8_t di_pan_gong = luo_shu[i];
            std::uint8_t di_pan_gan = pan.palaces[di_pan_gong - 1].di_gan;
            
            const std::size_t tian_pan_idx = (i + steps) % 8;
            
            std::uint8_t tian_pan_gong = luo_shu[tian_pan_idx];
            temp_tian_gan[tian_pan_gong - 1] = di_pan_gan;
        }
        
        // 中宫天盘干单独保留；转盘判宫时寄坤二宫
        temp_tian_gan[4] = pan.palaces[4].di_gan;
        
        // 应用到宫位
        for (std::size_t i = 0; i < 9; ++i) {
            pan.palaces[i].tian_gan = temp_tian_gan[i];
        }
        pan.zhi_fu_palace = get_palace_from_number(target_gong);
    }
    
    /**
     * @brief 排布九星（转盘法）
     * 
     * 九星按洛书顺序从值符宫整体转动到时干落宫
     * 天禽留中，参与转盘判宫时寄坤二宫
     */
    static void arrange_jiu_xing(QiMenPan& pan, std::uint8_t tian_gan_hour) {
        static_cast<void>(tian_gan_hour);
        const auto source_gong = get_number_from_palace(pan.zhi_fu_origin_palace);
        const auto target_gong = get_number_from_palace(pan.zhi_fu_palace);
        const auto steps = (ring_index(target_gong) - ring_index(source_gong) + 8) % 8;
        const auto luo_shu = get_luo_shu_order();
        
        // 4. 九星整体转动
        std::array<Star, 9> temp_stars;
        
        for (std::size_t i = 0; i < 8; ++i) {
            std::uint8_t original_gong = luo_shu[i];
            Palace original_palace = get_palace_from_number(original_gong);
            Star original_star = get_star_at_palace(original_palace);
            
            // 转动后的宫位
            std::size_t new_idx = (i + steps) % 8;
            std::uint8_t new_gong = luo_shu[new_idx];
            
            temp_stars[new_gong - 1] = original_star;
        }
        
        // 天禽在中宫，转盘判宫时寄坤二宫
        temp_stars[4] = Star::TianQin;
        
        // 应用到宫位
        for (std::size_t i = 0; i < 9; ++i) {
            pan.palaces[i].star = temp_stars[i];
            if (temp_stars[i] == Star::TianRui) {
                pan.palaces[i].tian_qin_lodged = true;
                pan.palaces[i].lodged_tian_gan = pan.palaces[4].di_gan;
            }
        }
    }
    
    /**
     * @brief 排布人盘八门（转盘法）
     * 
     * 值使从旬首宫起，从旬首地支数到当前时支：阳顺阴逆走九宫数字，
     * 路径包含中五；落中五时寄坤二，再带动八门在外围八宫整体转盘
     */
    static void arrange_ren_pan(
        QiMenPan& pan,
        std::uint8_t tian_gan_hour,
        std::uint8_t di_zhi_hour
    ) {
        const auto jia_xun = get_jia_xun_from_gan_zhi(tian_gan_hour, di_zhi_hour);
        const auto branch_steps = static_cast<int>(
            (di_zhi_hour + 12 - get_xun_head_branch(jia_xun)) % 12
        );
        const auto source_gong = get_number_from_palace(pan.zhi_fu_origin_palace);
        int target_gong = static_cast<int>(source_gong)
            + (pan.dun == Dun::Yang ? branch_steps : -branch_steps);
        target_gong = (target_gong - 1) % 9;
        if (target_gong < 0) target_gong += 9;
        target_gong = effective_rotating_palace(
            static_cast<std::uint8_t>(target_gong + 1)
        );
        const auto steps = (
            ring_index(static_cast<std::uint8_t>(target_gong))
            - ring_index(source_gong) + 8
        ) % 8;
        const auto luo_shu = get_luo_shu_order();
        pan.zhi_shi_palace = get_palace_from_number(
            static_cast<std::uint8_t>(target_gong)
        );
        
        // 4. 八门整体转动
        std::array<Gate, 9> temp_gates;
        
        for (std::size_t i = 0; i < 8; ++i) {
            std::uint8_t original_gong = luo_shu[i];
            Palace original_palace = get_palace_from_number(original_gong);
            Gate original_gate = get_gate_at_palace(original_palace);
            
            const std::size_t new_idx = (i + steps) % 8;
            
            std::uint8_t new_gong = luo_shu[new_idx];
            temp_gates[new_gong - 1] = original_gate;
        }
        
        // 中宫无门
        temp_gates[4] = Gate::Jing_Center;  // 中宫(5)无门
        
        // 应用到宫位
        for (std::size_t i = 0; i < 9; ++i) {
            pan.palaces[i].gate = temp_gates[i];
        }
    }
    
    /**
     * @brief 排布神盘八神
     * 
     * 八神根据直符宫和阴阳遁进行排列
     * 阳遁：从值符宫开始顺时针排列
     * 阴遁：从值符宫开始逆时针排列
     */
    static void arrange_shen_pan(QiMenPan& pan) {
        // 八神顺序：值符、腾蛇、太阴、六合、白虎、玄武、九地、九天
        std::array<Spirit, 8> spirit_seq = {
            Spirit::ZhiFu, Spirit::TengShe, Spirit::TaiYin, Spirit::LiuHe,
            Spirit::BaiHu, Spirit::XuanWu, Spirit::JiuDi, Spirit::JiuTian
        };
        
        // 获取值符宫的数字
        std::uint8_t zhi_fu_gong = get_number_from_palace(pan.zhi_fu_palace);
        
        // 根据阴阳遁选择排列方向
        std::array<std::uint8_t, 8> gong_order;
        if (pan.dun == Dun::Yang) {
            // 阳遁顺时针：1→8→3→4→9→2→7→6
            gong_order = get_luo_shu_order();
        } else {
            // 阴遁逆时针：1→6→7→2→9→4→3→8
            gong_order = get_luo_shu_reverse_order();
        }
        
        // 找到值符宫在宫位顺序中的位置
        std::size_t zhi_fu_idx = 0;
        for (std::size_t i = 0; i < gong_order.size(); ++i) {
            if (gong_order[i] == zhi_fu_gong) {
                zhi_fu_idx = i;
                break;
            }
        }
        
        // 按顺序排列八神
        std::array<Spirit, 9> temp_spirits;
        
        for (std::size_t i = 0; i < 8; ++i) {
            std::size_t gong_idx = (zhi_fu_idx + i) % 8;
            std::uint8_t gong_num = gong_order[gong_idx];
            temp_spirits[gong_num - 1] = spirit_seq[i];
        }
        
        // 中宫无神
        temp_spirits[4] = Spirit::None;
        
        // 应用到宫位
        for (std::size_t i = 0; i < 9; ++i) {
            pan.palaces[i].spirit = temp_spirits[i];
        }
    }
};

/**
 * @brief 格式化输出奇门盘
 */
[[nodiscard]] inline auto format_qi_men_pan(const QiMenPan& pan) -> std::string {
    using namespace ZhouYi::GanZhi;
    
    std::string result;
    
    result += fmt::format("奇门遁甲排盘\n");
    result += fmt::format("节气: {}\n", solar_term_name(pan.solar_term));
    result += fmt::format("阴阳遁: {}\n", pan.dun == Dun::Yang ? "阳遁" : "阴遁");
    result += fmt::format("三元: ");
    switch (pan.yuan) {
        case Yuan::Shang: result += "上元"; break;
        case Yuan::Zhong: result += "中元"; break;
        case Yuan::Xia: result += "下元"; break;
    }
    result += fmt::format("\n局数: {}\n", pan.ju);
    result += fmt::format("直符: {}\n", star_name(pan.zhi_fu_star));
    result += fmt::format("直使: {}\n", gate_name(pan.zhi_shi_gate));
    
    result += "\n══════════════════════════\n";
    result += "九宫排盘：\n";
    result += "══════════════════════════\n";
    
    // 九宫格布局：西北(6) 北(1) 东北(8)
    //             西(7)   中(5)  东(3)
    //             西南(2) 南(9) 东南(4)
    std::array<std::uint8_t, 9> gong_layout = {6, 1, 8, 7, 5, 3, 2, 9, 4};
    
    // 输出九宫格
    for (std::size_t row = 0; row < 3; ++row) {
        // 每个宫位显示5行信息
        
        // 第1行：宫名 + 九星
        for (std::size_t col = 0; col < 3; ++col) {
            std::uint8_t gong_num = gong_layout[row * 3 + col];
            const auto& info = pan.palaces[gong_num - 1];
            auto palace_str = std::string(palace_name(info.palace));
            auto star_str = std::string(star_name(info.star));
            // 宫名固定4个字符宽度，九星固定4个字符宽度
            result += fmt::format("║{:<4}{:>4}", palace_str, star_str);
        }
        result += "║\n";
        
        // 第2行：八门
        for (std::size_t col = 0; col < 3; ++col) {
            std::uint8_t gong_num = gong_layout[row * 3 + col];
            const auto& info = pan.palaces[gong_num - 1];
            auto gate_str = std::string(gate_name(info.gate));
            result += fmt::format("║ {:<7}", gate_str);
        }
        result += "║\n";
        
        // 第3行：八神
        for (std::size_t col = 0; col < 3; ++col) {
            std::uint8_t gong_num = gong_layout[row * 3 + col];
            const auto& info = pan.palaces[gong_num - 1];
            auto spirit_str = std::string(spirit_name(info.spirit));
            result += fmt::format("║ {:<7}", spirit_str);
        }
        result += "║\n";
        
        // 第4行：地盘干
        for (std::size_t col = 0; col < 3; ++col) {
            std::uint8_t gong_num = gong_layout[row * 3 + col];
            const auto& info = pan.palaces[gong_num - 1];
            auto di_gan_str = std::string(Mapper::to_zh(static_cast<TianGan>(info.di_gan)));
            result += fmt::format("║地:{:<6}", di_gan_str);
        }
        result += "║\n";
        
        // 第5行：天盘干
        for (std::size_t col = 0; col < 3; ++col) {
            std::uint8_t gong_num = gong_layout[row * 3 + col];
            const auto& info = pan.palaces[gong_num - 1];
            auto tian_gan_str = std::string(Mapper::to_zh(static_cast<TianGan>(info.tian_gan)));
            result += fmt::format("║天:{:<6}", tian_gan_str);
        }
        result += "║\n";
        
        // 行分隔线
        if (row < 2) {
            result += "╠════════╬════════╬════════╣\n";
        }
    }
    
    result += "══════════════════════════\n";
    
    return result;
}

}  // namespace ZhouYi::QiMen
