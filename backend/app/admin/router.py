from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.models.referral_code import ReferralCode
from app.models.user import User
from database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/referrals")
def get_referral_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    codes = db.query(ReferralCode).filter(
        ReferralCode.owner_clerk_id == current_user.clerk_id,
        ReferralCode.active.is_(True),
    ).all()
    if not codes:
        raise HTTPException(status_code=403, detail="Not authorized")
    return {"referrals": [
        {
            "code": code.code,
            "label": code.label,
            "unique_users": db.query(func.count(User.id)).filter(User.referral_code == code.code).scalar(),
            "created_at": code.created_at,
        }
        for code in codes
    ]}
