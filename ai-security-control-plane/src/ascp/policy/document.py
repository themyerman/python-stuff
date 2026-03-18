"""Versioned policy document schema (YAML/JSON) — tool allowlists first."""

from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class ToolsPolicy(BaseModel):
    """
    Tool invocation rules. ``mode=open`` skips checks unless ``deny`` matches.
    ``mode=allowlist`` requires each invoked tool to appear in ``allowed``.
    """

    mode: Literal["open", "allowlist"] = "open"
    allowed: list[str] = Field(default_factory=list)
    deny: list[str] = Field(default_factory=list)
    on_violation: Literal["block", "warn"] = "block"

    @field_validator("allowed", "deny", mode="before")
    @classmethod
    def _strip_tool_names(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise TypeError("expected list of strings")
        return [str(x).strip() for x in v if str(x).strip()]


class PolicyDocumentV1(BaseModel):
    """Policy document ``schema_version: \"1\"`` — extensible for PII, rate limits, etc."""

    schema_version: Literal["1"] = "1"
    tools: ToolsPolicy = Field(default_factory=ToolsPolicy)
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyDocumentV1:
        if not isinstance(data, dict):
            raise TypeError("policy document must be a mapping")
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def policy_document_from_yaml(text: str) -> PolicyDocumentV1:
    """Parse YAML into a validated v1 policy document."""
    raw = yaml.safe_load(text)
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("YAML root must be a mapping")
    return PolicyDocumentV1.from_dict(raw)
