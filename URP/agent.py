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
import random

from .core import Claim, ClaimType, Response, Decision, ProofReference, Stake


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
        # For the initial prototype, simply echo the query as the statement.
        # In a real implementation, this agent would research the query,
        # assemble evidence and provide a proof reference.
        claim_id = str(uuid.uuid4())
        proof = ProofReference(hash="dummyhash", location="ipfs://dummy", summary="Mock proof")
        stake = Stake(amount=0.1)  # place a small stake
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
        # Simple heuristic: randomly accept or reject with equal probability if challenged
        # Otherwise, echo the accept decision
        # In practice, the verifier would inspect the proof and decide deterministically
        if claim.proof_ref and claim.stake.amount > 0:
            # Simulate verification: 80% chance to accept
            decision = Decision.ACCEPT if random.random() < 0.8 else Decision.REJECT
        else:
            decision = Decision.REJECT
        return Response(
            claim_id=claim.id,
            decision=decision,
            proof_ref=None,
            stake=None,
        )
