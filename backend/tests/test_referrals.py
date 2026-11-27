from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.auth.deps import get_current_user
from app.main import app
from app.models.referral_code import ReferralCode
from app.models.user import User
from database import get_db

CREDS = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")


def stub_token(monkeypatch, clerk_id):
    monkeypatch.setattr("app.auth.deps.verify_clerk_token",
                        lambda _: {"sub": clerk_id, "email": f"{clerk_id}@example.test"})
    monkeypatch.setattr("app.core.limits.check_rate", lambda _: None)


def test_new_user_is_attributed(monkeypatch, db_session):
    db_session.add(ReferralCode(code="ACME", label="Acme", owner_clerk_id="manager-1"))
    db_session.commit()
    stub_token(monkeypatch, "new-user")

    user = get_current_user(CREDS, db_session, referral_code="ACME")

    assert user.referral_code == "ACME"


def test_invalid_code_is_ignored(monkeypatch, db_session):
    stub_token(monkeypatch, "new-user")
    user = get_current_user(CREDS, db_session, referral_code="NOPE")
    assert user.referral_code is None


def test_existing_user_is_not_reattributed(monkeypatch, db_session):
    db_session.add_all([
        ReferralCode(code="ACME", label="Acme", owner_clerk_id="manager-1"),
        ReferralCode(code="OTHER", label="Other", owner_clerk_id="manager-2"),
    ])
    existing = db_session.get(User, "test-user-id")
    existing.referral_code = "ACME"
    db_session.commit()
    stub_token(monkeypatch, "test-user-id")

    user = get_current_user(CREDS, db_session, referral_code="OTHER")

    assert user.referral_code == "ACME"


def test_manager_sees_only_their_counts(db_session):
    db_session.add_all([
        User(id="manager-row", clerk_id="manager-1", email="manager@example.test"),
        ReferralCode(code="ACME", label="Acme", owner_clerk_id="manager-1"),
        ReferralCode(code="OTHER", label="Other", owner_clerk_id="manager-2"),
    ])
    referred = db_session.get(User, "test-user-id")
    referred.referral_code = "ACME"
    other = db_session.get(User, "integration-test-user")
    other.referral_code = "OTHER"
    db_session.commit()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: db_session.get(User, "manager-row")
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/referrals")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    referrals = response.json()["referrals"]
    assert len(referrals) == 1
    assert referrals[0]["code"] == "ACME"
    assert referrals[0]["label"] == "Acme"
    assert referrals[0]["unique_users"] == 1


def test_non_manager_is_forbidden(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: db_session.get(User, "test-user-id")
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/referrals")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 403
