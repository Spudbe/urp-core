# urp/core.py

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ClaimType(Enum):
    """Type of a URP claim."""
    ASSERTION = "assertion"
    REQUEST = "request"


class Decision(Enum):
    """Possible decisions on a claim."""
    ACCEPT = "accept"
    CHALLENGE = "challenge"
    REJECT = "reject"
    EXPIRED = "expired"


@dataclass
class ToolReceipt:
    """A verifiable record of a tool call, suitable for replay verification.

    Attributes:
        tool_name: Name of the tool that was called.
        tool_version: Version string of the tool (use "unknown" if not available).
        inputs: The inputs passed to the tool, must be JSON-serialisable.
        output: The output returned by the tool, must be JSON-serialisable.
        timestamp: ISO 8601 UTC timestamp of when the tool was called.
        signature: Optional JWS signature over the canonical receipt.
        replay_hash: SHA-256 hash of (tool_name + tool_version + canonical JSON of inputs).
    """
    tool_name: str
    tool_version: str
    inputs: dict
    output: dict
    timestamp: str
    signature: Optional[str] = None
    replay_hash: str = ""

    def __post_init__(self) -> None:
        if not self.replay_hash:
            self.replay_hash = ToolReceipt.make_replay_hash(
                self.tool_name, self.tool_version, self.inputs
            )

    @classmethod
    def make_replay_hash(cls, tool_name: str, tool_version: str, inputs: dict) -> str:
        """Compute a deterministic SHA-256 hash for replay verification."""
        canonical = tool_name + tool_version + json.dumps(inputs, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = {
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "inputs": self.inputs,
            "output": self.output,
            "timestamp": self.timestamp,
            "replay_hash": self.replay_hash,
        }
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ToolReceipt:
        return cls(
            tool_name=data["tool_name"],
            tool_version=data["tool_version"],
            inputs=data["inputs"],
            output=data["output"],
            timestamp=data["timestamp"],
            signature=data.get("signature"),
            replay_hash=data.get("replay_hash", ""),
        )


@dataclass
class ProofReference:
    """
    A pointer to an external proof artifact.
    Attributes:
        hash: A content hash of the proof (e.g. SHA‑256).
        location: A URI where the proof is stored (e.g. IPFS link).
        summary: A human‑readable summary of the proof.
    """
    hash: str
    location: str
    summary: str
    confidence_score: Optional[float] = None
    evidence: Optional[ToolReceipt] = None

    def to_dict(self) -> dict:
        d = {
            "hash": self.hash,
            "location": self.location,
            "summary": self.summary,
        }
        if self.confidence_score is not None:
            d["confidence_score"] = self.confidence_score
        if self.evidence is not None:
            d["evidence"] = self.evidence.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ProofReference:
        return cls(
            hash=data["hash"],
            location=data["location"],
            summary=data["summary"],
            confidence_score=data.get("confidence_score"),
            evidence=ToolReceipt.from_dict(data["evidence"]) if data.get("evidence") else None,
        )


@dataclass
class Stake:
    """
    A stake of URP Credits.
    Attributes:
        amount: Numeric amount staked.
        currency: Currency code (default 'URC').
        refundable: True if the stake is returned on success.
    """
    amount: float
    currency: str = "URC"
    refundable: bool = True

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "currency": self.currency,
            "refundable": self.refundable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Stake:
        return cls(
            amount=data["amount"],
            currency=data.get("currency", "URC"),
            refundable=data.get("refundable", True),
        )


@dataclass
class Claim:
    """
    A URP claim (assertion or request).
    Attributes:
        id: UUID string identifying this claim.
        statement: The content of the claim.
        type: One of ClaimType.
        proof_ref: A ProofReference pointing to supporting evidence.
        stake: A Stake used to back the claim.
    """
    id: str
    statement: str
    type: ClaimType
    proof_ref: ProofReference
    stake: Stake

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type.value,
            "proof_ref": self.proof_ref.to_dict(),
            "stake": self.stake.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Claim:
        return cls(
            id=data["id"],
            statement=data["statement"],
            type=ClaimType(data["type"]),
            proof_ref=ProofReference.from_dict(data["proof_ref"]),
            stake=Stake.from_dict(data["stake"]),
        )


@dataclass
class Response:
    """
    A URP response to a claim.
    Attributes:
        claim_id: The UUID of the Claim being responded to.
        decision: One of Decision.{ACCEPT, CHALLENGE, REJECT}.
        proof_ref: Optional ProofReference for the response.
        stake: Optional Stake for a challenge or counter‑stake.
    """
    claim_id: str
    decision: Decision
    proof_ref: Optional[ProofReference] = None
    stake: Optional[Stake] = None

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "decision": self.decision.value,
            "proof_ref": self.proof_ref.to_dict() if self.proof_ref else None,
            "stake": self.stake.to_dict() if self.stake else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Response:
        return cls(
            claim_id=data["claim_id"],
            decision=Decision(data["decision"]),
            proof_ref=ProofReference.from_dict(data["proof_ref"]) if data.get("proof_ref") else None,
            stake=Stake.from_dict(data["stake"]) if data.get("stake") else None,
        )
