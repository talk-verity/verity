import os
for key, value in {"GROQ_API_KEY": "", "GEMINI_API_KEY": "", "PINECONE_API_KEY": "", "R2_ACCOUNT_ID": "", "EMBEDDING_PROVIDER": "mock", "STT_PROVIDER": "mock", "TTS_PROVIDER": "mock", "DEMO_MODE": "true"}.items():
    os.environ[key] = value
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from database import Base


@pytest.fixture(autouse=True)
def report_storage(tmp_path, monkeypatch):
    from app.reports import storage
    monkeypatch.setattr(storage, "LOCAL_STORAGE_DIR", tmp_path / "reports")

@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_fks(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    from app.models.user import User
    for uid in ("test-user-id", "integration-test-user"):
        session.add(User(id=uid, clerk_id=uid, email=f"{uid}@example.test"))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_scenario_id():
    return "networking_event"


@pytest.fixture
def user_id():
    return "test-user-id"
