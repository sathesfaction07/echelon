"""Bedrock/Claude client for delegate-chain.

Distilled from the proven pattern in ``validator/ai_validator.py`` (invoke +
retries + JSON parsing + disk cache + cost estimation), repackaged as a small
reusable class so every LevelAgent shares one code path. Model keys match that
module's registry so the two stay interchangeable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

    HAS_BOTO3 = True
except ImportError:  # pragma: no cover
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)

# Model registry — keys mirror validator/ai_validator.py.
MODELS = {
    "sonnet-4.5": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus-4.1": "us.anthropic.claude-opus-4-1-20250805-v1:0",
    "sonnet-4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "sonnet-3.7": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "haiku-3.5": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "haiku-3": "anthropic.claude-3-haiku-20240307-v1:0",
}

# USD per 1M tokens.
PRICING = {
    MODELS["sonnet-4.5"]: {"input": 3.00, "output": 15.00},
    MODELS["opus-4.1"]: {"input": 15.00, "output": 75.00},
    MODELS["sonnet-4"]: {"input": 3.00, "output": 15.00},
    MODELS["sonnet-3.7"]: {"input": 3.00, "output": 15.00},
    MODELS["haiku-3.5"]: {"input": 0.80, "output": 4.00},
    MODELS["haiku-3"]: {"input": 0.25, "output": 1.25},
}

DEFAULT_MODEL_KEY = "sonnet-4.5"

# Default AWS profile used for Bedrock; override via AWS_PROFILE env var.
DEFAULT_PROFILE = os.getenv("AWS_PROFILE", "default")


@dataclass
class LLMResponse:
    text: str
    usage: dict = field(default_factory=dict)
    model: str = ""
    cost_usd: float = 0.0
    cached: bool = False


def resolve_model(model_key_or_id: Optional[str]) -> str:
    """Accept a friendly key ('opus-4.1'), a raw Bedrock id, or None."""
    if not model_key_or_id:
        return MODELS[DEFAULT_MODEL_KEY]
    if model_key_or_id in MODELS:
        return MODELS[model_key_or_id]
    return model_key_or_id  # assume caller passed a full model id


def estimate_cost(usage: dict, model_id: str) -> float:
    if not usage:
        return 0.0
    rates = PRICING.get(model_id, PRICING[MODELS[DEFAULT_MODEL_KEY]])
    return round(
        (usage.get("input_tokens", 0) / 1_000_000) * rates["input"]
        + (usage.get("output_tokens", 0) / 1_000_000) * rates["output"],
        6,
    )


def parse_json_response(text: str) -> Optional[Any]:
    """Best-effort JSON extraction (handles ```json fences and prose wrappers)."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


class BedrockLLM:
    """Thin, cached wrapper over Bedrock's Anthropic messages API."""

    def __init__(
        self,
        region: Optional[str] = None,
        profile: Optional[str] = None,
        cache_dir: str = ".delegate_cache",
        cache_enabled: bool = True,
        max_retries: int = 3,
        read_timeout: int = 300,
    ):
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        # Pin to DEFAULT_PROFILE unless a caller explicitly overrides it.
        self.profile = profile or DEFAULT_PROFILE
        # A named profile must win: drop any (stale) creds the environment/.env
        # injected so boto3 resolves the profile's credentials instead.
        if self.profile:
            for _k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
                os.environ.pop(_k, None)
        self.cache_dir = cache_dir
        self.cache_enabled = cache_enabled
        self.max_retries = max_retries
        self.read_timeout = read_timeout
        self._client = None
        self.total_cost_usd = 0.0

    # -- client -------------------------------------------------------------
    @property
    def client(self):
        if self._client is None:
            if not HAS_BOTO3:
                raise RuntimeError("boto3 is not installed; cannot reach Bedrock.")
            session = boto3.Session(profile_name=self.profile) if self.profile else boto3.Session()
            # Opus can take >60s (the default) to generate thousands of tokens; raise the
            # read timeout and let our own loop handle retries (disable botocore's).
            cfg = Config(
                read_timeout=self.read_timeout, connect_timeout=15, retries={"max_attempts": 0}
            )
            self._client = session.client("bedrock-runtime", region_name=self.region, config=cfg)
        return self._client

    def available(self) -> bool:
        try:
            _ = self.client
            return True
        except Exception as e:  # pragma: no cover
            logger.error("Bedrock unavailable: %s", e)
            return False

    # -- cache --------------------------------------------------------------
    def _cache_key(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        blob = f"{model_id}|{max_tokens}|{temperature}|{system_prompt}|{user_prompt}"
        return hashlib.md5(blob.encode()).hexdigest()[:24]

    def _load_cache(self, key: str) -> Optional[dict]:
        if not self.cache_enabled:
            return None
        path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def _save_cache(self, key: str, data: dict) -> None:
        if not self.cache_enabled:
            return
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(os.path.join(self.cache_dir, f"{key}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    # -- tool-use invocation (stateful; no cache) --------------------------
    def invoke_tools(
        self,
        system_prompt: str,
        messages: list,
        tools: Optional[list] = None,
        model_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        """Raw Anthropic-on-Bedrock messages call with tool-use support.

        `messages` is the running conversation (list of {role, content}); returns
        the parsed result dict (content blocks + stop_reason + usage). Cost is
        tracked; a `_cost_usd` key is added. Not cached (tool loops are stateful).
        """
        model_id = resolve_model(model_key)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            body["tools"] = tools
        last_err = "unknown error"
        for attempt in range(self.max_retries):
            try:
                resp = self.client.invoke_model(
                    modelId=model_id, body=json.dumps(body), contentType="application/json"
                )
                result = json.loads(resp["body"].read())
                cost = estimate_cost(result.get("usage", {}), model_id)
                self.total_cost_usd += cost
                result["_cost_usd"] = cost
                return result
            except ClientError as e:  # type: ignore[misc]
                code = e.response["Error"]["Code"]
                last_err = f"{code}: {e.response['Error']['Message']}"
                if code in ("ThrottlingException", "ServiceUnavailableException"):
                    time.sleep(2**attempt)
                    continue
                break
            except (ReadTimeoutError, ConnectTimeoutError) as e:
                last_err = f"timeout: {e}"
                time.sleep(2**attempt)
                continue
            except Exception as e:  # pragma: no cover
                last_err = f"Invocation error: {e}"
                break
        raise RuntimeError(f"Bedrock invoke_tools failed: {last_err}")

    def embed(self, texts: list, model_id: str = "amazon.titan-embed-text-v2:0") -> list:
        """Embed a list of strings via Bedrock Titan; returns vectors. Cost metered."""
        vecs = []
        for t in texts:
            resp = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps({"inputText": t[:8000]}),
                contentType="application/json",
            )
            body = json.loads(resp["body"].read())
            vecs.append(body["embedding"])
            # Titan Text Embeddings V2: ~$0.02 / 1M input tokens.
            toks = body.get("inputTextTokenCount") or (len(t[:8000]) // 4)
            self.total_cost_usd += (toks / 1_000_000) * 0.02
        return vecs

    # -- invocation ---------------------------------------------------------
    def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        model_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> LLMResponse:
        model_id = resolve_model(model_key)

        key = self._cache_key(system_prompt, user_prompt, model_id, max_tokens, temperature)
        cached = self._load_cache(key)
        if cached:
            return LLMResponse(
                text=cached["text"],
                usage=cached.get("usage", {}),
                model=model_id,
                cost_usd=0.0,
                cached=True,
            )

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        last_err = "unknown error"
        bumped = False  # allow one automatic max_tokens bump on truncation
        for attempt in range(self.max_retries):
            try:
                resp = self.client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                )
                result = json.loads(resp["body"].read())
                text = result["content"][0]["text"]
                usage = result.get("usage", {})
                cost = estimate_cost(usage, model_id)
                self.total_cost_usd += cost
                # If the model was cut off mid-response, the JSON is unclosed.
                # Retry once with a larger budget rather than returning garbage.
                if (
                    result.get("stop_reason") == "max_tokens"
                    and not bumped
                    and body["max_tokens"] < 16384
                ):
                    body["max_tokens"] = min(body["max_tokens"] * 2, 16384)
                    bumped = True
                    logger.warning(
                        "Response truncated; retrying with max_tokens=%d", body["max_tokens"]
                    )
                    continue
                self._save_cache(key, {"text": text, "usage": usage})
                return LLMResponse(text=text, usage=usage, model=model_id, cost_usd=cost)
            except ClientError as e:  # type: ignore[misc]
                code = e.response["Error"]["Code"]
                last_err = f"{code}: {e.response['Error']['Message']}"
                if code in ("ThrottlingException", "ServiceUnavailableException"):
                    time.sleep(2**attempt)
                    continue
                break
            except (ReadTimeoutError, ConnectTimeoutError) as e:
                last_err = f"timeout: {e}"
                logger.warning("Bedrock timeout (attempt %d); retrying", attempt + 1)
                time.sleep(2**attempt)
                continue
            except Exception as e:  # pragma: no cover
                last_err = f"Invocation error: {e}"
                break
        raise RuntimeError(f"Bedrock invoke failed: {last_err}")
