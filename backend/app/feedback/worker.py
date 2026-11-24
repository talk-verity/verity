"""Run with python -m app.feedback.worker. Requires PostgreSQL in production.

A job row stays locked in its own transaction until processing finishes. Process
failure rolls back that claim, allowing another worker to resume it. Generation
and storage are repeatable using the report ID as the stable object key.
"""
import logging
import signal
from datetime import datetime, timedelta, timezone
from threading import Event
from sqlalchemy import select
from database import SessionLocal
from app.models.report import Report
from app.models.report_job import ReportJob
from app.feedback.service import FeedbackService
from app.feedback.advisor import ResearchAdvisor

logger = logging.getLogger(__name__)

def run_once(session_factory=SessionLocal, service_factory=None, report_id=None):
    with session_factory() as claims:
        with claims.begin():
            query = select(ReportJob).where(
                ReportJob.status == "pending", ReportJob.available_at <= datetime.now(timezone.utc)
            )
            if report_id is not None:
                query = query.where(ReportJob.report_id == report_id)
            job = claims.execute(query.order_by(ReportJob.available_at).limit(1)
                                 .with_for_update(skip_locked=True)).scalars().first()
            if job is None:
                return False
            job.attempts += 1
            with session_factory() as work:
                report = work.get(Report, job.report_id)
                if report is None or report.status == "ready":
                    job.status = "done"
                    return True
                try:
                    service = service_factory() if service_factory else FeedbackService(advisor=ResearchAdvisor())
                    if report.content:
                        from app.reports.service import ReportService
                        ReportService().render_and_store(work, job.report_id)
                    else:
                        service.generate_report(work, job.report_id)
                except Exception:
                    logger.exception("Report job failed")
                    work.rollback()
                    report = work.get(Report, job.report_id)
                    if report:
                        report.status = "failed"
                        work.commit()
                work.expire_all()
                report = work.get(Report, job.report_id)
                if report is None or report.status in ("ready", "render_failed"):
                    job.status = "done"
                elif job.attempts >= 3:
                    job.status = "failed"
                else:
                    job.available_at = datetime.now(timezone.utc) + timedelta(seconds=10 * job.attempts)
                    report.status = "generating"
                    work.commit()
            return True

def main():
    logging.basicConfig(level=logging.INFO)
    stopped = Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    while not stopped.is_set():
        try:
            if run_once():
                continue
        except Exception:
            logger.exception("Report worker iteration failed")
        stopped.wait(2)

if __name__ == "__main__":
    main()
