"""四工具 + 大六壬交叉的 meta.rule_profile 规则口径契约测试。

覆盖（全部 CLI 参数化，二进制未构建时跳过）：
* 每个 operation 输出携带 meta.rule_profile，结构为
  {profile_version, calibration_status, rules}；
* profile_version 命名必须为 "<tool>-rules/<ver>"；本任务交付的四工具
  （zi_wei/qi_men/ba_zi/liu_yao）锁定精确版本号、状态与 rules 键集合，
  大六壬样板为宽松交叉（锁命名前缀与通用结构，其口径演进由自身契约测试管理）；
* calibration_status ∈ {calibrated, in_progress, pending}；
* rules 非空，且每条值为含中文字符的字符串（口径描述面向中文使用者）；
* 五工具（含大六壬交叉）的 calibration_status 与 README「算法校准状态」表一致；
* 紫微 time_correction/chart/fortune/symbols 全部 operation 均挂载口径标识；
* 旧字段集合保持存在（纯增量约束，与 test_da_liu_ren_engine_contract 同风格）。
"""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "build" / "examples"

# calibration_status 与 README「算法校准状态」表（README.md 第 17-23 行的表格）的映射：
#   紫微斗数 已校准 / 奇门遁甲 已校准 / 八字 校准中 / 六爻 待校准 / 大六壬 待校准。
README_TO_CLAIM = {"已校准": "calibrated", "校准中": "in_progress", "待校准": "pending"}
README_ROWS = {"紫微斗数": "zi_wei_web_cli", "奇门遁甲": "qi_men_web_cli",
               "八字": "ba_zi_web_cli", "六爻": "liu_yao_web_cli", "大六壬": "da_liu_ren_web_cli"}

# 每个 CLI：最小合法请求、锁定的 profile_version、calibration_status、rules 精确键集合。
# 大六壬（样板）为交叉校验：其规则口径由内核 to_json 维护且正被并行任务升级，
# 故只锁命名前缀与通用结构（regex/中文/README 一致），不锁版本号与键集合，
# 避免把并行任务的移动目标误锁死。其余四工具（本任务交付）为精确锁定。
TOOL_CONTRACTS = {
    "zi_wei_web_cli": {
        "request": {"operation": "chart",
                    "birth": {"year": 1994, "month": 12, "day": 8, "hour": 9, "minute": 5,
                              "second": 0, "gender": "male"},
                    "time_correction": {"mode": "standard_time"}},
        "profile_version": "ziwei-rules/2.0",
        "calibration_status": "calibrated",
        "rules_keys": {"true_solar_time", "ming_gong_shen_gong", "zi_wei_star_method",
                       "si_hua", "brightness", "fortune_layers", "ge_ju_note"},
        "legacy_top_level": {"birth_time", "da_xian", "ge_ju", "gender", "lunar_date",
                             "lunar_hour", "ming_gong_index", "palaces", "shen_gong_index",
                             "si_hua", "si_zhu", "solar_date", "wu_xing_ju"},
    },
    "qi_men_web_cli": {
        "request": {"calendar": "solar",
                    "date": {"year": 2026, "month": 9, "day": 2, "hour": 20, "minute": 20}},
        "profile_version": "qi-men-rules/1.0",
        "calibration_status": "calibrated",
        "rules_keys": {"qi_ju_method", "shichen_scope", "pan_method", "zhi_fu_zhi_shi",
                       "jia_hidden", "zhong_gong_ji_kun", "shen_sha_set"},
        "legacy_top_level": {"method", "method_zh", "center_lodging", "solar_date", "lunar_date",
                             "ba_zi", "dun", "yuan", "ju", "solar_term", "zhi_fu_star",
                             "zhi_shi_gate", "zhi_fu_palace", "zhi_shi_palace", "palaces"},
    },
    "ba_zi_web_cli": {
        "request": {"date": {"year": 1994, "month": 12, "day": 8, "hour": 9, "minute": 5}},
        "profile_version": "bazi-rules/0.1",
        "calibration_status": "in_progress",
        "rules_keys": {"four_pillars", "true_solar_time", "shi_shen", "cang_gan",
                       "twelve_stages", "xun_kong_per_pillar", "na_yin", "shen_sha_basis",
                       "luck_pillars", "boundary_note"},
        "legacy_top_level": {"ba_zi", "is_male", "birth_date", "da_yun", "shi_shen",
                             "calendar", "gender", "birth_time", "solar_date", "lunar_date",
                             "chart_lunar_date", "pillars", "shen_sha_summary", "day_master",
                             "xun_kong"},
    },
    "liu_yao_web_cli": {
        "request": {"calendar": "solar", "date": {"year": 2025, "month": 4, "day": 7, "hour": 17},
                    "hexagram_code": "110001", "changing_lines": [1]},
        "profile_version": "liu-yao-rules/0.2",
        "calibration_status": "in_progress",
        "rules_keys": {"input_format", "na_jia", "shi_ying", "liu_qin_basis", "six_spirits",
                       "fu_shen", "wang_shuai", "bian_gua", "state_tags_scope"},
        "legacy_top_level": {"ba_zi", "ben_gua_name", "bian_gua_name", "shen_sa", "yao"},
    },
    # 大六壬样板交叉校验（宽松档）：命名前缀 + 结构 + README 一致性。
    "da_liu_ren_web_cli": {
        "request": {"calendar": "solar", "date": {"year": 2024, "month": 10, "day": 13, "hour": 14}},
        "version_prefix": "da-liu-ren-rules/",
        "legacy_top_level": {"ba_zi", "yue_jiang", "gui_ren", "is_day", "si_ke", "san_chuan",
                             "tian_di_pan", "shen_sha", "gua_ti"},
    },
}

PROFILE_VERSION_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*-rules/\d+\.\d+$")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def run_cli(binary: str, payload: dict):
    """运行网页 JSON CLI；二进制不存在时返回 None（由调用方 skipTest）。"""
    path = BIN_DIR / binary
    if not path.exists():
        return None
    completed = subprocess.run([str(path)], input=json.dumps(payload),
                               capture_output=True, text=True, timeout=30, cwd=ROOT,
                               check=False)
    if completed.returncode != 0:
        raise AssertionError(f"{binary} 退出码 {completed.returncode}: {completed.stdout[:200]}")
    return json.loads(completed.stdout)


def read_readme_calibration_table() -> dict:
    """解析 README「算法校准状态」表 → {算法名: 校准状态文本}。"""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("## 算法校准状态", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for algo, status, _ in re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$",
                                      section, re.MULTILINE):
        if algo in ("算法", "") or set(algo) <= {"-", " "}:
            continue
        rows[algo] = status
    return rows


class RuleProfileContractTests(unittest.TestCase):
    def test_readme_calibration_table_parses(self):
        rows = read_readme_calibration_table()
        for algo in README_ROWS:
            self.assertIn(algo, rows, f"README 校准表缺少 {algo} 行")
            self.assertIn(rows[algo], README_TO_CLAIM, f"README {algo} 状态 {rows[algo]} 未知")

    def test_cli_claims_match_readme(self):
        rows = read_readme_calibration_table()
        for algo, binary in README_ROWS.items():
            with self.subTest(cli=binary):
                data = run_cli(binary, TOOL_CONTRACTS[binary]["request"])
                if data is None:
                    self.skipTest(f"{binary} 尚未构建")
                claimed = data["meta"]["rule_profile"]["calibration_status"]
                self.assertEqual(claimed, README_TO_CLAIM[rows[algo]],
                                 f"{binary} 的 calibration_status 与 README「{algo}·{rows[algo]}」不一致")

    def test_profile_structure_for_every_cli(self):
        for binary, contract in TOOL_CONTRACTS.items():
            with self.subTest(cli=binary):
                data = run_cli(binary, contract["request"])
                if data is None:
                    self.skipTest(f"{binary} 尚未构建")
                profile = data["meta"]["rule_profile"]
                self.assertEqual(set(profile), {"profile_version", "calibration_status", "rules"})
                # 命名规范："<tool>-rules/<ver>"。
                self.assertRegex(profile["profile_version"], PROFILE_VERSION_RE)
                if "version_prefix" in contract:
                    # 宽松交叉档（大六壬样板）：只锁前缀，版本与键集合归其自身契约测试管理。
                    self.assertTrue(
                        profile["profile_version"].startswith(contract["version_prefix"]),
                        f"{binary} profile_version 前缀应为 {contract['version_prefix']}")
                else:
                    self.assertEqual(profile["profile_version"], contract["profile_version"])
                # 校准声明合法值。
                self.assertIn(profile["calibration_status"], {"calibrated", "in_progress", "pending"})
                rules = profile["rules"]
                if "rules_keys" in contract:
                    self.assertEqual(profile["calibration_status"], contract["calibration_status"])
                    # rules 键集合锁定（防口径静默漂移）。
                    self.assertEqual(set(rules), contract["rules_keys"])
                # rules 非空、每条为非空中文字符串。
                self.assertTrue(rules, f"{binary} rules 为空")
                for key, text in rules.items():
                    self.assertIsInstance(text, str, f"{binary} rules[{key}] 非字符串")
                    self.assertTrue(text.strip(), f"{binary} rules[{key}] 为空")
                    self.assertTrue(CJK_RE.search(text), f"{binary} rules[{key}] 缺少中文描述")
                # 纯增量：旧顶层字段集合仍在。
                self.assertTrue(contract["legacy_top_level"] <= set(data),
                                f"{binary} 旧字段缺失: {contract['legacy_top_level'] - set(data)}")

    def test_zi_wei_mounts_profile_on_all_operations(self):
        base = {"birth": {"year": 1994, "month": 12, "day": 8, "hour": 9, "minute": 5,
                          "second": 0, "gender": "male"}}
        requests = {
            "time_correction": dict(base, operation="time_correction",
                                    time_correction={"mode": "true_solar_time",
                                                     "longitude": 116.4,
                                                     "standard_meridian": 120.0,
                                                     "daylight_saving_minutes": 0}),
            "chart": dict(base, operation="chart", time_correction={"mode": "standard_time"}),
            "fortune": dict(base, operation="fortune",
                            time_correction={"mode": "standard_time"},
                            target={"year": 2020, "month": 1, "day": 1, "hour": 10,
                                    "minute": 0, "second": 0, "age": 27}),
            "symbols": {"operation": "symbols"},
        }
        for operation, payload in requests.items():
            with self.subTest(operation=operation):
                data = run_cli("zi_wei_web_cli", payload)
                if data is None:
                    self.skipTest("zi_wei_web_cli 尚未构建")
                profile = data["meta"]["rule_profile"]
                self.assertEqual(profile["profile_version"],
                                 TOOL_CONTRACTS["zi_wei_web_cli"]["profile_version"])
                self.assertTrue(profile["rules"])


if __name__ == "__main__":
    unittest.main()
