"""FastAPI entry point for the NOVA classroom MVP."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import edge_tts
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import database
from .services.language_index import available_indexes
from .services.translator import (
    LANGUAGES,
    provider_is_configured,
    provider_model,
    selected_provider,
    translate,
)

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"

# Neural voices served by edge-tts. The first one is the soft, soothing default
# used instead of the browser's default (often metallic) system voice.
DEFAULT_VOICE = "fr-FR-VivienneNeural"
VOICES = [
    {
        "id": DEFAULT_VOICE,
        "name": "Douce et apaisante",
        "description": "Voix féminine douce et calme",
        "rate": "-12%",
        "volume": "-5%",
    },
    {
        "id": "fr-FR-DeniseNeural",
        "name": "Claire et naturelle",
        "description": "Voix féminine claire",
        "rate": "-8%",
        "volume": "-5%",
    },
    {
        "id": "fr-FR-HenriNeural",
        "name": "Posée",
        "description": "Voix masculine posée",
        "rate": "-10%",
        "volume": "-5%",
    },
]
VOICE_SETTINGS = {voice["id"]: voice for voice in VOICES}
VOICE_IDS = set(VOICE_SETTINGS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialise()
    yield


app = FastAPI(
    title="NOVA API",
    version="0.1.0",
    description="API du MVP de traduction des langues ivoiriennes.",
    lifespan=lifespan,
)


class TranslationRequest(BaseModel):
    source_language: str = Field(min_length=2, max_length=10)
    target_language: str = Field(min_length=2, max_length=10)
    text: str = Field(min_length=1, max_length=1200)
    context: str = Field(default="quotidien", max_length=30)


class FeedbackRequest(BaseModel):
    translation_id: int = Field(gt=0)
    helpful: bool
    comment: str | None = Field(default=None, max_length=500)


@app.get("/api/health")
def health() -> dict:
    provider = selected_provider()
    configured = provider_is_configured(provider)
    return {
        "status": "ok",
        "service": "nova-api",
        "provider": provider,
        "model": provider_model(provider),
        "translation_engine": provider if configured else "demo-local",
        "tts_engine": "edge-tts",
        "reference_indexes": available_indexes(),
    }


@app.get("/api/languages")
def languages() -> list[dict]:
    return LANGUAGES


@app.post("/api/translations", status_code=201)
def create_translation(payload: TranslationRequest) -> dict:
    clean_text = " ".join(payload.text.split())
    try:
        result = translate(
            clean_text,
            payload.source_language,
            payload.target_language,
            payload.context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    saved = database.save_translation(
        payload.source_language,
        payload.target_language,
        clean_text,
        result.text,
        payload.context,
        result.engine,
        result.phonetic,
    )
    saved["warning"] = result.warning
    saved["references"] = result.references
    return saved


@app.get("/api/translations")
def history(limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return database.list_translations(limit)


@app.delete("/api/translations", status_code=204)
def clear_history() -> None:
    database.clear_translations()


@app.post("/api/feedback", status_code=201)
def feedback(payload: FeedbackRequest) -> dict:
    try:
        return database.save_feedback(payload.translation_id, payload.helpful, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/voices")
def voices() -> list[dict]:
    return [{**voice, "default": voice["id"] == DEFAULT_VOICE} for voice in VOICES]


@app.get("/api/tts")
async def text_to_speech(
    text: str = Query(min_length=1, max_length=1200),
    voice: str = Query(default=DEFAULT_VOICE),
) -> Response:
    if voice not in VOICE_IDS:
        raise HTTPException(status_code=422, detail="Voix non prise en charge")
    settings = VOICE_SETTINGS[voice]
    clean_text = " ".join(text.split())
    try:
        # Neural Edge TTS voices, slowed down slightly for a soft, soothing delivery.
        communicate = edge_tts.Communicate(
            clean_text,
            voice,
            rate=settings["rate"],
            volume=settings["volume"],
        )
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        if not audio_data:
            raise RuntimeError("aucun audio produit")
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-TTS-Engine": "edge-tts",
                "X-TTS-Voice": voice,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Edge TTS indisponible : {exc}",
        ) from exc


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}")
def frontend(full_path: str = "") -> FileResponse:
    candidate = STATIC_DIR / full_path
    if full_path and candidate.is_file() and STATIC_DIR in candidate.resolve().parents:
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
