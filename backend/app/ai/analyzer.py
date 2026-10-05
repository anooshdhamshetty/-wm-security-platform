"""
LLM security analysis module.

This module is the ONLY place in the platform that calls an LLM. It is used
purely as a reasoning/correlation layer over evidence that was already
collected by deterministic tools (httpx runner, evidence engine, static
analyzers). It never performs HTTP testing itself and never invents
evidence that wasn't passed to it.

Two providers are supported, selected via LLM_PROVIDER in .env:
  - "groq"      (default): Groq's OpenAI-compatible chat completions API
  - "anthropic": Anthropic's Messages API

If the selected provider has no API key configured, analyze_evidence()
returns a deterministic "inconclusive" result rather than silently skipping
analysis, so the pipeline degrades gracefully instead of pretending nothing
happened.
"""
import json
import re
from typing import Optional, Dict, Any

import requests

from app.config import get_settings
from app.ai.prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_TEMPLATE

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _fallback_result(reason: str) -> Dict[str, Any]:
    return {
        "is_expected_behavior": None,
        "could_be_vulnerability": None,
        "security_principle_violated": None,
        "supporting_evidence": reason,
        "related_code_path": None,
        "potential_impact": None,
        "additional_validation_required": "LLM analysis unavailable: " + reason,
        "confidence": "low",
        "verdict": "inconclusive",
        "recommended_fix": None,
    }


def _extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


import time

def _call_groq(settings, user_prompt: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY:
        return _fallback_result("GROQ_API_KEY is not configured.")
    for attempt in range(3):
        try:
            resp = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 700,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = _extract_json(raw_text)
            if parsed is None:
                return _fallback_result("Could not parse Groq response as JSON.")
            return parsed
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(2)
                continue
            return _fallback_result(f"Groq API request failed: {e}")
        except (KeyError, IndexError):
            return _fallback_result("Unexpected Groq API response shape.")


def _call_anthropic(settings, user_prompt: str) -> Dict[str, Any]:
    if not settings.ANTHROPIC_API_KEY:
        return _fallback_result("ANTHROPIC_API_KEY is not configured.")
    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": settings.ANTHROPIC_MODEL,
                "max_tokens": 700,
                "system": ANALYSIS_SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        raw_text = "\n".join(text_blocks)
        parsed = _extract_json(raw_text)
        if parsed is None:
            return _fallback_result("Could not parse Anthropic response as JSON.")
        return parsed
    except requests.RequestException as e:
        return _fallback_result(f"Anthropic API request failed: {e}")


def analyze_evidence(
    method: str,
    path: str,
    category: str,
    description: str,
    expected_behavior: str,
    actual_behavior: str,
    status_code: Optional[int],
    security_headers: Dict[str, Any],
    body_preview: str,
    code_location: Optional[str],
    static_context: Optional[str] = None,
) -> Dict[str, Any]:
    settings = get_settings()

    user_prompt = ANALYSIS_USER_TEMPLATE.format(
        method=method, path=path, category=category, description=description,
        expected_behavior=expected_behavior, actual_behavior=actual_behavior,
        status_code=status_code, security_headers=json.dumps(security_headers),
        body_preview=body_preview[:800], code_location=code_location or "unknown",
        static_context=static_context or "none",
    )

    if settings.LLM_PROVIDER == "anthropic":
        return _call_anthropic(settings, user_prompt)

    # default / "groq"
    return _call_groq(settings, user_prompt)
