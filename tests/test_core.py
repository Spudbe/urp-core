import pytest
from urp.core import ProofReference, Stake, Claim, ClaimType, Decision, ToolReceipt


class TestProofReference:
    def test_fields_set_correctly(self):
        pr = ProofReference(hash="abc123", location="ipfs://test", summary="A summary")
        assert pr.hash == "abc123"
        assert pr.location == "ipfs://test"
        assert pr.summary == "A summary"

    def test_confidence_score_set(self):
        pr = ProofReference(hash="h", location="l", summary="s", confidence_score=0.8)
        assert pr.confidence_score == 0.8

    def test_to_dict_with_confidence_score(self):
        pr = ProofReference(hash="h", location="l", summary="s", confidence_score=0.9)
        d = pr.to_dict()
        assert "confidence_score" in d
        assert d["confidence_score"] == 0.9

    def test_to_dict_without_confidence_score(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        d = pr.to_dict()
        assert "confidence_score" not in d


class TestStake:
    def test_defaults(self):
        s = Stake(amount=1.0)
        assert s.amount == 1.0
        assert s.currency == "URC"
        assert s.refundable is True


class TestClaim:
    def test_fields_set_correctly(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        st = Stake(amount=0.5)
        c = Claim(id="claim-1", statement="test", type=ClaimType.ASSERTION, proof_ref=pr, stake=st)
        assert c.id == "claim-1"
        assert c.statement == "test"
        assert c.type == ClaimType.ASSERTION
        assert c.proof_ref is pr
        assert c.stake is st

    def test_to_dict_from_dict_round_trip(self):
        pr = ProofReference(hash="h", location="l", summary="s", confidence_score=0.7)
        st = Stake(amount=0.5, currency="URC", refundable=False)
        original = Claim(id="claim-1", statement="test", type=ClaimType.REQUEST, proof_ref=pr, stake=st)
        reconstructed = Claim.from_dict(original.to_dict())
        assert reconstructed.id == original.id
        assert reconstructed.statement == original.statement
        assert reconstructed.type == original.type
        assert reconstructed.proof_ref.hash == original.proof_ref.hash
        assert reconstructed.proof_ref.confidence_score == original.proof_ref.confidence_score
        assert reconstructed.stake.amount == original.stake.amount
        assert reconstructed.stake.refundable == original.stake.refundable


class TestDecision:
    def test_enum_members(self):
        assert Decision.ACCEPT.value == "accept"
        assert Decision.REJECT.value == "reject"
        assert Decision.CHALLENGE.value == "challenge"
        assert Decision.EXPIRED.value == "expired"


class TestToolReceipt:
    def _make_receipt(self, **overrides):
        defaults = {
            "tool_name": "calculator",
            "tool_version": "1.0.0",
            "inputs": {"expression": "2+2"},
            "output": {"result": 4},
            "timestamp": "2026-03-22T12:00:00Z",
        }
        defaults.update(overrides)
        return ToolReceipt(**defaults)

    def test_fields_set_correctly(self):
        tr = self._make_receipt(signature="sig123")
        assert tr.tool_name == "calculator"
        assert tr.tool_version == "1.0.0"
        assert tr.inputs == {"expression": "2+2"}
        assert tr.output == {"result": 4}
        assert tr.timestamp == "2026-03-22T12:00:00Z"
        assert tr.signature == "sig123"
        assert isinstance(tr.replay_hash, str)
        assert len(tr.replay_hash) == 64  # SHA-256 hex

    def test_to_dict_from_dict_round_trip(self):
        original = self._make_receipt(signature="sig456")
        d = original.to_dict()
        reconstructed = ToolReceipt.from_dict(d)
        assert reconstructed.tool_name == original.tool_name
        assert reconstructed.tool_version == original.tool_version
        assert reconstructed.inputs == original.inputs
        assert reconstructed.output == original.output
        assert reconstructed.timestamp == original.timestamp
        assert reconstructed.signature == original.signature
        assert reconstructed.replay_hash == original.replay_hash

    def test_make_replay_hash_consistent(self):
        h1 = ToolReceipt.make_replay_hash("calc", "1.0", {"x": 1})
        h2 = ToolReceipt.make_replay_hash("calc", "1.0", {"x": 1})
        assert h1 == h2
        h3 = ToolReceipt.make_replay_hash("calc", "1.0", {"x": 2})
        assert h1 != h3

    def test_to_dict_omits_signature_when_none(self):
        tr = self._make_receipt()
        d = tr.to_dict()
        assert "signature" not in d

    def test_to_dict_includes_signature_when_set(self):
        tr = self._make_receipt(signature="jws-token")
        d = tr.to_dict()
        assert d["signature"] == "jws-token"


class TestProofReferenceWithEvidence:
    def test_to_dict_includes_evidence(self):
        tr = ToolReceipt(
            tool_name="search", tool_version="2.0",
            inputs={"query": "test"}, output={"hits": 5},
            timestamp="2026-03-22T12:00:00Z",
        )
        pr = ProofReference(hash="h", location="l", summary="s", evidence=tr)
        d = pr.to_dict()
        assert "evidence" in d
        assert d["evidence"]["tool_name"] == "search"

    def test_to_dict_excludes_evidence_when_none(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        d = pr.to_dict()
        assert "evidence" not in d

    def test_from_dict_round_trip_with_evidence(self):
        tr = ToolReceipt(
            tool_name="search", tool_version="2.0",
            inputs={"query": "test"}, output={"hits": 5},
            timestamp="2026-03-22T12:00:00Z",
        )
        original = ProofReference(hash="h", location="l", summary="s", evidence=tr)
        reconstructed = ProofReference.from_dict(original.to_dict())
        assert reconstructed.evidence is not None
        assert reconstructed.evidence.tool_name == "search"
        assert reconstructed.evidence.replay_hash == tr.replay_hash
