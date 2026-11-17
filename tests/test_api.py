"""API smoke tests for the NOVA MVP."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

UNCERTAIN_MARKER_RESPONSE = (
    b'{"choices":[{"message":{"content":'
    b'"{\\"translation\\":\\"[VALIDATION HUMAINE REQUISE]\\",'
    b'\\"phonetic\\":\\"\\"}"}}]}'
)


class NovaApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["NOVA_DB_PATH"] = str(Path(self.temp_dir.name) / "test.db")
        os.environ["AI_PROVIDER"] = "deepseek"
        os.environ.pop("NVIDIA_API_KEY", None)
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.environ.pop("GEMINI_API_KEY", None)
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.temp_dir.cleanup()

    def test_health_and_languages(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["provider"], "deepseek")
        self.assertEqual(health.json()["translation_engine"], "demo-local")

        languages = self.client.get("/api/languages")
        self.assertEqual(languages.status_code, 200)
        codes = {item["code"] for item in languages.json()}
        self.assertTrue({"fr", "dyu", "bci", "bet"}.issubset(codes))

    def test_translation_is_persisted(self) -> None:
        response = self.client.post(
            "/api/translations",
            json={
                "source_language": "fr",
                "target_language": "dyu",
                "text": "Bonjour, comment allez-vous ?",
                "context": "quotidien",
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["engine"], "demo-local")
        self.assertIsNotNone(payload["warning"])

        history = self.client.get("/api/translations").json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["source_text"], "Bonjour, comment allez-vous ?")

    @patch("app.services.translator.request.urlopen")
    def test_deepseek_adapter(self, mocked_urlopen: MagicMock) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.return_value = (
            b'{"choices":[{"message":{"content":"Traduction de test"}}]}'
        )
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["translated_text"], "Traduction de test")
        self.assertTrue(response.json()["engine"].startswith("deepseek:"))
        sent_request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://api.deepseek.com/chat/completions",
        )
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer sk-test-only")

    @patch("app.services.translator.request.urlopen")
    def test_nvidia_adapter(self, mocked_urlopen: MagicMock) -> None:
        os.environ["AI_PROVIDER"] = "nvidia"
        os.environ["NVIDIA_API_KEY"] = "nvapi-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.return_value = (
            b'{"choices":[{"message":{"content":"Traduction de test"}}]}'
        )
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("NVIDIA_API_KEY", None)
            os.environ["AI_PROVIDER"] = "deepseek"

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["translated_text"], "Traduction de test")
        self.assertTrue(response.json()["engine"].startswith("nvidia:"))
        sent_request = mocked_urlopen.call_args.args[0]
        self.assertEqual(
            sent_request.full_url,
            "https://integrate.api.nvidia.com/v1/chat/completions",
        )
        self.assertEqual(sent_request.get_header("Authorization"), "Bearer nvapi-test-only")

    def test_rejects_unknown_language(self) -> None:
        response = self.client.post(
            "/api/translations",
            json={
                "source_language": "xx",
                "target_language": "fr",
                "text": "Test",
                "context": "quotidien",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_feedback_requires_translation(self) -> None:
        response = self.client.post(
            "/api/feedback",
            json={"translation_id": 999, "helpful": True},
        )
        self.assertEqual(response.status_code, 404)


    @patch("app.services.translator.request.urlopen")
    def test_structured_translation_includes_phonetic(self, mocked_urlopen: MagicMock) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.return_value = (
            b'{"choices":[{"message":{"content":'
            b'"{\\"translation\\":\\"I ni s\\u00f6g\\u00f6\\",\\"phonetic\\":\\"i ni so-go\\"}"}}]}'
        )
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        payload = response.json()
        self.assertEqual(payload["translated_text"], "I ni sögö")
        self.assertEqual(payload["phonetic"], "i ni so-go")
        sent_payload = json.loads(mocked_urlopen.call_args.args[0].data)
        system_prompt = sent_payload["messages"][0]["content"]
        self.assertIn('"translation"', system_prompt)
        self.assertIn('"phonetic"', system_prompt)

    def test_voices_expose_soft_default(self) -> None:
        response = self.client.get("/api/voices")
        self.assertEqual(response.status_code, 200)
        defaults = [voice for voice in response.json() if voice.get("default")]
        self.assertEqual(len(defaults), 1)
        self.assertEqual(defaults[0]["id"], "fr-FR-VivienneNeural")
        self.assertEqual(defaults[0]["name"], "Douce et apaisante")

    @patch("app.main.edge_tts.Communicate")
    def test_tts_rejects_unknown_voice(self, mocked_communicate: MagicMock) -> None:
        response = self.client.get("/api/tts", params={"text": "Bonjour", "voice": "inconnu"})
        self.assertEqual(response.status_code, 422)
        mocked_communicate.assert_not_called()

    @patch("app.main.edge_tts.Communicate")
    def test_tts_uses_soft_voice_by_default(self, mocked_communicate: MagicMock) -> None:
        async def fake_stream():
            yield {"type": "audio", "data": b"audio-bytes"}
            yield {"type": "WordBoundary", "data": b""}

        mocked_communicate.return_value.stream = fake_stream
        response = self.client.get("/api/tts", params={"text": "Bonjour"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"audio-bytes")
        self.assertEqual(response.headers["content-type"], "audio/mpeg")
        self.assertEqual(response.headers["x-tts-engine"], "edge-tts")
        self.assertEqual(mocked_communicate.call_args.args[1], "fr-FR-VivienneNeural")
        self.assertEqual(mocked_communicate.call_args.kwargs["rate"], "-12%")
        self.assertEqual(mocked_communicate.call_args.kwargs["volume"], "-5%")

    def test_vercel_uses_writable_tmp_database(self) -> None:
        from app import database

        with patch.dict(os.environ, {"VERCEL": "1"}):
            os.environ.pop("NOVA_DB_PATH", None)
            self.assertEqual(database.database_path(), Path("/tmp/nova.db"))

    def test_legacy_database_gets_phonetic_column(self) -> None:
        from app import database

        legacy = Path(self.temp_dir.name) / "legacy.db"
        connection = sqlite3.connect(legacy)
        connection.execute(
            "CREATE TABLE translations ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "source_language TEXT NOT NULL, target_language TEXT NOT NULL, "
            "source_text TEXT NOT NULL, translated_text TEXT NOT NULL, "
            "context TEXT NOT NULL DEFAULT 'quotidien', engine TEXT NOT NULL, "
            "created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.commit()
        connection.close()

        with patch.dict(os.environ, {"NOVA_DB_PATH": str(legacy)}):
            database.initialise()
            with database.connect() as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(translations)")}
        self.assertIn("phonetic", columns)


    @patch("app.services.translator.request.urlopen")
    @patch("app.services.translator.build_reference")
    def test_deepseek_prompt_contains_the_appropriate_index(
        self, mocked_reference: MagicMock, mocked_urlopen: MagicMock
    ) -> None:
        mocked_reference.return_value = (
            "INDEX DE RÉFÉRENCE : bonjour -> i ni ce (p. 12)",
            [{"title": "Index français-dioula", "file": "Index-dioula-francais.pdf", "page": 12}],
        )
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.return_value = b'{"choices":[{"message":{"content":"I ni ce"}}]}'
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["references"][0]["page"], 12)
        sent_payload = json.loads(mocked_urlopen.call_args.args[0].data)
        self.assertIn("INDEX DE RÉFÉRENCE", sent_payload["messages"][0]["content"])
        mocked_reference.assert_called_once_with("fr", "dyu", "Bonjour")

    @patch("app.services.language_index.load_index")
    def test_index_json_sent_to_prompt(self, mocked_load: MagicMock) -> None:
        from app.services.language_index import build_reference

        mocked_load.return_value = {
            "language": "dyu",
            "name": "Dioula",
            "vocabulaire": {
                "entries": [
                    {
                        "fr": "bonjour",
                        "translation": "i ni ce",
                        "phonetic": "i ni tche",
                        "context": "salutation",
                    },
                    {
                        "fr": "maladie",
                        "translation": "bana",
                        "phonetic": "ba-na",
                        "context": "santé",
                    },
                ]
            },
            "phonetique": {
                "entries": [{"mot": "i ni ce", "phonetic": "i ni tche", "fr": "bonjour"}]
            },
            "prononciation": {"rules": [{"graphie": "ɛ", "son": "è"}], "notes": "test"},
        }
        reference, sources = build_reference("fr", "dyu", "bonjour")
        self.assertIn("INDEX JSON DE RÉFÉRENCE", reference)
        self.assertIn("i ni ce", reference)
        self.assertEqual(sources[0]["file"], "vocabulaire.json")
        self.assertEqual(build_reference("fr", "fr", "bonjour"), ("", []))

    def test_health_advertises_edge_tts_and_indexes(self) -> None:
        health = self.client.get("/api/health").json()
        self.assertEqual(health["tts_engine"], "edge-tts")
        codes = {item["language"] for item in health["reference_indexes"]}
        self.assertTrue({"dyu", "any", "bci", "bet"}.issubset(codes))

    @patch("app.services.translator.request.urlopen")
    def test_prompt_never_offers_human_validation(self, mocked_urlopen: MagicMock) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.return_value = b'{"choices":[{"message":{"content":"i ni ce"}}]}'
        try:
            self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        prompt = json.loads(mocked_urlopen.call_args.args[0].data)["messages"][0]["content"]
        self.assertNotIn("pas suffisamment certain", prompt)
        self.assertNotIn("Demandez une validation", prompt)
        self.assertIn("source terminologique validée et fiable", prompt)
        self.assertIn("Tu ne dois jamais demander de validation humaine", prompt)

    @patch("app.services.translator.request.urlopen")
    def test_validation_marker_triggers_strict_retry(self, mocked_urlopen: MagicMock) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        answer = b'{"choices":[{"message":{"content":"i ni ce"}}]}'
        response_context.read.side_effect = [UNCERTAIN_MARKER_RESPONSE, answer]
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "dyu",
                    "text": "Bonjour",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        payload = response.json()
        self.assertEqual(payload["translated_text"], "i ni ce")
        self.assertIsNone(payload["warning"])
        self.assertEqual(mocked_urlopen.call_count, 2)
        strict_prompt = json.loads(mocked_urlopen.call_args.args[0].data)["messages"][0]["content"]
        self.assertIn("RÈGLE ABSOLUE", strict_prompt)
        self.assertIn("[VALIDATION HUMAINE REQUISE]", strict_prompt)

    @patch("app.services.translator.best_entry")
    @patch("app.services.translator.request.urlopen")
    def test_persistent_validation_marker_falls_back_to_json(
        self, mocked_urlopen: MagicMock, mocked_best_entry: MagicMock
    ) -> None:
        os.environ["DEEPSEEK_API_KEY"] = "sk-test-only"
        response_context = mocked_urlopen.return_value.__enter__.return_value
        response_context.read.side_effect = [
            UNCERTAIN_MARKER_RESPONSE,
            UNCERTAIN_MARKER_RESPONSE,
        ]
        mocked_best_entry.return_value = {
            "language": "any",
            "translation": "ésika",
            "phonetic": "é-si-ka",
            "entries": [],
        }
        try:
            response = self.client.post(
                "/api/translations",
                json={
                    "source_language": "fr",
                    "target_language": "any",
                    "text": "Je n'ai pas d'argent",
                    "context": "quotidien",
                },
            )
        finally:
            os.environ.pop("DEEPSEEK_API_KEY", None)

        payload = response.json()
        self.assertEqual(payload["translated_text"], "ésika")
        self.assertEqual(payload["phonetic"], "é-si-ka")
        self.assertTrue(payload["engine"].endswith(":index-json"))
        self.assertIsNone(payload["warning"])
        mocked_best_entry.assert_called_once_with("fr", "any", "Je n'ai pas d'argent")


if __name__ == "__main__":
    unittest.main()
