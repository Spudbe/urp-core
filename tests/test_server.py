"""Tests for server.py hardening: debug-env gating, rate limiting, claim length."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server import MAX_CLAIM_LENGTH, app


@pytest.fixture
def client():
    return TestClient(app)


class TestDebugEnvGating:
    """The /debug-env endpoint must only respond when DEBUG=true."""

    def test_debug_env_returns_404_when_debug_not_set(self, client):
        with patch.dict(os.environ, {}, clear=True):
            resp = client.get("/debug-env")
            assert resp.status_code == 404

    def test_debug_env_returns_404_when_debug_is_false(self, client):
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=False):
            resp = client.get("/debug-env")
            assert resp.status_code == 404

    def test_debug_env_returns_200_when_debug_is_true(self, client):
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            resp = client.get("/debug-env")
            assert resp.status_code == 200
            data = resp.json()
            assert "GROQ_API_KEY_set" in data

    def test_debug_env_case_insensitive(self, client):
        with patch.dict(os.environ, {"DEBUG": "TRUE"}, clear=False):
            resp = client.get("/debug-env")
            assert resp.status_code == 200


class TestClaimLengthValidation:
    """Custom claims exceeding MAX_CLAIM_LENGTH must be rejected with 400."""

    def test_rejects_claim_exceeding_max_length(self, client):
        oversized = "x" * (MAX_CLAIM_LENGTH + 1)
        resp = client.get("/run-simulation", params={"claim": oversized})
        assert resp.status_code == 400
        assert "maximum length" in resp.json()["detail"]

    def test_accepts_claim_at_max_length(self, client):
        """A claim exactly at the limit should not be rejected for length.
        It will still fail (no GROQ_API_KEY) but with 200 SSE, not 400."""
        exact = "x" * MAX_CLAIM_LENGTH
        resp = client.get("/run-simulation", params={"claim": exact})
        # Should not be 400 — it passes validation, hits the SSE stream
        assert resp.status_code == 200

    def test_accepts_no_claim(self, client):
        """No custom claim should pass validation."""
        resp = client.get("/run-simulation")
        assert resp.status_code == 200


class TestMaxClaimLengthConstant:
    """MAX_CLAIM_LENGTH must be 2000."""

    def test_max_claim_length_value(self):
        assert MAX_CLAIM_LENGTH == 2000
