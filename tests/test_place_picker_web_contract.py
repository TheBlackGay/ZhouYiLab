"""G1b 出生地点组件前端契约测试（方案 §10「前端契约」，沿用 source-contract 风格）。

断言：区块 id 存在、输出控件 hidden 且无 required、请求体构造零改动、
ARIA combobox 键盘全流程可达、状态徽标有文字、无 hover-only 交互。
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "web" / "astro.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "web" / "astro.js").read_text(encoding="utf-8")
PICKER = (ROOT / "web" / "place-picker.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "place-picker.css").read_text(encoding="utf-8")


class PlacePickerWebContractTests(unittest.TestCase):
    # ---- 区块与输出控件（§5.3 沿用旧 id + 隐藏必填陷阱） ---------------------
    def test_place_section_and_mount_exist(self):
        self.assertIn('id="astro-place-section"', HTML)
        self.assertIn("<h2>出生地点</h2>", HTML)
        self.assertIn("mount: '#astro-place-section'", HTML)

    def test_output_controls_hidden_without_required_and_defaults_untouched(self):
        for element_id, default in (("astro-offset", "480"),
                                    ("astro-lat", "31.2304"),
                                    ("astro-lon", "121.4737")):
            pattern = re.compile(
                r'<input\s+id="%s"\s+type="hidden"\s+value="%s"([^>]*)>' % (element_id, re.escape(default)))
            match = pattern.search(HTML)
            self.assertIsNotNone(match, msg=f"{element_id} 应为 hidden 且保留默认值")
            self.assertNotIn("required", match.group(1),
                             msg="hidden 必填控件会触发 form submit 不可聚焦错误（§5.3）")

    def test_no_legacy_number_inputs_left_in_section(self):
        self.assertNotIn('step="30"', HTML)
        self.assertNotIn("UTC 偏移（分钟）", HTML)
        self.assertNotIn('for="astro-offset"', HTML)

    # ---- 提交契约：payload 构造零改动（§5.3 / §10 验收） ---------------------
    def test_chart_request_body_construction_unchanged(self):
        self.assertIn(
            "utc_offset_minutes:Number(document.querySelector('#astro-offset').value),"
            "location:{latitude:Number(document.querySelector('#astro-lat').value),"
            "longitude:Number(document.querySelector('#astro-lon').value)}",
            SCRIPT,
        )
        # 提交按钮选择器精确化：组件按钮不得被误伤
        self.assertIn('astroForm.querySelector(\'button[type="submit"]\')', SCRIPT)

    def test_prompt_echoes_place_state(self):
        # §4.7：状态原样写进「解析提示词」页签的输入回显
        self.assertIn("birth_place: (window.PlacePickerState && window.PlacePickerState.summary) || null", SCRIPT)
        self.assertIn("window.PlacePickerState", PICKER)

    # ---- 资源接入：跨页共用，不写进 astro.css（§8） --------------------------
    def test_component_assets_loaded(self):
        self.assertIn('<link rel="stylesheet" href="/place-picker.css">', HTML)
        self.assertIn('<script src="/place-picker.js" defer>', HTML)
        for selector in (".place-combobox", ".place-option", ".place-card", ".place-warning"):
            self.assertIn(selector, CSS)
        # 组件样式不引用占星页私有类/id（保证紫微/八字页可直接复用）
        self.assertNotIn("#astro", CSS)
        self.assertNotIn(".astro-", CSS)

    def test_adapter_declares_interface_shape(self):
        for key in ("mount:", "dateInput:", "timeInput:", "mode:", "outputs:", "recentKey:", "popular:"):
            self.assertIn(key, HTML)
        self.assertIn("mode: 'geo+offset'", HTML)
        self.assertIn("createPlacePicker", PICKER)

    # ---- 可访问性与交互（§8 / 验收：键盘可完成全流程） -----------------------
    def test_combobox_keyboard_flow(self):
        for token in ("'combobox'", "'listbox'", "'option'",
                      "aria-expanded", "aria-controls", "aria-activedescendant", "aria-autocomplete",
                      "'ArrowDown'", "'ArrowUp'", "'Enter'", "'Escape'"):
            self.assertIn(token, PICKER)

    def test_live_regions_for_resolution_and_warnings(self):
        self.assertIn("'aria-live', 'polite'", PICKER)
        self.assertIn("role', 'status'", PICKER)

    def test_status_badge_uses_text_not_color_only(self):
        # 状态徽标三态有文字（§4.7 视觉与文案区分，不靠颜色单独传达）
        for label in ("自动推导", "已手动校正", "未解析"):
            self.assertIn(label, PICKER)
        self.assertIn("place-status", PICKER)
        self.assertIn(".place-status", CSS)

    def test_touch_target_and_no_hover_only(self):
        # 候选行 44px 触控高度
        self.assertIn("min-height: 44px", CSS)
        # hover 只能做增强：不得用 :hover 控制显隐/透明（无 hover-only 交互）
        for block in re.finditer(r"([^{}]+):hover[^{]*\{([^}]*)\}", CSS):
            declarations = block.group(2)
            for forbidden in ("display:", "visibility:", "opacity:"):
                self.assertNotIn(forbidden, declarations)

    def test_popular_shortcuts_configured(self):
        # 空输入展示常用城市快捷项；「最近使用」（localStorage）属 G2，G1 不越界
        self.assertIn("popular:", HTML)
        self.assertIn("place-chip", PICKER)
        self.assertIn("常用城市", PICKER)
        self.assertNotIn("localStorage", PICKER)

    # ---- 主路径文案（§4.1/§4.2/§4.3） ----------------------------------------
    def test_no_match_gives_both_exits(self):
        self.assertIn("没有找到", PICKER)
        self.assertIn("手动输入坐标", PICKER)
        self.assertIn("按坐标找最近城市", PICKER)

    def test_card_actions_and_evidence(self):
        self.assertIn("更换", PICKER)
        self.assertIn("微调", PICKER)
        self.assertIn("恢复自动推导", PICKER)
        self.assertIn("为什么？", PICKER)
        self.assertIn("当地实行夏令时", PICKER)
        self.assertIn("起恢复", PICKER)
        self.assertIn("该日期当地不处于夏令时", PICKER)

    def test_tz_dropdown_covers_half_and_quarter_hours(self):
        # §4.3：UTC-12 … UTC+14，含 :30 / :45 档
        self.assertIn("-12; h <= 14", PICKER)
        for minutes in (330, 345, 525, 570, 390, 630):
            self.assertIn(str(minutes), PICKER)


if __name__ == "__main__":
    unittest.main()
