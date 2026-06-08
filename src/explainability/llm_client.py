"""LLM client: Groq as primary inference provider, Gemini as fallback."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-pro:generateContent"
)


def _call_groq(prompt: str, api_key: str) -> Optional[str]:
    """Return the Groq completion text, or None on any failure."""
    try:
        response = httpx.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("Groq call failed: %s", exc)
        return None


def _call_gemini(prompt: str, api_key: str) -> Optional[str]:
    """Return the Gemini completion text, or None on any failure."""
    try:
        response = httpx.post(
            f"{_GEMINI_URL}?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


def explain(
    prompt: str,
    groq_api_key: str = "",
    gemini_api_key: str = "",
) -> str:
    """Return an LLM explanation for *prompt*, trying Groq then Gemini as fallback."""
    if groq_api_key:
        result = _call_groq(prompt, groq_api_key)
        if result:
            return result

    if gemini_api_key:
        result = _call_gemini(prompt, gemini_api_key)
        if result:
            return result

    return "[No LLM explanation available — set GROQ_API_KEY or GEMINI_API_KEY in .env]"
