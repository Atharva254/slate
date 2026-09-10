import json

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.ai import ContentAssistant, create_assistant
from backend.main import create_app
from backend.providers import PROVIDERS
from backend.providers.base import ProviderAdapter, ProviderRequest
from backend.providers.openrouter import OpenRouterAdapter

RESULT = {"summary": "The pilot starts on Friday.", "tags": ["pilot", "schedule", "launch"]}


def envelope(result=RESULT, finish="stop", **message):
    return {
        "choices": [
            {"finish_reason": finish, "message": {"content": json.dumps(result), **message}}
        ]
    }


def client_for(tmp_path, handler):
    assistant = ContentAssistant(
        OpenRouterAdapter(),
        "test-secret",
        "openrouter/free",
        transport=httpx.MockTransport(handler),
    )
    return TestClient(create_app(tmp_path / "entries.db", assistant))


def test_openrouter_request_save_and_restart(tmp_path):
    def handler(request):
        assert str(request.url) == "https://openrouter.ai/api/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert "x-goog-api-key" not in request.headers
        body = json.loads(request.content)
        assert body["model"] == "openrouter/free"
        assert body["messages"][1] == {"role": "user", "content": "The pilot starts on Friday."}
        assert "untrusted" in body["messages"][0]["content"]
        assert body["provider"] == {"require_parameters": True}
        assert body["response_format"]["json_schema"]["strict"] is True
        assert (
            body["response_format"]["json_schema"]["schema"]["properties"]["tags"]["maxItems"] == 3
        )
        return httpx.Response(200, json=envelope())

    with client_for(tmp_path, handler) as client:
        result = client.post("/entries", json={"text": "The pilot starts on Friday."})
        assert result.status_code == 201
        saved = result.json()
        health = client.get("/health").json()
        assert health["provider"] == "openrouter"
        assert "test-secret" not in json.dumps(health)
        assert health["api_key_env"] == "OPENROUTER_API_KEY"
    with client_for(tmp_path, handler) as client:
        assert client.get(f"/entries/{saved['id']}").json() == saved


@pytest.mark.parametrize(
    "payload, status, code",
    [
        (envelope(finish="length"), 200, "invalid_ai_output"),
        (envelope(refusal="No"), 200, "invalid_ai_output"),
        (envelope(content=None), 200, "invalid_ai_output"),
        (envelope(result={"summary": "ok", "tags": ["a", "b"]}), 200, "invalid_ai_output"),
        ({"choices": []}, 200, "invalid_ai_output"),
        ({"error": {"code": 429, "message": "private upstream error"}}, 200, "ai_busy"),
        ({"error": {"message": "private upstream error"}}, 402, "ai_credit_limit"),
    ],
)
def test_openrouter_failures_do_not_persist(tmp_path, payload, status, code):
    with client_for(tmp_path, lambda request: httpx.Response(status, json=payload)) as client:
        response = client.post("/entries", json={"text": "A note"})
        assert response.status_code in (502, 503)
        assert response.json()["error"]["code"] == code
        assert "private upstream error" not in response.text
        assert client.get("/entries").json()["total"] == 0


def test_configuration_selects_only_the_requested_provider_key():
    env = {"OPENROUTER_API_KEY": "router-key", "GEMINI_API_KEY": "google-key"}
    router = create_assistant(env)
    assert router.adapter.name == "openrouter"
    assert router._api_key == "router-key"
    assert router.model == "deepseek/deepseek-v4-flash-0731"
    gemini = create_assistant({**env, "LLM_PROVIDER": "gemini", "GEMINI_MODEL": "legacy-model"})
    assert gemini._api_key == "google-key"
    assert gemini.model == "legacy-model"
    assert (
        create_assistant({**env, "LLM_PROVIDER": "gemini", "LLM_MODEL": "new-model"}).model
        == "new-model"
    )
    assert (
        create_assistant({"GEMINI_API_KEY": "google-key"}).public_config()["ai_configured"] is False
    )
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        create_assistant({"LLM_PROVIDER": "typo"})


def test_a_new_adapter_needs_no_route_or_service_changes(tmp_path, monkeypatch):
    class ExampleAdapter(ProviderAdapter):
        name, label, key_env, default_model, data_destination = (
            "example",
            "Example",
            "EXAMPLE_KEY",
            "small",
            "Example",
        )

        def build_request(self, *, api_key, model, text, system_prompt, schema):
            return ProviderRequest(
                "https://example.invalid/summarize", {"x-key": api_key}, {"input": text}
            )

        def extract_text(self, payload):
            return payload["output"]

    monkeypatch.setitem(PROVIDERS, "example", ExampleAdapter)
    assistant = create_assistant({"LLM_PROVIDER": "example", "EXAMPLE_KEY": "test-key"})
    assistant.transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"output": json.dumps(RESULT)})
    )
    with TestClient(create_app(tmp_path / "example.db", assistant)) as client:
        assert (
            client.post("/entries", json={"text": "The pilot starts on Friday."}).status_code == 201
        )
