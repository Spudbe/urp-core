import pytest
from urp.core import ProofReference, Stake, Claim, ClaimType, Decision


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
