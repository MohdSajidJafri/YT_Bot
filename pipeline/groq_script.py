"""Groq (OpenAI-compatible) — generate Short script + image prompts as JSON.

Supports two modes:
  • Single-language preset (legacy): returns full_narration, youtube_title, etc.
  • Multi-variant preset (bilingual): returns image_prompts once + variants[lang] = {title, desc, narration}.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

try:
    from groq import BadRequestError, Groq
except ImportError:
    Groq = None
    BadRequestError = Exception

from pipeline.channel_presets import ChannelPreset
from pipeline.story_history import history_prompt_block

GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


# ── Language-specific word-count guidance ──────────────────────────────
LANG_WORD_TARGETS = {
    "en": (
        120,
        155,
        "120-155 English words for variants.en.full_narration (~40-50 sec); "
        "add transitions, examples, and a closing takeaway — NOT a bullet list",
    ),
    "hi": (
        135,
        170,
        "135-170 Devanagari Hindi words — aim ~150 (~55-70 sec); full sentences, not headlines",
    ),
}

# Bilingual presets override per variant; these are fallbacks only.
DEFAULT_MIN_WORDS = {"hi": 80, "en": 80}


def _lang_label(lang: str) -> str:
    return {"en": "English", "hi": "Hindi (Devanagari script)"}.get(lang, lang)


def _clean_json_text(text: str) -> str:
    """Extract and clean raw JSON from LLM output (strips markdown fences and repairs syntax)."""
    text = text.strip()
    # Strip markdown fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            text = text.replace("```json", "").replace("```", "").strip()

    # Extract outermost JSON object { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]

    # Remove trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\}\]])", r"\1", text)
    return text


EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff\u2b50-\u2b55\ufe00-\ufe0f\u200d]+",
    flags=re.UNICODE,
)


def sanitize_narration(text: str) -> str:
    """Strip emojis, markdown formatting, brackets, and sound cues that break TTS."""
    clean = EMOJI_PATTERN.sub("", text)
    # Remove bracketed stage directions or sound notes like [screams] or (pause)
    clean = re.sub(r"\[.*?\]|\(.*?\)", "", clean)
    # Remove markdown formatting characters
    clean = re.sub(r"[*_#~`]", "", clean)
    return " ".join(clean.split())


def _parse_json_safely(raw: str) -> dict[str, Any]:
    """Parse JSON with multiple cleanup passes."""
    if not raw or not raw.strip():
        raise ValueError("Empty response string received from Groq")

    # 1. Direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Parse after cleaning markdown fences and trailing commas
    cleaned = _clean_json_text(raw)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # 3. Handle unescaped newlines in JSON strings
    try:
        repaired = re.sub(r'(?<!\\)\n', r'\\n', cleaned)
        data = json.loads(repaired)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    raise ValueError(f"Could not parse valid JSON object from response: {raw[:200]!r}")


def generate_short_pack(
    preset: ChannelPreset,
    *,
    topic_hint: str | None = None,
    channel_id: str | None = None,
) -> dict[str, Any]:
    topic_hint = (topic_hint or os.environ.get("SHORT_TOPIC", "")).strip()

    user = (
        f"Channel style: {preset['label']}.\n"
        f"Create ONE YouTube Short.\n"
    )
    if topic_hint:
        user += f"Topic idea from creator: {topic_hint}\n"

    if channel_id:
        anti_repeat = history_prompt_block(channel_id)
        if anti_repeat:
            user += anti_repeat

    n = preset["segment_count"]
    variants = preset.get("variants") or []

    if variants:
        return _generate_multivariant(preset, user, n, variants)
    return _generate_single(preset, user, n)


# ─────────────────────────────────────────────────────────────────────────
# Single-language path (backward compat for ghost_stories, school_story, etc.)
# ─────────────────────────────────────────────────────────────────────────
def _generate_single(preset: ChannelPreset, user: str, n: int) -> dict[str, Any]:
    language = (preset.get("language") or "en").lower()
    lo, hi, blurb = LANG_WORD_TARGETS.get(language, LANG_WORD_TARGETS["en"])

    if language == "hi":
        narration_rule = (
            '"full_narration": "COMPLETE narration as ONE continuous paragraph in Devanagari Hindi. '
            f'This is what the voice will read aloud. MUST be {blurb}. '
            'Natural spoken Hindi — no segment markers, no numbering, no English transliteration."'
        )
        strict_extra = (
            "- LANGUAGE: full_narration, youtube_title, and youtube_description MUST be in Devanagari Hindi.\n"
            "- image_prompts MUST be in ENGLISH (the image model does not understand Hindi).\n"
            f"- WORD COUNT: full_narration MUST contain {lo}-{hi} Hindi words.\n"
        )
    else:
        narration_rule = (
            '"full_narration": "COMPLETE story/script as one continuous paragraph. This is what the voice will read. '
            f'Must be {blurb}. Natural narration — no segment breaks, no numbering."'
        )
        strict_extra = f"- full_narration is ONE continuous paragraph, {lo}-{hi} English words.\n"

    user += f"""
Return ONLY valid JSON with this shape:
{{
  "youtube_title": "high-CTR curiosity-gap title under 55 characters (e.g. warning, impossible mystery, or first-person eerie encounter) with 1 relevant emoji (no hashtags)",
  "youtube_description": "2-3 suspenseful sentences setting the stage + #Shorts",
  "pinned_comment": "a provocative open-ended question (under 160 characters) asking viewers what they would do in this exact situation to spark comments",
  {narration_rule},
  "image_prompts": [
    "visual description for image 1: setting, subject, action. No style words. No text in image.",
    "visual description for image 2...",
    "..."
  ]
}}

STRICT RULES:
{strict_extra}- "image_prompts" array MUST have exactly {n} entries.
- Each image_prompt matches a different moment/beat in order.
- Image prompts are just visuals — no narration text, no style words, no quotes.
- The narration must flow naturally as one spoken piece (no "segment 1", "segment 2" etc).
- The FIRST sentence must be a hard hook: a direct question, a disturbing claim, or a curiosity gap.
- Reveal the climax or key mystery only near the final third; do not explain everything too early.
- The LAST sentence must deliver the final chilling punchline or loop cleanly into sentence 1. NEVER include outro phrases like 'subscribe', 'follow for more', or 'like this video'.
- ZERO EMOJIS: full_narration must contain ABSOLUTELY ZERO emojis, zero symbols, and zero stage directions (like [laughter] or *whispers*). Emojis cause speech synthesis errors. Plain spoken words only.
"""

    max_attempts = 3
    last_err = ""
    for attempt in range(max_attempts):
        extra = ""
        if attempt > 0:
            extra = (
                f"\n\nCRITICAL: Previous attempt failed validation: {last_err}.\n"
                "Please rewrite the narration to be longer and more detailed. "
                f"Aim for {lo}-{hi} words. Add more descriptive sentences to each beat.\n"
            )

        temp = 0.85 if attempt < 2 else 0.45
        data = _call_groq(preset, user + extra, temperature=temp)

        try:
            narration = sanitize_narration(data.get("full_narration", ""))
            data["full_narration"] = narration
            if not narration:
                raise ValueError("Missing full_narration")

            prompts = data.get("image_prompts")
            if not isinstance(prompts, list) or len(prompts) != n:
                raise ValueError(f"Expected {n} image_prompts, got {len(prompts or [])}")
            for i, p in enumerate(prompts):
                if not isinstance(p, str) or not p.strip():
                    raise ValueError(f"image_prompt {i} is empty")

            word_count = len(narration.split())
            min_words = preset.get("min_words", DEFAULT_MIN_WORDS.get(language, 80))
            if word_count < min_words:
                raise ValueError(
                    f"Narration too short ({word_count} words, expected ≥ {min_words} for {language})"
                )

            return data
        except ValueError as e:
            last_err = str(e)
            if attempt == max_attempts - 1:
                raise

    # Fallback (should be unreachable due to raise above)
    return data


# ─────────────────────────────────────────────────────────────────────────
# Multi-variant path (one Groq call returns every language's narration)
# ─────────────────────────────────────────────────────────────────────────
def _generate_multivariant(
    preset: ChannelPreset, user: str, n: int, variants: list,
) -> dict[str, Any]:
    # Build the per-language requirement lines
    lang_lines = []
    for v in variants:
        lang = v["lang"]
        lo, hi, blurb = LANG_WORD_TARGETS.get(lang, LANG_WORD_TARGETS["en"])
        lang_lines.append(
            f'    "{lang}": {{\n'
            f'      "youtube_title": "catchy title under 55 characters in {_lang_label(lang)} with 1-2 relevant emojis (no hashtags)",\n'
            f'      "youtube_description": "2-3 sentences in {_lang_label(lang)} + optional #Shorts",\n'
            f'      "pinned_comment": "creepy or engaging open-ended question (under 200 characters) in {_lang_label(lang)} to pin in comments",\n'
            f'      "full_narration": "ONE continuous paragraph in {_lang_label(lang)}. '
            f'{blurb}. Natural spoken narration, no segment markers."\n'
            f'    }}'
        )
    variants_block = ",\n".join(lang_lines)

    word_targets = "\n".join(
        f"  - {_lang_label(v['lang'])}: {LANG_WORD_TARGETS.get(v['lang'], LANG_WORD_TARGETS['en'])[2]}"
        for v in variants
    )
    lang_keys = ", ".join(f'"{v["lang"]}"' for v in variants)

    user += f"""
Return ONLY valid JSON with this shape:
{{
  "image_prompts": [
    "visual description for image 1 — IN ENGLISH ONLY: setting, subject, action. No style words. No text in image.",
    "visual description for image 2 — in English…",
    "..."
  ],
  "variants": {{
{variants_block}
  }}
}}

STRICT RULES:
- "image_prompts" array MUST have exactly {n} entries, ALL in English.
- "variants" object MUST contain keys: {lang_keys}.
- Each variant tells the SAME facts/story but written natively in that language (not literal translation).
- Word-count targets per language:
{word_targets}
- Narrations are continuous spoken paragraphs — no segment numbers, no headings.
- Titles/descriptions: each in its own language.
- BEFORE you output JSON: mentally count words in each full_narration. If English is under 115 words OR Hindi under 100 words, REWRITE that paragraph longer (same facts) until counts are met.
"""

    last_err: str | None = None
    max_attempts = 4
    for attempt in range(max_attempts):
        extra = ""
        if last_err:
            extra = (
                "\n\n=== REGENERATE (previous JSON failed validation) ===\n"
                f"{last_err}\n"
                "Return a NEW complete JSON object that fixes the issue. "
                "Keep the same facts/story and the same image_prompts beats; "
                "expand ONLY the narration(s) that were too short — add 3-5 full sentences each.\n"
            )
        # Later attempts: lower temperature so the model obeys length constraints more reliably.
        temp = 0.85 if attempt < 2 else 0.45
        data = _call_groq(preset, user + extra, temperature=temp)
        try:
            _assert_multivariant_valid(data, variants, n)
            return data
        except ValueError as e:
            last_err = str(e)
            if attempt == max_attempts - 1:
                raise


def _assert_multivariant_valid(data: dict[str, Any], variants: list, n: int) -> None:
    prompts = data.get("image_prompts")
    if not isinstance(prompts, list) or len(prompts) != n:
        raise ValueError(f"Expected {n} image_prompts, got {len(prompts or [])}")
    for i, p in enumerate(prompts):
        if not isinstance(p, str) or not p.strip():
            raise ValueError(f"image_prompt {i} is empty")

    vmap = data.get("variants")
    if not isinstance(vmap, dict):
        raise ValueError("Groq response missing 'variants' object")

    for v in variants:
        lang = v["lang"]
        node = vmap.get(lang)
        if not isinstance(node, dict):
            raise ValueError(f"variants['{lang}'] missing")

        node["full_narration"] = sanitize_narration(node.get("full_narration") or "")
        narration = node["full_narration"]
        if not narration:
            raise ValueError(f"variants['{lang}'].full_narration empty")

        min_words = v.get("min_words", DEFAULT_MIN_WORDS.get(lang, 80))
        word_count = len(narration.split())
        if word_count < min_words:
            lo, hi, _ = LANG_WORD_TARGETS.get(lang, LANG_WORD_TARGETS["en"])
            raise ValueError(
                f"variants['{lang}'].full_narration too short "
                f"({word_count} words, need ≥{min_words}; ideal range {lo}-{hi})"
            )

        if not (node.get("youtube_title") or "").strip():
            raise ValueError(f"variants['{lang}'].youtube_title empty")


def _call_groq(
    preset: ChannelPreset,
    user: str,
    *,
    temperature: float = 0.85,
) -> dict[str, Any]:
    system_prompt = preset["groq_system_hint"]
    if "JSON" not in system_prompt:
        system_prompt = (
            "You are a professional YouTube scriptwriter. Respond in valid JSON format only.\n"
            f"{system_prompt}"
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]

    # --- Mode A: Primary LLM (OpenAI / ChatAnywhere e.g. gpt-4o-mini) ---
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key and "your_" not in openai_key:
        base_url = (os.environ.get("OPENAI_BASE_URL", "") or "https://api.chatanywhere.org/v1").rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }

        try:
            print(f"   🤖 Trying primary LLM: {model} ({base_url})...")
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                if resp.status_code in (402, 429):
                    raise RuntimeError(f"Quota/Rate limit exhausted (HTTP {resp.status_code}): {resp.text[:120]}")
                if resp.status_code != 200:
                    # Retry without response_format in case proxy doesn't support json_object
                    payload.pop("response_format", None)
                    resp = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                result = _parse_json_safely(raw)
                print(f"   ✅ Primary LLM ({model}) generated script successfully.")
                return result
        except Exception as e:
            groq_key = os.environ.get("GROQ_API_KEY", "").strip()
            if groq_key:
                print(f"   ⚠️ Primary LLM ({model}) failed or quota exhausted: {e}")
                print("   🔄 Falling back to Groq Cloud...")
            else:
                raise RuntimeError(
                    f"Primary LLM ({model}) failed: {e}\n"
                    "Note: GROQ_API_KEY is not set in .env to use as a fallback."
                ) from e

    # --- Mode B: Groq API (Fallback or standalone) ---
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "Neither OPENAI_API_KEY nor GROQ_API_KEY is set. "
            "Please add your API key to YT_Bot/.env."
        )

    if Groq is None:
        raise RuntimeError("groq package not installed. Run: pip install groq (or set OPENAI_API_KEY in .env)")

    client = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", GROQ_MODEL).strip() or GROQ_MODEL

    is_reasoning_model = any(
        kw in model.lower()
        for kw in ("qwen", "deepseek", "r1", "gpt-oss", "reasoning", "qwq")
    )

    strategies: list[dict[str, Any]] = []
    if is_reasoning_model:
        # Strategy 1: JSON mode with parsed reasoning (standard for Qwen 3.6 / DeepSeek R1 on Groq)
        strategies.append({"response_format": {"type": "json_object"}, "reasoning_format": "parsed"})
        # Strategy 2: JSON mode with reasoning effort disabled
        strategies.append({"response_format": {"type": "json_object"}, "reasoning_effort": "none"})
        # Strategy 3: Standard JSON mode
        strategies.append({"response_format": {"type": "json_object"}})
        # Strategy 4: Unconstrained text mode with robust regex parser fallback
        strategies.append({})
    else:
        # Strategy 1: Standard JSON mode for non-reasoning models
        strategies.append({"response_format": {"type": "json_object"}})
        # Strategy 2: Unconstrained text mode with robust regex parser fallback
        strategies.append({})

    last_err: Exception | None = None

    for attempt_idx, strat in enumerate(strategies):
        try:
            call_kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 3072,
                **strat,
            }
            resp = client.chat.completions.create(**call_kwargs)
            raw = resp.choices[0].message.content or ""
            if not raw.strip():
                continue
            return _parse_json_safely(raw)
        except BadRequestError as e:
            last_err = e
            msg = str(e)
            print(f"   ⚠ Groq strategy {attempt_idx + 1}/{len(strategies)} failed: {msg[:120]}… retrying with fallback strategy.")
            continue
        except Exception as e:
            last_err = e
            print(f"   ⚠ Groq request error: {e}… trying next strategy.")
            continue

    raise RuntimeError(f"Groq JSON generation failed across all fallback strategies. Last error: {last_err}")

