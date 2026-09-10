from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MAX_TEXT_LENGTH = 10_000
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class EntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank")
        return value  # Preserve the submitted original, including formatting.


class AIResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]
    tags: list[Tag] = Field(min_length=3, max_length=3)

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: list[str]) -> list[str]:
        if len({tag.casefold() for tag in tags}) != 3:
            raise ValueError("Exactly three distinct tags are required")
        return tags


class Entry(AIResult):
    id: int
    text: str
    created_at: str


class EntryPage(BaseModel):
    entries: list[Entry]
    total: int
