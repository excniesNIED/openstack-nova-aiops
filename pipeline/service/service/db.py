from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Float, Integer, String, create_engine, text
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
    return create_engine(db_url, pool_pre_ping=True)


def wait_for_db(engine, *, timeout_sec: float = 30.0, interval_sec: float = 1.0) -> None:
    """
    Wait until the DB is reachable (mainly for containerized DBs like MariaDB).
    """
    if str(engine.url.drivername).startswith("sqlite"):
        return
    deadline = time.time() + float(timeout_sec)
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as e:
            last_err = e
            time.sleep(float(interval_sec))
    if last_err:
        raise last_err


def init_db(engine) -> None:
    wait_for_db(engine)
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


def update_alert_status(engine, alert_id: str, *, status: str) -> Optional[Alert]:
    status = (status or "").strip()
    if not status:
        return None
    with Session(engine) as s:
        a = s.get(Alert, alert_id)
        if a is None:
            return None
        a.status = status
        s.add(a)
        s.commit()
        s.refresh(a)
        return a


def append_alert_comment(engine, alert_id: str, *, comment: str, author: str = "user") -> Optional[Alert]:
    c = (comment or "").strip()
    if not c:
        return None
    with Session(engine) as s:
        a = s.get(Alert, alert_id)
        if a is None:
            return None
        evidence = dict(a.evidence or {})
        comments = list(evidence.get("comments") or [])
        comments.append({"ts": utcnow_iso(), "author": author, "comment": c})
        evidence["comments"] = comments[-50:]
        a.evidence = evidence
        s.add(a)
        s.commit()
        s.refresh(a)
        return a
