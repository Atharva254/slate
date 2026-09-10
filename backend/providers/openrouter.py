from backend.providers.base import ProviderAdapter, ProviderRequest


class OpenRouterAdapter(ProviderAdapter):
    name = "openrouter"
    label = "OpenRouter"
    key_env = "OPENROUTER_API_KEY"
    default_model = "deepseek/deepseek-v4-flash-0731"
    data_destination = "OpenRouter and the model provider it routes to"

    def build_request(self, *, api_key, model, text, system_prompt, schema):
        return ProviderRequest(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            body={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "content_summary", "strict": True, "schema": schema},
                },
                "provider": {"require_parameters": True},
                "max_tokens": 1024,
                "stream": False,
            },
        )

    def extract_text(self, payload):
        choice = payload["choices"][0]
        message = choice["message"]
        if choice.get("finish_reason") != "stop" or message.get("refusal"):
            raise ValueError("Refused or incomplete response")
        return message["content"]
