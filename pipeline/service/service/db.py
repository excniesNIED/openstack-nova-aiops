from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.exc import IntegrityError


class Base(DeclarativeBase):
    pass


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(32), index=True)

    entity_key: Mapped[str] = mapped_column(String(128), index=True)
    window_start: Mapped[str] = mapped_column(String(64), index=True)
    window_end: Mapped[str] = mapped_column(String(64), index=True)

    pred_class: Mapped[str] = mapped_column(String(64), index=True)
    pred_label_id: Mapped[int] = mapped_column(Integer)
    prob: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)

    severity: Mapped[str] = mapped_column(String(16), default="P2", index=True)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)

    # SQLite will store JSON as TEXT; SQLAlchemy abstracts this away.
    evidence: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)


def make_engine(db_url: str):
    # sqlite:///relative.db or sqlite:////abs/path.db
    if db_url.startswith("sqlite:"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    return create_engine(db_url)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def insert_alert(engine, alert: Alert) -> None:
    with Session(engine) as s:
        try:
            s.add(alert)
            s.commit()
        except IntegrityError:
            s.rollback()


def get_alert(engine, alert_id: str) -> Optional[Alert]:
    with Session(engine) as s:
        return s.get(Alert, alert_id)


def list_alerts(engine, limit: int = 50, offset: int = 0, status: Optional[str] = None):
    from sqlalchemy import select

    with Session(engine) as s:
        q = select(Alert).order_by(Alert.created_at.desc()).limit(limit).offset(offset)
        if status:
            q = q.where(Alert.status == status)
        return list(s.execute(q).scalars().all())
