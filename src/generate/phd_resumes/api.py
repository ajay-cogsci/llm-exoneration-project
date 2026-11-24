"""Minimal Responses API client. Credentials are never serialized or printed."""

import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class APIError(RuntimeError):
    pass


def request_body(model, instructions, payload, schema, settings, *, review=False):
    body = {"model": model, "store": False, "input": [{"role": "system", "content": instructions}, {"role": "user", "content": json.dumps(payload, sort_keys=True, ensure_ascii=False)}], "text": {"format": {"type": "json_schema", "name": "cv_review" if review else "phd_cv", "strict": True, "schema": schema}}, "max_output_tokens": settings["review_max_output_tokens" if review else "max_output_tokens"]}
    # Set to null for a model that does not expose reasoning.effort.
    if settings.get("reasoning_effort"):
        body["reasoning"] = {"effort": settings["reasoning_effort"]}
    return body


def response_json(response):
    if not isinstance(response, dict):
        raise APIError("API response must be a JSON object")
    if response.get("status") != "completed":
        raise APIError(f"Response not completed: {response.get('status')}; {response.get('incomplete_details')}")
    parts = []
    output = response.get("output", [])
    if not isinstance(output, list):
        raise APIError("API response output must be a list")
    for item in output:
        if not isinstance(item, dict):
            raise APIError("API output item must be an object")
        contents = item.get("content") or []
        if not isinstance(contents, list):
            raise APIError("API message content must be a list")
        for content in contents:
            if not isinstance(content, dict):
                raise APIError("API content item must be an object")
            if content.get("type") == "refusal":
                raise APIError("Model refused the request; retained in the raw response")
            if content.get("type") == "output_text":
                if not isinstance(content.get("text"), str):
                    raise APIError("API output text must be a string")
                parts.append(content["text"])
    try:
        result = json.loads("".join(parts))
    except (ValueError, TypeError) as exc:
        raise APIError("No valid structured JSON in response") from exc
    if not isinstance(result, dict):
        raise APIError("Response JSON must be an object")
    return result


class OpenAIResponses:
    def __init__(self):
        self.key = os.getenv("OPENAI_API_KEY")
        if not self.key:
            raise APIError("Set OPENAI_API_KEY in the environment; do not put it in project files")
        self.base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        parsed = urlsplit(self.base)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise APIError("OPENAI_BASE_URL must be an HTTPS base URL without credentials/query/fragment")

    def create(self, body):
        data = json.dumps(body).encode()
        request = urllib.request.Request(self.base + "/responses", data=data, headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}, method="POST")
        # Bounded retries only for explicit transient HTTP responses. Timeouts are
        # not retried automatically because the server may already have billed.
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(f"OpenAI request failed with HTTP {exc.code}; check model access, credentials and endpoint") from None
            except (urllib.error.URLError, TimeoutError):
                raise APIError("OpenAI connection failed or timed out; check connectivity before retrying") from None
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise APIError("OpenAI endpoint returned invalid JSON; check the endpoint before retrying") from None
        raise APIError("Request retries exhausted")
