"""Shared test fixtures and configuration."""

from healthcheck.models import Endpoint, HealthTracker, HTTPMethod

ENDPOINTS = [
    Endpoint(
        name="fetch index page",
        url="https://fetch.com/",
        method=HTTPMethod.GET,
        headers={"user-agent": "fetch-synthetic-monitor"},
    ),
    Endpoint(
        name="fetch careers page",
        url="https://fetch.com/careers",
        method=HTTPMethod.GET,
        headers={"user-agent": "fetch-synthetic-monitor"},
    ),
    Endpoint(
        name="fetch some fake post endpoint",
        url="https://fetch.com/some/post/endpoint",
        method=HTTPMethod.POST,
        headers={
            "content-type": "application/json",
            "user-agent": "fetch-synthetic-monitor",
        },
        body='{"foo":"bar"}',
    ),
    Endpoint(
        name="fetch rewards index page", url="https://www.fetchrewards.com/"
    ),
]

HEALTHTRACKERS = [
    HealthTracker(domain_name="fetch.com", requests_up=0, requests_total=0),
    HealthTracker(
        domain_name="www.fetchrewards.com", requests_up=0, requests_total=0
    ),
]
CONFIG = {
    "healthcheck": {"interval": 2, "max_concurrent_requests": 100},
    "session": {
        "request_timeout": 0.5,
    },
    "rate_limiter": {
        "per_second": 5,
        "per_host": True,
        "limit_statuses": [429],
    },
    "request_retry": {
        "status": 3,
        "status_forcelist": [429],
        "respect_retry_after_header": True,
        "backoff_factor": 0.5,
        "backoff_jitter": 1.0,
        "connect": 0,
        "read": 0,
        "other": 0,
    },
    "logging": {
        "loggers": {"root": {"level": "info", "handlers": ["console"]}},
        "formatters": {
            "custom": {
                "()": "healthcheck.helpers.LogFormatter",
                "base_formatter_args": {
                    "fmt": "%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s"
                },
                "info_formatter_args": {"fmt": "%(message)s"},
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "custom",
                "stream": "ext://sys.stdout",
            }
        },
        "version": 1,
        "disable_existing_loggers": False,
    },
}

ENDPOINTS_CONFIG = [
    {
        "name": "fetch index page",
        "url": "https://fetch.com/",
        "method": "GET",
        "headers": {"user-agent": "fetch-synthetic-monitor"},
    },
    {
        "name": "fetch careers page",
        "url": "https://fetch.com/careers",
        "method": "GET",
        "headers": {"user-agent": "fetch-synthetic-monitor"},
    },
    {
        "name": "fetch some fake post endpoint",
        "url": "https://fetch.com/some/post/endpoint",
        "method": "POST",
        "headers": {
            "content-type": "application/json",
            "user-agent": "fetch-synthetic-monitor",
        },
        "body": '{"foo":"bar"}',
    },
    {
        "name": "fetch rewards index page",
        "url": "https://www.fetchrewards.com/",
    },
]
