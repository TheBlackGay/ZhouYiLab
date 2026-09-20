"""六壬 2.1.0 天地盘可视化契约（dlr-plate.js）。

覆盖（对齐平台"三处一致 + 引擎字段锁"风格）：
* 方位环：盖天说南上——午居正上、子正下、卯左酉右，顺时针
  午未申酉戌亥子丑寅卯辰巳（几何错误一眼可见，必须锁死）；
* 引擎字段依赖锁：渲染器读取的每个字段（tian_di_pan 十二宫位/上神排列唯一性、
  san_chuan details 的 stage 枚举、旬空、月将/贵人/昼夜）在内核输出中真实存在，
  三传地支必落在天盘十二上神之内；
* 文案纪律：渲染器静态文案禁吉凶断语词，着色注记声明"结构性、不表吉凶"；
* 页面接线：双容器 + 脚本引入 + render 触发，一处不缺。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DLR_CLI = ROOT / "build" / "examples" / "da_liu_ren_web_cli"
PLATE_JS = (ROOT / "web" / "dlr-plate.js").read_text(encoding="utf-8")
PAGE_JS = (ROOT / "web" / "da-liu-ren.js").read_text(encoding="utf-8")
PAGE_HTML = (ROOT / "web" / "da-liu-ren.html").read_text(encoding="utf-8")

BRANCHES = list("子丑寅卯辰巳午未申酉戌亥")


class DlrPlateContractTests(unittest.TestCase):
    def exported_wheel(self):
        match = re.search(r"EARTHWHEEL_CLOCKWISE = \[(.*?)\]", PLATE_JS)
        self.assertIsNotNone(match, "组件未导出 EARTHWHEEL_CLOCKWISE")
        return re.findall(r"'(.)'", match.group(1))

    def test_south_up_clockwise_wheel(self):
        wheel = self.exported_wheel()
        self.assertEqual(wheel, list("午未申酉戌亥子丑寅卯辰巳"))
        self.assertEqual(wheel.index("午"), 0)      # 正上方（屏幕 0°）
        self.assertEqual(wheel.index("子"), 6)      # 正下方
        self.assertEqual(wheel.index("卯"), 9)      # 屏幕 270° 顺时针=左（东）
        self.assertEqual(wheel.index("酉"), 3)      # 右（西）

    def test_engine_fields_renderer_relies_on(self):
        if not DLR_CLI.exists():
            self.skipTest("da_liu_ren_web_cli 未构建")
        completed = subprocess.run(
            [str(DLR_CLI)], input=json.dumps({"calendar": "solar",
             "date": {"year": 2025, "month": 11, "day": 3, "hour": 16}}),
            capture_output=True, text=True, timeout=30, cwd=ROOT, check=False)
        data = json.loads(completed.stdout)
        pan = data["tian_di_pan"]
        self.assertEqual(sorted(s["position"] for s in pan), sorted(BRANCHES), "地盘十二位必须齐全")
        heavens = [s["tian_pan"] for s in pan]
        self.assertEqual(sorted(heavens), sorted(BRANCHES), "天盘上神必须是十二支的一个排列")
        for slot in pan:
            self.assertIn("dun_gan", slot)
            self.assertIn("shen_jiang", slot)
        stages = {d["stage"] for d in data["san_chuan"]["details"]}
        self.assertEqual(stages, {"chu_chuan", "zhong_chuan", "mo_chuan"})
        # 三传徽章前提：三传地支落在天盘上神集合内（按上神找位）
        for d in data["san_chuan"]["details"]:
            self.assertIn(d["branch"], heavens, f"{d['stage']} {d['branch']} 不在天盘上神中")
        self.assertIn("xun_kong_1", data["ba_zi"])
        self.assertIn("is_day", data)

    def test_renderer_static_text_no_auspice_claims(self):
        banned = ("主吉", "主凶", "大吉", "必凶", "必胜", "必败", "断曰")
        for word in banned:
            self.assertNotIn(word, PLATE_JS)
        self.assertIn("不表吉凶", PLATE_JS)   # 淡彩注记须自释结构性

    def test_page_wired(self):
        self.assertIn('id="dlr-plate-beginner"', PAGE_HTML)
        self.assertIn('id="dlr-plate-pro"', PAGE_HTML)
        self.assertIn("/dlr-plate.js", PAGE_HTML)
        self.assertIn("window.DlrPlate", PAGE_JS)
        self.assertIn("renderDlrPlates(data)", PAGE_JS)
        # 双容器都在渲染触发点覆盖内
        self.assertIn("#dlr-plate-beginner", PAGE_JS)
        self.assertIn("#dlr-plate-pro", PAGE_JS)


if __name__ == "__main__":
    unittest.main()
