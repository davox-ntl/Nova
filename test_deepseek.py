"""Test the configured DeepSeek endpoint without printing the API key."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=True)


def safe_error_body(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        message = data.get("error", data)
        if isinstance(message, dict):
            message = message.get("message") or message.get("detail") or message
        return " ".join(str(message).split())[:600]
    except (json.JSONDecodeError, OSError):
        return "Réponse d’erreur illisible."


def main() -> int:
    key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

    print(f"Endpoint : {base_url}/chat/completions")
    print(f"Modèle : {model}")
    print(f"Clé détectée : {'oui' if key else 'NON'} (longueur : {len(key)})")
    if not key:
        print("ERREUR : DEEPSEEK_API_KEY est absente du fichier nova/.env")
        return 1

    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "Réponds uniquement par OK"}],
            "temperature": 0.1,
            "max_tokens": 32,
            "stream": False,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )

    try:
        with request.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
        print(f"SUCCÈS HTTP 200 — réponse : {content[:200]}")
        return 0
    except error.HTTPError as exc:
        print(f"ÉCHEC HTTP {exc.code} — {safe_error_body(exc)}")
        return 2
    except error.URLError as exc:
        print(f"ÉCHEC RÉSEAU — {exc.reason}")
        return 3
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"RÉPONSE INATTENDUE — {type(exc).__name__}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
