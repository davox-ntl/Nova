"""Safe configuration diagnostic: never prints API keys."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


def main() -> int:
    print(f"Projet NOVA : {ROOT}")
    print(f"Fichier .env : {ENV_FILE}")
    print(f"Existe : {'oui' if ENV_FILE.is_file() else 'NON'}")
    if not ENV_FILE.is_file():
        print("Correction : copiez .env.example vers .env dans ce dossier.")
        return 1

    raw = dotenv_values(ENV_FILE)
    load_dotenv(ENV_FILE, override=True)
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    key_names = {
        "nvidia": "NVIDIA_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    models = {
        "nvidia": "NVIDIA_MODEL",
        "deepseek": "DEEPSEEK_MODEL",
        "gemini": "GEMINI_MODEL",
    }
    key_name = key_names.get(provider)
    print(f"AI_PROVIDER : {provider}")
    if not key_name:
        print("ERREUR : AI_PROVIDER doit valoir nvidia, deepseek ou gemini.")
        return 2

    key = os.getenv(key_name, "").strip()
    print(f"Variable attendue : {key_name}")
    print(f"Clé présente : {'oui' if key else 'NON'}")
    print(f"Longueur de la clé : {len(key)}")
    print(f"Modèle : {raw.get(models[provider], '')}")
    if provider == "nvidia":
        print(f"Base URL : {raw.get('NVIDIA_BASE_URL', '')}")
    if provider == "deepseek":
        print(f"Base URL : {raw.get('DEEPSEEK_BASE_URL', '')}")
    if not key:
        print(f"ERREUR : renseignez {key_name} dans {ENV_FILE}.")
        return 3

    print("Configuration locale détectée. Redémarrez maintenant : python run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
