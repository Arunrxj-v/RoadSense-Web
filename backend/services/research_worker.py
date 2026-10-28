import signal
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app import create_app
from db import db
from models import PotholeResearchRun
from services.research_agent import execute_research_run

STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


def recover_stale_runs(app):
    max_seconds = app.config.get("RESEARCH_MAX_DURATION_SECONDS", 180)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_seconds * 2 + 60)
    PotholeResearchRun.query.filter(
        PotholeResearchRun.status == "running",
        PotholeResearchRun.started_at < cutoff,
    ).update(
        {
            PotholeResearchRun.status: "failed",
            PotholeResearchRun.error: "worker_timeout",
            PotholeResearchRun.completed_at: datetime.now(timezone.utc),
        },
        synchronize_session=False,
    )
    db.session.commit()


def claim_next_run():
    now = datetime.now(timezone.utc)
    if db.engine.dialect.name == "postgresql":
        row = db.session.execute(
            text(
                "UPDATE pothole_research_runs "
                "SET status = 'running', started_at = :now, updated_at = :now "
                "WHERE id = ("
                "  SELECT id FROM pothole_research_runs "
                "  WHERE status = 'pending' "
                "  ORDER BY id "
                "  FOR UPDATE SKIP LOCKED "
                "  LIMIT 1"
                ") "
                "RETURNING id"
            ),
            {"now": now},
        ).fetchone()
        db.session.commit()
        if row:
            return db.session.get(PotholeResearchRun, row[0])
        return None

    run = (
        PotholeResearchRun.query.filter_by(status="pending")
        .order_by(PotholeResearchRun.id)
        .first()
    )
    if run is None:
        return None
    run.status = "running"
    run.started_at = now
    db.session.commit()
    return run


def run_once(app):
    with app.app_context():
        run = claim_next_run()
        if run is None:
            return False
        try:
            execute_research_run(run.id)
        except Exception:
            db.session.rollback()
            failed = db.session.get(PotholeResearchRun, run.id)
            if failed is not None and failed.status != "completed":
                failed.status = "failed"
                failed.error = "worker_error"
                failed.completed_at = datetime.now(timezone.utc)
                db.session.commit()
            app.logger.exception("Research worker failed for run %s", run.id)
        return True


def main():
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    app = create_app()
    with app.app_context():
        recover_stale_runs(app)
    poll_seconds = app.config.get("RESEARCH_WORKER_POLL_SECONDS", 5)
    while not STOP:
        worked = run_once(app)
        if not worked:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
