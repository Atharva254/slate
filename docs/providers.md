# LLM provider configuration

The app defaults to OpenRouter. The current environment supplies `OPENROUTER_API_KEY`; no credential is copied into source or frontend configuration.

| Setting | Purpose / default |
| --- | --- |
| `LLM_PROVIDER` | `openrouter` (default) or `gemini` |
| `LLM_MODEL` | Provider-specific model ID; blank uses that adapter's default |
| `OPENROUTER_API_KEY` | Read only when OpenRouter is selected |
| `GEMINI_API_KEY` | Read only when direct Gemini is selected |

Set these in the root `.env` or backend environment and restart the backend. Process environment wins over `.env`; remove an existing environment override if editing the file appears ineffective. Nothing changes in the database or frontend. `/health` shows the configured provider/model and key presence, never the key. Presence is not proof of valid credentials; the live request provides that check. Old `GEMINI_MODEL` is accepted when using direct Gemini with no `LLM_MODEL`.

## Choose a model

For the current paid demo:

```dotenv
LLM_PROVIDER=openrouter
LLM_MODEL=deepseek/deepseek-v4-flash-0731
```

Supply `OPENROUTER_API_KEY` separately. The named model keeps the demo repeatable; review current [pricing and availability](https://openrouter.ai/deepseek/deepseek-v4-flash-0731) before changing usage. One real end-to-end backend sample using this configuration passed, including structured output and persistence after an app restart.

For a free alternative, set `LLM_MODEL=openrouter/free`. OpenRouter's [free router](https://openrouter.ai/openrouter/free) selects among available free models and filters for requested capabilities. The chosen model can vary and free capacity can be limited; this option is not a fixed-model benchmark and has not been live-tested in this project. There is no application fallback from a free model to a paid model.

OpenRouter requests use `response_format.type=json_schema`, `strict=true`, and `provider.require_parameters=true`. Choose endpoints that support structured outputs. Unsupported models fail visibly rather than silently dropping the schema; local Pydantic validation always remains authoritative. See [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).

For direct Gemini:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash-lite
```

Supply `GEMINI_API_KEY`. An OpenRouter key cannot authenticate against Google's direct API. No silent fallback switches vendors when a key is missing or a request fails.

## Add a provider

1. Add a class in `backend/providers/<vendor>.py` extending `ProviderAdapter`. Declare `name`, `label`, `key_env`, `default_model`, and `data_destination`.
2. Implement `build_request(...) -> ProviderRequest` for the fixed endpoint, authentication headers, and payload; implement `extract_text(payload) -> str`. Reject refusals and unfinished output rather than returning partial text. Do not log inputs, outputs, or secrets.
3. Register the class in `PROVIDERS` in `backend/providers/__init__.py`, and add its credential name to `.env.example`. Select it with `LLM_PROVIDER`.
4. Test its HTTP contract and error/finish semantics with `httpx.MockTransport`, then run one synthetic live sample. If a vendor uses unusual error codes, normalize them in its adapter or extend the shared error policy deliberately.

The shared `ContentAssistant` owns the prompt, deadline, HTTP errors, and `AIResult` validation. Routes, SQL storage, and UI do not contain vendor branches. A test registers a third example adapter and saves a result through the unchanged API. This is extensibility for the assignment, not a claim of production scalability.

## Live verification

With the normal app running and a valid selected key, run from `frontend`:

```powershell
npm run verify:live
```

This manually submits **one synthetic sample**, which can consume API credits. It checks save/reload/detail and writes `docs/screenshot.png` and `docs/live-verification.json`. It is separate from the fixture tests and performs no automatic retry. Review the generated summary against the original; a passing schema does not establish factual quality for other inputs.
