"""
ai_engine.py
------------
Plain-English job of this file:
  1. Send crawled website text + search snippets to an AI model via
     OpenRouter (a service that gives access to many different AI models
     through one API).
  2. Ask for a structured summary: description, products, pain points,
     competitors, etc.
  3. Power the chat-style follow-up questions.

Why OpenRouter instead of calling one AI company directly?
  OpenRouter lets the user pick from many models (GPT, Claude, Llama,
  Gemini, etc.) through a single API key, which is what this assignment
  specifically asks for.
"""

import requests
import os
import json
import re
import time

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# A safe, free default. The user can override this from the sidebar dropdown.
DEFAULT_MODEL = "deepseek/deepseek-chat"


def _call_openrouter(prompt: str, model: str = DEFAULT_MODEL, max_retries: int = 3) -> str:
    """
    Low-level OpenRouter call. Returns plain text or an "ERROR: ..." string.
    Retries with a wait if we get rate-limited (free models share a busy queue).
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "PASTE_YOUR_OPENROUTER_KEY_HERE":
        return "ERROR: No OPENROUTER_API_KEY set."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=40)

            if resp.status_code == 429:
                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue
                return "ERROR: Still rate-limited after retries. Try again shortly, or pick a different model."

            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout:
            return "ERROR: AI request timed out."
        except (KeyError, IndexError):
            return f"ERROR: Unexpected AI response shape: {resp.text[:200]}"
        except Exception as e:
            return f"ERROR: {e}"

    return "ERROR: Rate limit hit repeatedly."


def _extract_json(text: str) -> dict:
    """Strips ```json fences and parses; falls back to finding the first {...} block."""
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"error": "Could not parse AI output as JSON", "raw": text}


def analyze_company(crawled_text: str, search_snippets: list, company_label: str,
                     known_phone: str = "", known_address: str = "", model: str = DEFAULT_MODEL) -> dict:
    """
    Core AI reasoning step. Returns a dict shaped like:
    {
      "company_name": "...",
      "website": "...",
      "phone": "...",
      "address": "...",
      "description": "...",
      "products_services": ["...", "..."],
      "pain_points": ["...", "..."],
      "competitors": [{"name": "..."}],   # website filled in later via Serper
    }
    """
    snippet_text = "\n".join(f"- {s['title']}: {s['snippet']}" for s in search_snippets)

    prompt = f"""
You are a B2B business research analyst. Based ONLY on the information below,
produce a structured JSON analysis of the company "{company_label}".

WEBSITE CONTENT:
{crawled_text}

ADDITIONAL SEARCH SNIPPETS:
{snippet_text}

KNOWN PHONE (from page scan, may be empty): {known_phone}
KNOWN ADDRESS (from page scan, may be empty): {known_address}

Return ONLY valid JSON (no markdown fences, no extra commentary) in exactly this shape:
{{
  "company_name": "string",
  "phone": "use KNOWN PHONE if provided, otherwise best guess or empty string",
  "address": "use KNOWN ADDRESS if provided, otherwise best guess or empty string",
  "description": "2-3 sentence plain-English summary of what the company does",
  "products_services": ["list", "of", "key", "offerings"],
  "pain_points": ["2-4 likely business pain points this company's customers face, that its product/service addresses"],
  "competitors": [
    {{"name": "Competitor company name only, no descriptions"}}
  ]
}}

List at least 3 realistic, real-world competitors in the same industry and (if identifiable) same country.
If information is missing, make a reasonable, clearly labeled inference rather than leaving a field empty.
"""
    raw = _call_openrouter(prompt, model=model)
    if raw.startswith("ERROR"):
        return {"error": raw}

    return _extract_json(raw)


def chat_about_company(company_context: dict, chat_history: list, user_question: str, model: str = DEFAULT_MODEL) -> str:
    """Powers the ChatGPT-style follow-up box, using the structured research as context."""
    context_str = json.dumps(company_context, indent=2)
    history_str = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in chat_history[-6:])

    prompt = f"""
You are a helpful research assistant. You already researched this company:

{context_str}

Recent conversation:
{history_str}

Answer the user's new question using the context above. If the answer isn't
in the context, say so honestly rather than making things up.

USER QUESTION: {user_question}
"""
    return _call_openrouter(prompt, model=model)
