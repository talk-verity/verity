"""Set TEST_DATABASE_URL to an isolated PostgreSQL database; never use app data."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.report import Report
from app.models.report_job import ReportJob
from app.conversations.service import ConversationService
from app.conversations.gemini_client import MockAIService
from app.conversations.router import complete_conversation
from app.feedback.worker import run_once

@pytest.fixture
def pg():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    engine = create_engine(url)
    factory = sessionmaker(bind=engine)
    # Per-test rows, cleaned using the ORM cascades. Schema is created by Alembic.
    with factory() as db:
        user = User(clerk_id=f"test-{time.time_ns()}", email="test@example.test")
        db.add(user); db.commit(); uid = user.id
    yield factory, uid
    with factory() as db:
        user = db.get(User, uid)
        db.delete(user); db.commit()
    engine.dispose()

def completed(factory, uid):
    service = ConversationService(ai_service=MockAIService())
    with factory() as db:
        session = service.create_session(db, uid, "job_interview")
        service.respond(db, session.id, uid, "I built an API")
        return session.id

def test_concurrent_completion_has_one_report_and_job(pg):
    factory, uid = pg
    sid = completed(factory, uid)
    def complete():
        with factory() as db:
            return complete_conversation(sid, db.get(User, uid), db, ConversationService(ai_service=MockAIService()))
    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(lambda _: complete(), range(2)))
    assert results[0] == results[1]
    with factory() as db:
        assert db.query(Report).filter_by(session_id=sid).count() == 1
        assert db.query(ReportJob).filter_by(report_id=results[0]["report_id"]).count() == 1

def test_worker_lock_and_crash_recovery(pg):
    factory, uid = pg
    sid = completed(factory, uid)
    with factory() as db:
        rid = complete_conversation(sid, db.get(User, uid), db, ConversationService(ai_service=MockAIService()))["report_id"]
    # A disconnected worker rolls back its uncommitted claim.
    abandoned = factory()
    abandoned.execute(text("SELECT report_id FROM report_jobs WHERE report_id=:id FOR UPDATE"), {"id": rid})
    assert run_once(factory) is False
    abandoned.close()
    entered, release = Event(), Event()
    class SlowService:
        def generate_report(self, db, report_id):
            entered.set()
            assert release.wait(5)
            db.get(Report, report_id).status = "ready"
            db.commit()
    with ThreadPoolExecutor(1) as pool:
        work = pool.submit(run_once, factory, SlowService)
        assert entered.wait(5)
        try:
            assert run_once(factory) is False
        finally:
            release.set()
        assert work.result() is True
    with factory() as db:
        assert db.get(ReportJob, rid).status == "done"
        assert db.get(ReportJob, rid).attempts == 1

def test_concurrent_retries_do_not_duplicate_turns(pg):
    from uuid import uuid4
    from app.models.turn import Turn
    factory, uid = pg
    service = ConversationService(ai_service=MockAIService())
    with factory() as db:
        sid = service.create_session(db, uid, "job_interview").id
    request_id = str(uuid4())
    def respond():
        with factory() as db:
            return service.respond(db, sid, uid, "I built an API", request_id).id
    with ThreadPoolExecutor(2) as executor:
        results = list(executor.map(lambda _: respond(), range(2)))
    assert results[0] == results[1]
    with factory() as db:
        assert db.query(Turn).filter_by(session_id=sid).count() == 3

def test_worker_retries_are_bounded(pg):
    from datetime import datetime, timezone, timedelta
    factory, uid = pg
    sid = completed(factory, uid)
    with factory() as db:
        rid = complete_conversation(sid, db.get(User, uid), db, ConversationService(ai_service=MockAIService()))["report_id"]
    class FailingService:
        def generate_report(self, db, rid):
            raise RuntimeError("test provider failure")
    for attempt in range(1, 4):
        assert run_once(factory, FailingService)
        with factory() as db:
            job = db.get(ReportJob, rid)
            assert job.attempts == attempt
            assert job.status == ("pending" if attempt < 3 else "failed")
            job.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
    assert run_once(factory, FailingService) is False
    with factory() as db:
        assert db.get(Report, rid).status == "failed"
