"""""Tests for helpers module."""

import argparse
import copy
import logging
import unittest
from http import HTTPMethod
from itertools import islice
from unittest.mock import Mock, call, patch

from requests import Session

from healthcheck.helpers import (
    HealthcheckSession,
    LogFormatter,
    create_session,
    get_start_times,
    load_yaml,
    parse_args,
    parse_endpoints,
    validate_schema,
)
from healthcheck.models import Endpoint, EndpointSchema, HealthTracker

from .shared import ENDPOINTS_CONFIG


class TestHealthcheckSession(unittest.TestCase):
    """Test cases for HealthcheckSession class."""

    def setUp(self):
        """Set up test dependencies."""
        self.mock_session = Mock(spec=Session)
        self.session = HealthcheckSession(self.mock_session, 0.5)

    def tearDown(self):
        """Clean up test dependencies."""
        del self.mock_session
        del self.session

    def test_request(self):
        """Test request method passes through to underlying session."""
        self.session.request("GET", "http://example.com")
        self.mock_session.request.assert_called_with(
            "GET",
            "http://example.com",
            timeout=0.5,
        )

    def test_close(self):
        """Test close method passes through to underlying session."""
        self.session.close()
        self.mock_session.close.assert_called()


class TestLogFormatter(unittest.TestCase):
    """Test cases for LogFormatter class."""

    def test_format_info_level(self):
        """Test that INFO level messages are formatted without metadata."""
        base_formatter_args = {"fmt": "%(levelname)s %(message)s"}
        info_formatter_args = {"fmt": "%(message)s"}

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        formatter = LogFormatter(base_formatter_args, info_formatter_args)
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "Test message", None, None
        )
        self.assertEqual(formatter.format(record), "Test message")
        record = logging.LogRecord(
            "test", logging.DEBUG, "", 0, "Test message", None, None
        )
        self.assertEqual(formatter.format(record), "DEBUG Test message")

        root_logger.setLevel(logging.DEBUG)
        record = logging.LogRecord(
            "test", logging.INFO, "", 0, "Test message", None, None
        )
        self.assertEqual(formatter.format(record), "INFO Test message")
        record = logging.LogRecord(
            "test", logging.DEBUG, "", 0, "Test message", None, None
        )
        self.assertEqual(formatter.format(record), "DEBUG Test message")


class TestHelpers(unittest.TestCase):
    """Test cases for helpers module."""

    def setUp(self):
        self.endpoints = copy.deepcopy(ENDPOINTS_CONFIG)

    def tearDown(self):
        del self.endpoints

    @patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(filepath="test.yaml"),
        autospec=True,
    )
    def test_parse_args(self, _):
        """Test parse_args function."""
        args = parse_args()
        self.assertEqual(args.filepath, "test.yaml")

    @patch("healthcheck.helpers.load_yaml", autospec=True)
    def test_validate_schema_valid(self, mock_load_yaml):
        """Test validate_schema with valid data."""
        mock_load_yaml.return_value = [self.endpoints[0]]
        expected = [
            {
                "name": "fetch index page",
                "url": "https://fetch.com/",
                "method": HTTPMethod.GET,
                "headers": {"user-agent": "fetch-synthetic-monitor"},
            }
        ]

        result = validate_schema("test.yaml", EndpointSchema)
        self.assertEqual(result, expected)

    @patch("healthcheck.helpers.load_yaml", autospec=True)
    @patch("healthcheck.helpers.logger.error", autospec=True)
    @patch("sys.exit", autospec=True)
    def test_validate_schema_invalid(
        self, mock_sys_exit, mock_logger_error, mock_load_yaml
    ):
        """Test validate_schema with invalid data."""
        invalid_endpoint = self.endpoints[0]
        invalid_endpoint.pop("name")

        mock_load_yaml.return_value = [invalid_endpoint]
        validate_schema("test.yaml", EndpointSchema)
        mock_logger_error.assert_called()
        mock_sys_exit.assert_called_with(1)

    @patch("builtins.open", create=True, autospec=True)
    @patch("yaml.safe_load", return_value={"test": "data"}, autospec=True)
    def test_load_yaml(self, *_):
        """Test load_yaml function."""
        result = load_yaml("test.yaml")
        self.assertEqual(result, {"test": "data"})

    @patch(
        "builtins.open",
        side_effect=FileNotFoundError("File not found"),
        autospec=True,
    )
    @patch("healthcheck.helpers.logger.error", autospec=True)
    @patch("sys.exit", autospec=True)
    def test_load_yaml_file_not_found(
        self, mock_sys_exit, mock_logger_error, _
    ):
        """Test load_yaml when file is not found."""
        load_yaml("missing.yaml")
        mock_logger_error.assert_called()
        mock_sys_exit.assert_called_with(1)

    def test_parse_endpoints(self):
        """Test parse_endpoints function."""
        endpoints, healthtrackers = parse_endpoints(self.endpoints)
        self.assertEqual(len(endpoints), 4)
        self.assertEqual(len(healthtrackers), 2)
        self.assertIsInstance(endpoints[0], Endpoint)
        self.assertIsInstance(healthtrackers[0], HealthTracker)

    @patch("requests.Session", autospec=True)
    @patch("requests_ratelimiter.LimiterAdapter", autospec=True)
    def test_create_session(self, mock_limiter_adapter, mock_session):
        """Test create_session function."""

        session = create_session(mock_session, mock_limiter_adapter, 0.5)
        self.assertIsInstance(session, HealthcheckSession)
        self.assertEqual(session.request_timeout, 0.5)
        session.session.mount.assert_has_calls(
            [
                call("http://", mock_limiter_adapter),
                call("https://", mock_limiter_adapter),
            ]
        )

    @patch(
        "time.time",
        return_value=100.0,
        autospec=True,
    )  # Mock time.time to return a fixed value
    def test_get_start_times(self, _):
        """Test get_start_times returns correct sequence of start times."""
        check_interval = 5
        gen = get_start_times(check_interval)

        # Extract first 3 values from the generator
        start_times = list(islice(gen, 3))

        expected_start_times = [100.5, 105.5, 110.5]
        self.assertEqual(start_times, expected_start_times)


if __name__ == "__main__":
    unittest.main()
