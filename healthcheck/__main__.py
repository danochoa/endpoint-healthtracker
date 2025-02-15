"""Entry point for healthcheck."""

import logging.config
import sys
from concurrent.futures import ThreadPoolExecutor

from pyrate_limiter import SQLiteBucket
from requests import Session
from requests_ratelimiter import LimiterAdapter
from urllib3 import Retry

from .healthcheck import run_healthchecks
from .helpers import (
    create_session,
    get_start_times,
    parse_args,
    parse_endpoints,
    validate_schema,
)
from .models import ConfigSchema, EndpointSchema


def main() -> None:
    """Start the healthcheck cycle."""

    config = validate_schema("config.yaml", ConfigSchema)

    logging.config.dictConfig(config["logging"])

    endpoints = validate_schema(parse_args().filepath, EndpointSchema)
    endpoints, healthtrackers = parse_endpoints(endpoints)

    max_workers = min(
        len(endpoints), config["healthcheck"]["max_concurrent_requests"]
    )
    executor = ThreadPoolExecutor(max_workers=max_workers)

    adapter = LimiterAdapter(
        **config["rate_limiter"],
        max_retries=Retry(**config["request_retry"]),
        bucket_class=SQLiteBucket,
    )
    session = create_session(
        Session(), adapter, config["session"]["request_timeout"]
    )

    start_times = get_start_times(config["healthcheck"]["interval"])

    run_healthchecks(
        endpoints,
        healthtrackers,
        executor,
        session,
        start_times,
    )


sys.exit(main())
