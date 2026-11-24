import uuid
from datetime import datetime, timezone

from sqlalchemy import Index, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Turn(Base):
    __tablename__ = "turns"
    __table_args__ = (Index("ix_turns_lookup", "session_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True)
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    session: Mapped["Session"] = relationship("Session", back_populates="turns")
