from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.models.report import Report
from app.models.user import User
from app.reports.service import ReportService
from database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


def get_report_service() -> ReportService:
    return ReportService()


class ReportMeta(BaseModel):
    id: str
    session_id: str | None
    title: str
    status: str
    storage_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportDetail(ReportMeta):
    content: dict | None = None


class RetryResponse(BaseModel):
    report_id: str
    status: str


def _to_meta(report: Report) -> ReportMeta:
    return ReportMeta(
        id=report.id,
        session_id=report.session_id,
        title=report.title,
        status=report.status,
        storage_url=report.storage_url,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("", response_model=list[ReportMeta])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    return [_to_meta(r) for r in service.list_reports(db, current_user.id)]


@router.get("/{report_id}", response_model=ReportDetail)
def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    report = service.get_report(db, report_id, current_user.id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    import json
    content = json.loads(report.content) if report.content else None
    return ReportDetail(
        **_to_meta(report).model_dump(),
        content=content,
    )


@router.get("/{report_id}/download", response_class=HTMLResponse)
def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    data = service.download_html(db, report_id, current_user.id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return Response(
        content=data,
        media_type="text/html",
        headers={
            "Content-Disposition": 'attachment; filename="delphi-report.html"',
            "Content-Security-Policy": "sandbox; default-src 'none'; style-src 'unsafe-inline'",
        },
    )


@router.post("/{report_id}/process", response_model=RetryResponse)
def process_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    """Execute one durable job inside a request on hosts without a worker."""
    report = service.get_report(db, report_id, current_user.id)
    if not report:
        raise HTTPException(404, "Report not found")
    from app.core.settings import settings
    if settings.REPORT_EXECUTION_MODE == "request" and report.status == "generating":
        user_id = current_user.id
        # Release the authorization read transaction before claiming on another
        # connection. The worker keeps its PostgreSQL lock until work finishes.
        db.rollback()
        from app.feedback.worker import run_once
        run_once(report_id=report_id)
        db.expire_all()
        report = service.get_report(db, report_id, user_id)
        if not report:
            raise HTTPException(404, "Report not found")
    return RetryResponse(report_id=report_id, status=report.status)


@router.post("/{report_id}/retry", response_model=RetryResponse)
def retry_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    if not service.get_report(db, report_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    from app.models.report_job import ReportJob
    db.query(ReportJob).filter(ReportJob.report_id == report_id).with_for_update().first()
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    db.refresh(report)
    if report.status == "failed":
        from app.feedback.service import FeedbackService
        FeedbackService.queue_generation(db, report_id)
        report.status = "generating"
        db.commit()
        new_status = "generating"
    elif report.status == "generating":
        new_status = "generating"
    else:
        new_status = service.retry_render(db, report_id)
    return RetryResponse(report_id=report_id, status=new_status)


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    deleted = service.delete_report(db, report_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
