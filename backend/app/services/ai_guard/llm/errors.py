"""User-facing LLM error messages."""
from __future__ import annotations

from openai import APIStatusError


def format_llm_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, APIStatusError):
        body = exc.body if isinstance(exc.body, dict) else {}
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            msg = err.get("message") or str(exc)
            err_type = err.get("type") or ""
            status = getattr(exc, "status_code", None)
            if err_type == "model_not_found" or "not supported" in msg.lower():
                return f"模型不可用：{msg}。请在「模型」中填写中转站支持的名称。"
            if status == 502 or err_type == "upstream_error":
                return (
                    "中转站上游服务暂时不可用（502 upstream_error）。"
                    "这通常不是 WAF 配置问题，请检查 mxou 账号余额、分组权限、"
                    "服务状态，或稍后重试。"
                )
            if status == 401:
                return "API Key 无效或已过期，请重新填写并保存。"
            return msg
        return str(exc)
    text = str(exc)
    if "502" in text and "upstream" in text.lower():
        return (
            "中转站上游服务暂时不可用（502）。"
            "请检查 mxou 控制台余额/分组状态，或稍后重试。"
        )
    if "上游" in text or "upstream" in text.lower():
        return (
            f"{text}。请确认 API Base URL、模型名称是否正确，"
            "以及中转站账号是否已开通对应模型。"
        )
    return text or "AI 请求失败，请稍后重试。"
