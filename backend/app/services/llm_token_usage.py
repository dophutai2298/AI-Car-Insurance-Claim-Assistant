from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any


# Uvicorn owns the development server's INFO handler, so usage lines are visible
# without changing global application logging levels.
logger = logging.getLogger("uvicorn.error")


def _value(source: object, key: str) -> object | None:
    if isinstance(source, Mapping):
        return source.get(key)
    return getattr(source, key, None)


def _integer(source: object, *keys: str) -> int | None:
    for key in keys:
        value = _value(source, key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _usage_from_response(response: object) -> tuple[int, int, int] | None:
    raw_response: Any = response
    if isinstance(response, Mapping) and "raw" in response:
        raw_response = response.get("raw")
    if raw_response is None:
        return None

    usage = _value(raw_response, "usage_metadata")
    if usage:
        input_tokens = _integer(usage, "input_tokens")
        output_tokens = _integer(usage, "output_tokens")
        total_tokens = _integer(usage, "total_tokens")
    else:
        response_metadata = _value(raw_response, "response_metadata") or {}
        usage = _value(response_metadata, "token_usage") or {}
        input_tokens = _integer(usage, "input_tokens", "prompt_tokens")
        output_tokens = _integer(usage, "output_tokens", "completion_tokens")
        total_tokens = _integer(usage, "total_tokens")

    if input_tokens is None or output_tokens is None:
        return None
    return input_tokens, output_tokens, total_tokens or input_tokens + output_tokens


def log_llm_token_usage(
    *,
    enabled: bool,
    operation: str,
    document_type: str,
    model: str,
    response: object,
    field_key: str | None = None,
) -> None:
    """Log provider-reported usage without logging prompts, OCR text, or model output."""
    if not enabled:
        return

    context = (
        f"operation={operation} document={document_type} model={model}"
        + (f" field={field_key}" if field_key else "")
    )
    usage = _usage_from_response(response)
    if usage is None:
        logger.info("[LLM_TOKEN_USAGE] %s status=unavailable", context)
        return

    input_tokens, output_tokens, total_tokens = usage
    logger.info(
        "[LLM_TOKEN_USAGE] %s input_tokens=%d output_tokens=%d total_tokens=%d",
        context,
        input_tokens,
        output_tokens,
        total_tokens,
    )
