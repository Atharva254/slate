import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.ai import ContentAssistant
from backend.providers.gemini import GeminiAdapter
from backend.main import create_app

RESULT = {
    "summary": "The team will simplify onboarding before the next pilot.",
    "tags": ["onboarding", "design", "pilot"],
}


def envelope(result=RESULT):
    return {
        "candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(result)}]}}
        ]
    }


def client_for(tmp_path, handler, **kwargs):
    provider = ContentAssistant(
        GeminiAdapter(),
        "test-key-not-a-credential",
        "gemini-2.5-flash-lite",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )
    return TestClient(create_app(tmp_path / "entries.db", provider))


def test_create_list_detail_and_restart(tmp_path):
    text = "  The team will simplify onboarding before the next pilot.\n' ; DROP TABLE entries; --"

    def provider(request):
        body = json.loads(request.content)
        assert body["contents"][0]["parts"][0]["text"] == text
        assert "untrusted" in body["systemInstruction"]["parts"][0]["text"]
        assert body["generationConfig"]["responseJsonSchema"]["properties"]["tags"]["minItems"] == 3
        assert request.headers["x-goog-api-key"] == "test-key-not-a-credential"
        assert "key=" not in str(request.url)
        return httpx.Response(200, json=envelope())

    with client_for(tmp_path, provider) as client:
        response = client.post("/entries", json={"text": text})
        assert response.status_code == 201
        saved = response.json()
        assert saved["text"] == text
        assert saved["tags"] == RESULT["tags"]
        assert client.get(f"/entries/{saved['id']}").json() == saved

    # New app and SQLite connections, same disk file: no in-memory persistence.
    with client_for(tmp_path, provider) as restarted:
        assert restarted.get("/entries").json() == {"entries": [saved], "total": 1}
        assert restarted.get("/entries/999").status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"text": ""},
        {"text": " \n\t"},
        {"text": "a" * 10001},
        {"text": 42},
        {"text": "ok", "extra": "no"},
    ],
)
def test_invalid_input_never_calls_provider(tmp_path, body):
    def fail(request):
        pytest.fail("Provider must not be called for invalid input")

    with client_for(tmp_path, fail) as client:
        assert client.post("/entries", json=body).status_code == 422
        assert client.get("/entries").json()["total"] == 0


@pytest.mark.parametrize(
    "result",
    [
        {"summary": "ok", "tags": ["a", "b"]},
        {"summary": "ok", "tags": ["a", "b", "c", "d"]},
        {"summary": "  ", "tags": ["a", "b", "c"]},
        {"summary": "ok", "tags": ["Tag", " tag ", "other"]},
        {"summary": "ok", "tags": ["", "b", "c"]},
    ],
)
def test_malformed_output_is_not_saved(tmp_path, result):
    with client_for(tmp_path, lambda request: httpx.Response(200, json=envelope(result))) as client:
        response = client.post("/entries", json={"text": "A sample note"})
        assert response.status_code == 502
        assert response.json()["error"]["code"] == "invalid_ai_output"
        assert client.get("/entries").json()["total"] == 0


@pytest.mark.parametrize(
    "response, code",
    [
        (httpx.Response(200, text="not json"), "invalid_ai_output"),
        (httpx.Response(200, json={"candidates": []}), "invalid_ai_output"),
        (httpx.Response(200, json={"candidates": [None]}), "invalid_ai_output"),
        (
            httpx.Response(
                200,
                json={
                    "candidates": [
                        {"finishReason": "STOP", "content": {"parts": [{"text": "not json"}]}}
                    ]
                },
            ),
            "invalid_ai_output",
        ),
        (
            httpx.Response(200, json={"candidates": [{"finishReason": "MAX_TOKENS"}]}),
            "invalid_ai_output",
        ),
        (httpx.Response(429, text="private provider error"), "ai_busy"),
        (httpx.Response(403, text="private provider error"), "ai_unavailable"),
    ],
)
def test_provider_failure_is_safe(tmp_path, response, code):
    with client_for(tmp_path, lambda request: response) as client:
        result = client.post("/entries", json={"text": "A sample note"})
        assert result.status_code in (502, 503)
        assert result.json()["error"]["code"] == code
        assert "private provider error" not in result.text
        assert client.get("/entries").json()["total"] == 0


def test_total_timeout_and_retry(tmp_path):
    calls = 0

    async def provider(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            await asyncio.sleep(0.1)
        return httpx.Response(200, json=envelope())

    with client_for(tmp_path, provider, timeout=0.03) as client:
        assert client.post("/entries", json={"text": "A note"}).status_code == 504
        assert client.get("/entries").json()["total"] == 0
        assert client.post("/entries", json={"text": "A note"}).status_code == 201
        assert client.get("/entries").json()["total"] == 1


def test_pagination(tmp_path):
    with client_for(tmp_path, lambda request: httpx.Response(200, json=envelope())) as client:
        first = client.post("/entries", json={"text": "First"}).json()
        second = client.post("/entries", json={"text": "Second"}).json()
        assert client.get("/entries?limit=1").json() == {"entries": [second], "total": 2}
        assert client.get("/entries?limit=1&offset=1").json()["entries"] == [first]
        assert client.get("/entries?limit=0").status_code == 422
        assert client.get(f"/entries?offset={2**64}").status_code == 422
        assert client.get(f"/entries/{2**64}").status_code == 422


def test_delete_entry_and_missing_entry(tmp_path):
    with client_for(tmp_path, lambda request: httpx.Response(200, json=envelope())) as client:
        saved = client.post("/entries", json={"text": "Delete this summary"}).json()
        assert client.delete(f"/entries/{saved['id']}").status_code == 204
        assert client.get(f"/entries/{saved['id']}").status_code == 404
        assert client.get("/entries").json() == {"entries": [], "total": 0}
        assert client.delete(f"/entries/{saved['id']}").status_code == 404
        assert client.delete("/entries/0").status_code == 422
        assert client.delete(f"/entries/{2**64}").status_code == 422

    with client_for(
        tmp_path, lambda request: pytest.fail("Deletion does not call AI")
    ) as restarted:
        assert restarted.get(f"/entries/{saved['id']}").status_code == 404


def test_missing_key_remains_readable(tmp_path):
    with TestClient(
        create_app(
            tmp_path / "entries.db", ContentAssistant(GeminiAdapter(), "", "gemini-2.5-flash-lite")
        )
    ) as client:
        assert client.get("/health").json()["ai_configured"] is False
        assert client.post("/entries", json={"text": "A note"}).status_code == 503
        assert client.get("/entries").json()["total"] == 0
