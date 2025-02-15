# Endpoint Health Tracker

A lightweight Python program to monitor the health of HTTP endpoints and log the availability percentage for each domain.

**Project goals**:

This project began as a take-home exercise for a job interview and may not be fully optimized for all real-world applications. The primary goal is to showcase skills in developing tools, with a focus on:

1. Software engineering principals including modularity, readability, maintainability, error handling, testing, etc.
1. Delivering a near-production ready program that meets a set of requirements summarized in the [Overview](#overview) section and detailed in the [Usage](#usage), [Availability Calculation](#availability-calculation), and [Endpoint Schema](#endpoint-schema) sections.
1. Additional robustness and usability features as outlined in the [Key Features](#key-features) section.

## Table of Contents

- [Overview](#overview)
  - [Key features:](#key-features)
- [Usage](#usage)
  - [Example](#example)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)
- [Availability Calculation](#availability-calculation)
- [Endpoint Schema](#endpoint-schema)
- [Debug Logging](#debug-logging)
- [Configuration Parameters](#configuration-parameters)
- [Assumptions and Limitations](#assumptions-and-limitations)
- [Future Improvements](#future-improvements)

## Overview

The program reads a YAML file containing a list of HTTP endpoints and their configurations. It performs periodic health checks on these endpoints, calculates the cumulative availability percentage for each domain, and logs the results to the console. The health check cycle repeats every 15 seconds until manually terminated.

### Key features:

- Aggregated availability metrics by domain.
- Concurrent health checks using worker threads.
- Rate limiting to avoid overwhelming hosts.
- Configurable request timeouts, retries, and backoff strategies.
- Debug logging to inspect thread connection pool and rate limit logs.

## Usage

To run the program, use the following command:

```shell
$ python3 -m healthcheck -h
usage: healthcheck [-h] filepath

Start healthcheck cycle for a given set of endpoints.
Press CTRL-C to exit.

positional arguments:
  filepath    Path to YAML file with serialized endpoint data.
              Relative and absolute paths are supported.
              See README.md for endpoint schema info.

options:
  -h, --help  show this help message and exit
```

### Example

```shell
$ python3 -m healthcheck sample_endpoints.yaml
fetch.com has 67% availability percentage
www.fetchrewards.com has 100% availability percentage
...
```

## Installation

### Prerequisites

- **Python** version **3.13**. Other Python versions have not been tested.
- Python **pip** module compatible with Python 3.13. Usually pip comes installed with Python.

If **Python** or **pip** is not installed on your system, see the official installation guides for [Python](https://wiki.python.org/moin/BeginnersGuide/Download) and [pip](https://pip.pypa.io/en/stable/installation/).

For macOS Homebrew users:

```shell
brew install python@3.13
```

Verify Python 3.13 installation:

```shell
$ python3 --version
Python 3.13.0

$ python3 -m pip --version
pip 24.3.1 from /Path/to/python3.13/site-packages/pip (python 3.13)
```

### Steps

```shell
# Clone the repo and cd to the project root
git clone git@github.com:danochoa/endpoint-healthtracker.git
cd endpoint-healthtracker
# Install pipenv for deterministic builds
python3 -m pip install --user pipenv
# Install the Python modules in the Pipfile
python3 -m pipenv install
# Activate the virtual environment
python3 -m pipenv shell
# Test that it's working
python3 -m healthcheck -h
```

## Availability Calculation

The program calculates the availability percentage for each domain based on the results of HTTP requests.

Definition:

- **UP**: The HTTP response code is 2xx (any 200–299 response code) and the response latency is less than 500 ms.
- **DOWN**: The endpoint is not UP.

The availability percentage is calculated as:
_100 \* (Number of UP requests / Total number of requests)_

Results are rounded to the nearest whole number.

## Endpoint Schema

Each endpoint in the YAML file should following this schema:

```yaml
- name: string  # Required: A free-text name to describe the endpoint.
  url: string  # Required: The URL of the endpoint.
  method: string  # Optional: The HTTP method. (default: GET).
  headers: dictionary  # Optional: The HTTP headers to include in the request.
  body: string  # Optional: A JSON-encoded string to include as the HTTP body in the request.
  ...
```

See [sample_endpoints.yaml](sample_endpoints.yaml) for a complete example.

## Debug Logging

Debug logging can be enabled by setting the root logger level to `debug` in the provided `config.yaml` before starting the program.

The default logging configuration uses a custom log formatter that creates a pair of standard formatters to control how messages are formatted based on the root logger level and log record level, as outlined in the following table:

| Root Logger Level | Log Record Level | Formatter |
| ----------------- | ---------------- | --------- |
| info (default)    | info             | info      |
| info (default)    | non-info         | base      |
| non-info          | all              | base      |

When the root logger is set to `info` (the default mode), the `info` formatter applies only to info-level records to provide the plain availability status messages logged to the console at the end of each health check cycle. The `base` formatter applies to non-info level messages, providing more context such as timestamps, log levels, logger names, thread names, etc., for debugging and troubleshooting.

If the root logger is set to anything other than `info`, the `base` formatter applies to all log records.

Both formatters are full formatters from the standard logging module and are fully customizable in `config.yaml`. Additionally, the full logging configuration is exposed in `config.yaml` to allow more advanced customization, such as logging to a file.

## Configuration Parameters

The program reads configuration settings from [config.yaml](config.yaml). This file must be located in the same directory as the `healthcheck` module.

Default `config.yaml`:

```yaml
healthcheck:
  interval: 5
  max_concurrent_requests: 100
session:
  request_timeout: 0.5
rate_limiter:
  per_second: 5
  per_host: true
  limit_statuses: [429]
request_retry:
  status: 3
  status_forcelist: [429]
  respect_retry_after_header: true
  backoff_factor: 0.5
  backoff_jitter: 1.0
  connect: 0
  read: 0
  other: 0
logging:
  loggers:
    root:
      level: info
      handlers: [console]
  formatters:
    custom:
      (): healthcheck.helpers.LogFormatter
      base_formatter_args:
        { fmt: "%(asctime)s %(levelname)s %(name)s %(threadName)s %(message)s" }
      info_formatter_args: { fmt: "%(message)s" }
  handlers:
    console:
      class: logging.StreamHandler
      formatter: custom
      stream: ext://sys.stdout
  version: 1
  disable_existing_loggers: false
```

See the following docs for more information:

- [Rate limiter adapter](https://requests-ratelimiter.readthedocs.io/en/stable/reference.html#requests_ratelimiter.LimiterAdapter)
- [Retry config](https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry)
- [Logging config](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig)

## Assumptions and Limitations

- The program performs minimal input validation. The content and schema of the input file should be validated before running the program.
- The program considers all 2xx response codes as an "UP" response and all non-2xx response codes as "DOWN", except for 429 (too many requests) which may trigger a retry.
  - The program therefore does not attempt to handle network errors, invalid URLs, or malformed responses.
- The program runs health checks concurrently using one worker thread per endpoint and rate limits requests per host.
- The program does not persist data to external storage. Availability metrics are kept in memory and lost when the program exits.
- The request timeout applies per connection attempt per IP address. If a domain resolves to multiple IPs, the program tries each address sequentially.
- > The request timeout applies to each connection attempt to an IP address. If multiple addresses exist for a domain name, the underlying urllib3 will try each address sequentially until one successfully connects. This may lead to an effective total connection timeout multiple times longer than the specified time, e.g. an unresponsive server having both IPv4 and IPv6 addresses will have its perceived timeout doubled, so take that into account when setting the connection timeout.

## Future Improvements

- Thorough input validation:
  - Validate endpoint headers and prevent duplicate endpoints.
- Containerization:
  - Package the program as a Docker container for easier deployment.
- Service mode:
  - Run the program as a background service or cron job.
- CLI options:
  - Allow configuration via command-line arguments.
- Persistence:
  - Store availability metrics to disk or external storage to persist restarts
- Enable metrics collection and/or enhanced logging:
  - Expose metrics and/or add structured logging for historical analysis.
- General:
  - Clean up config.yaml and provide more user-friendly notes to explain options

## Contributions

See [CONTRIBUTIONS.md](.github/CONTRUBUTING.md)
