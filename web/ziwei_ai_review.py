#!/usr/bin/env python3
import hashlib
import json
import math
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ziwei_blind_review import generate_blind_packet, load_blind_review_resources
from ziwei_research_engine import ResearchConfigError, _read_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROTOCOL_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "ai_review_protocol.json"
)
DEFAULT_PROVIDER_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "ai_model_providers.json"
)
LOCAL_PROVIDER_CONFIG_PATH = (
    PROJECT_ROOT / "config" / "ziwei" / "research" / "ai_model_providers.local.json"
)
DEFAULT_DATABASE_PATH = PROJECT_ROOT / ".zhouyilab" / "research" / "ai_review.sqlite3"


class AiReviewError(Exception):
    pass


class AiReviewProviderError(AiReviewError):
    pass


def _utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _score_direction(score):
    if score < 0:
        return "negative"
    if score > 0:
        return "positive"
    return "neutral"


def summarize_dimension_rows(dimension_rows):
    """Collapse repetitions first, then compare providers within each case."""
    provider_case_scores = {}
    for row in dimension_rows:
        if row["score"] is not None:
            provider_case_scores.setdefault(
                (row["provider_id"], row["case_code"]), []
            ).append(row["score"])

    model_case_scores = {
        key: sum(values) / len(values)
        for key, values in provider_case_scores.items()
    }
    model_case_directions = {
        key: _score_direction(score) for key, score in model_case_scores.items()
    }
    direction_counts = {
        direction: sum(value == direction for value in model_case_directions.values())
        for direction in ("negative", "neutral", "positive")
    }
    model_case_count = len(model_case_scores)
    largest_direction_count = max(direction_counts.values(), default=0)

    case_directions = {}
    for (_, case_code), direction in model_case_directions.items():
        case_directions.setdefault(case_code, []).append(direction)

    case_modal_agreements = []
    unanimous_case_count = 0
    matching_pairs = 0
    comparable_pairs = 0
    for directions in case_directions.values():
        if len(directions) < 2:
            continue
        counts = {
            direction: directions.count(direction)
            for direction in ("negative", "neutral", "positive")
        }
        modal_count = max(counts.values())
        case_modal_agreements.append(modal_count / len(directions))
        unanimous_case_count += modal_count == len(directions)
        for left in range(len(directions)):
            for right in range(left + 1, len(directions)):
                comparable_pairs += 1
                matching_pairs += directions[left] == directions[right]

    comparable_case_count = len(case_modal_agreements)
    return {
        "model_case_scores": list(model_case_scores.values()),
        "model_case_direction_counts": direction_counts,
        "model_case_count": model_case_count,
        "direction_prevalence_ratio": (
            round(largest_direction_count / model_case_count, 4)
            if model_case_count else None
        ),
        "within_case_cross_model_agreement": (
            round(sum(case_modal_agreements) / comparable_case_count, 4)
            if comparable_case_count else None
        ),
        "unanimous_case_count": unanimous_case_count,
        "comparable_case_count": comparable_case_count,
        "pairwise_direction_agreement": (
            round(matching_pairs / comparable_pairs, 4) if comparable_pairs else None
        ),
        "comparable_model_pairs": comparable_pairs,
    }


def load_ai_review_protocol(path=DEFAULT_PROTOCOL_PATH):
    protocol = _read_json(path)
    if protocol.get("status") != "frozen_before_collection":
        raise ResearchConfigError("AI 预评审协议必须在采集前冻结")
    boundary = protocol.get("interpretation_boundary", {})
    if not boundary.get("model_runs_are_not_human_raters"):
        raise ResearchConfigError("AI 运行不得被定义为真人评分者")
    if not boundary.get("repeated_runs_are_not_independent_experts"):
        raise ResearchConfigError("重复运行不得被定义为独立专家")
    if boundary.get("may_create_numeric_star_weights"):
        raise ResearchConfigError("AI 预评审不得直接生成星曜权重")
    if protocol.get("data_policy", {}).get("persist_api_keys"):
        raise ResearchConfigError("研究数据库不得持久化 API Key")
    return protocol


def load_provider_catalog(protocol, path=None):
    selected = Path(path) if path else (
        LOCAL_PROVIDER_CONFIG_PATH if LOCAL_PROVIDER_CONFIG_PATH.exists()
        else DEFAULT_PROVIDER_CONFIG_PATH
    )
    value = _read_json(selected)
    if value.get("config_version") != "0.1.0":
        raise ResearchConfigError("AI 模型连接配置版本无效")
    providers = value.get("providers")
    if not isinstance(providers, list) or len(providers) > 20:
        raise ResearchConfigError("AI 模型连接配置必须包含不超过 20 项的 providers 数组")
    normalized = []
    for item in providers:
        if not isinstance(item, dict) or not isinstance(item.get("enabled"), bool):
            raise ResearchConfigError("AI 模型连接缺少 enabled 布尔字段")
        if not item["enabled"]:
            continue
        provider = validate_provider(item, protocol)
        provider["enabled"] = True
        normalized.append(provider)
    ids = [item["provider_id"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise ResearchConfigError("AI 模型连接配置包含重复 provider_id")
    if selected == DEFAULT_PROVIDER_CONFIG_PATH and any(item.get("api_key") for item in normalized):
        raise ResearchConfigError("仓库配置不得保存明文 API Key，请使用本地配置或环境变量")
    return selected, normalized


def validate_provider(provider, protocol):
    if not isinstance(provider, dict):
        raise AiReviewError("模型连接必须是对象")
    result = {
        "provider_id": str(provider.get("provider_id") or uuid.uuid4().hex[:12]),
        "label": str(provider.get("label") or "").strip(),
        "protocol": str(provider.get("protocol") or "").strip(),
        "base_url": str(provider.get("base_url") or "").strip().rstrip("/"),
        "model": str(provider.get("model") or "").strip(),
        "model_family": str(provider.get("model_family") or provider.get("model") or "").strip(),
        "api_key": str(provider.get("api_key") or ""),
        "api_key_env": str(provider.get("api_key_env") or "").strip(),
        "temperature": provider.get(
            "temperature", protocol["run_policy"]["default_temperature"]
        ),
        "repetitions": provider.get("repetitions", 1),
        "model_seed": provider.get("model_seed"),
    }
    if not result["label"] or len(result["label"]) > 80:
        raise AiReviewError("模型连接名称长度必须为 1-80 个字符")
    if not result["provider_id"] or len(result["provider_id"]) > 80:
        raise AiReviewError("模型连接 ID 长度必须为 1-80 个字符")
    if result["protocol"] not in protocol["supported_provider_protocols"]:
        raise AiReviewError("不支持的模型接口协议")
    parsed = urlparse(result["base_url"])
    if len(result["base_url"]) > 500 or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AiReviewError("模型服务地址必须是有效的 http(s) URL")
    if not result["model"] or len(result["model"]) > 160:
        raise AiReviewError("模型名称长度必须为 1-160 个字符")
    if not result["model_family"] or len(result["model_family"]) > 80:
        raise AiReviewError("模型系列长度必须为 1-80 个字符")
    if not isinstance(result["temperature"], (int, float)) or not math.isfinite(
        result["temperature"]
    ) or not 0 <= result["temperature"] <= 2:
        raise AiReviewError("temperature 必须在 0-2 之间")
    minimum = protocol["run_policy"]["minimum_repetitions"]
    maximum = protocol["run_policy"]["maximum_repetitions"]
    if not isinstance(result["repetitions"], int) or not minimum <= result["repetitions"] <= maximum:
        raise AiReviewError(f"重复次数必须为 {minimum}-{maximum}")
    if result["model_seed"] is not None and not isinstance(result["model_seed"], int):
        raise AiReviewError("模型随机种子必须是整数或留空")
    if result["api_key_env"]:
        if not result["api_key_env"].replace("_", "").isalnum():
            raise AiReviewError("API Key 环境变量名无效")
        result["api_key"] = os.environ.get(result["api_key_env"], result["api_key"])
    return result


def redacted_provider(provider):
    return {
        key: value for key, value in provider.items()
        if key != "api_key"
    } | {"has_api_key": bool(provider.get("api_key"))}


def build_case_prompt(packet, case_data, protocol):
    prompt_data = {
        "case_code": case_data["case_code"],
        "source_layer": case_data["source_layer"],
        "focus": case_data["focus"],
        "stars": case_data["stars"],
        "controlled_transformation_signals": case_data["transformation_signals"],
        "dimensions": packet["dimensions"],
        "allowed_scores": packet["rating_scale"]["allowed_values"],
    }
    return (
        "你正在参与紫微斗数星曜作用的匿名定性预评审。只根据下方提供的匿名事实和维度定义独立判断，"
        "不要猜测格局名称、原始案例编号、预期答案或其他评分者结论。分值表示该维度定义方向的相对变化，"
        "不统一表示吉凶。null 表示信息不足，0 表示中性或正负方向并存，两者不能混淆。\n\n"
        "必须只返回一个 JSON 对象，格式为："
        '{"ratings":[{"dimension_id":"...","score":-1|-0.5|0|0.5|1|null,'
        '"rationale":"简短、可核对的中文依据"}]}。必须恰好覆盖全部维度且不得重复；非 null 评分必须有依据。\n\n'
        f"匿名材料：\n{json.dumps(prompt_data, ensure_ascii=False, separators=(',', ':'))}"
        f"\n\n提示词版本：{protocol['prompt_version']}"
    )


def _extract_json(text):
    if not isinstance(text, str) or not text.strip():
        raise AiReviewProviderError("模型返回了空内容")
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(stripped[start:end + 1])
            except json.JSONDecodeError:
                pass
    raise AiReviewProviderError("模型没有返回有效 JSON")


def validate_model_ratings(value, packet):
    ratings = value.get("ratings") if isinstance(value, dict) else None
    if not isinstance(ratings, list):
        raise AiReviewProviderError("模型响应缺少 ratings 数组")
    dimension_ids = {item["id"] for item in packet["dimensions"]}
    allowed = set(packet["rating_scale"]["allowed_values"])
    submitted = [item.get("dimension_id") for item in ratings if isinstance(item, dict)]
    if len(submitted) != len(set(submitted)) or set(submitted) != dimension_ids:
        raise AiReviewProviderError("模型响应的维度集合不完整或存在重复")
    normalized = []
    for item in ratings:
        score = item.get("score")
        rationale = item.get("rationale", "")
        if score is not None and score not in allowed:
            raise AiReviewProviderError(f"{item['dimension_id']} 分值不在允许量尺中")
        if not isinstance(rationale, str):
            raise AiReviewProviderError(f"{item['dimension_id']} 的依据必须是文本")
        if score is not None and not rationale.strip():
            raise AiReviewProviderError(f"{item['dimension_id']} 缺少判断依据")
        normalized.append({
            "dimension_id": item["dimension_id"],
            "score": score,
            "rationale": rationale.strip(),
        })
    order = {item["id"]: index for index, item in enumerate(packet["dimensions"])}
    return sorted(normalized, key=lambda item: order[item["dimension_id"]])


def _request_json(url, method="GET", payload=None, api_key="", timeout=120):
    headers = {"Accept": "application/json", "User-Agent": "ZhouYiLab-AI-Review/0.1"}
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise AiReviewProviderError(f"模型服务返回 HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise AiReviewProviderError(f"无法连接模型服务：{error.reason}") from error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise AiReviewProviderError(f"模型服务响应无效：{error}") from error


def test_provider_connection(provider, protocol):
    provider = validate_provider(provider, protocol)
    timeout = min(protocol["run_policy"]["request_timeout_seconds"], 20)
    started = time.monotonic()
    if provider["protocol"] == "ollama":
        response = _request_json(
            provider["base_url"] + "/api/tags", timeout=timeout
        )
        models = [item.get("name") for item in response.get("models", []) if item.get("name")]
    else:
        response = _request_json(
            provider["base_url"] + "/models",
            api_key=provider["api_key"],
            timeout=timeout,
        )
        models = [item.get("id") for item in response.get("data", []) if item.get("id")]
    return {
        "reachable": True,
        "latency_ms": round((time.monotonic() - started) * 1000),
        "configured_model_found": provider["model"] in models,
        "available_models": models[:100],
        "provider": redacted_provider(provider),
    }


def call_model(provider, prompt, protocol):
    timeout = protocol["run_policy"]["request_timeout_seconds"]
    if provider["protocol"] == "ollama":
        response = _request_json(
            provider["base_url"] + "/api/chat",
            method="POST",
            payload={
                "model": provider["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": provider["temperature"],
                    **({"seed": provider["model_seed"]} if provider["model_seed"] is not None else {}),
                },
            },
            timeout=timeout,
        )
        return response.get("message", {}).get("content", ""), {
            "input_tokens": response.get("prompt_eval_count"),
            "output_tokens": response.get("eval_count"),
        }
    response = _request_json(
        provider["base_url"] + "/chat/completions",
        method="POST",
        api_key=provider["api_key"],
        payload={
            "model": provider["model"],
            "temperature": provider["temperature"],
            **({"seed": provider["model_seed"]} if provider["model_seed"] is not None else {}),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    choices = response.get("choices", [])
    if not choices:
        raise AiReviewProviderError("模型响应缺少 choices")
    usage = response.get("usage", {})
    return choices[0].get("message", {}).get("content", ""), {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
    }


class AiReviewStore:
    def __init__(self, path=DEFAULT_DATABASE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self):
        with self.connect() as connection:
            connection.executescript("""
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS ai_review_experiments (
                    id TEXT PRIMARY KEY,
                    packet_id TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_tasks INTEGER NOT NULL,
                    completed_tasks INTEGER NOT NULL DEFAULT 0,
                    failed_tasks INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    provider_config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS ai_review_runs (
                    id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL REFERENCES ai_review_experiments(id) ON DELETE CASCADE,
                    provider_id TEXT NOT NULL,
                    provider_label TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_family TEXT NOT NULL,
                    repetition INTEGER NOT NULL,
                    case_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    prompt_hash TEXT NOT NULL,
                    raw_response TEXT,
                    error_message TEXT,
                    latency_ms INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    UNIQUE(experiment_id, provider_id, repetition, case_code)
                );
                CREATE TABLE IF NOT EXISTS ai_review_ratings (
                    run_id TEXT NOT NULL REFERENCES ai_review_runs(id) ON DELETE CASCADE,
                    dimension_id TEXT NOT NULL,
                    score REAL,
                    rationale TEXT NOT NULL,
                    PRIMARY KEY(run_id, dimension_id)
                );
            """)
            connection.execute(
                "UPDATE ai_review_experiments SET status = 'interrupted', completed_at = ? WHERE status IN ('queued', 'running')",
                (_utc_now(),),
            )

    def create_experiment(self, experiment_id, packet, seed, protocol, providers):
        total = len(packet["cases"]) * sum(item["repetitions"] for item in providers)
        redacted = [redacted_provider(item) for item in providers]
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO ai_review_experiments
                (id, packet_id, seed, prompt_version, status, total_tasks, provider_config_json, created_at)
                VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)
            """, (
                experiment_id, packet["packet_id"], seed, protocol["prompt_version"],
                total, json.dumps(redacted, ensure_ascii=False), _utc_now(),
            ))

    def list_experiments(self):
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ai_review_experiments ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
        return [self._experiment_dict(row) for row in rows]

    def get_experiment(self, experiment_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM ai_review_experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
        if not row:
            raise AiReviewError("实验不存在")
        return self._experiment_dict(row)

    def _experiment_dict(self, row):
        item = dict(row)
        item["providers"] = json.loads(item.pop("provider_config_json"))
        item["cancel_requested"] = bool(item["cancel_requested"])
        item["progress_percent"] = round(
            (item["completed_tasks"] + item["failed_tasks"]) / item["total_tasks"] * 100, 1
        ) if item["total_tasks"] else 0
        return item

    def mark_running(self, experiment_id):
        with self.connect() as connection:
            connection.execute(
                "UPDATE ai_review_experiments SET status = 'running', started_at = ? WHERE id = ?",
                (_utc_now(), experiment_id),
            )

    def is_cancel_requested(self, experiment_id):
        with self.connect() as connection:
            row = connection.execute(
                "SELECT cancel_requested FROM ai_review_experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
        return bool(row and row[0])

    def request_cancel(self, experiment_id):
        with self.connect() as connection:
            cursor = connection.execute(
                "UPDATE ai_review_experiments SET cancel_requested = 1 WHERE id = ? AND status IN ('queued', 'running')",
                (experiment_id,),
            )
        if cursor.rowcount == 0:
            raise AiReviewError("实验不存在或已经结束")

    def begin_run(self, experiment_id, provider, repetition, case_code, prompt_hash):
        run_id = uuid.uuid4().hex
        with self.connect() as connection:
            connection.execute("""
                INSERT INTO ai_review_runs
                (id, experiment_id, provider_id, provider_label, protocol, base_url, model, model_family,
                 repetition, case_code, status, prompt_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """, (
                run_id, experiment_id, provider["provider_id"], provider["label"],
                provider["protocol"], provider["base_url"], provider["model"],
                provider["model_family"], repetition, case_code, prompt_hash, _utc_now(),
            ))
        return run_id

    def finish_run(self, experiment_id, run_id, ratings, raw_response, attempts, latency_ms, usage):
        with self.connect() as connection:
            connection.executemany(
                "INSERT INTO ai_review_ratings (run_id, dimension_id, score, rationale) VALUES (?, ?, ?, ?)",
                [(run_id, item["dimension_id"], item["score"], item["rationale"]) for item in ratings],
            )
            connection.execute("""
                UPDATE ai_review_runs SET status = 'completed', attempts = ?, raw_response = ?,
                    latency_ms = ?, input_tokens = ?, output_tokens = ?, completed_at = ? WHERE id = ?
            """, (
                attempts, raw_response, latency_ms, usage.get("input_tokens"),
                usage.get("output_tokens"), _utc_now(), run_id,
            ))
            connection.execute(
                "UPDATE ai_review_experiments SET completed_tasks = completed_tasks + 1 WHERE id = ?",
                (experiment_id,),
            )

    def fail_run(self, experiment_id, run_id, raw_response, attempts, latency_ms, message):
        with self.connect() as connection:
            connection.execute("""
                UPDATE ai_review_runs SET status = 'failed', attempts = ?, raw_response = ?,
                    latency_ms = ?, error_message = ?, completed_at = ? WHERE id = ?
            """, (attempts, raw_response, latency_ms, message[:2000], _utc_now(), run_id))
            connection.execute(
                "UPDATE ai_review_experiments SET failed_tasks = failed_tasks + 1 WHERE id = ?",
                (experiment_id,),
            )

    def finish_experiment(self, experiment_id, status):
        with self.connect() as connection:
            connection.execute(
                "UPDATE ai_review_experiments SET status = ?, completed_at = ? WHERE id = ?",
                (status, _utc_now(), experiment_id),
            )

    def results(self, experiment_id, packet):
        experiment = self.get_experiment(experiment_id)
        with self.connect() as connection:
            rows = connection.execute("""
                SELECT r.provider_id, r.provider_label, r.model, r.model_family, r.repetition, r.case_code,
                       r.status, r.error_message, d.dimension_id, d.score, d.rationale
                FROM ai_review_runs r
                LEFT JOIN ai_review_ratings d ON d.run_id = r.id
                WHERE r.experiment_id = ?
                ORDER BY r.provider_label, r.repetition, r.case_code, d.dimension_id
            """, (experiment_id,)).fetchall()
        dimensions = []
        for dimension in packet["dimensions"]:
            dimension_rows = [row for row in rows if row["dimension_id"] == dimension["id"]]
            summary = summarize_dimension_rows(dimension_rows)
            model_case_scores = summary.pop("model_case_scores")
            total = len(model_case_scores)
            dimensions.append({
                "dimension_id": dimension["id"],
                "name": dimension["name"],
                "score_count": total,
                "explicit_null_count": sum(row["score"] is None for row in dimension_rows),
                "mean_score": round(sum(model_case_scores) / total, 4) if total else None,
                **summary,
                # Compatibility alias. From schema 0.2.0 onward this is true same-case agreement.
                "cross_model_descriptive_consensus_ratio": summary[
                    "within_case_cross_model_agreement"
                ],
                "interpretation": "within_case_descriptive_only_not_human_agreement",
            })
        provider_stability = []
        provider_index = {
            item["provider_id"]: item for item in experiment["providers"]
        }
        for provider_id, provider in provider_index.items():
            dimension_stability = []
            for dimension in packet["dimensions"]:
                case_scores = {}
                for row in rows:
                    if (
                        row["provider_id"] == provider_id
                        and row["dimension_id"] == dimension["id"]
                        and row["score"] is not None
                    ):
                        case_scores.setdefault(row["case_code"], []).append(row["score"])
                matches = 0
                pairs = 0
                for values in case_scores.values():
                    for left in range(len(values)):
                        for right in range(left + 1, len(values)):
                            pairs += 1
                            matches += values[left] == values[right]
                dimension_stability.append({
                    "dimension_id": dimension["id"],
                    "name": dimension["name"],
                    "exact_pair_agreement": round(matches / pairs, 4) if pairs else None,
                    "comparable_pairs": pairs,
                    "status": "descriptive" if pairs else "not_computed_single_repetition",
                })
            comparable = [
                item["exact_pair_agreement"] for item in dimension_stability
                if item["exact_pair_agreement"] is not None
            ]
            provider_stability.append({
                "provider_id": provider_id,
                "provider_label": provider["label"],
                "model": provider["model"],
                "model_family": provider["model_family"],
                "repetitions": provider["repetitions"],
                "mean_exact_pair_agreement": (
                    round(sum(comparable) / len(comparable), 4) if comparable else None
                ),
                "dimensions": dimension_stability,
                "interpretation": "within_model_repeatability_not_independent_experts",
            })
        run_items = []
        grouped = {}
        for row in rows:
            key = (row["provider_id"], row["repetition"], row["case_code"])
            item = grouped.setdefault(key, {
                "provider_id": row["provider_id"], "provider_label": row["provider_label"],
                "model": row["model"], "model_family": row["model_family"], "repetition": row["repetition"],
                "case_code": row["case_code"], "status": row["status"],
                "error_message": row["error_message"], "ratings": [],
            })
            if row["dimension_id"]:
                item["ratings"].append({
                    "dimension_id": row["dimension_id"], "score": row["score"],
                    "rationale": row["rationale"],
                })
        run_items.extend(grouped.values())
        return {
            "results_schema_version": "0.2.0",
            "experiment": experiment,
            "report_label": "AI 多模型定性预评审",
            "interpretation_boundary": {
                "model_runs_are_not_human_raters": True,
                "repeated_runs_are_not_independent_experts": True,
                "agreement_is_descriptive_only": True,
                "may_create_numeric_star_weights": False,
            },
            "dimensions": dimensions,
            "provider_stability": provider_stability,
            "runs": run_items,
        }


class AiReviewService:
    def __init__(self, database_path=DEFAULT_DATABASE_PATH, provider_config_path=None):
        self.protocol = load_ai_review_protocol()
        self.resources, self.blind_protocol = load_blind_review_resources()
        if self.protocol["blind_review_protocol_id"] != self.blind_protocol["id"]:
            raise ResearchConfigError("AI 协议引用了错误的盲评协议")
        self.store = AiReviewStore(database_path)
        self.provider_config_path = provider_config_path
        self._threads = {}
        self._lock = threading.Lock()

    def packet(self, seed):
        return generate_blind_packet(self.resources, self.blind_protocol, seed)[0]

    def configured_providers(self):
        return load_provider_catalog(self.protocol, self.provider_config_path)

    def provider_meta(self):
        path, providers = self.configured_providers()
        return {
            "config_path": str(path),
            "providers": [redacted_provider(item) for item in providers],
        }

    def resolve_provider(self, provider_id, overrides=None):
        _, providers = self.configured_providers()
        provider = next((item for item in providers if item["provider_id"] == provider_id), None)
        if provider is None:
            raise AiReviewError(f"模型连接不存在或未启用：{provider_id}")
        provider = dict(provider)
        overrides = overrides or {}
        for field in ("temperature", "repetitions", "model_seed"):
            if field in overrides:
                provider[field] = overrides[field]
        return validate_provider(provider, self.protocol)

    def test_connection(self, provider_id):
        return test_provider_connection(
            self.resolve_provider(provider_id), self.protocol
        )

    def create_experiment(self, payload):
        seed = str(payload.get("seed") or "pilot-2026")
        if len(seed) > 128:
            raise AiReviewError("seed 长度不能超过 128 个字符")
        provider_ids = payload.get("provider_ids")
        if not isinstance(provider_ids, list) or len(provider_ids) < self.protocol["run_policy"]["minimum_models"]:
            raise AiReviewError("至少需要一个模型连接")
        if len(provider_ids) > 10:
            raise AiReviewError("单次实验最多允许 10 个模型连接")
        if any(not isinstance(item, str) for item in provider_ids):
            raise AiReviewError("provider_ids 必须是字符串数组")
        overrides = payload.get("overrides") or {}
        if not isinstance(overrides, dict):
            raise AiReviewError("overrides 必须是对象")
        providers = [
            self.resolve_provider(provider_id, overrides.get(provider_id))
            for provider_id in provider_ids
        ]
        ids = [item["provider_id"] for item in providers]
        if len(ids) != len(set(ids)):
            raise AiReviewError("模型连接 ID 不能重复")
        packet = self.packet(seed)
        experiment_id = "air-" + uuid.uuid4().hex[:16]
        self.store.create_experiment(experiment_id, packet, seed, self.protocol, providers)
        thread = threading.Thread(
            target=self._run_experiment,
            args=(experiment_id, packet, providers),
            name=f"ai-review-{experiment_id}",
            daemon=True,
        )
        with self._lock:
            self._threads[experiment_id] = thread
        thread.start()
        return self.store.get_experiment(experiment_id)

    def _run_experiment(self, experiment_id, packet, providers):
        self.store.mark_running(experiment_id)
        try:
            for provider in providers:
                provider_blocked_error = None
                for repetition in range(1, provider["repetitions"] + 1):
                    for case_data in packet["cases"]:
                        if self.store.is_cancel_requested(experiment_id):
                            self.store.finish_experiment(experiment_id, "cancelled")
                            return
                        prompt = build_case_prompt(packet, case_data, self.protocol)
                        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                        run_id = self.store.begin_run(
                            experiment_id, provider, repetition, case_data["case_code"], prompt_hash
                        )
                        if provider_blocked_error:
                            self.store.fail_run(
                                experiment_id, run_id, "", 0, 0,
                                f"连接已停止：{provider_blocked_error}",
                            )
                            continue
                        started = time.monotonic()
                        raw = ""
                        last_error = None
                        usage = {}
                        maximum = self.protocol["run_policy"]["maximum_retry_attempts"] + 1
                        for attempt in range(1, maximum + 1):
                            try:
                                active_prompt = prompt if attempt == 1 else (
                                    prompt + "\n\n上一次响应未通过格式校验。请重新生成完整、合法且只包含 JSON 的响应。"
                                )
                                raw, usage = call_model(provider, active_prompt, self.protocol)
                                ratings = validate_model_ratings(_extract_json(raw), packet)
                                self.store.finish_run(
                                    experiment_id, run_id, ratings, raw, attempt,
                                    round((time.monotonic() - started) * 1000), usage,
                                )
                                break
                            except AiReviewError as error:
                                last_error = error
                        else:
                            self.store.fail_run(
                                experiment_id, run_id, raw, maximum,
                                round((time.monotonic() - started) * 1000), str(last_error),
                            )
                            message = str(last_error)
                            permanent_prefixes = (
                                "无法连接模型服务",
                                "模型服务返回 HTTP 401",
                                "模型服务返回 HTTP 403",
                                "模型服务返回 HTTP 404",
                            )
                            if message.startswith(permanent_prefixes):
                                provider_blocked_error = message
            experiment = self.store.get_experiment(experiment_id)
            status = "completed_with_errors" if experiment["failed_tasks"] else "completed"
            self.store.finish_experiment(experiment_id, status)
        except Exception as error:
            self.store.finish_experiment(experiment_id, "failed")
            print(f"[ai-review] experiment={experiment_id} failed: {error}")
        finally:
            with self._lock:
                self._threads.pop(experiment_id, None)

    def results(self, experiment_id):
        experiment = self.store.get_experiment(experiment_id)
        return self.store.results(experiment_id, self.packet(experiment["seed"]))
