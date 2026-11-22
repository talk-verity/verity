import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.auth.deps import get_current_user
from app.core.settings import settings
from app.main import app
from app.models.report_job import ReportJob
from app.models.user import User
from app.reports.service import ReportService
from app.feedback.worker import run_once
from database import get_db
from test_reports import make_report, SAMPLE_CONTENT


def test_database_report_download_without_files(db_session, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "REPORT_STORAGE_MODE", "database")
    report, uid = make_report(db_session)
    service = ReportService()
    assert service.render_and_store(db_session, report.id) == "ready"
    assert report.storage_key is None and report.storage_url is None
    assert json.loads(report.content) == SAMPLE_CONTENT
    assert b"Overall Summary" in service.download_html(db_session, report.id, uid)
    assert not list(tmp_path.rglob("*.html"))


def test_request_processing_authorizes_and_targets_one_job(db_session, monkeypatch):
    from app.feedback import worker
    monkeypatch.setattr(settings, "REPORT_EXECUTION_MODE", "request")
    monkeypatch.setattr(settings, "REPORT_STORAGE_MODE", "database")
    other, _ = make_report(db_session, user_id="other-user")
    own, uid = make_report(db_session, user_id="own-user")
    db_session.add_all([ReportJob(report_id=other.id), ReportJob(report_id=own.id)])
    db_session.commit()
    own_id, other_id = own.id, other.id
    factory = sessionmaker(bind=db_session.get_bind())
    original = run_once
    monkeypatch.setattr(worker, "run_once", lambda **kwargs: original(factory, **kwargs))
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: db_session.get(User, uid)
    try:
        with TestClient(app) as client:
            assert client.post(f"/api/v1/reports/{other_id}/process").status_code == 404
            result = client.post(f"/api/v1/reports/{own_id}/process")
            assert result.status_code == 200
            assert result.json()["status"] == "ready"
            assert client.post(f"/api/v1/reports/{own_id}/process").json()["status"] == "ready"
        db_session.expire_all()
        assert db_session.get(ReportJob, own_id).attempts == 1
        assert db_session.get(ReportJob, other_id).attempts == 0
    finally:
        app.dependency_overrides.clear()
