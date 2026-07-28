from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.models.user import User
from database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session")
def create_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.session import Session as SessionModel
    session = SessionModel(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
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
