"""Run health checks for a given set of endpoints."""

from __future__ import annotations

import logging
import signal
import sys
import time
from concurrent.futures import as_completed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor
    from typing import Generator

    from .helpers import HealthcheckSession
    from .models import Endpoint, HealthTracker

logger = logging.getLogger(__package__)


def run_healthchecks(
    endpoints: list[Endpoint],
    healthtrackers: list[HealthTracker],
    executor: ThreadPoolExecutor,
    session: HealthcheckSession,
    start_times: Generator[float, None, None],
) -> None:
    """Run healthcheck cycle continuously."""

    register_exit_handler(executor, session)
    for start_time in start_times:
        sleep_until(start_time)
        check_endpoints(endpoints, session, executor)
        log_statuses(healthtrackers)


def register_exit_handler(
    executor: ThreadPoolExecutor, session: HealthcheckSession
) -> None:
    """Register CTRL-C/SIGINT handler to gracefully exit healthchecks."""

    signal.signal(
        signal.SIGINT, lambda *_: exit_healthchecks(executor, session)
    )


def exit_healthchecks(
    executor: ThreadPoolExecutor, session: HealthcheckSession
) -> None:
    """Cleanup and exit the process."""

    logger.debug("Exiting healthchecks...")
    executor.shutdown(wait=False, cancel_futures=True)
    session.close()
    sys.exit(0)


def sleep_until(epoch_time_s: float) -> None:
    """Sleep until the given epoch time in seconds."""

    wait_time = epoch_time_s - time.time()
    if wait_time >= 0:
        time.sleep(wait_time)
    else:
        logger.warning("Missed start time by %s seconds", abs(wait_time))


def check_endpoints(
    endpoints: list[Endpoint],
    session: HealthcheckSession,
    executor: ThreadPoolExecutor,
) -> None:
    """Run health checks in parallel and record results."""

    futures = []
    for endpoint in endpoints:
        futures.append(executor.submit(endpoint.check_health, session))

    for future in as_completed(futures):
        healthtracker, is_up = future.result()
        healthtracker.record_request(is_up)


def log_statuses(healthtrackers: list[HealthTracker]) -> None:
    """Log availability status."""

    for healthtracker in healthtrackers:
        logger.info("%s", healthtracker.availability_status)

    logger.debug("%s", healthtrackers)
