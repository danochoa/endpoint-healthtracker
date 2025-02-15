"""Tests for the healthcheck module."""

import signal
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, PropertyMock, patch

from healthcheck.healthcheck import (
    check_endpoints,
    exit_healthchecks,
    log_statuses,
    register_exit_handler,
    run_healthchecks,
    sleep_until,
)
from healthcheck.helpers import HealthcheckSession
from healthcheck.models import Endpoint, HealthTracker


class TestHealthcheck(unittest.TestCase):
    """Test suite for healthcheck functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=HealthcheckSession)
        self.mock_executor = Mock(spec=ThreadPoolExecutor)
        self.mock_endpoints = [Mock(spec=Endpoint) for _ in range(3)]
        self.mock_healthtrackers = [Mock(spec=HealthTracker) for _ in range(3)]

    def tearDown(self):
        """Clean up test fixtures."""
        del self.mock_session
        del self.mock_executor
        del self.mock_endpoints
        del self.mock_healthtrackers

    @patch("healthcheck.healthcheck.register_exit_handler", autospec=True)
    @patch("healthcheck.healthcheck.sleep_until", autospec=True)
    @patch("healthcheck.healthcheck.check_endpoints", autospec=True)
    @patch(
        "healthcheck.healthcheck.log_statuses",
        side_effect=KeyboardInterrupt,
        autospec=True,
    )
    def test_run_healthchecks(
        self,
        mock_log_statuses,
        mock_check_endpoints,
        mock_sleep_until,
        mock_register_exit_hanlder,
    ):
        """Test run_healthchecks executes health check cycle."""

        with self.assertRaises(KeyboardInterrupt):
            run_healthchecks(
                self.mock_endpoints,
                self.mock_healthtrackers,
                self.mock_executor,
                self.mock_session,
                (t for t in [0, 1, 2]),
            )

        mock_register_exit_hanlder.assert_called_with(
            self.mock_executor, self.mock_session
        )
        mock_sleep_until.assert_called_with(0)
        mock_check_endpoints.assert_called_with(
            self.mock_endpoints, self.mock_session, self.mock_executor
        )
        mock_log_statuses.assert_called_with(self.mock_healthtrackers)

    @patch("healthcheck.healthcheck.exit_healthchecks", autospec=True)
    def test_register_exit_handler(self, mock_exit_healthchecks):
        """Test that SIGINT triggers exit handler."""
        executor = Mock(spec=ThreadPoolExecutor)
        session = Mock(spec=HealthcheckSession)

        register_exit_handler(executor, session)
        signal.raise_signal(signal.SIGINT)

        mock_exit_healthchecks.assert_called_with(executor, session)

    @patch("sys.exit", autospec=True)
    def test_exit_healthchecks(self, mock_sys_exit):
        """Test exit_healthchecks performs proper cleanup before exiting."""
        exit_healthchecks(self.mock_executor, self.mock_session)
        self.mock_executor.shutdown.assert_called_with(
            wait=False, cancel_futures=True
        )
        self.mock_session.close.assert_called()
        mock_sys_exit.assert_called_with(0)

    @patch("time.sleep", side_effect=lambda _: None, autospec=True)
    @patch("healthcheck.healthcheck.logger.warning", autospec=True)
    def test_sleep_until(self, mock_logger, mock_sleep):
        """Test sleep_until handles both normal and missed start times."""
        with patch("time.time", side_effect=[0], autospec=True):
            sleep_until(1)
        mock_sleep.assert_called_with(1)

        with patch("time.time", side_effect=[2], autospec=True):
            sleep_until(1)
        mock_logger.assert_called_with("Missed start time by %s seconds", 1)

    def test_check_endpoints(self):
        """Test check_endpoints submits tasks and handles results correctly."""
        for i, e in enumerate(self.mock_endpoints):
            e.check_health.return_value = (self.mock_healthtrackers[i], True)
        executor = ThreadPoolExecutor(max_workers=3)
        check_endpoints(self.mock_endpoints, self.mock_session, executor)
        executor.shutdown(wait=False, cancel_futures=True)

        for e in self.mock_endpoints:
            e.check_health.assert_called_with(self.mock_session)
        for a in self.mock_healthtrackers:
            a.record_request.assert_called_with(True)

    def test_log_statuses(self):
        """Test log_statuses calls status for each healthtracker."""
        p = PropertyMock()
        for a in self.mock_healthtrackers:
            type(a).availability_status = p
        log_statuses(self.mock_healthtrackers)
        assert p.call_count == len(self.mock_healthtrackers)


if __name__ == "__main__":
    unittest.main()
