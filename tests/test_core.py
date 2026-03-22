import pytest
from urp.core import (
    ProofReference, Stake, Claim, ClaimType, Decision, ToolReceipt,
    EvidenceStrength, NondeterminismClass, SideEffectClass, ReplayClass,
    SettlementMessage, SettlementOutcome,
    ClaimKind, EvidenceType, AgentIdentity, StakePolicy, JWSSignature, AgentCapability,
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


class TestSettlementOutcome:
    def test_enum_values(self):
        assert SettlementOutcome.ACCEPTED.value == "accepted"
        assert SettlementOutcome.REJECTED.value == "rejected"
        assert SettlementOutcome.EXPIRED.value == "expired"


class TestSettlementMessage:
    def _make_settlement(self, **overrides):
        defaults = {
            "settlement_id": "s-1",
            "claim_id": "c-1",
            "outcome": SettlementOutcome.ACCEPTED,
            "researcher_delta": 0.5,
            "challenger_delta": -0.3,
            "timestamp": "2026-03-22T13:00:00Z",
        }
        defaults.update(overrides)
        return SettlementMessage(**defaults)

    def test_fields_set_correctly(self):
        sm = self._make_settlement(notes="Claim verified by replay")
        assert sm.settlement_id == "s-1"
        assert sm.claim_id == "c-1"
        assert sm.outcome == SettlementOutcome.ACCEPTED
        assert sm.researcher_delta == 0.5
        assert sm.challenger_delta == -0.3
        assert sm.timestamp == "2026-03-22T13:00:00Z"
        assert sm.notes == "Claim verified by replay"

    def test_to_dict_from_dict_round_trip(self):
        original = self._make_settlement(notes="Round trip test")
        d = original.to_dict()
        reconstructed = SettlementMessage.from_dict(d)
        assert reconstructed.settlement_id == original.settlement_id
        assert reconstructed.claim_id == original.claim_id
        assert reconstructed.outcome == original.outcome
        assert reconstructed.researcher_delta == original.researcher_delta
        assert reconstructed.challenger_delta == original.challenger_delta
        assert reconstructed.timestamp == original.timestamp
        assert reconstructed.notes == original.notes

    def test_auto_assigns_uuid(self):
        sm = SettlementMessage(
            settlement_id="", claim_id="c-1",
            outcome=SettlementOutcome.REJECTED,
            researcher_delta=-0.5, challenger_delta=0.8,
            timestamp="2026-03-22T13:00:00Z",
        )
        assert sm.settlement_id != ""
        assert len(sm.settlement_id) == 36  # UUID format

    def test_to_dict_omits_notes_when_none(self):
        sm = self._make_settlement()
        d = sm.to_dict()
        assert "notes" not in d

    def test_to_dict_includes_notes_when_set(self):
        sm = self._make_settlement(notes="Challenger won")
        d = sm.to_dict()
        assert d["notes"] == "Challenger won"


class TestClaimKindEnum:
    def test_all_values(self):
        assert ClaimKind.FACTUAL_ASSERTION.value == "factual_assertion"
        assert ClaimKind.TOOL_OUTPUT.value == "tool_output"
        assert ClaimKind.CODE_VERIFICATION.value == "code_verification"
        assert ClaimKind.DATA_INTEGRITY.value == "data_integrity"
        assert ClaimKind.PROVENANCE_CHECK.value == "provenance_check"
        assert ClaimKind.POLICY_COMPLIANCE.value == "policy_compliance"
        assert ClaimKind.SAFETY_CHECK.value == "safety_check"


class TestEvidenceTypeEnum:
    def test_all_values(self):
        assert EvidenceType.PROOF_REFERENCE.value == "proof_reference"
        assert EvidenceType.TOOL_RECEIPT.value == "tool_receipt"


class TestStakePolicy:
    def test_defaults(self):
        sp = StakePolicy()
        assert sp.required is False
        assert sp.minimum_amount == 0.0
        assert sp.currency == "credits"


class TestJWSSignature:
    def test_minimal(self):
        sig = JWSSignature(protected="eyJ0eXAiOiJKV1MifQ", signature="abc123")
        assert sig.protected == "eyJ0eXAiOiJKV1MifQ"
        assert sig.signature == "abc123"
        assert sig.header is None
        d = sig.to_dict()
        assert "header" not in d


def _make_capability(**overrides) -> AgentCapability:
    defaults = {
        "protocol_version": "0.3.0",
        "agent": AgentIdentity(id="a-1", name="TestAgent", version="1.0"),
        "supported_claim_types": [ClaimType.ASSERTION],
        "supported_claim_kinds": [ClaimKind.FACTUAL_ASSERTION],
        "accepted_evidence_types": [EvidenceType.TOOL_RECEIPT],
        "minimum_evidence_strength": EvidenceStrength.UNSIGNED,
        "stake_policy": StakePolicy(),
        "compatible_protocol_versions": ["0.3.0"],
    }
    defaults.update(overrides)
    return AgentCapability(**defaults)


class TestAgentCapability:
    def test_minimal_valid(self):
        cap = _make_capability()
        assert cap.protocol_version == "0.3.0"
        assert cap.agent.name == "TestAgent"
        assert cap.supported_claim_kinds == [ClaimKind.FACTUAL_ASSERTION]
        d = cap.to_dict()
        reconstructed = AgentCapability.from_dict(d)
        assert reconstructed.agent.id == "a-1"
        assert reconstructed.supported_claim_types == [ClaimType.ASSERTION]

    def test_with_optional_fields(self):
        cap = _make_capability(
            expires_at="2026-12-31T23:59:59Z",
            refresh_url="https://example.com/refresh",
            metadata={"region": "eu-west-1"},
        )
        d = cap.to_dict()
        assert d["expires_at"] == "2026-12-31T23:59:59Z"
        assert d["refresh_url"] == "https://example.com/refresh"
        assert d["metadata"]["region"] == "eu-west-1"
        reconstructed = AgentCapability.from_dict(d)
        assert reconstructed.expires_at == "2026-12-31T23:59:59Z"
        assert reconstructed.metadata == {"region": "eu-west-1"}

    def test_rejects_empty_supported_claim_types(self):
        with pytest.raises(ValueError, match="supported_claim_types"):
            _make_capability(supported_claim_types=[])

    def test_rejects_empty_supported_claim_kinds(self):
        with pytest.raises(ValueError, match="supported_claim_kinds"):
            _make_capability(supported_claim_kinds=[])

    def test_rejects_empty_accepted_evidence_types(self):
        with pytest.raises(ValueError, match="accepted_evidence_types"):
            _make_capability(accepted_evidence_types=[])

    def test_rejects_empty_compatible_protocol_versions(self):
        with pytest.raises(ValueError, match="compatible_protocol_versions"):
            _make_capability(compatible_protocol_versions=[])
