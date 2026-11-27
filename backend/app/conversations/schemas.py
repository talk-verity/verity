from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class ConversationCreate(BaseModel):
    scenario_id: str


class TurnResponse(BaseModel):
    id: str
    speaker: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    scenario: str
    status: str
    created_at: datetime
    updated_at: datetime
    time_limit_seconds: int = 300
    turns: list[TurnResponse] = []

    model_config = {"from_attributes": True}


class ConversationCompleteRequest(BaseModel):
    reason: Literal["time_expired"] | None = None


class TurnCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    request_id: UUID

    @field_validator("content")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Message must not be blank")
        return value.strip()


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    difficulty: str


class ScenarioDetailResponse(ScenarioResponse):
    persona: dict
    goal: str
    context: str
    opening_line: str
    tips: list[str] = []
