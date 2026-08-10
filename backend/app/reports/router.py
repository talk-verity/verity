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
    return Response(content=data, media_type="text/html")


@router.post("/{report_id}/retry", response_model=RetryResponse)
def retry_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
):
    if not service.get_report(db, report_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
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
