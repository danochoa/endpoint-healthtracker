"""Helpers for healthcheck."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from schema import SchemaError

from .models import Endpoint, HealthTracker

if TYPE_CHECKING:
    from typing import Generator

    from requests import Response, Session
    from requests_ratelimiter import LimiterAdapter
    from schema import Schema


type Endpoints = list[dict[str, any]]
type Config = dict[str, any]

logger = logging.getLogger(__package__)


class HealthcheckSession:
    """Session wrapper that adds request timeout."""

    def __init__(self, session: Session, request_timeout: float):
        self.session = session
        self.request_timeout = request_timeout

    def request(self, *args, **kwargs) -> Response:
        """Send request with configured timeout."""

        return self.session.request(
            *args, **kwargs, timeout=self.request_timeout
        )

    def close(self) -> None:
        """Close session."""

        self.session.close()


class LogFormatter:
    """Custom log formatter."""

    def __init__(
        self,
        base_formatter_args: dict,
        info_formatter_args: dict,
        formatter: logging.Formatter = logging.Formatter,
    ) -> None:
        self.base_formatter = formatter(**base_formatter_args)
        self.info_formatter = formatter(**info_formatter_args)

    def format(self, record: logging.LogRecord) -> any:
        """Format INFO level messages according to availability log spec."""

        return (
            self.info_formatter.format(record)
            if logging.root.level == record.levelno == logging.INFO
            else self.base_formatter.format(record)
        )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        prog="healthcheck",
        description=(
            "Start healthcheck cycle for a given set of endpoints.\n"
            "Press CTRL-C to exit."
        ),
    )
    parser.add_argument(
        "filepath",
        help=(
            "Path to YAML file with serialized endpoint data.\n"
            "Relative and absolute paths are supported.\n"
            "See README.md for endpoint schema info."
        ),
    )
    return parser.parse_args()


def validate_schema(filepath: str, schema: Schema) -> Endpoints | Config:
    """Validate input endpoints."""

    content = load_yaml(filepath)
    try:
        return schema.validate(content)
    except SchemaError as e:
        logger.error("Schema error in %s: %s", filepath, e)
    sys.exit(1)


def load_yaml(filepath: str) -> Endpoints | Config:
    """Load/deserialize yaml content from file."""

    try:
        with open(Path(filepath).resolve(), "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except FileNotFoundError as e:
        logger.error("%s", e)
    except yaml.YAMLError as e:
        logger.error("YAML error: %s", e)
    sys.exit(1)


def parse_endpoints(
    input_endpoints: Endpoints,
) -> tuple[list[Endpoint], list[HealthTracker]]:
    """Parse endpoints"""

    healthtrackers = {}
    endpoints = []
    for endpoint in input_endpoints:
        e = Endpoint(**endpoint)
        if e.domain_name not in healthtrackers:
            healthtrackers[e.domain_name] = HealthTracker(e.domain_name)
        e.healthtracker = healthtrackers[e.domain_name]
        endpoints.append(e)

    return (
        endpoints,
        sorted(healthtrackers.values(), key=lambda a: a.domain_name),
    )


def create_session(
    session: Session, adapter: LimiterAdapter, request_timeout: float
) -> HealthcheckSession:
    """Create HealthcheckSession."""

    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return HealthcheckSession(session, request_timeout)


def get_start_times(check_interval: int) -> Generator[float, None, None]:
    """Generate sequence of start times for health checks."""

    first_start = time.time() + 0.5
    return (first_start + i for i in count(0, check_interval))
