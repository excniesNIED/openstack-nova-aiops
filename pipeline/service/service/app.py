from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .db import get_alert, init_db, list_alerts, make_engine
from .worker import InferenceWorker, config_from_env


def create_app() -> FastAPI:
    app = FastAPI(title="OpenStack AIOps (Scheme Pipeline)", version="1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db_url = os.environ.get("APP_DB_URL", "sqlite:////data/alerts.db")
    engine = make_engine(db_url)
    init_db(engine)

    cfg = config_from_env()
    worker = InferenceWorker(cfg)

    @app.on_event("startup")
    def _startup() -> None:
        worker.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        worker.stop()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/alerts")
    def alerts(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0), status: Optional[str] = None):
        rows = list_alerts(engine, limit=limit, offset=offset, status=status)
        return [
            {
                "alert_id": r.alert_id,
                "created_at": r.created_at,
                "entity_key": r.entity_key,
                "window_start": r.window_start,
                "window_end": r.window_end,
                "pred_class": r.pred_class,
                "pred_label_id": r.pred_label_id,
                "prob": r.prob,
                "threshold": r.threshold,
                "severity": r.severity,
                "status": r.status,
                "evidence": r.evidence,
            }
            for r in rows
        ]

    @app.get("/alerts/{alert_id}")
    def alert_detail(alert_id: str):
        r = get_alert(engine, alert_id)
        if r is None:
            raise HTTPException(status_code=404, detail="alert not found")
        return {
            "alert_id": r.alert_id,
            "created_at": r.created_at,
            "entity_key": r.entity_key,
            "window_start": r.window_start,
            "window_end": r.window_end,
            "pred_class": r.pred_class,
            "pred_label_id": r.pred_label_id,
            "prob": r.prob,
            "threshold": r.threshold,
            "severity": r.severity,
            "status": r.status,
            "evidence": r.evidence,
        }

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
