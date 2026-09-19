#!/usr/bin/env python3
"""ZhouYiLab 工具注册表（P0-1 工具 Manifest 机制）

平台定位下，"新增一门术数工具"应当只需：
  1. 在 ``config/platform/tools/`` 放一份 ``<tool>.json`` 清单；
  2. 提供引擎 CLI 与页面；
  3. （可选）复用内置 ``engine_chart`` handler，无需改 server.py。

清单只描述稳定的平台元数据（引擎路径、路由、页面、校准状态），
不含业务规则；规则仍归 ``config/<tool>/`` 各目录管理。

加载语义：
  * 清单目录存在   → 严格校验加载（fail fast，坏清单直接拒绝启动）；
  * 清单目录缺失   → 使用 ``builtin_tools()`` 内建默认值（等价回退路径）；
  * 路由 dispatch  → 仅 ``ROUTABLE_HANDLERS`` 参与分发；
                     ``legacy_chain`` / ``python_service`` 为纯元数据声明，
                     由 server.py 保留既有专用分支处理。
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CALIBRATION_STATUSES = {"calibrated", "in_progress", "pending", "experimental"}
ALLOWED_METHODS = {"GET", "POST"}
ROUTABLE_HANDLERS = {"engine_chart", "static_config"}
METADATA_HANDLERS = {"legacy_chain", "python_service"}
KNOWN_HANDLERS = ROUTABLE_HANDLERS | METADATA_HANDLERS
MANIFEST_SCHEMA_VERSION = "zhouyilab-tool/1.0"
TOOLS_DIRECTORY_RELPATH = "config/platform/tools"


class ToolRegistryError(ValueError):
    """工具清单非法。加载期一次性暴露，避免运行期半注册状态。"""


@dataclass(frozen=True)
class ToolRoute:
    method: str
    path: str
    handler: str
    options: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolManifest:
    id: str
    name: str
    engine_cli: str
    calibration_status: str
    pages: tuple
    api_prefixes: tuple
    routes: tuple
    health_key: str
    optional_env: str = None
    required_at_startup: bool = True
    interface_doc: str = None
    rule_profile_version: str = None
    visibility: str = "public"

    def engine_path(self, project_root: Path) -> Path:
        return project_root / self.engine_cli


def builtin_tools():
    """与 server.py 历史硬编码等价的默认清单（清单目录缺失时的回退）。"""
    return [
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "ziwei",
            "name": "紫微斗数",
            "engine_cli": "build/examples/zi_wei_web_cli",
            "calibration_status": "calibrated",
            "rule_profile_version": "ziwei-rules/2.0",
            "interface_doc": "docs/ziwei/紫微斗数HTTP接口文档.md",
            "pages": ["index.html"],
            "api_prefixes": ["/api/v1/ziwei/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/ziwei/time-correction", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/ziwei/charts", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/ziwei/fortune", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/ziwei/analysis", "handler": "legacy_chain"},
                {"method": "GET", "path": "/api/v1/ziwei/meta", "handler": "python_service"},
                {"method": "GET", "path": "/api/v1/ziwei/symbols", "handler": "python_service"},
                {"method": "GET", "path": "/api/v1/ziwei/research/blind-review/packet", "handler": "python_service"},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "qimen",
            "name": "奇门遁甲",
            "engine_cli": "build/examples/qi_men_web_cli",
            "calibration_status": "calibrated",
            "interface_doc": "docs/奇门遁甲HTTP接口文档.md",
            "pages": ["qimen.html"],
            "api_prefixes": ["/api/v1/qimen/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/qimen/charts", "handler": "engine_chart",
                 "options": {"timeout_message": "奇门排盘计算超时"}},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "bazi",
            "name": "八字",
            "engine_cli": "build/examples/ba_zi_web_cli",
            "calibration_status": "in_progress",
            "pages": ["bazi.html"],
            "api_prefixes": ["/api/v1/bazi/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/bazi/charts", "handler": "engine_chart",
                 "options": {"timeout_message": "八字排盘计算超时"}},
                {"method": "GET", "path": "/api/v1/bazi/shen-sha/<id>", "handler": "python_service"},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "liu_yao",
            "name": "六爻",
            "engine_cli": "build/examples/liu_yao_web_cli",
            "calibration_status": "pending",
            "pages": ["liu-yao.html"],
            "api_prefixes": ["/api/v1/liu-yao/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/liu-yao/charts", "handler": "engine_chart",
                 "options": {"timeout_message": "六爻排盘计算超时"}},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "da_liu_ren",
            "name": "大六壬",
            "engine_cli": "build/examples/da_liu_ren_web_cli",
            "calibration_status": "pending",
            "interface_doc": "docs/大六壬HTTP接口文档.md",
            "rule_profile_version": "da-liu-ren-rules/0.2",
            "pages": ["da-liu-ren.html"],
            "api_prefixes": ["/api/v1/da-liu-ren/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/da-liu-ren/charts", "handler": "engine_chart",
                 "options": {"timeout_message": "大六壬排盘计算超时"}},
                {"method": "GET", "path": "/api/v1/da-liu-ren/glossary", "handler": "static_config",
                 "options": {"config_path": "config/daliuren/glossary.json",
                             "not_found_code": "GLOSSARY_NOT_FOUND"}},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "calendar",
            "name": "公共日历",
            "engine_cli": "build/examples/common_calendar_web_cli",
            "calibration_status": "calibrated",
            "required_at_startup": False,
            "interface_doc": "docs/common/公共日历API.md",
            "pages": [],
            "api_prefixes": ["/api/v1/calendar/"],
            "routes": [
                {"method": "POST", "path": "/api/v1/calendar/convert", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/calendar/true-solar-time", "handler": "legacy_chain"},
            ],
        },
        {
            "schema": MANIFEST_SCHEMA_VERSION,
            "id": "astro",
            "name": "西洋占星",
            "engine_cli": "build/examples/astro_web_cli",
            "calibration_status": "experimental",
            "visibility": "frozen",
            "interface_doc": "docs/astro/西洋占星HTTP接口文档.md",
            "pages": ["astro.html"],
            "api_prefixes": ["/api/v1/astro/", "/api/v1/geo/"],
            "optional_env": "ZHOUYILAB_ENABLE_ASTRO",
            "routes": [
                {"method": "POST", "path": "/api/v1/astro/charts", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/astro/transits", "handler": "legacy_chain"},
                {"method": "GET", "path": "/api/v1/astro/meta", "handler": "python_service"},
                {"method": "POST", "path": "/api/v1/astro/analysis", "handler": "legacy_chain"},
                {"method": "POST", "path": "/api/v1/astro/transit-analysis", "handler": "python_service"},
                {"method": "POST", "path": "/api/v1/astro/daily-reading", "handler": "python_service"},
                {"method": "POST", "path": "/api/v1/astro/natal-analysis", "handler": "python_service"},
                {"method": "POST", "path": "/api/v1/astro/natal-reading", "handler": "python_service"},
                {"method": "POST", "path": "/api/v1/geo/place-resolve", "handler": "python_service"},
            ],
        },
    ]


def _require_string(source, key, where, allow_empty=False):
    value = source.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ToolRegistryError(f"{where}: 字段 {key} 必须是非空字符串")
    return value.strip()


def _validate_relative_asset(value, where, key):
    normalized = value.replace("\\", "/")
    from pathlib import PurePosixPath
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ToolRegistryError(f"{where}: 字段 {key} 必须是不含越界的仓库相对路径")


def _validate_manifest(raw, source_label):
    where = f"工具清单 {source_label}"
    if not isinstance(raw, dict):
        raise ToolRegistryError(f"{where}: 根节点必须是 JSON 对象")
    schema = raw.get("schema")
    if schema != MANIFEST_SCHEMA_VERSION:
        raise ToolRegistryError(f"{where}: schema 必须为 {MANIFEST_SCHEMA_VERSION}")
    tool_id = _require_string(raw, "id", where)
    if not TOOL_ID_PATTERN.match(tool_id):
        raise ToolRegistryError(f"{where}: id 只允许小写字母/数字/下划线，且以字母开头")
    name = _require_string(raw, "name", where)
    engine_cli = _require_string(raw, "engine_cli", where)
    _validate_relative_asset(engine_cli, where, "engine_cli")
    calibration = _require_string(raw, "calibration_status", where)
    if calibration not in CALIBRATION_STATUSES:
        raise ToolRegistryError(f"{where}: calibration_status 必须是 {sorted(CALIBRATION_STATUSES)} 之一")

    def string_list(key):
        items = raw.get(key, [])
        if not isinstance(items, list) or any(not isinstance(x, str) or not x.strip() for x in items):
            raise ToolRegistryError(f"{where}: {key} 必须是非空字符串数组")
        return tuple(items)

    pages = string_list("pages")
    api_prefixes = string_list("api_prefixes")
    for prefix in api_prefixes:
        if not prefix.startswith("/api/"):
            raise ToolRegistryError(f"{where}: api_prefixes 必须以 /api/ 开头：{prefix}")

    routes_raw = raw.get("routes")
    if not isinstance(routes_raw, list) or not routes_raw:
        raise ToolRegistryError(f"{where}: routes 至少声明一条")
    routes = []
    seen_local = set()
    for route_raw in routes_raw:
        if not isinstance(route_raw, dict):
            raise ToolRegistryError(f"{where}: route 必须是对象")
        method = _require_string(route_raw, "method", where).upper()
        if method not in ALLOWED_METHODS:
            raise ToolRegistryError(f"{where}: method 必须是 {sorted(ALLOWED_METHODS)}")
        path = _require_string(route_raw, "path", where)
        if not path.startswith("/api/"):
            raise ToolRegistryError(f"{where}: route.path 必须以 /api/ 开头：{path}")
        handler = _require_string(route_raw, "handler", where)
        if handler not in KNOWN_HANDLERS:
            raise ToolRegistryError(
                f"{where}: 未知 handler {handler!r}，可用 {sorted(KNOWN_HANDLERS)}")
        options = route_raw.get("options", {})
        if not isinstance(options, dict):
            raise ToolRegistryError(f"{where}: route options 必须是对象")
        if handler == "engine_chart" and "operation" in options \
                and not isinstance(options["operation"], str):
            raise ToolRegistryError(f"{where}: engine_chart options.operation 必须是字符串")
        if handler == "static_config":
            config_path = options.get("config_path")
            if not isinstance(config_path, str) or not config_path.strip():
                raise ToolRegistryError(f"{where}: static_config 必须声明 options.config_path")
            _validate_relative_asset(config_path, where, "options.config_path")
            if not config_path.startswith("config/"):
                raise ToolRegistryError(f"{where}: static_config 只允许暴露 config/ 下的 JSON")
        key = (method, path)
        if key in seen_local:
            raise ToolRegistryError(f"{where}: 路由重复 {method} {path}")
        seen_local.add(key)
        routes.append(ToolRoute(method, path, handler, options))

    health_key = raw.get("health_key")
    if health_key is None:
        health_key = "cli_available" if tool_id == "ziwei" else f"{tool_id}_cli_available"
    optional_env = raw.get("optional_env")
    if optional_env is not None and not isinstance(optional_env, str):
        raise ToolRegistryError(f"{where}: optional_env 必须是字符串")
    required_at_startup = raw.get("required_at_startup", True)
    if not isinstance(required_at_startup, bool):
        raise ToolRegistryError(f"{where}: required_at_startup 必须是布尔值")
    interface_doc = raw.get("interface_doc")
    if interface_doc is not None:
        interface_doc = _require_string(raw, "interface_doc", where)
        _validate_relative_asset(interface_doc, where, "interface_doc")
        if not interface_doc.startswith("docs/"):
            raise ToolRegistryError(f"{where}: interface_doc 必须位于 docs/ 下")
    rule_profile_version = raw.get("rule_profile_version")
    if rule_profile_version is not None and (
            not isinstance(rule_profile_version, str) or not rule_profile_version.strip()):
        raise ToolRegistryError(f"{where}: rule_profile_version 必须是非空字符串")

    visibility = raw.get("visibility", "public")
    if visibility not in {"public", "frozen"}:
        raise ToolRegistryError(f"{where}: visibility 只能是 public/frozen")

    return ToolManifest(tool_id, name, engine_cli, calibration,
                        pages, api_prefixes, tuple(routes), health_key,
                        optional_env, required_at_startup,
                        interface_doc, rule_profile_version, visibility)


class ToolRegistry:
    def __init__(self, manifests, source):
        self._tools = {}
        self.source = source
        seen_routes = {}
        for manifest in manifests:
            if manifest.id in self._tools:
                raise ToolRegistryError(f"工具 id 重复：{manifest.id}")
            self._tools[manifest.id] = manifest
            for route in manifest.routes:
                key = (route.method, route.path)
                if key in seen_routes:
                    raise ToolRegistryError(
                        f"路由 {route.method} {route.path} 被 {seen_routes[key]} 与 {manifest.id} 同时声明")
                seen_routes[key] = manifest.id
        # 按 id 排序存储：summary/health 等派生输出与清单加载来源（文件名序、
        # 内建定义序）无关，保证 API 响应确定性。
        self._tools = dict(sorted(self._tools.items()))
        self._routable = {
            (route.method, route.path): (manifest, route)
            for manifest in self._tools.values()
            for route in manifest.routes
            if route.handler in ROUTABLE_HANDLERS
        }

    @property
    def tools(self):
        return dict(self._tools)

    def resolve(self, method, path):
        """仅返回可分发（routable）绑定；元数据路由返回 None，由 server 专用分支处理。"""
        return self._routable.get((method, path))

    def engine_paths(self, project_root):
        return {tool_id: manifest.engine_path(project_root)
                for tool_id, manifest in self._tools.items()}

    def health_flags(self, project_root):
        """派生健康检查的引擎可用位；ziwei 的历史键名 cli_available 由清单 health_key 保证。"""
        return {
            manifest.health_key: manifest.engine_path(project_root).exists()
            for manifest in self._tools.values()
        }

    def calibration_map(self):
        return {tool_id: {
            "name": manifest.name,
            "calibration_status": manifest.calibration_status,
            "api_prefixes": list(manifest.api_prefixes),
            "pages": list(manifest.pages),
        } for tool_id, manifest in self._tools.items()}

    def summary(self, project_root):
        return {
            "schema": MANIFEST_SCHEMA_VERSION,
            "registry_source": self.source,
            "tool_count": len(self._tools),
            "tools": [
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "engine_cli": manifest.engine_cli,
                    "engine_available": manifest.engine_path(project_root).exists(),
                    "calibration_status": manifest.calibration_status,
                    "required_at_startup": manifest.required_at_startup,
                    "interface_doc": manifest.interface_doc,
                    "rule_profile_version": manifest.rule_profile_version,
                    "visibility": manifest.visibility,
                    "pages": list(manifest.pages),
                    "api_prefixes": list(manifest.api_prefixes),
                    "optional_env": manifest.optional_env,
                    "routes": [
                        {"method": route.method, "path": route.path,
                         "handler": route.handler, "routable": route.handler in ROUTABLE_HANDLERS}
                        for route in manifest.routes
                    ],
                }
                for manifest in self._tools.values()
            ],
        }

    def required_startup_engine_paths(self, project_root, environ):
        """启动门槛：必需引擎必须存在；optional_env 关闭或非启动必需时豁免。"""
        paths = []
        for manifest in self._tools.values():
            if not manifest.required_at_startup:
                continue
            if manifest.optional_env and environ.get(manifest.optional_env, "ON") == "OFF":
                continue
            paths.append(manifest.engine_path(project_root))
        return paths


def load_tool_registry(project_root, directory=None):
    """加载注册表。目录缺失 → 内建默认；目录存在 → 严格加载。"""
    project_root = Path(project_root)
    tools_dir = Path(directory) if directory is not None else project_root / TOOLS_DIRECTORY_RELPATH
    if not tools_dir.is_dir():
        manifests = [_validate_manifest(raw, "<builtin>") for raw in builtin_tools()]
        return ToolRegistry(manifests, "builtin")
    manifests = []
    for path in sorted(tools_dir.glob("*.json")):
        if path.name.startswith(("tool.schema", "_")):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ToolRegistryError(f"无法读取工具清单 {path.name}: {error}") from error
        manifests.append(_validate_manifest(raw, path.name))
    if not manifests:
        raise ToolRegistryError(f"{tools_dir} 存在但没有任何工具清单")
    try:
        source = str(tools_dir.relative_to(project_root))
    except ValueError:  # 显式传入项目外目录（测试场景）
        source = str(tools_dir)
    return ToolRegistry(manifests, source)
