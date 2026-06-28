"""
LLM client (provider-agnostic).

One job: send a system prompt + a user prompt and return the model's text.
Supports Anthropic (default) and OpenAI. The actual SDK is imported lazily
inside each helper, so you only need the library for the provider you use.
"""
from __future__ import annotations

from config.settings import LLM


class LLMNotConfigured(Exception):
    """Raised when no API key is set. The pipeline catches this and falls
    back to 'Unknown' answers instead of crashing."""


def is_available() -> bool:
    return LLM.is_configured


def complete(system: str, user: str) -> str:
    if not LLM.is_configured:
        raise LLMNotConfigured("No LLM API key configured. See the .env file.")
    if LLM.provider == "anthropic":
        return _anthropic(system, user)
    if LLM.provider == "openai":
        return _openai(system, user)
    raise LLMNotConfigured(f"Unknown LLM provider: {LLM.provider}")


def _anthropic(system: str, user: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=LLM.anthropic_api_key)
    msg = client.messages.create(
        model=LLM.anthropic_model,
        max_tokens=LLM.max_tokens,
        temperature=LLM.temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _openai(system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=LLM.openai_api_key)
    resp = client.chat.completions.create(
        model=LLM.openai_model,
        max_tokens=LLM.max_tokens,
        temperature=LLM.temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def complete_claude_knowledge(system: str, user: str) -> str:
    """Always calls Claude (Anthropic) directly, with no evidence attached.
    Used ONLY by the optional knowledge fallback
    (intelligence/knowledge_fallback.py) for questions still Unknown after
    research. Reuses the same ANTHROPIC_API_KEY as the main pipeline above —
    no separate key needed."""
    from config.settings import KNOWLEDGE_FALLBACK

    if not KNOWLEDGE_FALLBACK.is_configured:
        raise LLMNotConfigured("No ANTHROPIC_API_KEY configured for the Claude fallback.")

    from anthropic import Anthropic

    client = Anthropic(api_key=LLM.anthropic_api_key)
    msg = client.messages.create(
        model=KNOWLEDGE_FALLBACK.model,
        max_tokens=300,
        temperature=0.0,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")