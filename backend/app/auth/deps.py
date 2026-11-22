from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.constants import ALGORITHMS
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.user import User
from database import get_db

import logging
import time
from threading import Lock
import httpx
from sqlalchemy.exc import IntegrityError

security = HTTPBearer()
jwks_cache: list | None = None
_jwks_loaded = 0.0
_jwks_lock = Lock()

def get_jwks(force=False):
    global jwks_cache, _jwks_loaded
    with _jwks_lock:
        age = time.monotonic() - _jwks_loaded
        if jwks_cache is not None and age < settings.CLERK_JWKS_TTL_SECONDS and (not force or age < 5):
            return jwks_cache
        if not settings.clerk_jwks_url:
            raise HTTPException(503, "Authentication is not configured")
        try:
            response = httpx.get(settings.clerk_jwks_url, timeout=5)
            response.raise_for_status()
            keys = response.json()["keys"]
            if not isinstance(keys, list) or not keys:
                raise ValueError("Invalid key set")
        except Exception as exc:
            logging.getLogger(__name__).exception("Signing key refresh failed")
            raise HTTPException(503, "Authentication temporarily unavailable") from exc
        jwks_cache, _jwks_loaded = keys, time.monotonic()
        return keys

def verify_clerk_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise ValueError("Invalid token header")
        keys = get_jwks()
        key = next((k for k in keys if k.get("kid") == header["kid"]), None)
        if key is None:
            key = next((k for k in get_jwks(force=True) if k.get("kid") == header["kid"]), None)
        if key is None:
            raise ValueError("Unknown signing key")
        payload = jwt.decode(token, jwk.construct(key, algorithm="RS256"), algorithms=["RS256"],
            issuer=f"https://{settings.CLERK_DOMAIN}", audience=settings.CLERK_AUDIENCE or None,
            options={"require_exp": True, "require_sub": True, "require_iss": True,
                     "verify_aud": bool(settings.CLERK_AUDIENCE)})
        if payload.get("azp") and payload["azp"] not in settings.CLERK_AUTHORIZED_PARTIES:
            raise ValueError("Unauthorized origin")
        if payload.get("sts") == "pending":
            raise ValueError("Pending session")
        return payload
    except (JWTError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(401, "Invalid token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    from app.core.limits import check_rate
    check_rate(clerk_id)
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        email = payload.get("email", "")
        first_name = payload.get("given_name", "")
        last_name = payload.get("family_name", "")
        user = User(clerk_id=clerk_id, email=email, first_name=first_name, last_name=last_name)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.clerk_id == clerk_id).one()
        db.refresh(user)
    return user
