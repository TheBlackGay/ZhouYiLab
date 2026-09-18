"""P0-1 工具注册表测试：清单校验、路由派生、回退与内建/外置一致性。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from tool_registry import (  # noqa: E402
    MANIFEST_SCHEMA_VERSION,
    ToolRegistryError,
    builtin_tools,
    load_tool_registry,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "config" / "platform" / "tools"
SERVER_SOURCE = (PROJECT_ROOT / "web" / "server.py").read_text(encoding="utf-8")


def write_manifest(directory, raw):
    path = Path(directory) / f"{raw['id']}.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return path


class ToolRegistryLoadingTests(unittest.TestCase):
    def test_repo_manifests_load_and_match_builtin(self):
        """外置清单是权威运行配置；与内建默认必须零漂移（直到 P1 移除内建）。"""
        external = load_tool_registry(PROJECT_ROOT)
        builtin = load_tool_registry(PROJECT_ROOT, directory=PROJECT_ROOT / "__missing__")
        self.assertEqual(external.source, "config/platform/tools")
        self.assertEqual(builtin.source, "builtin")
        external_summary = external.summary(PROJECT_ROOT)
        builtin_summary = builtin.summary(PROJECT_ROOT)
        # registry_source 本应不同，其余（工具集、路由、校准状态）必须一致
        external_summary.pop("registry_source")
        builtin_summary.pop("registry_source")
        self.assertEqual(builtin_summary, external_summary)

    def test_missing_directory_falls_back_to_builtin(self):
        registry = load_tool_registry(PROJECT_ROOT, directory=PROJECT_ROOT / "__missing__")
        self.assertEqual(len(registry.tools), 7)

    def test_empty_directory_fails_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".gitkeep").touch()
            with self.assertRaises(ToolRegistryError):
                load_tool_registry(PROJECT_ROOT, directory=Path(tmp))

    def test_invalid_manifests_rejected(self):
        base = dict(builtin_tools()[1])  # qimen
        cases = []
        bad_id = dict(base, id="Bad-Id")
        cases.append(bad_id)
        bad_calibration = dict(base, calibration_status="verified")
        cases.append(bad_calibration)
        unknown_handler = dict(base, routes=[
            {"method": "POST", "path": "/api/v1/qimen/charts", "handler": "magic"}])
        cases.append(unknown_handler)
        escape_engine = dict(base, engine_cli="../outside/build/qi_men_web_cli")
        cases.append(escape_engine)
        bad_prefix = dict(base, api_prefixes=["/qimen/"])
        cases.append(bad_prefix)
        for raw in cases:
            with tempfile.TemporaryDirectory() as tmp:
                write_manifest(tmp, raw)
                with self.assertRaises(ToolRegistryError):
                    load_tool_registry(PROJECT_ROOT, directory=Path(tmp))

    def test_duplicate_route_across_tools_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = dict(builtin_tools()[1])
            clone = dict(first, id="qimen_clone", name="奇门克隆")
            write_manifest(tmp, first)
            write_manifest(tmp, clone)
            with self.assertRaises(ToolRegistryError):
                load_tool_registry(PROJECT_ROOT, directory=Path(tmp))


class ToolRegistryDispatchTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_tool_registry(PROJECT_ROOT)

    def test_only_consolidated_routes_are_routable(self):
        routable = sorted(self.registry._routable)
        self.assertEqual(routable, [
            ("GET", "/api/v1/da-liu-ren/glossary"),
            ("POST", "/api/v1/bazi/charts"),
            ("POST", "/api/v1/da-liu-ren/charts"),
            ("POST", "/api/v1/liu-yao/charts"),
            ("POST", "/api/v1/qimen/charts"),
        ])
        self.assertIsNone(self.registry.resolve("POST", "/api/v1/ziwei/charts"))
        self.assertIsNone(self.registry.resolve("POST", "/api/v1/astro/charts"))
        self.assertIsNone(self.registry.resolve("GET", "/api/v1/qimen/charts"))
        # 平台内建端点不得被清单抢占
        self.assertIsNone(self.registry.resolve("GET", "/api/v1/health"))
        self.assertIsNone(self.registry.resolve("GET", "/api/v1/tools"))

    def test_static_config_options_validated(self):
        base = dict(builtin_tools()[4])  # da_liu_ren
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(base, routes=[{
                "method": "GET", "path": "/api/v1/da-liu-ren/glossary",
                "handler": "static_config", "options": {"config_path": "../etc/passwd"}}])
            write_manifest(tmp, bad)
            with self.assertRaises(ToolRegistryError):
                load_tool_registry(PROJECT_ROOT, directory=Path(tmp))
            outside = dict(base, routes=[{
                "method": "GET", "path": "/api/v1/da-liu-ren/glossary",
                "handler": "static_config",
                "options": {"config_path": "web/server.py"}}])
            write_manifest(tmp, outside)
            with self.assertRaises(ToolRegistryError):
                load_tool_registry(PROJECT_ROOT, directory=Path(tmp))
            missing = dict(base, routes=[{
                "method": "GET", "path": "/api/v1/da-liu-ren/glossary",
                "handler": "static_config", "options": {}}])
            write_manifest(tmp, missing)
            with self.assertRaises(ToolRegistryError):
                load_tool_registry(PROJECT_ROOT, directory=Path(tmp))

    def test_engine_chart_options_preserve_timeout_messages(self):
        expected = {
            "/api/v1/qimen/charts": "奇门排盘计算超时",
            "/api/v1/bazi/charts": "八字排盘计算超时",
            "/api/v1/liu-yao/charts": "六爻排盘计算超时",
            "/api/v1/da-liu-ren/charts": "大六壬排盘计算超时",
        }
        for path, message in expected.items():
            _, route = self.registry.resolve("POST", path)
            self.assertEqual(route.options["timeout_message"], message)

    def test_health_keys_match_legacy_names(self):
        flags = self.registry.health_flags(PROJECT_ROOT)
        self.assertEqual(set(flags), {
            "cli_available", "qimen_cli_available", "bazi_cli_available",
            "liu_yao_cli_available", "da_liu_ren_cli_available",
            "calendar_cli_available", "astro_cli_available",
        })

    def test_startup_requirements(self):
        paths = self.registry.required_startup_engine_paths(PROJECT_ROOT, {})
        names = {path.name for path in paths}
        self.assertIn("zi_wei_web_cli", names)
        self.assertNotIn("common_calendar_web_cli", names, "calendar 不是启动必需")
        astro_off = self.registry.required_startup_engine_paths(
            PROJECT_ROOT, {"ZHOUYILAB_ENABLE_ASTRO": "OFF"})
        self.assertNotIn("astro_web_cli", {path.name for path in astro_off})


class PlatformRouteContractTests(unittest.TestCase):
    """server.py 集成点静态契约（与既有 web contract 测试同风格）。"""

    def test_server_uses_registry_dispatch_and_fallback(self):
        self.assertIn('TOOL_REGISTRY = load_tool_registry(PROJECT_ROOT)', SERVER_SOURCE)
        self.assertIn('binding = TOOL_REGISTRY.resolve("POST", parsed.path)', SERVER_SOURCE)
        self.assertIn("def _handle_engine_chart", SERVER_SOURCE)
        self.assertIn('"/api/v1/tools"', SERVER_SOURCE)
        # 被收敛的四个纯转发分支不得复活
        self.assertNotIn('parsed.path == "/api/v1/qimen/charts"', SERVER_SOURCE)
        self.assertNotIn('parsed.path == "/api/v1/da-liu-ren/charts"', SERVER_SOURCE)

    def test_platform_discovery_endpoint_registered(self):
        self.assertIn('parsed.path in ("/api/v1", "/api/v1/")', SERVER_SOURCE)
        self.assertIn("def platform_discovery()", SERVER_SOURCE)

    def test_manifest_files_exist_with_schema(self):
        for raw in builtin_tools():
            path = TOOLS_DIR / f"{raw['id']}.json"
            self.assertTrue(path.is_file(), path)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["schema"],
                MANIFEST_SCHEMA_VERSION,
            )
        self.assertTrue((TOOLS_DIR / "tool.schema.json").is_file())


if __name__ == "__main__":
    unittest.main()
