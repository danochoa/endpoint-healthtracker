"""Unit tests for models module."""

import copy
import unittest
from unittest.mock import Mock, patch

from requests import RequestException, Response, Session

from healthcheck.helpers import HealthcheckSession
from healthcheck.models import ConfigSchema, EndpointSchema

from .shared import CONFIG, ENDPOINTS, ENDPOINTS_CONFIG, HEALTHTRACKERS


class TestAvailability(unittest.TestCase):
    """Test cases for HealthTracker class."""

    def setUp(self):
        """Set up test dependencies."""
        self.healthtracker = copy.deepcopy(HEALTHTRACKERS[0])

    def tearDown(self):
        """Reset test dependencies."""
        del self.healthtracker

    def test_record_request_up(self):
        """Test recording an up request increments counters correctly."""
        self.healthtracker.record_request(True)
        self.assertEqual(self.healthtracker.requests_up, 1)
        self.assertEqual(self.healthtracker.requests_total, 1)

    def test_record_request_down(self):
        """Test recording a down request increments only total counter."""
        self.healthtracker.record_request(False)
        self.assertEqual(self.healthtracker.requests_up, 0)
        self.assertEqual(self.healthtracker.requests_total, 1)

    def test_availability_percentage(self):
        """Test availability percentage calculation."""
        self.healthtracker.record_request(True)
        self.healthtracker.record_request(False)
        self.assertEqual(self.healthtracker.availability_percentage, 50)

    def test_percentage_no_requests(self):
        """Test percentage returns 0 and logs warning when no requests recorded."""
        with patch(
            "healthcheck.models.logging.warning", autospec=True
        ) as mock_warn:
            self.assertEqual(self.healthtracker.availability_percentage, 0)
            mock_warn.assert_called()

    def test_status(self):
        """Test status string contains domain name."""
        self.healthtracker.record_request(True)
        self.assertEqual(
            "fetch.com has 100% availability percentage",
            self.healthtracker.availability_status,
        )


class TestEndpoint(unittest.TestCase):
    """Test cases for Endpoint class."""

    def setUp(self):
        """Set up test dependencies."""
        self.endpoint = copy.deepcopy(ENDPOINTS[0])
        self.endpoint.healthtracker = copy.deepcopy(HEALTHTRACKERS[0])
        self.mock_session = Mock(spec=Session)
        self.session = HealthcheckSession(
            self.mock_session, CONFIG["session"]["request_timeout"]
        )

    def tearDown(self):
        """Reset test dependencies."""
        del self.endpoint.healthtracker
        del self.endpoint
        del self.mock_session
        del self.session

    def test_domain_name(self):
        """Test domain name extraction from URL."""
        self.assertEqual(self.endpoint.domain_name, "fetch.com")

    @patch.object(HealthcheckSession, "request", autospec=True)
    def test_check_health_success(self, mock_request):
        """Test health check returns success for 200 status code."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        healthtracker, is_up = self.endpoint.check_health(self.session)
        self.assertTrue(is_up)
        self.assertEqual(healthtracker, self.endpoint.healthtracker)

    @patch.object(HealthcheckSession, "request", autospec=True)
    def test_check_health_failure(self, mock_request):
        """Test health check returns failure for 500 status code."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        healthtracker, is_up = self.endpoint.check_health(self.session)
        self.assertFalse(is_up)
        self.assertEqual(healthtracker, self.endpoint.healthtracker)

    @patch.object(
        HealthcheckSession,
        "request",
        side_effect=RequestException,
        autospec=True,
    )
    def test_check_health_exception(self, _):
        """Test health check returns failure on request exception."""
        healthtracker, is_up = self.endpoint.check_health(self.session)
        self.assertFalse(is_up)
        self.assertEqual(healthtracker, self.endpoint.healthtracker)


class TestSchemas(unittest.TestCase):
    """Test cases for schema validation."""

    def setUp(self):
        """Set up test dependencies."""
        self.endpoints_config = copy.deepcopy(ENDPOINTS_CONFIG)
        self.config = copy.deepcopy(CONFIG)

    def tearDown(self):
        """Reset test dependencies."""
        del self.endpoints_config
        del self.config

    def test_valid_endpoint_schema(self):
        """Test that valid endpoint configuration passes schema validation."""
        self.assertTrue(EndpointSchema.is_valid(self.endpoints_config))

    def test_invalid_endpoint_schema(self):
        """Test that invalid endpoint configuration fails schema validation."""
        invalid_data = [{"name": "", "url": "invalid-url"}]
        self.assertFalse(EndpointSchema.is_valid(invalid_data))

    def test_valid_config_schema(self):
        """Test that valid configuration passes schema validation."""
        self.assertTrue(ConfigSchema.is_valid(self.config))

    def test_invalid_config_schema(self):
        """Test that invalid configuration fails schema validation."""
        invalid_config = {"healthcheck": {"interval": "invalid"}}
        self.assertFalse(ConfigSchema.is_valid(invalid_config))


if __name__ == "__main__":
    unittest.main()
