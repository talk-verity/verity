import json
import pytest

from app.feedback.analyzer import Analyzer
from app.feedback.generator import FeedbackGenerator
from app.feedback.service import FeedbackService
from app.models.report import Report
from app.models.session import Session as SessionModel
from app.models.turn import Turn


class TestAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return Analyzer()

    def test_analyze_basic_output(self, analyzer):
        user_turns = ["Hi there, nice to meet you!", "I've been building software for 5 years."]
        ai_turns = ["Hello! Tell me about yourself.", "That's impressive."]
        result = analyzer.analyze("networking_event", user_turns, ai_turns)
        assert "overall_score" in result
        assert "strengths" in result
        assert "weaknesses" in result
        assert "confidence_score" in result
        assert "clarity_score" in result
        assert "total_turns" in result
        assert result["total_turns"] == 2
        assert result["total_user_words"] >= 10

    def test_analyze_filler_words(self, analyzer):
        user_turns = ["Um, like, I think this is a good idea actually."]
        ai_turns = ["Go on."]
        result = analyzer.analyze("networking_event", user_turns, ai_turns)
        assert result["filler_word_count"] > 0
        assert "um" in result["filler_words"]
        assert "like" in result["filler_words"]

    def test_analyze_strengths_detected(self, analyzer):
        user_turns = ["I built a scalable API that reduced latency by 40%."]
        ai_turns = ["Tell me more."]
        result = analyzer.analyze("job_interview", user_turns, ai_turns)
        assert len(result["strengths"]) > 0
        assert any("action verbs" in s for s in result["strengths"])

    def test_analyze_goal_completion(self, analyzer):
        user_turns = ["Present a compelling case for promotion to Senior Engineer with specific achievements."]
        ai_turns = ["Go on."]
        result = analyzer.analyze("promotion_discussion", user_turns, ai_turns)
        assert result["goal_completion"] in ("highly addressed", "partially addressed")


class TestFeedbackGenerator:
    @pytest.fixture
    def generator(self):
        return FeedbackGenerator()

    def test_generate_report_content(self, generator):
        analysis = {
            "overall_score": 75.0,
            "strengths": ["Asks thoughtful questions", "Clear articulation"],
            "weaknesses": ["Overuses filler words"],
            "confidence_score": 70.0,
            "clarity_score": 80.0,
            "filler_word_count": 5,
            "filler_words": ["um", "like"],
            "interruption_count": 0,
            "goal_completion": "partially addressed",
            "total_turns": 4,
            "total_user_words": 120,
            "avg_response_length": 30.0,
        }
        content = generator.generate(analysis, "Networking Event", "Jordan Chen")
        data = json.loads(content)
        assert data["overall_score"] == 75.0
        assert data["scenario"] == "Networking Event"
        assert data["persona"] == "Jordan Chen"
        assert len(data["strengths"]) == 2
        assert len(data["recommendations"]) >= 2
        assert data["metrics"]["confidence"] == 70.0
        assert data["metrics"]["clarity"] == 80.0


class TestFeedbackService:
    @pytest.fixture
    def service(self):
        return FeedbackService()

    def test_generate_report_sets_status_ready(self, db_session, service):
        from app.models.user import User
        user = User(id="fb-test-user", clerk_id="fb-clerk", email="fb@test.com")
        db_session.add(user)
        db_session.flush()

        session = SessionModel(user_id="fb-test-user", scenario="job_interview", status="completed")
        db_session.add(session)
        db_session.flush()

        report = Report(
            user_id="fb-test-user",
            session_id=session.id,
            title="Test Report",
            status="generating",
        )
        db_session.add(report)
        db_session.commit()

        service.generate_report(db_session, report.id)

        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "ready"
        assert updated.content != ""
        data = json.loads(updated.content)
        assert "overall_score" in data
        assert "metrics" in data

    def test_generate_report_with_turns(self, db_session, service):
        from app.models.user import User
        user = User(id="fb-user-2", clerk_id="fb-clerk-2", email="fb2@test.com")
        db_session.add(user)
        db_session.flush()

        session = SessionModel(user_id="fb-user-2", scenario="networking_event", status="completed")
        db_session.add(session)
        db_session.flush()

        db_session.add(Turn(session_id=session.id, speaker="ai", content="Hi, I'm Jordan."))
        db_session.add(Turn(session_id=session.id, speaker="user", content="Hi Jordan, I'm excited to be here!"))
        db_session.add(Turn(session_id=session.id, speaker="ai", content="What brings you to the event?"))
        db_session.add(Turn(session_id=session.id, speaker="user", content="I built a startup and I'm looking for connections."))

        report = Report(
            user_id="fb-user-2",
            session_id=session.id,
            title="Test Report",
            status="generating",
        )
        db_session.add(report)
        db_session.commit()

        service.generate_report(db_session, report.id)

        updated = db_session.query(Report).filter(Report.id == report.id).first()
        assert updated.status == "ready"
        data = json.loads(updated.content)
        assert data["metrics"]["total_turns"] == 2
        assert data["metrics"]["total_user_words"] > 0
        assert "networking" in data["scenario"].lower()
        assert len(data["strengths"]) > 0 or len(data["weaknesses"]) > 0

    def test_get_report_nonexistent(self, db_session, service):
        report = service.get_report(db_session, "no-session", "no-user")
        assert report is None
