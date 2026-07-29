from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.feedback.schemas import ReportResponse, ReportStatusResponse
from app.feedback.service import FeedbackService
from app.models.user import User
from database import get_db

router = APIRouter(tags=["feedback"])


def get_feedback_service() -> FeedbackService:
    return FeedbackService()


@router.get("/sessions/{session_id}/report", response_model=ReportResponse | ReportStatusResponse)
def get_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: FeedbackService = Depends(get_feedback_service),
):
    report = service.get_report(db, session_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    base = {"session_id": session_id, "status": report.status}

    if report.status == "ready":
        import json
        content = json.loads(report.content) if report.content else None
        return ReportResponse(
            **base,
            id=report.id,
            title=report.title,
            content=content,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    return ReportStatusResponse(**base)
