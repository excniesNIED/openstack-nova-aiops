from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .broadcast import AlertBroadcaster
from .db import append_alert_comment, get_alert, init_db, list_alerts, make_engine, update_alert_status
from .replay import ReplayController, replay_config_from_env
from .worker import InferenceWorker, config_from_env


class StartReplayRequest(BaseModel):
    dataset_id: str = Field(default="sample", min_length=1)
    log_name: Optional[str] = None
    rate: Optional[float] = Field(default=None, ge=0)
    loop: bool = False
    max_records: int = Field(default=0, ge=0)


class CommentRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=1000)


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
    broadcaster = AlertBroadcaster()
    worker = InferenceWorker(cfg, broadcaster=broadcaster)

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

    @app.post("/alerts/{alert_id}/ack")
    def alert_ack(alert_id: str, req: Optional[CommentRequest] = None):
        if req and req.comment:
            r = append_alert_comment(engine, alert_id, comment=req.comment, author="user")
            if r is None:
                raise HTTPException(status_code=404, detail="alert not found")
        r2 = update_alert_status(engine, alert_id, status="ack")
        if r2 is None:
            raise HTTPException(status_code=404, detail="alert not found")
        return {"ok": True, "alert_id": alert_id, "status": r2.status}

    @app.post("/alerts/{alert_id}/close")
    def alert_close(alert_id: str, req: Optional[CommentRequest] = None):
        if req and req.comment:
            r = append_alert_comment(engine, alert_id, comment=req.comment, author="user")
            if r is None:
                raise HTTPException(status_code=404, detail="alert not found")
        r2 = update_alert_status(engine, alert_id, status="resolved")
        if r2 is None:
            raise HTTPException(status_code=404, detail="alert not found")
        return {"ok": True, "alert_id": alert_id, "status": r2.status}

    @app.post("/alerts/{alert_id}/comment")
    def alert_comment(alert_id: str, req: CommentRequest):
        r = append_alert_comment(engine, alert_id, comment=req.comment, author="user")
        if r is None:
            raise HTTPException(status_code=404, detail="alert not found")
        return {"ok": True, "alert_id": alert_id}

    @app.get("/metrics/overview")
    def metrics_overview(minutes: int = Query(15, ge=1, le=24 * 60)):
        from collections import Counter
        from datetime import datetime, timedelta, timezone

        rows = list_alerts(engine, limit=5000, offset=0, status=None)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=int(minutes))

        def parse_dt(s: str):
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        selected = []
        for r in rows:
            ts = parse_dt(r.created_at)
            if ts is None or ts < cutoff:
                continue
            selected.append(r)

        sev = Counter(r.severity for r in selected)
        st = Counter(r.status for r in selected)
        cls = Counter(r.pred_class for r in selected)

        return {
            "window_minutes": int(minutes),
            "now": now.replace(microsecond=0).isoformat(),
            "total": len(selected),
            "by_severity": dict(sev),
            "by_status": dict(st),
            "top_pred_class": [{"pred_class": k, "count": v} for k, v in cls.most_common(10)],
            "latest_alert_at": selected[0].created_at if selected else None,
        }

    @app.get("/events/alerts")
    def alerts_sse():
        """
        Server-Sent Events stream for newly created alerts (best-effort).
        Client should still periodically call /alerts to recover from disconnects.
        """
        import json
        import queue
        import time

        q = broadcaster.subscribe()

        def gen():
            try:
                yield "retry: 3000\n\n"
                last_ping = time.time()
                while True:
                    try:
                        msg = q.get(timeout=15)
                        data = json.dumps(msg, ensure_ascii=False)
                        yield f"event: alert\ndata: {data}\n\n"
                    except queue.Empty:
                        # Keep connection alive through proxies.
                        if (time.time() - last_ping) >= 15:
                            yield "event: ping\ndata: {}\n\n"
                            last_ping = time.time()
            finally:
                broadcaster.unsubscribe(q)

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
