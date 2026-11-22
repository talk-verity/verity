import json
import logging

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

            transcript = "\n".join(f"{'User' if t.speaker == 'user' else 'AI'}: {t.content}" for t in turns)
            try:
                rag_context = self.rag.retrieve_context(scenario_id, transcript)
            except Exception:
                logger.exception("Optional research retrieval unavailable")
                rag_context = ""

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
            db.rollback()
            report = db.get(Report, report_id)
            if report:
                report.status = "failed"
                db.commit()

    @staticmethod
    def queue_generation(db: Session, report_id: str):
        """Persist with the caller's transaction; the separate worker executes it."""
        from app.models.report_job import ReportJob
        from datetime import datetime, timezone
        job = db.get(ReportJob, report_id)
        if job is None:
            db.add(ReportJob(report_id=report_id))
        else:
            job.status = "pending"
            job.attempts = 0
            job.available_at = datetime.now(timezone.utc)

    def get_report(self, db: Session, session_id: str, user_id: str) -> Report | None:
        return (
            db.query(Report)
            .filter(Report.session_id == session_id, Report.user_id == user_id)
            .first()
        )
