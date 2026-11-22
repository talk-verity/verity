import json

import pytest

from app.models.report import Report
from app.models.user import User
from app.reports.renderer import ReportRenderer
from app.reports.service import ReportService
from app.reports.storage import LocalReportStorage, create_storage

SAMPLE_CONTENT = {
    "scenario": "Networking Event",
    "persona": "Jordan Chen",
    "overall_score": 82.0,
    "summary": "Strong performance. You communicated effectively.",
    "metrics": {
        "confidence": 80.0,
        "clarity": 85.0,
        "filler_word_count": 2,
        "filler_words": ["um"],
        "total_turns": 4,
        "total_user_words": 120,
        "avg_response_length": 30.0,
    },
    "goal_completion": "highly addressed",
    "strengths": ["Uses concrete action verbs", "Asks thoughtful questions"],
    "weaknesses": ["Overuses filler adverbs"],
    "recommendations": ["Pause instead of filling silence."],
    "transcript_examples": [
        {"type": "strength", "label": "Uses concrete action verbs", "quote": "I built a platform that reduced latency."},
        {"type": "weakness", "label": "Overuses filler adverbs", "quote": "Basically, um, I think we should ship it."},
    ],
    "references": [{"source": "hbr.pdf", "snippet": "Active listening is key to effective communication."}],
}


@pytest.fixture
def storage(tmp_path):
    return LocalReportStorage(base_dir=tmp_path / "reports")


@pytest.fixture
def service(storage):
    return ReportService(storage=storage)


def make_report(db_session, user_id="report-user", status="generating", content=None):
    from app.models.session import Session as SessionModel
    user = User(id=user_id, clerk_id=f"clerk-{user_id}", email=f"{user_id}@test.com")
    db_session.add(user)
    db_session.flush()
    session = SessionModel(user_id=user_id, scenario="networking_event", status="completed")
    db_session.add(session)
    db_session.flush()
    report = Report(
        user_id=user_id,
        session_id=session.id,
        title="Feedback — Networking Event",
        status=status,
        content=json.dumps(content or SAMPLE_CONTENT),
    )
    db_session.add(report)
    db_session.commit()
    return report, user_id


class TestReportRenderer:
    @pytest.fixture
    def renderer(self):
        return ReportRenderer()

    def test_renders_all_sections(self, renderer):
        html = renderer.render_html(SAMPLE_CONTENT)
        assert "<h1>Overall Summary</h1>" in html
        assert "<h2>Metrics</h2>" in html
        assert "<h2>Strengths</h2>" in html
        assert "<h2>Areas to Improve</h2>" in html
        assert "<h2>Suggested Next Steps</h2>" in html
        assert "<h2>Transcript References</h2>" in html
        assert "82" in html
        assert "I built a platform that reduced latency." in html

    def test_renders_minimal_content(self, renderer):
        html = renderer.render_html({"overall_score": 50})
        assert "<h1>Overall Summary</h1>" in html
        assert "<h2>Metrics</h2>" not in html
        assert "<h2>Strengths</h2>" not in html

    def test_escapes_html_in_quotes(self, renderer):
        content = dict(SAMPLE_CONTENT)
        content["transcript_examples"] = [{"type": "strength", "label": "<script>", "quote": "<b>bold</b>"}]
        html = renderer.render_html(content)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestLocalReportStorage:
    def test_upload_download_roundtrip(self, tmp_path):
        storage = LocalReportStorage(base_dir=tmp_path / "r")
        url = storage.upload("reports/abc.html", b"<html>hi</html>")
        assert storage.download("reports/abc.html") == b"<html>hi</html>"
        assert url.endswith("abc.html")

    def test_delete(self, tmp_path):
        storage = LocalReportStorage(base_dir=tmp_path / "r")
        storage.upload("reports/x.html", b"data")
        storage.delete("reports/x.html")
        with pytest.raises(FileNotFoundError):
            storage.download("reports/x.html")

    def test_is_available(self, tmp_path):
        storage = LocalReportStorage(base_dir=tmp_path / "r")
        assert storage.is_available is True

    def test_create_storage_fallback_is_local(self):
        storage = create_storage()
        assert isinstance(storage, LocalReportStorage)


class TestReportService:
    def test_render_and_store_sets_ready(self, db_session, service):
        report, _ = make_report(db_session)
        status = service.render_and_store(db_session, report.id)
        assert status == "ready"
        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "ready"
        assert updated.storage_key == f"reports/{report.id}.html"
        assert updated.storage_url is not None

    def test_uploaded_html_downloadable(self, db_session, service):
        report, _ = make_report(db_session)
        service.render_and_store(db_session, report.id)
        data = service.download_html(db_session, report.id, report.user_id)
        assert data is not None
        assert b"<h1>Overall Summary</h1>" in data

    def test_download_fallback_renders_when_no_storage_key(self, db_session, service):
        report, _ = make_report(db_session)
        data = service.download_html(db_session, report.id, report.user_id)
        assert data is not None
        assert b"Overall Summary" in data

    def test_retry_render_rerenders_without_content_change(self, db_session, service):
        report, _ = make_report(db_session, status="render_failed")
        service.retry_render(db_session, report.id)
        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "ready"
        assert json.loads(updated.content)["overall_score"] == 82.0

    def test_retry_noop_when_ready(self, db_session, service):
        report, _ = make_report(db_session)
        service.render_and_store(db_session, report.id)
        first_url = db_session.query(Report).filter(Report.id == report.id).first().storage_url
        status = service.retry_render(db_session, report.id)
        assert status == "ready"
        assert db_session.query(Report).filter(Report.id == report.id).first().storage_url == first_url

    def test_render_failure_preserves_content(self, db_session, service):
        report, _ = make_report(db_session)
        report.content = json.dumps(SAMPLE_CONTENT)

        class BoomStorage:
            def upload(self, key, data, content_type="text/html"):
                raise RuntimeError("R2 unavailable")

            def download(self, key):
                raise FileNotFoundError

            def delete(self, key):
                pass

            is_available = True

        failing = ReportService(storage=BoomStorage())
        status = failing.render_and_store(db_session, report.id)
        assert status == "render_failed"
        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "render_failed"
        assert json.loads(updated.content)["overall_score"] == 82.0

    def test_list_and_get_ownership(self, db_session, service):
        report, user_id = make_report(db_session)
        reports = service.list_reports(db_session, user_id)
        assert len(reports) == 1
        got = service.get_report(db_session, report.id, user_id)
        assert got.id == report.id
        assert service.get_report(db_session, report.id, "someone-else") is None

    def test_delete_removes_row_and_blob(self, db_session, service, storage):
        report, _ = make_report(db_session)
        service.render_and_store(db_session, report.id)
        ok = service.delete_report(db_session, report.id, report.user_id)
        assert ok is True
        assert db_session.query(Report).filter(Report.id == report.id).first() is None
        assert service.download_html(db_session, report.id, report.user_id) is None

    def test_render_timed_out_banner(self):
        content = dict(SAMPLE_CONTENT)
        content["timed_out"] = True
        renderer = ReportRenderer()
        html = renderer.render_html(content)
        assert "Time Expired" in html
        assert "5:00 Limit" in html
