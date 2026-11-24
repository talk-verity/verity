from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class ReportJob(Base):
    __tablename__ = "report_jobs"
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
