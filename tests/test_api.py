"""API smoke tests for the NOVA MVP."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


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


if __name__ == "__main__":
    unittest.main()
