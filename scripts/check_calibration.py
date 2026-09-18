#!/usr/bin/env python3
"""校验"校准声明"与"验证套件"是否一致（决策登记 A2 / 架构评审 P2-2 前身）。

用法：
    python3 scripts/check_calibration.py           # CI 常规模式
    python3 scripts/check_calibration.py --strict  # 缺引擎也视为失败（发布检查）

规则：
* 每个工具的 claim 来自 config/platform/tools/<id>.json 的 calibration_status；
* 任何套件执行失败 → 该工具 fail（与 claim 无关，回归必须挡住）；
* claim == calibrated 且存在未执行套件（引擎缺失）→ 常规模式 warn、strict 模式 fail；
* claim == pending / in_progress / experimental 且套件全过 → 提示可考虑升级 claim（不失败）；
* manifest 与套件登记表必须键集合一致，防止新增工具漏登记。
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "config" / "platform" / "tools"
SUITES_PATH = PROJECT_ROOT / "config" / "platform" / "calibration_suites.json"
BUILD_EXAMPLES = PROJECT_ROOT / "build" / "examples"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def engine_available(name):
    return (BUILD_EXAMPLES / name).exists()


def run_python_test(target):
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-q", target],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=600, check=False)
    ok = completed.returncode == 0
    detail = (completed.stderr or completed.stdout).strip().splitlines()
    return ok, (detail[-1] if detail else "")


def run_pattern_catalog(directory):
    completed = subprocess.run(
        [sys.executable, "-c",
         "import sys, json\n"
         "sys.path.insert(0, 'web')\n"
         "from pathlib import Path\n"
         "from ziwei_pattern_engine import load_pattern_catalog, run_catalog_examples\n"
         f"catalog = load_pattern_catalog(Path(r'{directory}'))\n"
         "cases = run_catalog_examples(catalog)\n"
         "failed = [c for c in cases if not c['passed']]\n"
         "print(json.dumps({'patterns': len(catalog['patterns']), 'cases': len(cases), 'failed': [c['case_id'] for c in failed]}))\n"
         "sys.exit(1 if failed else 0)"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=600, check=False)
    ok = completed.returncode == 0
    return ok, (completed.stdout.strip() or completed.stderr.strip().splitlines()[-1:])


def evaluate_tool(tool_id, claim, suites, strict):
    statuses = []
    for suite in suites:
        if suite["type"] == "python_test":
            engine = suite.get("requires_engine")
            if engine and not engine_available(engine):
                statuses.append(("skipped", suite["target"], f"引擎未构建：{engine}"))
                continue
            ok, detail = run_python_test(suite["target"])
            statuses.append(("pass" if ok else "fail", suite["target"], detail))
        elif suite["type"] == "pattern_catalog":
            ok, detail = run_pattern_catalog(suite["directory"])
            statuses.append(("pass" if ok else "fail", f"pattern_catalog:{suite['directory']}", detail))
        else:
            statuses.append(("fail", suite["type"], "未知套件类型"))

    failed = [s for s in statuses if s[0] == "fail"]
    skipped = [s for s in statuses if s[0] == "skipped"]
    # 语义纪律：套件只验证"声明与既有行为回归一致"。行为测试全绿不构成把
    # pending 升级为 calibrated 的依据——升级必须由人工案例校准决策。
    if failed:
        verdict = "FAIL"
    elif skipped and claim == "calibrated" and strict:
        verdict = "FAIL"
    elif skipped and claim == "calibrated":
        verdict = "WARN"
    else:
        verdict = "OK"
    return verdict, statuses


def main():
    strict = "--strict" in sys.argv[1:]
    manifests = {}
    for path in sorted(TOOLS_DIR.glob("*.json")):
        if path.name.startswith(("tool.schema", "_")):
            continue
        raw = load_json(path)
        manifests[raw["id"]] = raw["calibration_status"]
    suites_doc = load_json(SUITES_PATH)
    registered = suites_doc["tools"]

    unknown = set(registered) - set(manifests)
    missing = set(manifests) - set(registered)
    if unknown or missing:
        print("❌ 套件登记与工具清单不一致")
        for tool_id in sorted(unknown):
            print(f"   登记了不存在的工具：{tool_id}")
        for tool_id in sorted(missing):
            print(f"   工具缺少套件登记：{tool_id}（claim={manifests[tool_id]}）")
        return 1

    worst = 0
    for tool_id, claim in manifests.items():
        verdict, statuses = evaluate_tool(tool_id, claim, registered[tool_id]["suites"], strict)
        icon = {"OK": "✅", "WARN": "⚠️ ", "FAIL": "❌"}[verdict]
        print(f"{icon} {tool_id:<11} claim={claim:<12} {verdict}")
        for status, target, detail in statuses:
            if status != "pass":
                print(f"     [{status}] {target}  {str(detail)[:100]}")
        if verdict == "FAIL":
            worst = 1
    if worst == 0:
        print(f"校准声明检查通过（模式：{'strict' if strict else 'permissive'}）"
              "；claim 升级仅由人工案例校准决策，不由本脚本推断")
    return worst


if __name__ == "__main__":
    sys.exit(main())
