import json
import logging
import threading

from sqlalchemy.orm import Session

from app.feedback.analyzer import Analyzer
from app.feedback.generator import FeedbackGenerator
from app.models.report import Report
from app.models.turn import Turn

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self):
        self.analyzer = Analyzer()
        self.generator = FeedbackGenerator()

    def generate_report(self, db: Session, report_id: str):
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error("Report %s not found", report_id)
            return

        try:
            turns = (
                db.query(Turn)
                .filter(Turn.session_id == report.session_id)
                .order_by(Turn.created_at)
                .all()
            )

            user_turns = [t.content for t in turns if t.speaker == "user"]
            ai_turns = [t.content for t in turns if t.speaker == "ai"]

            scenario_id = report.session.scenario if report.session else ""
            from app.conversations.scenarios import get_scenario
            scenario = get_scenario(scenario_id) or {}
            persona = scenario.get("persona", {})

            analysis = self.analyzer.analyze(scenario_id, user_turns, ai_turns)
            content = self.generator.generate(
                analysis,
                scenario.get("name", "Unknown"),
                persona.get("name", ""),
            )

            report.content = content
            report.title = f"Feedback — {scenario.get('name', 'Conversation')}"
            report.status = "ready"
            db.commit()
            logger.info("Report %s generated successfully", report_id)
        except Exception as e:
            logger.error("Report generation failed for %s: %s", report_id, e)
            report.status = "failed"
            db.commit()

    def queue_generation(self, db: Session, report_id: str):
        thread = threading.Thread(target=self._run_generation, args=(report_id,), daemon=True)
        thread.start()

    def _run_generation(self, report_id: str):
        from database import SessionLocal
        db = SessionLocal()
        try:
            self.generate_report(db, report_id)
        finally:
            db.close()

    def get_report(self, db: Session, session_id: str, user_id: str) -> Report | None:
        return (
            db.query(Report)
            .filter(Report.session_id == session_id, Report.user_id == user_id)
            .first()
        )
