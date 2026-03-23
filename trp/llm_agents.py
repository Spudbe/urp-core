"""Shared LLM-backed agent classes for TRP simulations.

Provides ResearcherLLM, ChallengerLLM, and VerifierLLM — the three agent
roles in the TRP claim lifecycle. Each wraps an LLMAdapter and handles
prompt construction, response parsing, and protocol object creation.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from trp.core import (
    Claim,
    ClaimType,
    Decision,
    NondeterminismClass,
    ProofReference,
    ReplayClass,
    Response,
    SideEffectClass,
    Stake,
    ToolReceipt,
)
from trp.llm import LLMAdapter


class ResearcherLLM:
    """Agent that uses an LLM to generate a claim with reasoning.

    Args:
        name: Display name for this agent.
        llm: An LLMAdapter instance to use for completions.
    """

    def __init__(self, name: str, llm: LLMAdapter) -> None:
        self.name = name
        self.llm = llm

    def create_claim(self, query: str) -> Claim:
        """Generate a claim for the given query using the LLM.

        Prompts the LLM for an ANSWER and REASONING, builds a ProofReference
        from the answer, and attaches a ToolReceipt recording the LLM call
        to the claim's evidence list.

        Args:
            query: The question or statement to generate a claim for.

        Returns:
            A Claim with proof reference, stake, and a ToolReceipt in evidence.
        """
        system_prompt = (
            "You are a research agent in a verification protocol. "
            "Given a question or statement, provide a concise factual answer and a brief "
            "reasoning summary (2-3 sentences). You must always produce an answer, even if "
            "the statement is incorrect — state what you believe to be true. "
            "Reply in this exact format:\n"
            "ANSWER: <your answer>\n"
            "REASONING: <your reasoning>\n"
            "CONFIDENCE: <a number between 0.0 and 1.0 where 1.0 means certain and 0.0 means speculative>"
        )
        raw = self.llm.complete(system_prompt, query)

        answer = raw
        reasoning = raw
        confidence: float | None = None
        for line in raw.splitlines():
            if line.strip().upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, IndexError):
                    confidence = None

        if confidence is None:
            confidence = 0.5

        model_name = getattr(self.llm, "model", "unknown")

        proof_hash = hashlib.sha256(reasoning.encode()).hexdigest()
        proof = ProofReference(
            hash=proof_hash,
            location=f"llm://groq/{model_name}",
            summary=answer,
            confidence_score=confidence,
        )

        receipt = ToolReceipt(
            receipt_id="",
            tool_name="llm_reasoning",
            tool_version=model_name,
            provider_name="groq",
            provider_id=model_name,
            protocol_family="llm_chat_completion",
            started_at=datetime.now(timezone.utc).isoformat(),
            input_inline={"system_prompt": system_prompt, "user_prompt": query},
            output_inline={"answer": answer, "reasoning": reasoning},
            nondeterminism_class=NondeterminismClass.MODEL_BASED,
            replay_class=ReplayClass.WEAK,
            side_effect_class=SideEffectClass.NONE,
        )

        return Claim(
            id=str(uuid.uuid4()),
            statement=query,
            type=ClaimType.ASSERTION,
            proof_ref=proof,
            stake=Stake(amount=0.5),
            evidence=[receipt],
        )


class ChallengerLLM:
    """Agent that uses an LLM to evaluate a claim and decide accept or challenge.

    Args:
        name: Display name for this agent.
        llm: An LLMAdapter instance to use for completions.
    """

    def __init__(self, name: str, llm: LLMAdapter) -> None:
        self.name = name
        self.llm = llm

    def evaluate_claim(self, claim: Claim, sceptical: bool = False) -> tuple[Response, str]:
        """Evaluate a claim and return a decision with reasoning.

        Args:
            claim: The claim to evaluate.
            sceptical: If True, use an aggressive prompt that looks for flaws.

        Returns:
            A tuple of (Response, reason_string).
        """
        if sceptical:
            system_prompt = (
                "You are a highly sceptical challenger agent in a verification protocol. "
                "Your job is to find flaws, oversimplifications, or misleading aspects "
                "in the claim. Look for nuance that the claim ignores. Be critical. "
                "If there is ANY reason to doubt the claim, you MUST challenge it and "
                "provide a counter-argument. "
                "Reply in this exact format:\n"
                "DECISION: accept OR challenge\n"
                "REASON: <one sentence explanation>"
            )
        else:
            system_prompt = (
                "You are a challenger agent in a verification protocol. "
                "You are given a claim statement and the proof summary provided by the researcher. "
                "Evaluate whether the proof supports the claim. "
                "Reply in this exact format:\n"
                "DECISION: accept OR challenge\n"
                "REASON: <one sentence explanation>"
            )
        user_prompt = (
            f"Claim: {claim.statement}\n"
            f"Proof summary: {claim.proof_ref.summary}\n"
            f"Proof confidence: {claim.proof_ref.confidence_score}"
        )
        raw = self.llm.complete(system_prompt, user_prompt)

        decision = Decision.CHALLENGE
        reason = ""
        for line in raw.splitlines():
            if line.strip().upper().startswith("DECISION:"):
                value = line.split(":", 1)[1].strip().lower()
                if value == "accept":
                    decision = Decision.ACCEPT
                else:
                    decision = Decision.CHALLENGE
            elif line.strip().upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()

        challenge_stake = Stake(amount=0.3) if decision == Decision.CHALLENGE else None
        resp = Response(claim_id=claim.id, decision=decision, proof_ref=None, stake=challenge_stake)
        return resp, reason


class VerifierLLM:
    """Agent that uses an LLM to make a final decision on a claim.

    Args:
        name: Display name for this agent.
        llm: An LLMAdapter instance to use for completions.
    """

    def __init__(self, name: str, llm: LLMAdapter) -> None:
        self.name = name
        self.llm = llm

    def evaluate_claim(self, claim: Claim) -> tuple[Response, str]:
        """Evaluate a claim and return a final accept/reject decision with reasoning.

        Args:
            claim: The claim to verify.

        Returns:
            A tuple of (Response, reason_string).
        """
        system_prompt = (
            "You are a verifier agent in a verification protocol. "
            "You are given a claim and its proof summary. "
            "Determine whether the claim is factually correct based on the evidence. "
            "Reply in this exact format:\n"
            "DECISION: accept OR reject\n"
            "REASON: <one sentence explanation>"
        )
        user_prompt = (
            f"Claim: {claim.statement}\n"
            f"Proof summary: {claim.proof_ref.summary}\n"
            f"Proof hash: {claim.proof_ref.hash}\n"
            f"Proof confidence: {claim.proof_ref.confidence_score}"
        )
        raw = self.llm.complete(system_prompt, user_prompt)

        decision = Decision.REJECT
        reason = ""
        for line in raw.splitlines():
            if line.strip().upper().startswith("DECISION:"):
                value = line.split(":", 1)[1].strip().lower()
                if value == "accept":
                    decision = Decision.ACCEPT
                else:
                    decision = Decision.REJECT
            elif line.strip().upper().startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()

        resp = Response(claim_id=claim.id, decision=decision, proof_ref=None, stake=None)
        return resp, reason
