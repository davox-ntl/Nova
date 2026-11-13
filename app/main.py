"""FastAPI entry point for the NOVA classroom MVP."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import database
from .services.translator import (
    LANGUAGES,
    provider_is_configured,
    provider_model,
    selected_provider,
    translate,
)

load_dotenv()

STATIC_DIR = Path(__file__).parent / "static"


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
    )
    saved["warning"] = result.warning
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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}")
def frontend(full_path: str = "") -> FileResponse:
    candidate = STATIC_DIR / full_path
    if full_path and candidate.is_file() and STATIC_DIR in candidate.resolve().parents:
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
