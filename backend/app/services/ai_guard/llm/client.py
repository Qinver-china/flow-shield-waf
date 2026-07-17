"""OpenAI-compatible LLM client."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from app.services.ai_guard.config import AiGuardRuntimeConfig

log = logging.getLogger("waf.ai_guard.llm")

# 部分 OpenAI 兼容中转站会拦截官方 SDK 的 User-Agent，导致 chat 返回 502。
_LLM_USER_AGENT = "FlowShield-WAF/1.0"
_LLM_TIMEOUT_SEC = 60.0
_LLM_MAX_ATTEMPTS = 3
_RETRYABLE_STATUS = frozenset({429, 502, 503, 524})


class LlmClient:
    def __init__(self, config: AiGuardRuntimeConfig):
        if not config.api_key:
            raise ValueError("未配置 AI API Key")
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key.strip(),
            base_url=config.provider_base_url.strip().rstrip("/"),
            max_retries=0,
            timeout=_LLM_TIMEOUT_SEC,
            default_headers={"User-Agent": _LLM_USER_AGENT},
        )

    async def _create_completion(self, **kwargs: Any):
        last_exc: Exception | None = None
        for attempt in range(1, _LLM_MAX_ATTEMPTS + 1):
            try:
                return await self._client.chat.completions.create(**kwargs)
            except APIStatusError as exc:
                last_exc = exc
                if exc.status_code in _RETRYABLE_STATUS and attempt < _LLM_MAX_ATTEMPTS:
                    delay = 1.5 * attempt
                    log.warning(
                        "LLM upstream %s on attempt %s/%s, retry in %.1fs",
                        exc.status_code,
                        attempt,
                        _LLM_MAX_ATTEMPTS,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
            except (APITimeoutError, APIConnectionError) as exc:
                last_exc = exc
                if attempt < _LLM_MAX_ATTEMPTS:
                    delay = 1.5 * attempt
                    log.warning(
                        "LLM connection error on attempt %s/%s, retry in %.1fs: %s",
                        attempt,
                        _LLM_MAX_ATTEMPTS,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("LLM request failed without exception")

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._config.temperature,
            "max_tokens": max_tokens or self._config.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await self._create_completion(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        tool_calls = None
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        return {
            "content": msg.content or "",
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
        }

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict] | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        stream = await self._create_completion(**kwargs)
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def chat_json(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        result = await self.chat_completion(
            messages, temperature=temperature, json_mode=True
        )
        raw = result.get("content") or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("LLM returned invalid JSON: %s", raw[:200])
            raise ValueError("AI 返回了无效的 JSON") from exc

    async def list_model_ids(self) -> list[str]:
        page = await self._client.models.list()
        return [m.id for m in (page.data or []) if getattr(m, "id", None)]

    async def test_connection(self) -> str:
        model_ids = await self.list_model_ids()
        if not model_ids:
            raise ValueError("无法获取模型列表，请检查 API Base URL 与 API Key 是否正确。")

        current = self._config.model.strip()
        if current not in model_ids:
            samples = "、".join(model_ids[:6])
            raise ValueError(
                f"模型「{current}」不在中转站可用列表中。可选示例：{samples}"
            )

        try:
            result = await self.chat_completion(
                [{"role": "user", "content": "Reply with exactly: OK"}],
                temperature=0,
                max_tokens=16,
            )
        except APIStatusError as exc:
            if exc.status_code in _RETRYABLE_STATUS:
                raise ValueError(
                    f"聊天接口暂时不可用（HTTP {exc.status_code}），"
                    "多为中转站上游繁忙或限流，请稍后重试。"
                ) from exc
            raise ValueError(f"聊天接口失败：{exc}") from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise ValueError(
                "聊天接口请求超时或网络中断，请稍后重试；"
                "若频繁出现，可尝试更换模型或联系中转站服务商。"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                "API Key 与模型列表校验通过，但聊天接口失败："
                f"{exc}。这通常是中转站上游临时故障、余额不足或账号分组限流，"
                "请到 mxou 控制台检查余额/分组状态，或稍后重试。"
            ) from exc
        return (result.get("content") or "").strip()
