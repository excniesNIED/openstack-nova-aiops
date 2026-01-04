from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .db import get_alert, init_db, list_alerts, make_engine
from .replay import ReplayController, replay_config_from_env
from .worker import InferenceWorker, config_from_env


class StartReplayRequest(BaseModel):
    dataset_id: str = Field(default="sample", min_length=1)
    log_name: Optional[str] = None
    rate: Optional[float] = Field(default=None, ge=0)
    loop: bool = False
    max_records: int = Field(default=0, ge=0)


def create_app() -> FastAPI:
    app = FastAPI(title="OpenStack AIOps (Scheme Pipeline)", version="1.1")

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

    replay = ReplayController(replay_config_from_env())

    @app.on_event("startup")
    def _startup() -> None:
        worker.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        worker.stop()

    @app.get("/health")
    def health():
        st = replay.status()
        return {"ok": True, "replay_running": bool(st.get("running"))}

    @app.get("/control/status")
    def control_status():
        return replay.status()

    @app.get("/control/logs")
    def control_logs():
        return replay.list_logs()

    @app.post("/control/start")
    def control_start(req: StartReplayRequest):
        # Common datasets used in this project; caller may still pass an explicit log_name.
        dataset_to_log = {
            "sample": "openstack-nova-sample.log",
            "normal": "openstack-nova-normal-vm-create.log",
            "fault1": "openstack-vm-destroy-immediately-after-create.log",
            "fault2": "openstack-nova-dhcpoff.log",
            "fault3": "openstack-nova-undefine-vm-after-create.log",
        }
        log_name = (req.log_name or "").strip() or dataset_to_log.get(req.dataset_id)
        if not log_name:
            raise HTTPException(status_code=400, detail="log_name is required (or use a known dataset_id)")
        try:
            replay.start(
                dataset_id=req.dataset_id,
                log_name=log_name,
                rate=req.rate,
                loop=req.loop,
                max_records=req.max_records,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return replay.status()

    @app.post("/control/stop")
    def control_stop():
        replay.stop()
        return replay.status()

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
