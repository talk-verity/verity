import json
import time
from uuid import uuid4
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.auth.deps import get_current_user
from app.conversations.router import get_conversation_service, complete_conversation
from app.conversations.service import ConversationService
from app.conversations.gemini_client import MockAIService
from app.feedback.analyzer import Analyzer
from app.feedback.generator import FeedbackGenerator
from app.feedback.service import FeedbackService
from app.models.user import User
from app.models.turn import Turn
from app.models.report import Report
from app.models.report_job import ReportJob
from app.voice.router import get_voice_service
from app.voice.service import VoiceService
from app.voice.stt import MockSTTService
from app.voice.tts import MockTTSService
from database import get_db

@pytest.fixture
def http(db_session):
    service = ConversationService(ai_service=MockAIService())
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: db_session.get(User, "test-user-id")
    app.dependency_overrides[get_conversation_service] = lambda: service
    voice = VoiceService(stt=MockSTTService(), tts=MockTTSService(), conversation_service=service)
    app.dependency_overrides[get_voice_service] = lambda: voice
    # Without context-manager startup, no local speech model warmup.
    client = TestClient(app, raise_server_exceptions=False)
    yield client, service, voice
    client.close()
    app.dependency_overrides.clear()

def test_no_fake_scoring_or_ai_credit():
    analysis = Analyzer().analyze("job_interview", ["Bananas orbit purple staplers beyond the moon."], ["I built a system and improved outcomes by 40%."])
    assert analysis["overall_score"] is None
    assert analysis["confidence_score"] is None
    assert not any(o["observed"] for o in analysis["rubric_observations"])
    report = json.loads(FeedbackGenerator().generate(analysis, "Interview", "Interviewer"))
    assert "addressed the scenario goals well" not in report["summary"]
    assert report["assessment_note"]

def test_politeness_and_questions_are_not_penalized():
    a = Analyzer().analyze("job_interview", ["Sorry, could you clarify what you would like to know?"], [])
    assert a["weaknesses"] == []
    assert a["filler_word_count"] == 0
    assert a["confidence_score"] is None

def test_provider_failure_rolls_back_user_turn(db_session):
    ai = Mock()
    ai.generate.side_effect = RuntimeError("secret provider detail")
    service = ConversationService(ai_service=ai)
    session = service.create_session(db_session, "test-user-id", "job_interview")
    with pytest.raises(HTTPException) as failure:
        service.respond(db_session, session.id, "test-user-id", "Hello")
    assert failure.value.status_code == 503
    assert db_session.query(Turn).count() == 1

def test_text_request_is_idempotent_and_validated(http, db_session):
    client, service, _ = http
    session = service.create_session(db_session, "test-user-id", "job_interview")
    body = {"content": "I built a product", "request_id": str(uuid4())}
    path = f"/api/v1/conversations/{session.id}/respond"
    first = client.post(path, json=body)
    second = client.post(path, json=body)
    assert first.status_code == 200, first.text
    assert first.json()["id"] == second.json()["id"]
    assert db_session.query(Turn).count() == 3
    assert client.post(path, json={**body, "content": "  "}).status_code == 422

def test_completion_creates_one_durable_job(http, db_session):
    client, service, _ = http
    session = service.create_session(db_session, "test-user-id", "job_interview")
    path = f"/api/v1/conversations/{session.id}/complete"
    assert client.post(path).status_code == 422
    service.respond(db_session, session.id, "test-user-id", "I built an API")
    first = client.post(path)
    second = client.post(path)
    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    assert db_session.query(Report).count() == 1
    assert db_session.query(ReportJob).count() == 1

def test_voice_form_selects_explicit_session_and_checks_owner(http, db_session):
    from test_voice import _wav_bytes
    client, service, _ = http
    older = service.create_session(db_session, "test-user-id", "job_interview")
    newer = service.create_session(db_session, "test-user-id", "networking_event")
    data = {"session_id": older.id, "request_id": str(uuid4())}
    response = client.post("/api/v1/voice/converse", data=data, files={"file": ("a.wav", _wav_bytes(), "audio/wav")})
    assert response.status_code == 200, response.text
    assert "event: done" in response.text
    assert len(service.get_turns(db_session, older.id)) == 3
    assert len(service.get_turns(db_session, newer.id)) == 1
    missing = client.post("/api/v1/voice/converse", files={"file": ("a", b"test")})
    assert missing.status_code == 422
    other = service.create_session(db_session, "integration-test-user", "job_interview")
    assert client.post("/api/v1/voice/converse", data={**data, "session_id": other.id}, files={"file": ("a", b"test")}).status_code == 404

def test_research_failure_preserves_feedback_and_transcript_order(db_session):
    service = ConversationService(ai_service=MockAIService())
    session = service.create_session(db_session, "test-user-id", "job_interview")
    service.respond(db_session, session.id, "test-user-id", "MY ANSWER")
    report = Report(user_id="test-user-id", session_id=session.id, title="Test")
    db_session.add(report); db_session.commit()
    feedback = FeedbackService()
    feedback.rag.retrieve_context = Mock(side_effect=RuntimeError("offline"))
    feedback.generate_report(db_session, report.id)
    transcript = feedback.rag.retrieve_context.call_args.args[1]
    assert transcript.startswith("AI:")
    assert transcript.index("AI:") < transcript.index("User: MY ANSWER")
    assert db_session.get(Report, report.id).status == "ready"

def test_foreign_keys_really_enforced(db_session):
    db_session.add(Turn(session_id="missing", speaker="user", content="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_malformed_jwt_is_401():
    from app.auth.deps import verify_clerk_token
    with pytest.raises(HTTPException) as error:
        verify_clerk_token("not-a-token")
    assert error.value.status_code == 401

def test_rotated_jwks_refresh(monkeypatch):
    from app.auth import deps
    from jose import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    from jose import jwk
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    key = jwk.construct(public, algorithm="RS256").to_dict()
    key["kid"] = "new-key"
    monkeypatch.setattr(deps, "jwks_cache", [{**key, "kid": "old-key"}])
    monkeypatch.setattr(deps, "_jwks_loaded", time.monotonic() - 10)
    monkeypatch.setattr(deps.settings, "CLERK_DOMAIN", "example.clerk.test")
    response = Mock(); response.json.return_value = {"keys": [key]}
    fetch = Mock(return_value=response)
    monkeypatch.setattr(deps.httpx, "get", fetch)
    token = jwt.encode({"sub": "u", "iss": "https://example.clerk.test", "exp": time.time()+60, "azp": "http://localhost:3000"}, pem, algorithm="RS256", headers={"kid": "new-key"})
    assert deps.verify_clerk_token(token)["sub"] == "u"
    assert fetch.call_count == 1
    assert deps.verify_clerk_token(token)["sub"] == "u"
    assert fetch.call_count == 1

@pytest.mark.asyncio
async def test_voice_work_does_not_block_event_loop(db_session):
    import asyncio
    from threading import Event
    from test_voice import _wav_bytes
    entered, release = Event(), Event()
    class SlowSTT(MockSTTService):
        def transcribe(self, path):
            entered.set()
            assert release.wait(2)
            return "I built an API"
    service = ConversationService(ai_service=MockAIService())
    sid = service.create_session(db_session, "test-user-id", "job_interview").id
    voice = VoiceService(stt=SlowSTT(), tts=MockTTSService(), conversation_service=service)
    async def consume():
        return [event async for event in voice.converse(db_session, "test-user-id", sid, _wav_bytes())]
    task = asyncio.create_task(consume())
    try:
        for _ in range(100):
            if entered.is_set(): break
            await asyncio.sleep(.01)
        assert entered.is_set()
        assert not task.done()
    finally:
        release.set()
    assert (await task)[-1][0] == "audio"

def test_bad_audio_conversion_cleans_temporary_files(tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    voice = VoiceService(stt=MockSTTService(), tts=MockTTSService())
    with pytest.raises(HTTPException):
        voice._prepare_audio(b"RIFFxxxxWAVEbad-data", None)
    assert list(tmp_path.iterdir()) == []

@pytest.mark.asyncio
async def test_upload_limit_closes_file(monkeypatch):
    import io
    from starlette.datastructures import UploadFile
    from app.voice.router import read_audio
    from app.core.settings import settings
    monkeypatch.setattr(settings, "MAX_AUDIO_BYTES", 3)
    file = UploadFile(io.BytesIO(b"oversize"), filename="x")
    with pytest.raises(HTTPException) as err:
        await read_audio(file)
    assert err.value.status_code == 413
    assert file.file.closed

def test_failed_report_can_be_requeued(http, db_session):
    client, service, _ = http
    session = service.create_session(db_session, "test-user-id", "job_interview")
    service.respond(db_session, session.id, "test-user-id", "Answer")
    result = client.post(f"/api/v1/conversations/{session.id}/complete").json()
    report = db_session.get(Report, result["report_id"])
    report.status = "failed"
    job = db_session.get(ReportJob, report.id)
    job.status = "failed"; job.attempts = 3
    db_session.commit()
    assert client.post(f"/api/v1/reports/{report.id}/retry").json()["status"] == "generating"
    db_session.refresh(job)
    assert job.status == "pending" and job.attempts == 0

def test_health_reports_database_failure(monkeypatch):
    import database
    monkeypatch.setattr(database, "check_db_connection", lambda: False)
    client = TestClient(app)
    assert client.get("/health").status_code == 503
    assert client.get("/live").status_code == 200
    client.close()

@pytest.mark.asyncio
async def test_tts_failure_does_not_discard_saved_conversation(db_session, monkeypatch):
    from test_voice import _wav_bytes
    from app.voice import service as voice_module
    monkeypatch.setattr(voice_module, "get_tts_service", Mock(side_effect=HTTPException(503, "Unavailable")))
    conversation = ConversationService(ai_service=MockAIService())
    sid = conversation.create_session(db_session, "test-user-id", "job_interview").id
    voice = VoiceService(stt=MockSTTService(), conversation_service=conversation)
    events = [event async for event in voice.converse(db_session, "test-user-id", sid, _wav_bytes())]
    assert events[-1][0] == "warning"
    assert len(conversation.get_turns(db_session, sid)) == 3
