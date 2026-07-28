from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwk, jwt
from jose.constants import ALGORITHMS
from sqlalchemy.orm import Session

from app.core.settings import settings
from app.models.user import User
from database import get_db

security = HTTPBearer()
jwks_cache: list | None = None


def get_jwks():
    global jwks_cache
    if jwks_cache is None:
        import httpx
        url = settings.clerk_jwks_url
        if not url:
            raise HTTPException(status_code=500, detail="Clerk JWKS URL not configured")
        response = httpx.get(url)
        response.raise_for_status()
        jwks_cache = response.json()["keys"]
    return jwks_cache


def verify_clerk_token(token: str) -> dict:
    jwks = get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    for key in jwks:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
                "alg": "RS256",
            }
            break
    if not rsa_key:
        raise HTTPException(status_code=401, detail="Unable to find appropriate key")
    try:
        payload = jwt.decode(
            token,
            jwk.construct(rsa_key),
            algorithms=[ALGORITHMS.RS256],
            audience=settings.CLERK_PUBLISHABLE_KEY,
            issuer=f"https://{settings.CLERK_DOMAIN}",
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_clerk_token(credentials.credentials)
    clerk_id = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        email = payload.get("email", "")
        first_name = payload.get("given_name", "")
        last_name = payload.get("family_name", "")
        user = User(clerk_id=clerk_id, email=email, first_name=first_name, last_name=last_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
