import re

from backend.providers.base import ProviderAdapter, ProviderRequest


class GeminiAdapter(ProviderAdapter):
    name = "gemini"
    label = "Google Gemini"
    key_env = "GEMINI_API_KEY"
    default_model = "gemini-2.5-flash-lite"
    data_destination = "Google Gemini"

    def build_request(self, *, api_key, model, text, system_prompt, schema):
        if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
            raise ValueError("Gemini requires a model name, not a URL or router model ID")
        return ProviderRequest(
            url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            body={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": schema,
                    "maxOutputTokens": 1024,
                },
            },
        )

    def extract_text(self, payload):
        candidate = payload["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise ValueError("Blocked or incomplete response")
        return "".join(
            part["text"] for part in candidate["content"]["parts"] if not part.get("thought")
        )
