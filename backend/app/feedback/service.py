import json
import logging
import threading

from sqlalchemy.orm import Session

from app.feedback.analyzer import Analyzer
from app.feedback.generator import FeedbackGenerator
from app.feedback.rag import RAGService
from app.models.report import Report
from app.models.turn import Turn

logger = logging.getLogger(__name__)


class FeedbackService:
    def __init__(self, advisor=None):
        self.analyzer = Analyzer()
        self.generator = FeedbackGenerator()
        self.rag = RAGService()
        self.advisor = advisor

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

            transcript = self._build_transcript(user_turns, ai_turns)
            rag_context = self.rag.retrieve_context(scenario_id, transcript)

            analysis = self.analyzer.analyze(scenario_id, user_turns, ai_turns)

            suggestions = None
            if self.advisor is not None:
                try:
                    suggestions = self.advisor.suggest(scenario, analysis, rag_context)
                except Exception as e:
                    logger.warning("Research suggestions failed for %s: %s", report_id, e)

            content = self.generator.generate(
                analysis,
                scenario.get("name", "Unknown"),
                persona.get("name", ""),
                rag_context=rag_context,
                suggestions=suggestions,
            )

            report.content = content
            report.title = f"Feedback — {scenario.get('name', 'Conversation')}"
            db.commit()

            from app.reports.service import ReportService
            new_status = ReportService().render_and_store(db, report.id)
            if new_status != "ready":
                logger.warning("Render/store failed for %s — structured content preserved", report_id)
            else:
                logger.info("Report %s generated and stored successfully", report_id)
        except Exception as e:
            logger.error("Report generation failed for %s: %s", report_id, e)
            report.status = "failed"
            db.commit()

    def _build_transcript(self, user_turns: list[str], ai_turns: list[str]) -> str:
        lines = []
        for i in range(max(len(user_turns), len(ai_turns))):
            if i < len(user_turns):
                lines.append(f"User: {user_turns[i]}")
            if i < len(ai_turns):
                lines.append(f"AI: {ai_turns[i]}")
        return "\n".join(lines)

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
