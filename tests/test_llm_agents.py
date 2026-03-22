"""Tests for urp.llm_agents and urp.llm adapters."""

import pytest
from unittest.mock import MagicMock

from urp.core import (
    Claim,
    ClaimType,
    Decision,
    NondeterminismClass,
    ProofReference,
    Stake,
)
from urp.llm import OllamaAdapter, OpenAIAdapter
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

    def test_confidence_score_parsed_from_llm(self):
        llm = _mock_llm("ANSWER: test\nREASONING: because\nCONFIDENCE: 0.9")
        researcher = ResearcherLLM("test-researcher", llm)
        claim = researcher.create_claim("test query")
        assert claim.proof_ref.confidence_score == 0.9

    def test_confidence_score_defaults_when_missing(self):
        llm = _mock_llm("ANSWER: test\nREASONING: because")
        researcher = ResearcherLLM("test-researcher", llm)
        claim = researcher.create_claim("test query")
        assert claim.proof_ref.confidence_score == 0.5

    def test_confidence_score_clamped_to_max(self):
        llm = _mock_llm("ANSWER: test\nREASONING: because\nCONFIDENCE: 1.5")
        researcher = ResearcherLLM("test-researcher", llm)
        claim = researcher.create_claim("test query")
        assert claim.proof_ref.confidence_score == 1.0

    def test_confidence_score_falls_back_on_invalid(self):
        llm = _mock_llm("ANSWER: test\nREASONING: because\nCONFIDENCE: not_a_number")
        researcher = ResearcherLLM("test-researcher", llm)
        claim = researcher.create_claim("test query")
        assert claim.proof_ref.confidence_score == 0.5


class TestOllamaAdapter:
    def test_raises_runtime_error_when_connection_fails(self):
        adapter = OllamaAdapter(model="llama3", host="http://127.0.0.1:1")
        with pytest.raises(RuntimeError, match="Could not connect to Ollama"):
            adapter.complete("system", "user")

    def test_default_host(self):
        adapter = OllamaAdapter()
        assert adapter.host == "http://localhost:11434"
        assert adapter.model == "llama3"

    def test_custom_host(self):
        adapter = OllamaAdapter(model="mistral", host="http://myhost:8080")
        assert adapter.host == "http://myhost:8080"
        assert adapter.model == "mistral"


class TestOpenAIAdapter:
    def test_raises_runtime_error_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable not set"):
            OpenAIAdapter()

    def test_default_model(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        adapter = OpenAIAdapter()
        assert adapter.model == "gpt-4o-mini"

    def test_custom_model_and_key(self):
        adapter = OpenAIAdapter(model="gpt-4o", api_key="sk-test")
        assert adapter.model == "gpt-4o"
