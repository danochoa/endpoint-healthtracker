"""Data models for the various healthcheck components."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from http import HTTPMethod
from typing import TYPE_CHECKING

import tldextract
from requests import RequestException
from schema import And, Optional, Schema, Use

if TYPE_CHECKING:
    from healthcheck.helpers import HealthcheckSession


@dataclass
class HealthTracker:
    """Dataclass to manage health information."""

    domain_name: str
    requests_up: int = 0
    requests_total: int = 0

    @property
    def availability_percentage(self) -> int:
        """Calculate availability percentage."""

        try:
            return round(100 * (self.requests_up / self.requests_total))
        except ZeroDivisionError:
            logging.warning(
                "Domain %s has no requests recorded.", self.domain_name
            )
        return 0

    @property
    def availability_status(self) -> str:
        """Return string representation of availability status."""

        return (
            f"{self.domain_name} has {self.availability_percentage}% availability "
            f"percentage"
        )

    def record_request(self, is_up: bool) -> None:
        """Record request result."""

        self.requests_total += 1
        if is_up:
            self.requests_up += 1


@dataclass
class Endpoint:
    """Dataclass to store endpoint information."""

    name: str
    url: str
    method: HTTPMethod = HTTPMethod.GET
    headers: dict | None = None
    body: str | None = None
    healthtracker: HealthTracker = field(init=False)

    @property
    def domain_name(self):
        """Extract domain name from URL."""
        url = tldextract.extract(self.url)
        return ".".join(filter(None, [url.subdomain, url.domain, url.suffix]))

    def check_health(
        self,
        session: HealthcheckSession,
    ) -> tuple[HealthTracker, bool]:
        """Check if endpoint is up."""

        try:
            response = session.request(
                self.method,
                self.url,
                headers=self.headers,
                data=self.body,
            )
        except RequestException:
            response = None
        if response and response.status_code in range(200, 300):
            return (self.healthtracker, True)
        return (self.healthtracker, False)


EndpointSchema = Schema(
    [
        {
            "name": And(str, len),
            "url": And(str, len),
            Optional("method"): Use(HTTPMethod),
            Optional("headers"): dict,
            Optional("body"): str,
        }
    ]
)


ConfigSchema = Schema(
    {
        "healthcheck": {
            "interval": int,
            "max_concurrent_requests": int,
        },
        "session": {
            "request_timeout": float,
        },
        "rate_limiter": {
            "per_second": int,
            "per_host": bool,
            "limit_statuses": list[int],
        },
        "request_retry": {
            "status": int,
            "status_forcelist": list[int],
            "respect_retry_after_header": bool,
            "backoff_factor": float,
            "backoff_jitter": float,
            "connect": int,
            "read": int,
            "other": int,
        },
        "logging": {
            "loggers": {
                "root": {
                    "level": Use(lambda l: getattr(logging, l.upper())),
                    "handlers": list[str],
                }
            },
            "formatters": dict,
            "handlers": dict,
            "version": int,
            "disable_existing_loggers": bool,
        },
    }
)
