"""Provider-specific wire formats; business rules live in backend.ai instead."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderRequest:
    url: str
    headers: dict[str, str]
    body: dict[str, Any]


class ProviderAdapter(ABC):
    name: str
    label: str
    key_env: str
    default_model: str
    data_destination: str

    @abstractmethod
    def build_request(
        self, *, api_key: str, model: str, text: str, system_prompt: str, schema: dict
    ) -> ProviderRequest:
        """Translate the shared task into this provider's HTTP request."""

    @abstractmethod
    def extract_text(self, payload: dict) -> str:
        """Return completed output text, or raise ValueError on refusal/truncation."""
