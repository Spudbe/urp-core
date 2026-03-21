"""Agent base classes and simple implementations for URP.

This module defines an abstract `Agent` class with methods for sending and
receiving URP messages. Concrete agent classes (`ResearcherAgent`,
`ChallengerAgent`, `VerifierAgent`) extend `Agent` and implement specific
behaviours:

- `ResearcherAgent` creates claims based on input queries.
- `ChallengerAgent` inspects claims and raises challenges when a proof is
  missing or insufficient.
- `VerifierAgent` makes final decisions on claims based on simple heuristics.

These classes are intentionally naive; the goal is to provide a starting
point for experimentation rather than a sophisticated reasoning engine.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Optional

from .core import Claim, ClaimType, Response, Decision, ProofReference, Stake
from .knowledge_base import get_fact


class Agent(ABC):
    """Abstract base class for URP agents."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def create_claim(self, query: str) -> Claim:
        """Produce a claim based on an input query or task."""

    @abstractmethod
    def evaluate_claim(self, claim: Claim) -> Response:
        """Examine a claim and return a response (accept, reject, challenge)."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class ResearcherAgent(Agent):
    """Agent that formulates claims from queries."""

    def create_claim(self, query: str) -> Claim:
        """Create a claim from a query with an attached proof summary.

        If the knowledge base contains an answer, include it in the proof
        summary. Otherwise, state that the answer is unknown. In a real
        implementation, the proof reference would point to a verifiable
        reasoning trace.
        """
        claim_id = str(uuid.uuid4())
        answer = get_fact(query) or "unknown"
        proof_summary = answer
        proof = ProofReference(hash="dummyhash", location="ipfs://dummy", summary=proof_summary)
        stake = Stake(amount=0.1)
        return Claim(
            id=claim_id,
            statement=query,
            type=ClaimType.ASSERTION,
            proof_ref=proof,
            stake=stake,
        )

    def evaluate_claim(self, claim: Claim) -> Response:
        # Researcher does not evaluate others' claims in this simple prototype
        raise NotImplementedError


class ChallengerAgent(Agent):
    """Agent that challenges claims that lack sufficient proof."""

    def create_claim(self, query: str) -> Claim:
        # This agent does not create original claims
        raise NotImplementedError

    def evaluate_claim(self, claim: Claim) -> Response:
        # Challenge the claim if it lacks a proof reference or if the stake is too low
        if not claim.proof_ref or claim.stake.amount < 0.05:
            # Place a challenge stake
            challenge_stake = Stake(amount=0.1)
            return Response(
                claim_id=claim.id,
                decision=Decision.CHALLENGE,
                proof_ref=None,
                stake=challenge_stake,
            )
        else:
            # Accept without staking anything
            return Response(
                claim_id=claim.id,
                decision=Decision.ACCEPT,
                proof_ref=None,
                stake=None,
            )


class VerifierAgent(Agent):
    """Agent that makes final decisions on claims."""

    def create_claim(self, query: str) -> Claim:
        # Verifier does not create claims
        raise NotImplementedError

    def evaluate_claim(self, claim: Claim) -> Response:
        """Evaluate a claim by checking it against the knowledge base.

        If the claim's statement matches a known fact and the proof summary
        equals that fact, accept the claim. Otherwise, reject it. If the
        question is unknown in the knowledge base, default to reject.
        """
        expected_answer = get_fact(claim.statement)
        provided_answer = claim.proof_ref.summary if claim.proof_ref else None
        if expected_answer is None:
            # Unknown question
            decision = Decision.REJECT
        elif expected_answer == provided_answer:
            decision = Decision.ACCEPT
        else:
            decision = Decision.REJECT
        return Response(
            claim_id=claim.id,
            decision=decision,
            proof_ref=None,
            stake=None,
        )
