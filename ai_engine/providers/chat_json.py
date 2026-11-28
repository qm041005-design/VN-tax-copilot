"""Configurable HTTPS Chat Completions JSON transport; no vendor/model default.

Expects model/messages/response_format and choices[0].message.content. Endpoints
using other protocols need another adapter. Never log request/response bodies.
"""
import json
import math
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values

from ai_engine.guardrails.provider_errors import SafeProviderError

MAX_REQUEST_BYTES = 256_000
MAX_RESPONSE_BYTES = 1_000_000


def json_object(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("nonfinite JSON")
    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
        if not isinstance(data, dict):
            raise ValueError("object required")
        return data
    except (ValueError, TypeError, RecursionError):
        raise SafeProviderError("provider_invalid_output") from None


@dataclass(frozen=True)
class ChatConfig:
    url: str = field(repr=False)
    model: str
    api_key: str = field(repr=False)
    timeout: float = 30.0
    max_tokens: int = 4096

    def __post_init__(self):
        try:
            parts = urlsplit(self.url)
            valid = (parts.scheme == "https" and parts.hostname and not parts.username and not parts.password
                     and not parts.query and not parts.fragment and self.model.strip() and self.api_key.strip()
                     and math.isfinite(self.timeout) and 0 < self.timeout <= 120
                     and type(self.max_tokens) is int and 1 <= self.max_tokens <= 16384)
        except (ValueError, TypeError, AttributeError):
            valid = False
        if not valid:
            raise SafeProviderError("provider_configuration")

    @classmethod
    def from_env(cls):
        # Same working-directory .env convention as backend settings; OS env wins.
        env = {**dotenv_values(".env"), **os.environ}
        if str(env.get("RESEARCH_AI_ENABLED", "")).lower() != "true":
            raise SafeProviderError("provider_disabled")
        try:
            return cls(str(env.get("RESEARCH_AI_URL") or ""), str(env.get("RESEARCH_AI_MODEL") or ""),
                       str(env.get("RESEARCH_AI_API_KEY") or ""), float(env.get("RESEARCH_AI_TIMEOUT", "30")),
                       int(env.get("RESEARCH_AI_MAX_TOKENS", "4096")))
        except (ValueError, TypeError):
            raise SafeProviderError("provider_configuration") from None


class ChatJSON:
    def __init__(self, config, *, transport=None):
        self.config = config
        self.transport = transport  # httpx.MockTransport in tests; no live fallback.

    def __call__(self, messages):
        if not isinstance(messages, list) or not messages or any(
            not isinstance(m, dict) or set(m) != {"role", "content"} or
            m["role"] not in ("system", "user", "assistant") or not isinstance(m["content"], str)
            for m in messages
        ):
            raise SafeProviderError("provider_configuration")
        payload = {"model": self.config.model, "messages": messages, "response_format": {"type": "json_object"},
                   "max_completion_tokens": self.config.max_tokens}
        body = json.dumps(payload, ensure_ascii=False).encode()
        if len(body) > MAX_REQUEST_BYTES:
            raise SafeProviderError("provider_limit")
        try:
            # No redirects, environment proxies or implicit retries; key goes only to configured endpoint.
            with httpx.Client(timeout=self.config.timeout, follow_redirects=False, trust_env=False,
                              transport=self.transport) as client:
                with client.stream("POST", self.config.url, content=body,
                                   headers={"Authorization": "Bearer " + self.config.api_key,
                                            "Content-Type": "application/json"}) as response:
                    code = response.status_code
                    if code in (401, 403):
                        raise SafeProviderError("provider_auth")
                    if code == 429:
                        raise SafeProviderError("provider_rate_limit")
                    if not 200 <= code < 300:
                        raise SafeProviderError("provider_http")
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise SafeProviderError("provider_limit")
                        chunks.append(chunk)
                    envelope = json_object(b"".join(chunks))
            choices = envelope.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError("choice required")
            choice = choices[0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("truncated/refused output")
            message = choice["message"]
            if message.get("refusal") or message.get("tool_calls"):
                raise ValueError("unsupported output")
            return json_object(message["content"])
        except SafeProviderError:
            raise
        except httpx.TimeoutException:
            raise SafeProviderError("provider_timeout") from None
        except httpx.HTTPError:
            raise SafeProviderError("provider_network") from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise SafeProviderError("provider_invalid_output") from None


def complete(messages):
    """RESEARCH_COMPLETION=ai_engine.providers.chat_json:complete"""
    return ChatJSON(ChatConfig.from_env())(messages)
