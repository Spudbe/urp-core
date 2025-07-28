"""Core data structures for the Universal Reasoning Protocol.

This module defines Python classes representing the main URP constructs:
* Claim
* ProofReference
* Stake
* Response
* SettlementInstruction

These classes are simple containers with minimal validation. In a production
system, they would enforce more constraints (e.g. valid hashes, non‑negative
stakes) and provide serialization to and from wire formats (JSON, protobuf,
etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ClaimType(str, Enum):
    """Enumeration of supported claim types."""

    ASSERTION = "assertion"
    REQUEST = "request"


class Decision(str, Enum):
    """Possible decisions returned in a Response."""

    ACCEPT = "accept"
    REJECT = "reject"
    CHALLENGE = "challenge"


@dataclass
class Stake:
    """Represents a quantity of URP credits staked on a claim or response."""

    amount: float
    currency: str = "URC"
    refundable: bool = True

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Stake amount must be non‑negative")


@dataclass
class ProofReference:
    """A pointer to a proof supporting a claim or response."""

    hash: str
    location: str
    summary: Optional[str] = None


@dataclass
class Claim:
    """A structured assertion or request in the URP network."""

    id: str
    statement: str
    type: ClaimType
    proof_ref: Optional[ProofReference] = None
    stake: Optional[Stake] = None

    def __post_init__(self) -> None:
        if self.stake is None:
            # Default to zero stake if not specified
            self.stake = Stake(amount=0.0)


@dataclass
class Response:
    """Result of evaluating a claim."""

    claim_id: str
    decision: Decision
    proof_ref: Optional[ProofReference] = None
    stake: Optional[Stake] = None

    def __post_init__(self) -> None:
        if self.decision == Decision.CHALLENGE and self.stake is None:
            raise ValueError("A challenge must include a stake")


@dataclass
class SettlementInstruction:
    """Instructions for transferring credits after a claim is resolved.

    This is a placeholder; in a real implementation, this would interface
    with a ledger or smart contract to actually move funds.
    """

    claimant: str
    responder: Optional[str]
    amount_to_claimant: float
    amount_to_responder: float
    currency: str = "URC"
