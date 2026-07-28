from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.conversations.schemas import (
    ConversationCreate,
    ConversationResponse,
    ScenarioDetailResponse,
    ScenarioResponse,
    TurnCreate,
    TurnResponse,
)
from app.conversations.scenarios import get_scenario, list_scenarios
from app.conversations.service import ConversationService
from app.models.user import User
from database import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_conversation_service() -> ConversationService:
    return ConversationService()


@router.get("/scenarios", response_model=list[ScenarioResponse])
def get_scenarios():
    return list_scenarios()


@router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailResponse)
def get_scenario_detail(scenario_id: str):
    scenario = get_scenario(scenario_id)
    if not scenario:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return scenario


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
    turn = service.respond(db, session_id, current_user.id, body.content)
    return TurnResponse.model_validate(turn)
