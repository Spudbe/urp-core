"""Tests for urp.llm_agents — LLM response parsing and agent behaviour."""

from unittest.mock import MagicMock

from urp.core import (
    Claim,
    ClaimType,
    Decision,
    NondeterminismClass,
    ProofReference,
    Stake,
)
from urp.llm_agents import ChallengerLLM, ResearcherLLM, VerifierLLM


def _mock_llm(response: str) -> MagicMock:
    """Create a mock LLMAdapter that returns a fixed response."""
    llm = MagicMock()
    llm.complete.return_value = response
    llm.model = "test-model"
    return llm


def _make_claim() -> Claim:
    """Create a minimal claim for testing evaluators."""
    return Claim(
        id="test-claim-1",
        statement="The sky is blue",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(hash="abc", location="test://loc", summary="It is blue"),
        stake=Stake(amount=0.5),
    )


class TestChallengerLLMParsing:
    def test_accept_decision(self):
        llm = _mock_llm("DECISION: accept\nREASON: looks good")
        challenger = ChallengerLLM("test-challenger", llm)
        resp, reason = challenger.evaluate_claim(_make_claim())
        assert resp.decision == Decision.ACCEPT
        assert reason == "looks good"
        assert resp.stake is None

    def test_challenge_decision(self):
        llm = _mock_llm("DECISION: challenge\nREASON: missing evidence")
        challenger = ChallengerLLM("test-challenger", llm)
        resp, reason = challenger.evaluate_claim(_make_claim())
        assert resp.decision == Decision.CHALLENGE
        assert reason == "missing evidence"
        assert resp.stake is not None
        assert resp.stake.amount == 0.3

    def test_malformed_output_defaults_to_challenge(self):
        llm = _mock_llm("I don't know what format you want")
        challenger = ChallengerLLM("test-challenger", llm)
        resp, reason = challenger.evaluate_claim(_make_claim())
        assert resp.decision == Decision.CHALLENGE
        assert reason == ""


class TestVerifierLLMParsing:
    def test_accept_decision(self):
        llm = _mock_llm("DECISION: accept\nREASON: verified")
        verifier = VerifierLLM("test-verifier", llm)
        resp, reason = verifier.evaluate_claim(_make_claim())
        assert resp.decision == Decision.ACCEPT
        assert reason == "verified"

    def test_reject_decision(self):
        llm = _mock_llm("DECISION: reject\nREASON: factually wrong")
        verifier = VerifierLLM("test-verifier", llm)
        resp, reason = verifier.evaluate_claim(_make_claim())
        assert resp.decision == Decision.REJECT
        assert reason == "factually wrong"

    def test_malformed_output_defaults_to_reject(self):
        llm = _mock_llm("Some garbage output with no structure")
        verifier = VerifierLLM("test-verifier", llm)
        resp, reason = verifier.evaluate_claim(_make_claim())
        assert resp.decision == Decision.REJECT
        assert reason == ""


class TestResearcherLLM:
    def test_creates_claim_with_tool_receipt(self):
        llm = _mock_llm("ANSWER: test answer\nREASONING: because reasons")
        researcher = ResearcherLLM("test-researcher", llm)
        claim = researcher.create_claim("What is 2+2?")

        assert claim.statement == "What is 2+2?"
        assert claim.proof_ref.summary == "test answer"
        assert claim.type == ClaimType.ASSERTION
        assert claim.stake.amount == 0.5

        # ToolReceipt should be attached
        assert len(claim.evidence) == 1
        receipt = claim.evidence[0]
        assert receipt.tool_name == "llm_reasoning"
        assert receipt.nondeterminism_class == NondeterminismClass.MODEL_BASED
        assert receipt.provider_id == "test-model"
        assert receipt.input_inline["user_prompt"] == "What is 2+2?"
        assert receipt.output_inline["answer"] == "test answer"
