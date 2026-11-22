from datetime import datetime

from pydantic import BaseModel


class ReportStatusResponse(BaseModel):
    status: str
    session_id: str


class ReportResponse(ReportStatusResponse):
    id: str
    title: str
    content: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FeedbackAnalysis(BaseModel):
    overall_score: float | None = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []
    confidence_score: float | None = None
    clarity_score: float | None = None
    filler_word_count: int = 0
    filler_words: list[str] = []
    interruption_count: int | None = None
    goal_completion: str = ""
    total_turns: int = 0
    total_user_words: int = 0
    avg_response_length: float = 0.0
