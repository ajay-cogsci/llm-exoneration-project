"""Offline CLI and HTTP-boundary checks; never contact a live API."""

import contextlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from phd_resumes.__main__ import main
from phd_resumes.api import APIError, OpenAIResponses, request_body, response_json
from phd_resumes.io import read_json
from phd_resumes.sampling import check_config
from phd_resumes.writing import content_schema
from test_pipeline import FakeAPI, config


class ConfigurationBoundaryTests(unittest.TestCase):
    def test_invalid_numeric_and_date_settings_fail_before_sampling(self):
        changes = [
            {"max_publications": 0.5},
            {"max_publications": True},
            {"performance_weights": {**config()["performance_weights"], "gpa": float("nan")}},
            {"performance_weights": {**config()["performance_weights"], "gpa": float("inf")}},
            {"review_month": "2026-2"},
            {"gpa_as_of": "2025-13-99"},
            {"gpa_bins": [[3.2, 3.8], [3.0, 3.5]], "gpa_bin_probabilities": [0.5, 0.5]},
        ]
        for change in changes:
            with self.subTest(change=change):
                cfg = config()
                cfg.update(change)
                with self.assertRaises(ValueError):
                    check_config(cfg)


class CLITests(unittest.TestCase):
    def invoke(self, arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_inspect_needs_no_key_and_cannot_create_a_client(self):
        with patch.dict(os.environ, {}, clear=True), patch("phd_resumes.__main__.OpenAIResponses") as client:
            code, output, error = self.invoke(["inspect"])
        self.assertEqual(code, 0, error)
        result = json.loads(output)
        self.assertEqual(result["api_calls"], 0)
        self.assertEqual(result["records_generated"], 0)
        client.assert_not_called()

    def test_sample_generate_resume_and_models_through_cli(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            run = str(Path(folder) / "cli-run")
            with patch("phd_resumes.__main__.OpenAIResponses") as constructor:
                code, output, error = self.invoke(["sample", "--out", run, "--n-per-cohort", "20", "--oversample", "10"])
                self.assertEqual(code, 0, error)
                self.assertEqual(json.loads(output)["profiles"], 60)
                code, _, error = self.invoke(["generate", "--run", run, "--limit", "1"])
                self.assertEqual(code, 1)
                self.assertIn("Choose a model", error)
                constructor.assert_not_called()
            client = FakeAPI()
            with patch.dict(os.environ, {"OPENAI_MODEL": "environment-model"}), patch("phd_resumes.__main__.OpenAIResponses", return_value=client):
                args = ["generate", "--run", run, "--limit", "3", "--model", "cli-model"]
                for _ in range(2):
                    code, _, error = self.invoke(args)
                    self.assertEqual(code, 0, error)
            self.assertEqual(client.calls, 6)
            contract = read_json(Path(run) / "generation/contract.json")
            self.assertEqual(contract["model"], "cli-model")
            self.assertEqual(contract["review_model"], "cli-model")
            self.assertEqual(len(list((Path(run) / "generation/cvs").glob("*.txt"))), 3)


class APIBoundaryTests(unittest.TestCase):
    def client(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only-placeholder"}, clear=True):
            return OpenAIResponses()

    def test_request_transport_and_structured_response(self):
        response = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}]}
        body = request_body("test-model", "test instructions", {}, content_schema(), config()["generation"])
        with patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as send:
            result = self.client().create(body)
        self.assertEqual(response_json(result), {})
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(json.loads(request.data)["text"]["format"]["strict"], True)
        self.assertFalse(json.loads(request.data)["store"])
        self.assertNotIn("test-only-placeholder", request.data.decode())

    def test_transient_http_retries_are_bounded(self):
        error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 429, "test", {}, None)
        with patch("urllib.request.urlopen", side_effect=error) as send, patch("time.sleep") as pause:
            with self.assertRaises(APIError):
                self.client().create({})
        self.assertEqual(send.call_count, 3)
        self.assertEqual(pause.call_count, 2)

    def test_timeout_and_authentication_errors_are_not_retried(self):
        failures = [TimeoutError(), urllib.error.HTTPError("https://api.openai.com/v1/responses", 401, "test", {}, None)]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), patch("urllib.request.urlopen", side_effect=failure) as send, patch("time.sleep") as pause:
                with self.assertRaises(APIError):
                    self.client().create({})
                self.assertEqual(send.call_count, 1)
                pause.assert_not_called()

    def test_malformed_transport_json_is_a_controlled_api_error(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"not JSON")) as send:
            with self.assertRaises(APIError):
                self.client().create({})
        self.assertEqual(send.call_count, 1)

    def test_malformed_response_envelopes_are_controlled_api_errors(self):
        for response in ([], {"status": "completed", "output": None}, {"status": "completed", "output": [None]}, {"status": "completed", "output": [{"content": [None]}]}):
            with self.subTest(response=response), self.assertRaises(APIError):
                response_json(response)


if __name__ == "__main__":
    unittest.main()
