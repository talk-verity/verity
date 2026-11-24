import json
import logging

from sqlalchemy.orm import Session

from app.models.report import Report
from app.reports.renderer import ReportRenderer
from app.reports.storage import LocalReportStorage, ReportStorage, create_storage

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, storage: ReportStorage | None = None):
        self.storage = storage or create_storage()
        self.renderer = ReportRenderer()

    def render_and_store(self, db: Session, report_id: str) -> str:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return "not_found"
        try:
            content = json.loads(report.content) if report.content else {}
            html = self.renderer.render_html(content)
            from app.core.settings import settings
            if settings.REPORT_STORAGE_MODE == "database":
                # Structured content is already committed in PostgreSQL. Render
                # downloads on demand without writing into a read-only bundle.
                report.storage_key = None
                report.storage_url = None
                report.status = "ready"
                db.commit()
                return "ready"
            key = f"reports/{report.id}.html"
            url = self.storage.upload(key, html.encode("utf-8"))
            report.storage_key = key
            report.storage_url = url
            report.status = "ready"
            db.commit()
            logger.info("Report %s rendered and stored at %s", report_id, url)
            return "ready"
        except Exception as e:
            logger.error("Render/store failed for %s: %s", report_id, e)
            report.status = "render_failed"
            db.commit()
            return "render_failed"

    def retry_render(self, db: Session, report_id: str) -> str:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return "not_found"
        if report.status == "ready":
            return "ready"
        if not report.content:
            logger.warning("Report %s has no structured content to render", report_id)
            return "no_content"
        logger.info("Retrying render for report %s (no LLM re-run)", report_id)
        return self.render_and_store(db, report_id)

    def get_report(self, db: Session, report_id: str, user_id: str) -> Report | None:
        return (
            db.query(Report)
            .filter(Report.id == report_id, Report.user_id == user_id)
            .first()
        )

    def list_reports(self, db: Session, user_id: str) -> list[Report]:
        return (
            db.query(Report)
            .filter(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
            .all()
        )

    def download_html(self, db: Session, report_id: str, user_id: str) -> bytes | None:
        report = self.get_report(db, report_id, user_id)
        if not report:
            return None
        if report.storage_key:
            try:
                return self.storage.download(report.storage_key)
            except Exception as e:
                logger.warning("Storage download failed for %s, falling back to render: %s", report_id, e)
        if report.content:
            content = json.loads(report.content)
            return self.renderer.render_html(content).encode("utf-8")
        return None

    def delete_report(self, db: Session, report_id: str, user_id: str) -> bool:
        report = self.get_report(db, report_id, user_id)
        if not report:
            return False
        if report.storage_key:
            try:
                self.storage.delete(report.storage_key)
            except Exception as e:
                logger.warning("Storage delete failed for %s: %s", report_id, e)
        db.delete(report)
        db.commit()
        return True

    def is_using_r2(self) -> bool:
        return not isinstance(self.storage, LocalReportStorage)
