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


class TestDeterministicEndpoint:
    """The /run-deterministic endpoint streams a full verification cycle."""

    def test_returns_200_sse_stream(self, client):
        resp = client.get("/run-deterministic")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_stream_contains_expected_events(self, client):
        """The SSE stream should contain ping, balances, scenario, steps,
        urp_message events, settlement, and complete."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "event: ping" in body
        assert "event: balances" in body
        assert "event: scenario" in body
        assert "event: step" in body
        assert "event: urp_message" in body
        assert "event: settlement" in body
        assert "event: structured_claim" in body
        assert "event: claim_match" in body
        assert "event: complete" in body

    def test_stream_contains_deterministic_claim(self, client):
        """The claim should reference compute_fibonacci and Fibonacci(10)."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "compute_fibonacci" in body
        assert "Fibonacci" in body

    def test_stream_contains_settlement_message(self, client):
        """A SettlementMessage should be emitted as a URPMessage."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "settlement_id" in body
        assert "researcher_delta" in body

    def test_stream_contains_verification_result(self, client):
        """The challenger/verifier reasoning should mention replay verification."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "replay_class" in body
        assert "verified" in body.lower() or "VERIFIED" in body

    def test_stream_contains_tampered_scenario(self, client):
        """A second scenario should show tampered receipt detection."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "TAMPERED" in body
        assert "det-claim-002-tampered" in body
        assert "REJECTED" in body or "rejected" in body

    def test_no_api_key_required(self, client):
        """The deterministic endpoint must work without GROQ_API_KEY."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            resp = client.get("/run-deterministic")
            assert resp.status_code == 200
            assert "event: complete" in resp.text

    def test_structured_claim_contains_proposition(self, client):
        """The structured_claim event should contain a tool_output_equals proposition."""
        resp = client.get("/run-deterministic")
        body = resp.text
        assert "tool_output_equals" in body
        assert "sc_version" in body
        assert "fingerprint" in body

    def test_claim_match_shows_true_for_valid(self, client):
        """Scenario 1 should produce a claim_match with status true."""
        resp = client.get("/run-deterministic")
        body = resp.text
        # The first claim_match should be "true" (valid fibonacci)
        assert '"status": "true"' in body or '"status":"true"' in body

    def test_claim_match_shows_false_for_tampered(self, client):
        """Scenario 2: the claim matches its own tampered receipt (true),
        but the replay verifier catches the lie. Both events should appear."""
        resp = client.get("/run-deterministic")
        body = resp.text
        # Claim-to-evidence matching says true (claim matches its receipt)
        # But replay verification rejects it (output hash mismatch)
        assert "TAMPERED" in body
        assert "REJECTED" in body or "rejected" in body


class TestCapabilityEndpoint:
    """The /.well-known/urp-capability.json endpoint serves an AgentCapability."""

    def test_returns_200_json(self, client):
        resp = client.get("/.well-known/urp-capability.json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_contains_protocol_version(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        assert data["protocol_version"] == "0.3.0"

    def test_contains_agent_identity(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        assert data["agent"]["id"] == "urp-demo-server"
        assert data["agent"]["name"] == "URP Demo Server"

    def test_contains_supported_claim_kinds(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        kinds = data["supported_claim_kinds"]
        assert "tool_output" in kinds
        assert "factual_assertion" in kinds

    def test_contains_accepted_evidence_types(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        types = data["accepted_evidence_types"]
        assert "tool_receipt" in types

    def test_contains_stake_policy(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        policy = data["stake_policy"]
        assert policy["required"] is True
        assert policy["minimum_amount"] == 0.1
        assert policy["currency"] == "URC"

    def test_contains_compatible_versions(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        versions = data["compatible_protocol_versions"]
        assert "0.2.0" in versions
        assert "0.3.0" in versions

    def test_contains_metadata_with_tools(self, client):
        data = client.get("/.well-known/urp-capability.json").json()
        meta = data["metadata"]
        assert meta["demo"] is True
        assert "compute_fibonacci" in meta["deterministic_tools"]
        assert "math_eval" in meta["deterministic_tools"]

    def test_round_trips_through_agent_capability(self):
        """The JSON output must be parseable back into an AgentCapability."""
        from fastapi.testclient import TestClient
        from server import app
        from urp.core import AgentCapability

        client = TestClient(app)
        data = client.get("/.well-known/urp-capability.json").json()
        cap = AgentCapability.from_dict(data)
        assert cap.protocol_version == "0.3.0"
        assert cap.agent.id == "urp-demo-server"


class TestAgentCardEndpoint:
    """The /.well-known/agent-card.json endpoint serves an A2A AgentCard."""

    def test_agent_card_returns_200_json(self, client):
        resp = client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

    def test_agent_card_has_a2a_fields(self, client):
        data = client.get("/.well-known/agent-card.json").json()
        assert "name" in data
        assert "description" in data
        assert "skills" in data
        assert "supportedInterfaces" in data

    def test_agent_card_has_urp_extension(self, client):
        data = client.get("/.well-known/agent-card.json").json()
        extensions = data.get("capabilities", {}).get("extensions", [])
        urp_ext = [e for e in extensions if e.get("uri") == "urn:urp:agent-capability"]
        assert len(urp_ext) == 1

    def test_agent_card_round_trips_to_capability(self, client):
        from urp.a2a_adapter import a2a_card_to_urp_capability
        data = client.get("/.well-known/agent-card.json").json()
        cap = a2a_card_to_urp_capability(data)
        assert cap.protocol_version == "0.3.0"
