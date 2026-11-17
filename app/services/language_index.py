"""Per-language JSON indexes injected into the provider prompt before translation.

Each language has its own folder in data/index_de_langue/ containing:
    vocabulaire.json    -> French / language equivalents
    phonetique.json     -> simplified pronunciation of those words
    prononciation.json  -> orthographic and pronunciation rules

The relevant entries are selected from the message and the resulting JSON is sent
to DeepSeek (or NVIDIA/Gemini) as reference material, before it translates.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "index_de_langue"
INDEX_DIR = Path(os.getenv("NOVA_INDEX_DIR", str(DEFAULT_INDEX_DIR)))

LANGUAGE_NAMES = {"dyu": "Dioula", "any": "Agni", "bci": "Baoulé", "bet": "Bété"}
FILENAMES = ("vocabulaire.json", "phonetique.json", "prononciation.json")
MAX_ENTRIES = 12

STOPWORDS = frozenset(
    """le la les un une des de du au aux et ou mais est sont je tu il elle nous vous ils
    elles ce cet cette ces mon ma mes ton ta tes son sa ses notre vos leur leurs ne pas
    plus très bien oui non si en dans sur pour par avec sans chez a ai as avons avez ont
    étais était étions étiez étaient être été aussi alors quand comment quel quelle quels
    quelles qui que quoi dont où me te se m t s c d j l n qu""".split()
)


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _tokens(text: str) -> set[str]:
    folded = _fold(text)
    return {
        word
        for word in re.findall(r"[^\W\d_]{2,}", folded, flags=re.UNICODE)
        if word not in STOPWORDS
    }


@lru_cache(maxsize=8)
def load_index(code: str) -> dict:
    """Load the three JSON files of one language (cached for the process lifetime)."""
    folder = INDEX_DIR / code
    index: dict = {"language": code, "name": LANGUAGE_NAMES.get(code, code)}
    for filename in FILENAMES:
        path = folder / filename
        try:
            index[filename.removesuffix(".json")] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            index[filename.removesuffix(".json")] = {}
    return index


def available_indexes() -> list[dict]:
    """Describe the JSON indexes, for the health endpoint."""
    return [
        {
            "language": code,
            "name": name,
            "files": [
                filename
                for filename in FILENAMES
                if (INDEX_DIR / code / filename).is_file()
            ],
        }
        for code, name in LANGUAGE_NAMES.items()
    ]


def _score(entry: dict, terms: set[str]) -> int:
    searchable = " ".join(
        str(entry.get(key, "")) for key in ("fr", "translation", "mot", "context")
    )
    return len(terms & _tokens(searchable))


def _language_code(source: str, target: str) -> str:
    return target if target in LANGUAGE_NAMES else source if source in LANGUAGE_NAMES else ""


def build_reference(source: str, target: str, text: str) -> tuple[str, list[dict]]:
    """Return the JSON reference block and the files actually sent to the provider."""
    code = _language_code(source, target)
    if not code or source == target:
        return "", []

    index = load_index(code)
    vocabulary = index.get("vocabulaire", {}).get("entries", [])
    phonetics = index.get("phonetique", {}).get("entries", [])
    pronunciation = index.get("prononciation", {})
    if not vocabulary and not pronunciation:
        return "", []

    terms = _tokens(text)
    ordered = sorted(enumerate(vocabulary), key=lambda pair: (-_score(pair[1], terms), pair[0]))
    ranked = [entry for _, entry in ordered]
    matched = [entry for entry in ranked if _score(entry, terms) > 0][:MAX_ENTRIES]
    selected = matched or ranked[:MAX_ENTRIES]

    # Keep the phonetic lines that match the selected vocabulary (or the first ones).
    phonetic_lines: list[dict] = []
    for entry in phonetics:
        word = _fold(entry.get("mot", ""))
        if any(word == _fold(item.get("translation", "")) for item in selected):
            phonetic_lines.append(entry)
    if not phonetic_lines:
        phonetic_lines = phonetics[:MAX_ENTRIES]

    reference_data = {
        "langue": index["name"],
        "utilisation": (
            "Consulte ce vocabulaire et ces règles AVANT de traduire. Reprends les équivalents "
            "et la phonétique fournis quand ils correspondent au message. Ne mentionne pas "
            "l'existence de cet index dans ta réponse."
        ),
        "vocabulaire": selected,
        "phonetique": phonetic_lines,
        "prononciation": {
            "regles": pronunciation.get("rules", []),
            "notes": pronunciation.get("notes", ""),
        },
    }
    reference = (
        "INDEX JSON DE RÉFÉRENCE (à consulter avant la traduction) :\n"
        + json.dumps(reference_data, ensure_ascii=False)
    )
    counts = {
        "vocabulaire.json": len(selected),
        "phonetique.json": len(phonetic_lines),
        "prononciation.json": len(pronunciation.get("rules", [])),
    }
    sources = [
        {
            "language": code,
            "file": filename,
            "entries": counts[filename],
            "matched": len(matched) if filename == "vocabulaire.json" else 0,
        }
        for filename in FILENAMES
        if (INDEX_DIR / code / filename).is_file()
    ]
    return reference, sources


def best_entry(source: str, target: str, text: str) -> dict | None:
    """Build a translation from the JSON index when the provider refuses to answer."""
    code = _language_code(source, target)
    if not code or source == target:
        return None

    vocabulary = load_index(code).get("vocabulaire", {}).get("entries", [])
    terms = _tokens(text)
    ordered = sorted(
        enumerate(vocabulary),
        key=lambda pair: (-_score(pair[1], terms), pair[0]),
    )
    matched = [entry for _, entry in ordered if _score(entry, terms) > 0]
    if not matched:
        return None

    return {
        "language": code,
        "translation": " ".join(
            str(entry.get("translation", "")) for entry in matched
        ).strip(),
        "phonetic": " ".join(str(entry.get("phonetic", "")) for entry in matched).strip(),
        "entries": matched,
    }
