"""Long-lived objects shared by every Streamlit rerun."""
from __future__ import annotations

import config
from pipeline.dispatcher import Dispatcher, WorkerClient
from pipeline.history import RuntimeHistory
from pipeline.rtt import RttTracker
from pipeline.scheduler import OffloadingScheduler
from pipeline.telemetry import DecisionLog


def build_dispatcher(rtt_ms: float) -> Dispatcher:
    """Scheduler (explicit RTT from the sidebar slider) + workers + decision log,
    with runtime history warmed from earlier runs in the log."""
    log = DecisionLog(config.DECISION_LOG)
    scheduler = OffloadingScheduler(cloud_rtt_ms=rtt_ms, rtt_tracker=RttTracker(),
                                    history=RuntimeHistory.from_log(log))
    cloud = WorkerClient(config.CLOUD_WORKER_URL) if config.CLOUD_WORKER_URL else None
    return Dispatcher(scheduler, WorkerClient(config.LOCAL_WORKER_URL), cloud, log=log)
