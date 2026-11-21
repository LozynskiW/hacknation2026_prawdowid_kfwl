"""Wywołanie dostawcy AI (Gemini, Anthropic, API zgodne z OpenAI). Jedno zapytanie, bez strumieniowania."""

import asyncio

import httpx

from prawdowid.api.settings import AI_API_KEY, AI_BASE_URL, AI_MODEL, AI_PROVIDER


async def ask_ai(system: str, message: str) -> str:
    """Wysyła skill + wiadomość do dostawcy AI. Ponawia do 3 razy przy 429/500/503."""
    for attempt in range(3):
        try:
            return await _ask_ai_once(system, message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 500, 503) and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))  # 2 s, potem 4 s
                continue
            print("Błąd dostawcy AI:", e.response.status_code, e.response.text[:500])
            raise


async def _ask_ai_once(system: str, message: str) -> str:
    base = (AI_BASE_URL or "").rstrip("/")
    async with httpx.AsyncClient(timeout=300) as client:
        if AI_PROVIDER == "gemini":
            r = await client.post(
                f"{base or 'https://generativelanguage.googleapis.com/v1beta'}/models/{AI_MODEL}:generateContent",
                headers={"x-goog-api-key": AI_API_KEY},
                json={"systemInstruction": {"parts": [{"text": system}]},
                      "contents": [{"role": "user", "parts": [{"text": message}]}]},
            )
            r.raise_for_status()
            parts = r.json()["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if not p.get("thought"))

        if AI_PROVIDER == "anthropic":
            r = await client.post(
                f"{base or 'https://api.anthropic.com'}/v1/messages",
                headers={"x-api-key": AI_API_KEY, "anthropic-version": "2023-06-01"},
                json={"model": AI_MODEL, "max_tokens": 4096, "system": system,
                      "messages": [{"role": "user", "content": message}]},
            )
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")

        if AI_PROVIDER == "openai":
            r = await client.post(
                f"{base or 'https://api.openai.com/v1'}/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}"},
                json={"model": AI_MODEL, "messages": [{"role": "system", "content": system},
                                                      {"role": "user", "content": message}]},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""

        raise ValueError(f"Nieznany AI_PROVIDER: {AI_PROVIDER} (dozwolone: gemini, anthropic, openai)")
