from datetime import datetime

from pydantic import BaseModel


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
    turns: list[TurnResponse] = []

    model_config = {"from_attributes": True}


class TurnCreate(BaseModel):
    content: str


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
