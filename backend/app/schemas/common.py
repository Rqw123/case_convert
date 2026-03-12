from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SignalCandidate(BaseModel):
    signal_desc: str | None = Field(default=None)
    msg_id: str | None = Field(default=None)
    signal_name: str
    signal_val: str | None = Field(default=None)
    info_str: str | None = Field(default=None)
    match_reason: str | None = Field(default=None)


class CaseMatchResultSchema(BaseModel):
    case_id: str
    case_step: str
    matched: bool
    case_info: list[SignalCandidate] = Field(default_factory=list)
    unmatched_reason: str | None = None


class MatchResponseSchema(BaseModel):
    results: list[CaseMatchResultSchema] = Field(default_factory=list)


class ModelConfigSchema(BaseModel):
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.0
    timeout_seconds: int = 60


class MatchRunRequest(BaseModel):
    signal_source_id: int
    case_batch_id: int
    llm_config: ModelConfigSchema


class ParseResponseSchema(BaseModel):
    id: int
    summary: dict[str, Any]


class ExportResponseSchema(BaseModel):
    export_id: int
    export_file_name: str
    export_url: str
