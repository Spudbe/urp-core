import json
import pytest
from urp.core import Claim, ClaimType, ProofReference, Stake
from urp.message import URPMessage, PROTOCOL_VERSION


def _make_claim():
    pr = ProofReference(hash="h", location="ipfs://test", summary="s")
    st = Stake(amount=0.1)
    return Claim(id="test-id", statement="test statement", type=ClaimType.ASSERTION, proof_ref=pr, stake=st)


class TestURPMessage:
    def test_protocol_version_default(self):
        msg = URPMessage("claim", _make_claim(), "agent-1")
        assert msg.protocol_version == "0.3.0"

    def test_to_json_compact_contains_protocol_version(self):
        msg = URPMessage("claim", _make_claim(), "agent-1")
        raw = msg.to_json(compact=True)
        data = json.loads(raw)
        assert "protocol_version" in data
        assert data["protocol_version"] == "0.3.0"

    def test_from_json_round_trip(self):
        original = URPMessage("claim", _make_claim(), "agent-1")
        raw = original.to_json(compact=True)
        restored = URPMessage.from_json(raw, payload_cls=Claim)
        assert restored.sender == "agent-1"
        assert restored.type == "claim"
        assert restored.protocol_version == PROTOCOL_VERSION
        assert restored.payload.id == "test-id"

    def test_from_json_mismatched_version_still_parses(self):
        """from_json does not currently validate version, so a mismatched
        version round-trips. This test documents that behaviour; a future
        version may raise ValueError instead."""
        original = URPMessage("claim", _make_claim(), "agent-1", protocol_version="99.0.0")
        raw = original.to_json(compact=True)
        restored = URPMessage.from_json(raw, payload_cls=Claim)
        assert restored.protocol_version == "99.0.0"
