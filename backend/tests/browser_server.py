"""Explicit test-only server: real API/SQLite, deterministic provider HTTP transport.

Never used by backend.main:app. Each server run gets a separate disposable database.
"""

import asyncio
import json
from uuid import uuid4

import httpx

from backend.ai import ContentAssistant
from backend.providers.openrouter import OpenRouterAdapter
from backend.main import ROOT, create_app


async def respond(request):
    text = json.loads(request.content)["messages"][1]["content"]
    await asyncio.sleep(0.5)
    if text == "TEST_INVALID_OUTPUT":
        return httpx.Response(
            200,
            json={"choices": [{"finish_reason": "stop", "message": {"content": "not valid JSON"}}]},
        )
    result = {
        "summary": "The team will improve the onboarding pilot by making document upload easier to find and simplifying help text. Priya will prepare design updates by Friday, while support gathers feedback from the next testers. A launch date is still unconfirmed.",
        "tags": ["onboarding", "user-feedback", "product-design"],
    }
    return httpx.Response(
        200,
        json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(result)}}]},
    )


provider = ContentAssistant(
    OpenRouterAdapter(),
    "test-key-not-a-credential",
    "google/gemini-2.5-flash-lite",
    transport=httpx.MockTransport(respond),
)
app = create_app(ROOT / "tmp" / "browser-tests" / f"{uuid4()}.db", provider)
