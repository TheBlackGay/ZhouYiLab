"""P0-2 公网最小治理测试：令牌桶、密钥、模式语义与在线服务行为。"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from governance import ApiKeyStore, Governance, TokenBucket  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENGINE_BIN = PROJECT_ROOT / "build" / "examples" / "zi_wei_web_cli"


class TokenBucketTests(unittest.TestCase):
    def test_burst_then_deny_then_refill(self):
        clock = [0.0]
        bucket = TokenBucket(rate_per_minute=60)  # capacity 60, 1/s
        for _ in range(60):
            allowed, _retry = bucket.take("k", now=clock[0])
            self.assertTrue(allowed)
        allowed, retry = bucket.take("k", now=clock[0])
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry, 1)
        clock[0] += 2.0  # 2 秒 → 回 2 令牌
        self.assertTrue(bucket.take("k", now=clock[0])[0])
        self.assertTrue(bucket.take("k", now=clock[0])[0])
        self.assertFalse(bucket.take("k", now=clock[0])[0])

    def test_subjects_are_isolated(self):
        bucket = TokenBucket(rate_per_minute=1)
        self.assertTrue(bucket.take("a")[0])
        self.assertFalse(bucket.take("a")[0])
        self.assertTrue(bucket.take("b")[0])

    def test_invalid_rate_rejected(self):
        with self.assertRaises(ValueError):
            TokenBucket(rate_per_minute=0)


class ApiKeyStoreTests(unittest.TestCase):
    def test_missing_file_yields_empty_store(self):
        store = ApiKeyStore.from_file(Path(tempfile.gettempdir()) / "no-such-keys.json")
        self.assertTrue(store.is_empty())
        self.assertIsNone(store.label_for("anything"))

    def test_load_and_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keys.json"
            path.write_text(json.dumps({"partner-a": "sekrit-1"}), encoding="utf-8")
            store = ApiKeyStore.from_file(path)
            self.assertEqual(store.label_for("sekrit-1"), "partner-a")
            self.assertIsNone(store.label_for("sekrit-2"))
            self.assertIsNone(store.label_for(""))

    def test_malformed_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keys.json"
            path.write_text('["not", "a", "map"]', encoding="utf-8")
            with self.assertRaises(ValueError):
                ApiKeyStore.from_file(path)


class GovernanceDecisionTests(unittest.TestCase):
    def _governance(self, mode, keys=None, rate=1000):
        return Governance(
            mode=mode,
            keys=ApiKeyStore(keys or {}),
            limiter=TokenBucket(rate),
            log=None,
        )

    def test_off_mode_skips_everything(self):
        decision = self._governance("off").decide(None, "/api/v1/qimen/charts", "1.2.3.4")
        self.assertEqual(decision, {"mode": "off", "blocked": False, "decision": None})

    def test_static_assets_and_health_exempt(self):
        governance = self._governance("enforce", {"partner": "sekrit"})
        for path in ("/qimen.html", "/assets/x.css"):
            decision = governance.decide(None, path, "1.2.3.4")
            self.assertFalse(decision["blocked"])
            self.assertEqual(decision["decision"], "static")
        decision = governance.decide(None, "/api/v1/health", "1.2.3.4")
        self.assertFalse(decision["blocked"])
        self.assertEqual(decision["decision"], "exempt")

    def test_observe_never_blocks_but_records_would_block(self):
        governance = self._governance("observe")
        decision = governance.decide(None, "/api/v1/bazi/charts", "1.2.3.4")
        self.assertFalse(decision["blocked"])
        self.assertTrue(decision["would_block"])
        self.assertEqual(decision["decision"], "missing_key")

    def test_enforce_requires_valid_key(self):
        governance = self._governance("enforce", {"partner": "sekrit"})
        missing = governance.decide(None, "/api/v1/bazi/charts", "1.2.3.4")
        self.assertTrue(missing["blocked"])
        self.assertEqual((missing["status"], missing["code"]), (401, "API_KEY_REQUIRED"))
        unknown = governance.decide("wrong", "/api/v1/bazi/charts", "1.2.3.4")
        self.assertTrue(unknown["blocked"])
        self.assertEqual((unknown["status"], unknown["code"]), (403, "API_KEY_INVALID"))
        good = governance.decide("sekrit", "/api/v1/bazi/charts", "1.2.3.4")
        self.assertFalse(good["blocked"])
        self.assertEqual(good["key_label"], "partner")

    def test_enforce_without_keys_degrades_to_observe(self):
        governance = self._governance("enforce", {})
        decision = governance.decide(None, "/api/v1/bazi/charts", "1.2.3.4")
        self.assertFalse(decision["blocked"])
        self.assertEqual(decision["decision"], "no_keys_configured")

    def test_enforce_rate_limit(self):
        governance = self._governance("enforce", {"partner": "sekrit"}, rate=1)
        first = governance.decide("sekrit", "/api/v1/bazi/charts", "1.2.3.4")
        self.assertFalse(first["blocked"])
        second = governance.decide("sekrit", "/api/v1/bazi/charts", "1.2.3.4")
        self.assertTrue(second["blocked"])
        self.assertEqual((second["status"], second["code"]), (429, "RATE_LIMITED"))
        self.assertGreaterEqual(second["retry_after"], 1)

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            Governance(mode="block")


class _LiveServerMixin:
    """在一次性子进程里启动 server.py，用真实 HTTP 验证治理关卡。"""

    @staticmethod
    def _free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _start_server(self, extra_env):
        env = os.environ.copy()
        env.update({
            "ZHOUYILAB_ENABLE_ASTRO": "OFF",
            "ZHOUYILAB_ACCESS_LOG": str(Path(self.tmp.name) / "access.jsonl"),
            **extra_env,
        })
        port = self._free_port()
        process = subprocess.Popen(
            [sys.executable, "web/server.py", "--port", str(port)],
            cwd=PROJECT_ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        def _terminate():
            process.kill()
            process.wait(timeout=10)

        self.addCleanup(_terminate)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                self._request(port, "GET", "/api/v1/health")
                return port
            except OSError:
                if process.poll() is not None:
                    self.fail("服务进程提前退出")
                time.sleep(0.3)
        self.fail("服务启动超时")

    @staticmethod
    def _request(port, method, path, headers=None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}", method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    @staticmethod
    def _access_records(tmp_dir):
        path = Path(tmp_dir) / "access.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class LiveGovernanceTests(unittest.TestCase, _LiveServerMixin):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        keys_file = Path(self.tmp.name) / "keys.json"
        keys_file.write_text(json.dumps({"ci-tester": "unit-test-key"}), encoding="utf-8")
        self.keys_file = str(keys_file)

    def test_observe_mode_serves_without_key_and_logs_would_block(self):
        port = self._start_server({
            "ZHOUYILAB_API_MODE": "observe",
            "ZHOUYILAB_API_KEYS_FILE": self.keys_file,
        })
        status, body = self._request(port, "GET", "/api/v1/tools")
        self.assertEqual(status, 200)
        self.assertTrue(body["success"])
        self.assertGreaterEqual(body["data"]["tool_count"], 7)
        deadline = time.time() + 5
        records = []
        while time.time() < deadline:
            records = self._access_records(self.tmp.name)
            if any(record["path"] == "/api/v1/tools" for record in records):
                break
            time.sleep(0.2)
        target = next(r for r in records if r["path"] == "/api/v1/tools")
        self.assertEqual(target["governance_decision"], "missing_key")
        self.assertTrue(target["governance_would_block"])
        self.assertFalse(target["governance_blocked"])
        self.assertTrue(target["request_id"])

    def test_enforce_mode_gates_api_but_exempts_health(self):
        port = self._start_server({
            "ZHOUYILAB_API_MODE": "enforce",
            "ZHOUYILAB_API_KEYS_FILE": self.keys_file,
            "ZHOUYILAB_RATE_LIMIT_RPM": "1",
        })
        self.assertEqual(self._request(port, "GET", "/api/v1/health")[0], 200)
        status, body = self._request(port, "GET", "/api/v1/tools")
        self.assertEqual(status, 401)
        self.assertEqual(body["error"]["code"], "API_KEY_REQUIRED")
        status, body = self._request(port, "GET", "/api/v1/tools",
                                     headers={"X-API-Key": "nope"})
        self.assertEqual(status, 403)
        self.assertEqual(body["error"]["code"], "API_KEY_INVALID")
        status, body = self._request(port, "GET", "/api/v1/tools",
                                     headers={"X-API-Key": "unit-test-key"})
        self.assertEqual(status, 200)
        status, body = self._request(port, "GET", "/api/v1/tools",
                                     headers={"X-API-Key": "unit-test-key"})
        self.assertEqual(status, 429)
        self.assertEqual(body["error"]["code"], "RATE_LIMITED")

    def test_registry_post_route_live(self):
        if not (PROJECT_ROOT / "build" / "examples" / "qi_men_web_cli").exists():
            self.skipTest("未构建奇门网页 CLI")
        port = self._start_server({"ZHOUYILAB_API_MODE": "off"})
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/qimen/charts",
            data=json.dumps({"date": {"year": 2024, "month": 6, "day": 15,
                                      "hour": 10, "minute": 30}}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.load(response)
            status = response.status
        except urllib.error.HTTPError as error:
            status, body = error.code, json.load(error)
        # 入参形状以引擎为准；400/422 均说明请求已穿过注册表分发到达 handler。
        self.assertIn(status, (200, 400, 422))
        self.assertIn("meta", body)
        self.assertTrue(body["meta"]["request_id"])


if __name__ == "__main__":
    unittest.main()
