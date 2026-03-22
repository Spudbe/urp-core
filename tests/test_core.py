import pytest
from urp.core import (
    ProofReference, Stake, Claim, ClaimType, Decision, ToolReceipt,
    EvidenceStrength, NondeterminismClass, SideEffectClass, ReplayClass,
)


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
        assert c.evidence == []

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
        assert reconstructed.evidence == []

    def test_to_dict_with_evidence(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        st = Stake(amount=0.5)
        tr = ToolReceipt(
            receipt_id="r-1", tool_name="calc", provider_name="test",
            provider_id="p-1", input_inline={"x": 1}, output_inline={"y": 2},
            started_at="2026-03-22T12:00:00Z",
        )
        c = Claim(id="c-1", statement="test", type=ClaimType.ASSERTION,
                  proof_ref=pr, stake=st, evidence=[tr])
        d = c.to_dict()
        assert len(d["evidence"]) == 1
        assert d["evidence"][0]["tool_name"] == "calc"

    def test_to_dict_without_evidence(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        st = Stake(amount=0.5)
        c = Claim(id="c-1", statement="test", type=ClaimType.ASSERTION,
                  proof_ref=pr, stake=st)
        d = c.to_dict()
        assert d["evidence"] == []

    def test_from_dict_round_trip_with_evidence(self):
        pr = ProofReference(hash="h", location="l", summary="s")
        st = Stake(amount=0.5)
        tr = ToolReceipt(
            receipt_id="r-1", tool_name="calc", provider_name="test",
            provider_id="p-1", input_inline={"x": 1}, output_inline={"y": 2},
            started_at="2026-03-22T12:00:00Z",
        )
        original = Claim(id="c-1", statement="test", type=ClaimType.ASSERTION,
                         proof_ref=pr, stake=st, evidence=[tr])
        reconstructed = Claim.from_dict(original.to_dict())
        assert len(reconstructed.evidence) == 1
        assert reconstructed.evidence[0].tool_name == "calc"
        assert reconstructed.evidence[0].input_sha256 == tr.input_sha256


class TestDecision:
    def test_enum_members(self):
        assert Decision.ACCEPT.value == "accept"
        assert Decision.REJECT.value == "reject"
        assert Decision.CHALLENGE.value == "challenge"
        assert Decision.EXPIRED.value == "expired"


class TestToolReceipt:
    def _make_receipt(self, **overrides):
        defaults = {
            "receipt_id": "r-1",
            "tool_name": "calculator",
            "tool_version": "1.0.0",
            "provider_name": "math-service",
            "provider_id": "provider-1",
            "input_inline": {"expression": "2+2"},
            "output_inline": {"result": 4},
            "started_at": "2026-03-22T12:00:00Z",
        }
        defaults.update(overrides)
        return ToolReceipt(**defaults)

    def test_fields_set_correctly(self):
        tr = self._make_receipt(signature="sig123")
        assert tr.receipt_id == "r-1"
        assert tr.tool_name == "calculator"
        assert tr.tool_version == "1.0.0"
        assert tr.provider_name == "math-service"
        assert tr.provider_id == "provider-1"
        assert tr.protocol_family == "local_python"
        assert tr.started_at == "2026-03-22T12:00:00Z"
        assert tr.status == "succeeded"
        assert tr.side_effect_class == SideEffectClass.NONE
        assert tr.nondeterminism_class == NondeterminismClass.DETERMINISTIC
        assert tr.input_inline == {"expression": "2+2"}
        assert tr.input_sha256.startswith("sha256:")
        assert tr.output_inline == {"result": 4}
        assert tr.output_sha256.startswith("sha256:")
        assert tr.replay_class == ReplayClass.STRONG
        assert tr.evidence_strength == EvidenceStrength.UNSIGNED
        assert tr.signature == "sig123"

    def test_auto_assigns_receipt_id(self):
        tr = ToolReceipt(
            receipt_id="", tool_name="t", provider_name="p", provider_id="pid",
            input_inline={}, output_inline={}, started_at="2026-01-01T00:00:00Z",
        )
        assert tr.receipt_id != ""
        assert len(tr.receipt_id) == 36  # UUID format

    def test_to_dict_from_dict_round_trip(self):
        original = self._make_receipt(signature="sig456")
        d = original.to_dict()
        reconstructed = ToolReceipt.from_dict(d)
        assert reconstructed.receipt_id == original.receipt_id
        assert reconstructed.tool_name == original.tool_name
        assert reconstructed.tool_version == original.tool_version
        assert reconstructed.provider_name == original.provider_name
        assert reconstructed.provider_id == original.provider_id
        assert reconstructed.protocol_family == original.protocol_family
        assert reconstructed.started_at == original.started_at
        assert reconstructed.status == original.status
        assert reconstructed.side_effect_class == original.side_effect_class
        assert reconstructed.nondeterminism_class == original.nondeterminism_class
        assert reconstructed.input_inline == original.input_inline
        assert reconstructed.input_sha256 == original.input_sha256
        assert reconstructed.output_inline == original.output_inline
        assert reconstructed.output_sha256 == original.output_sha256
        assert reconstructed.replay_class == original.replay_class
        assert reconstructed.evidence_strength == original.evidence_strength
        assert reconstructed.signature == original.signature

    def test_make_input_hash_consistent(self):
        h1 = ToolReceipt.make_input_hash({"x": 1, "y": 2})
        h2 = ToolReceipt.make_input_hash({"y": 2, "x": 1})
        assert h1 == h2
        assert h1.startswith("sha256:")
        h3 = ToolReceipt.make_input_hash({"x": 99})
        assert h1 != h3

    def test_make_output_hash_consistent(self):
        h1 = ToolReceipt.make_output_hash({"result": 42})
        h2 = ToolReceipt.make_output_hash({"result": 42})
        assert h1 == h2
        assert h1.startswith("sha256:")
        h3 = ToolReceipt.make_output_hash({"result": 99})
        assert h1 != h3

    def test_to_dict_omits_signature_when_none(self):
        tr = self._make_receipt()
        d = tr.to_dict()
        assert "signature" not in d

    def test_to_dict_includes_signature_when_set(self):
        tr = self._make_receipt(signature="jws-token")
        d = tr.to_dict()
        assert d["signature"] == "jws-token"


class TestEvidenceEnums:
    def test_evidence_strength_values(self):
        assert EvidenceStrength.UNSIGNED.value == "unsigned"
        assert EvidenceStrength.CALLER_SIGNED.value == "caller_signed"
        assert EvidenceStrength.PROVIDER_SIGNED.value == "provider_signed"
        assert EvidenceStrength.DUAL_SIGNED.value == "dual_signed"

    def test_nondeterminism_class_values(self):
        assert NondeterminismClass.DETERMINISTIC.value == "deterministic"
        assert NondeterminismClass.TIME_DEPENDENT.value == "time_dependent"
        assert NondeterminismClass.RANDOMIZED.value == "randomized"
        assert NondeterminismClass.MODEL_BASED.value == "model_based"
        assert NondeterminismClass.ENVIRONMENT_DEPENDENT.value == "environment_dependent"

    def test_side_effect_class_values(self):
        assert SideEffectClass.NONE.value == "none"
        assert SideEffectClass.READ_ONLY.value == "read_only"
        assert SideEffectClass.EXTERNAL_WRITE.value == "external_write"
        assert SideEffectClass.IRREVERSIBLE.value == "irreversible"

    def test_replay_class_values(self):
        assert ReplayClass.NONE.value == "none"
        assert ReplayClass.WEAK.value == "weak"
        assert ReplayClass.STATEFUL.value == "stateful"
        assert ReplayClass.STRONG.value == "strong"
        assert ReplayClass.WITNESS_ONLY.value == "witness_only"
