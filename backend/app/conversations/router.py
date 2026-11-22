from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.conversations.schemas import (
    ConversationCompleteRequest,
    ConversationCreate,
    ConversationResponse,
    ScenarioDetailResponse,
    ScenarioResponse,
    TurnCreate,
    TurnResponse,
)
from app.conversations.scenarios import get_scenario, list_scenarios
from app.conversations.service import ConversationService
from app.feedback.advisor import ResearchAdvisor
from app.models.user import User
from database import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service() -> ConversationService:
    return ConversationService()


@router.get("/scenarios", response_model=list[ScenarioResponse])
def get_scenarios():
    return list_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario_detail(scenario_id: str, current_user: User = Depends(get_current_user)):
    scenario = get_scenario(scenario_id)
    if not scenario:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    result = dict(scenario)
    try:
        from app.feedback.advisor import ResearchAdvisor
        tips = ResearchAdvisor().scenario_tips(scenario_id)
        if tips:
            result["tips"] = tips
    except Exception as e:
        from app.core.settings import settings
        import logging
        logging.getLogger(__name__).warning("Research tips unavailable for %s: %s", scenario_id, e)
    return result


@router.post("", response_model=ConversationResponse, status_code=201)
def create_conversation(
    body: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ConversationService = Depends(get_conversation_service),
):
    session = service.create_session(db, current_user.id, body.scenario_id)
    return ConversationResponse(
        id=session.id,
        scenario=session.scenario,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        turns=[],
    )


@router.get("/{session_id}", response_model=ConversationResponse)
def get_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ConversationService = Depends(get_conversation_service),
):
    session = service.get_session(db, session_id, current_user.id)
    turns = service.get_turns(db, session_id)
    return ConversationResponse(
        id=session.id,
        scenario=session.scenario,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        turns=[TurnResponse.model_validate(t) for t in turns],
    )


@router.delete("/{session_id}", status_code=204)
def delete_conversation(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ConversationService = Depends(get_conversation_service),
):
    service.delete_session(db, session_id, current_user.id)


@router.post("/{session_id}/respond", response_model=TurnResponse)
def respond(
    session_id: str,
    body: TurnCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ConversationService = Depends(get_conversation_service),
):
    turn = service.respond(db, session_id, current_user.id, body.content, str(body.request_id))
    return TurnResponse.model_validate(turn)


@router.post("/{session_id}/complete", status_code=200)
def complete_conversation(
    session_id: str,
    body: ConversationCompleteRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ConversationService = Depends(get_conversation_service),
):
    from datetime import datetime, timezone
    from app.models.session import Session as SessionModel
    from app.models.report import Report
    from app.models.turn import Turn
    from fastapi import HTTPException

    session = (db.query(SessionModel).filter(SessionModel.id == session_id,
               SessionModel.user_id == current_user.id).populate_existing().with_for_update().first())
    if not session:
        raise HTTPException(404, "Session not found")
    report = db.query(Report).filter(Report.session_id == session.id).order_by(Report.created_at).first()
    if report:
        return {"status": session.status, "report_id": report.id, "timed_out": session.status == "timed_out"}

    now = datetime.now(timezone.utc)
    created_at = session.created_at if session.created_at.tzinfo else session.created_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - created_at).total_seconds()
    is_timed_out = bool(body and body.reason == "time_expired") or elapsed_seconds >= 300

    has_user_turn = db.query(Turn).filter(Turn.session_id == session.id, Turn.speaker == "user").first() is not None
    if not is_timed_out and not has_user_turn:
        raise HTTPException(422, "Add a response before requesting feedback")

    session.status = "timed_out" if is_timed_out else "completed"
    scenario = get_scenario(session.scenario) or {}
    report_title = f"Feedback — {scenario.get('name', 'Conversation')}"
    if is_timed_out:
        report_title += " (Timed Out)"

    report = Report(user_id=current_user.id, session_id=session.id,
                    title=report_title, status="generating")
    db.add(report)
    db.flush()
    from app.feedback.service import FeedbackService
    FeedbackService.queue_generation(db, report.id)
    db.commit()
    return {"status": session.status, "report_id": report.id, "timed_out": is_timed_out}
