from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.models.user import User
from database import get_db
from app.conversations.schemas import ConversationCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session")
def create_session(body: ConversationCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.conversations.service import ConversationService
    session = ConversationService().create_session(db, current_user.id, body.scenario_id)
    return {"session_id": session.id, "status": session.status}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "clerk_id": current_user.clerk_id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
    }
