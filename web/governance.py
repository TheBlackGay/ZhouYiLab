#!/usr/bin/env python3
"""ZhouYiLab 公网最小治理层（P0-2）：访问日志 + API Key + 限流。

三档模式（环境变量 ``ZHOUYILAB_API_MODE``）：

* ``off``      完全关闭治理（本机开发可选项，不落访问日志）。
* ``observe``  **默认**。全量计算并记录"若拦截会发生什么"，但永不拦截；
               用于观察误杀率，等价上线前一周的只记录阶段。
* ``enforce``  对 ``/api/`` 路由强制执行 X-API-Key 与每密钥令牌桶限流。

设计边界：
* ``/api/v1/health`` 永远豁免（容器 HEALTHCHECK 依赖）。
* enforce 且未配置任何密钥时自动降级为 observe 并在日志告警——防止
  误配置把整站 API 锁死。
* 生产部署推荐由反向代理（nginx ``proxy_set_header X-API-Key``）为
  浏览器同源流量注入内部密钥，外部接入方发放独立密钥，从而按密钥
  维度归因、限流；本模块不感知代理拓扑。
* 访问日志 JSON Lines 落 ``.zhouyilab/logs/access.jsonl``；写盘失败
  自动禁用日志，不影响请求。
"""
import hmac
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

MODES = {"off", "observe", "enforce"}
EXEMPT_PATHS = {"/api/v1/health"}
API_KEY_HEADER = "X-API-Key"
DEFAULT_RATE_PER_MINUTE = 120
KEYS_FILE_RELPATH = "config/platform/api_keys.local.json"
LOG_RELPATH = ".zhouyilab/logs/access.jsonl"


class TokenBucket:
    """每主体（密钥标签或对端 IP）一个令牌桶。线程安全，粗粒度锁足够 P0 规模。"""

    def __init__(self, rate_per_minute, burst=None):
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute 必须为正整数")
        self.rate_per_minute = rate_per_minute
        self.capacity = max(1, int(burst or rate_per_minute))
        self._refill_per_second = rate_per_minute / 60.0
        self._buckets = {}
        self._lock = threading.Lock()

    def take(self, subject, now=None):
        """取 1 个令牌。返回 (allowed, retry_after_seconds)。"""
        now = time.monotonic() if now is None else now
        with self._lock:
            state = self._buckets.get(subject)
            if state is None:
                state = [self.capacity, now]
                self._buckets[subject] = state
            tokens, last = state
            tokens = min(self.capacity, tokens + (now - last) * self._refill_per_second)
            if tokens >= 1.0:
                state[0] = tokens - 1.0
                state[1] = now
                return True, 0.0
            state[0] = tokens
            state[1] = now
            retry = (1.0 - tokens) / self._refill_per_second
            return False, max(1.0, round(retry))


class ApiKeyStore:
    """从本地 JSON（``{label: key}``）加载密钥；比较使用常数时间。"""

    def __init__(self, pairs=None):
        self._pairs = dict(pairs or {})

    @classmethod
    def from_file(cls, path):
        path = Path(path)
        if not path.is_file():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or any(
            not isinstance(label, str) or not isinstance(key, str) or not key
            for label, key in raw.items()
        ):
            raise ValueError("api_keys 文件必须是 {label: key} 字符串映射")
        return cls({label: key for label, key in raw.items() if label and key})

    def is_empty(self):
        return not self._pairs

    def label_for(self, candidate):
        if not candidate:
            return None
        for label, key in self._pairs.items():
            if hmac.compare_digest(candidate, key):
                return label
        return None


class AccessLog:
    """JSON Lines 访问日志。任何写盘故障只降级自身，不影响服务。"""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._disabled = False

    @property
    def disabled(self):
        return self._disabled

    def write(self, record):
        if self._disabled:
            return
        line = json.dumps(record, ensure_ascii=False, default=str)
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
        except OSError as error:
            self._disabled = True
            print(f"[governance] 访问日志不可写，已禁用：{error}")


class Governance:
    def __init__(self, mode="observe", keys=None, limiter=None, log=None,
                 rate_per_minute=DEFAULT_RATE_PER_MINUTE):
        if mode not in MODES:
            raise ValueError(f"未知治理模式：{mode}")
        self.mode = mode
        self.keys = keys if keys is not None else ApiKeyStore()
        self.limiter = limiter or TokenBucket(rate_per_minute)
        self.log = log
        self._warned_no_keys = False

    @classmethod
    def from_env(cls, project_root):
        project_root = Path(project_root)
        mode = os.environ.get("ZHOUYILAB_API_MODE", "observe").strip().lower()
        if mode not in MODES:
            print(f"[governance] 未知 ZHOUYILAB_API_MODE={mode!r}，回落 observe")
            mode = "observe"
        try:
            rate = int(os.environ.get("ZHOUYILAB_RATE_LIMIT_RPM", DEFAULT_RATE_PER_MINUTE))
            if rate <= 0:
                raise ValueError
        except ValueError:
            print("[governance] ZHOUYILAB_RATE_LIMIT_RPM 非法，使用默认 "
                  f"{DEFAULT_RATE_PER_MINUTE}")
            rate = DEFAULT_RATE_PER_MINUTE
        keys_file = os.environ.get("ZHOUYILAB_API_KEYS_FILE") or \
            project_root / KEYS_FILE_RELPATH
        try:
            keys = ApiKeyStore.from_file(keys_file)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"[governance] 密钥配置加载失败（按无密钥处理）：{error}")
            keys = ApiKeyStore()
        log_file = os.environ.get("ZHOUYILAB_ACCESS_LOG") or project_root / LOG_RELPATH
        return cls(mode=mode, keys=keys, limiter=TokenBucket(rate),
                   log=AccessLog(log_file), rate_per_minute=rate)

    def enforce_verdict(self, header_key, client_ip):
        """按 enforce 规则给出裁决，供 observe/enforce 共用。"""
        if self.mode == "enforce" and self.keys.is_empty():
            return {"reason": "no_keys_configured", "key_label": None,
                    "subject": f"ip:{client_ip}", "allowed": True}
        if not header_key:
            return {"reason": "missing_key", "key_label": None,
                    "subject": f"ip:{client_ip}", "allowed": False}
        label = self.keys.label_for(header_key)
        if label is None:
            return {"reason": "unknown_key", "key_label": None,
                    "subject": f"ip:{client_ip}", "allowed": False}
        allowed, retry = self.limiter.take(label)
        if not allowed:
            return {"reason": "rate_limited", "key_label": label,
                    "subject": label, "allowed": False, "retry_after": retry}
        return {"reason": "allowed", "key_label": label,
                "subject": label, "allowed": True}

    def decide(self, header_key, path, client_ip):
        """返回本次请求的治理决策；blocked 只在 enforce（且密钥已配置）时为 True。"""
        if self.mode == "off":
            return {"mode": "off", "blocked": False, "decision": None}
        if not path.startswith("/api/"):
            return {"mode": self.mode, "blocked": False, "decision": "static",
                    "key_label": None}
        if path in EXEMPT_PATHS:
            return {"mode": self.mode, "blocked": False, "decision": "exempt",
                    "key_label": None}
        verdict = self.enforce_verdict(header_key, client_ip)
        no_keys_degraded = verdict["reason"] == "no_keys_configured"
        blocked = self.mode == "enforce" and not verdict["allowed"]
        decision = {
            "mode": self.mode,
            "decision": verdict["reason"],
            "key_label": verdict["key_label"],
            "would_block": not verdict["allowed"],
            "blocked": blocked,
        }
        if blocked:
            decision["status"], decision["code"], decision["message"] = {
                "missing_key": (401, "API_KEY_REQUIRED",
                                "缺少 X-API-Key；请联系平台方申领接入密钥"),
                "unknown_key": (403, "API_KEY_INVALID", "X-API-Key 无效"),
                "rate_limited": (429, "RATE_LIMITED",
                                 f"请求频率超过每分钟 {self.limiter.rate_per_minute} 次配额"),
            }[verdict["reason"]]
            decision["retry_after"] = verdict.get("retry_after")
        elif no_keys_degraded and not self._warned_no_keys:
            self._warned_no_keys = True
            print("[governance] enforce 模式未配置任何密钥，本次启动按 observe 处理")
        return decision
