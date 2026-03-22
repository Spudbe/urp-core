# urp/core.py

from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass, field
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


class SettlementOutcome(Enum):
    """Outcome of a claim settlement."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class EvidenceStrength(Enum):
    """How strongly a ToolReceipt is authenticated."""
    UNSIGNED = "unsigned"
    CALLER_SIGNED = "caller_signed"
    PROVIDER_SIGNED = "provider_signed"
    DUAL_SIGNED = "dual_signed"


class NondeterminismClass(Enum):
    """How reproducible a tool call's output is."""
    DETERMINISTIC = "deterministic"
    TIME_DEPENDENT = "time_dependent"
    RANDOMIZED = "randomized"
    MODEL_BASED = "model_based"
    ENVIRONMENT_DEPENDENT = "environment_dependent"


class SideEffectClass(Enum):
    """What external effects a tool call has."""
    NONE = "none"
    READ_ONLY = "read_only"
    EXTERNAL_WRITE = "external_write"
    IRREVERSIBLE = "irreversible"


class ReplayClass(Enum):
    """How verifiable a tool call is by replay."""
    NONE = "none"
    WEAK = "weak"
    STATEFUL = "stateful"
    STRONG = "strong"
    WITNESS_ONLY = "witness_only"


class ClaimKind(Enum):
    """Routable verification category for claims."""
    FACTUAL_ASSERTION = "factual_assertion"
    TOOL_OUTPUT = "tool_output"
    CODE_VERIFICATION = "code_verification"
    DATA_INTEGRITY = "data_integrity"
    PROVENANCE_CHECK = "provenance_check"
    POLICY_COMPLIANCE = "policy_compliance"
    SAFETY_CHECK = "safety_check"


class EvidenceType(Enum):
    """Types of evidence a claim can carry."""
    PROOF_REFERENCE = "proof_reference"
    TOOL_RECEIPT = "tool_receipt"


@dataclass
class ToolReceipt:
    """A verifiable record of a tool call with strength and replay classification.

    Attributes:
        receipt_id: UUID identifying this receipt, auto-assigned if not provided.
        tool_name: Name of the tool that was called.
        tool_version: Version string of the tool (default "unknown").
        provider_name: Human-readable name of the tool provider.
        provider_id: Identifier for the tool provider.
        protocol_family: Protocol used to invoke the tool (default "local_python").
        started_at: ISO 8601 UTC timestamp of when the tool was called.
        status: Outcome of the tool call (default "succeeded").
        side_effect_class: What external effects the tool call has.
        nondeterminism_class: How reproducible the output is.
        input_inline: The inputs passed to the tool, JSON-serialisable.
        input_sha256: SHA-256 hash of canonical JSON of inputs.
        output_inline: The output returned by the tool, JSON-serialisable.
        output_sha256: SHA-256 hash of canonical JSON of output.
        replay_class: How verifiable the call is by replay.
        evidence_strength: How strongly the receipt is authenticated.
        signature: Optional JWS signature over the canonical receipt.
    """
    receipt_id: str
    tool_name: str
    provider_name: str
    provider_id: str
    input_inline: dict
    output_inline: dict
    started_at: str
    tool_version: str = "unknown"
    protocol_family: str = "local_python"
    status: str = "succeeded"
    side_effect_class: SideEffectClass = SideEffectClass.NONE
    nondeterminism_class: NondeterminismClass = NondeterminismClass.DETERMINISTIC
    input_sha256: str = ""
    output_sha256: str = ""
    replay_class: ReplayClass = ReplayClass.STRONG
    evidence_strength: EvidenceStrength = EvidenceStrength.UNSIGNED
    signature: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = str(uuid.uuid4())
        if not self.input_sha256:
            self.input_sha256 = ToolReceipt.make_input_hash(self.input_inline)
        if not self.output_sha256:
            self.output_sha256 = ToolReceipt.make_output_hash(self.output_inline)

    @classmethod
    def make_input_hash(cls, inputs: dict) -> str:
        """Return 'sha256:<hex>' hash of canonical JSON of inputs."""
        canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    @classmethod
    def make_output_hash(cls, output: dict) -> str:
        """Return 'sha256:<hex>' hash of canonical JSON of output."""
        canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict:
        d = {
            "receipt_id": self.receipt_id,
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "provider_name": self.provider_name,
            "provider_id": self.provider_id,
            "protocol_family": self.protocol_family,
            "started_at": self.started_at,
            "status": self.status,
            "side_effect_class": self.side_effect_class.value,
            "nondeterminism_class": self.nondeterminism_class.value,
            "input_inline": self.input_inline,
            "input_sha256": self.input_sha256,
            "output_inline": self.output_inline,
            "output_sha256": self.output_sha256,
            "replay_class": self.replay_class.value,
            "evidence_strength": self.evidence_strength.value,
        }
        if self.signature is not None:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ToolReceipt:
        return cls(
            receipt_id=data.get("receipt_id", ""),
            tool_name=data["tool_name"],
            tool_version=data.get("tool_version", "unknown"),
            provider_name=data["provider_name"],
            provider_id=data["provider_id"],
            protocol_family=data.get("protocol_family", "local_python"),
            started_at=data["started_at"],
            status=data.get("status", "succeeded"),
            side_effect_class=SideEffectClass(data.get("side_effect_class", "none")),
            nondeterminism_class=NondeterminismClass(data.get("nondeterminism_class", "deterministic")),
            input_inline=data["input_inline"],
            input_sha256=data.get("input_sha256", ""),
            output_inline=data["output_inline"],
            output_sha256=data.get("output_sha256", ""),
            replay_class=ReplayClass(data.get("replay_class", "strong")),
            evidence_strength=EvidenceStrength(data.get("evidence_strength", "unsigned")),
            signature=data.get("signature"),
        )


@dataclass
class ProofReference:
    """
    A pointer to an external proof artifact.
    Attributes:
        hash: A content hash of the proof (e.g. SHA-256).
        location: A URI where the proof is stored (e.g. IPFS link).
        summary: A human-readable summary of the proof.
    """
    hash: str
    location: str
    summary: str
    confidence_score: Optional[float] = None

    def to_dict(self) -> dict:
        d = {
            "hash": self.hash,
            "location": self.location,
            "summary": self.summary,
        }
        if self.confidence_score is not None:
            d["confidence_score"] = self.confidence_score
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ProofReference:
        return cls(
            hash=data["hash"],
            location=data["location"],
            summary=data["summary"],
            confidence_score=data.get("confidence_score"),
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
        evidence: A list of ToolReceipt objects backing this claim.
    """
    id: str
    statement: str
    type: ClaimType
    proof_ref: ProofReference
    stake: Stake
    evidence: list[ToolReceipt] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "type": self.type.value,
            "proof_ref": self.proof_ref.to_dict(),
            "stake": self.stake.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Claim:
        return cls(
            id=data["id"],
            statement=data["statement"],
            type=ClaimType(data["type"]),
            proof_ref=ProofReference.from_dict(data["proof_ref"]),
            stake=Stake.from_dict(data["stake"]),
            evidence=[ToolReceipt.from_dict(e) for e in data.get("evidence", [])],
        )


@dataclass
class Response:
    """
    A URP response to a claim.
    Attributes:
        claim_id: The UUID of the Claim being responded to.
        decision: One of Decision.{ACCEPT, CHALLENGE, REJECT}.
        proof_ref: Optional ProofReference for the response.
        stake: Optional Stake for a challenge or counter-stake.
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


@dataclass
class SettlementMessage:
    """A first-class protocol message recording the outcome of a claim settlement.

    Attributes:
        settlement_id: UUID identifying this settlement, auto-assigned if empty.
        claim_id: The claim this settlement resolves.
        outcome: The settlement outcome (accepted, rejected, or expired).
        researcher_delta: Change in researcher balance (positive = gained, negative = lost).
        challenger_delta: Change in challenger balance (positive = gained, negative = lost).
        timestamp: ISO 8601 UTC timestamp of when settlement occurred.
        notes: Optional human-readable summary of why this outcome was reached.
    """
    settlement_id: str
    claim_id: str
    outcome: SettlementOutcome
    researcher_delta: float
    challenger_delta: float
    timestamp: str
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.settlement_id:
            self.settlement_id = str(uuid.uuid4())

    def to_dict(self) -> dict:
        d = {
            "settlement_id": self.settlement_id,
            "claim_id": self.claim_id,
            "outcome": self.outcome.value,
            "researcher_delta": self.researcher_delta,
            "challenger_delta": self.challenger_delta,
            "timestamp": self.timestamp,
        }
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SettlementMessage:
        return cls(
            settlement_id=data.get("settlement_id", ""),
            claim_id=data["claim_id"],
            outcome=SettlementOutcome(data["outcome"]),
            researcher_delta=data["researcher_delta"],
            challenger_delta=data["challenger_delta"],
            timestamp=data["timestamp"],
            notes=data.get("notes"),
        )


@dataclass
class AgentIdentity:
    """Identity of a URP agent.

    Attributes:
        id: Unique identifier for the agent.
        name: Human-readable name.
        version: Agent software version string.
    """
    id: str
    name: str
    version: str

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "version": self.version}

    @classmethod
    def from_dict(cls, data: dict) -> AgentIdentity:
        return cls(id=data["id"], name=data["name"], version=data["version"])


@dataclass
class StakePolicy:
    """Stake requirements for claims sent to this agent.

    Attributes:
        required: Whether a stake must be attached.
        minimum_amount: Minimum stake amount accepted.
        currency: Currency unit for stakes.
    """
    required: bool = False
    minimum_amount: float = 0.0
    currency: str = "credits"

    def to_dict(self) -> dict:
        return {
            "required": self.required,
            "minimum_amount": self.minimum_amount,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: dict) -> StakePolicy:
        return cls(
            required=data.get("required", False),
            minimum_amount=data.get("minimum_amount", 0.0),
            currency=data.get("currency", "credits"),
        )


@dataclass
class JWSSignature:
    """A JWS signature block.

    Attributes:
        protected: Base64url-encoded protected header.
        signature: Base64url-encoded signature value.
        header: Optional unprotected header parameters.
    """
    protected: str
    signature: str
    header: Optional[dict] = None

    def to_dict(self) -> dict:
        d: dict = {"protected": self.protected, "signature": self.signature}
        if self.header is not None:
            d["header"] = self.header
        return d

    @classmethod
    def from_dict(cls, data: dict) -> JWSSignature:
        return cls(
            protected=data["protected"],
            signature=data["signature"],
            header=data.get("header"),
        )


@dataclass
class AgentCapability:
    """Preflight declaration of what an agent can verify.

    Used for routing claims to capable agents before submission. Not part of
    claim settlement — this is a discovery/preflight mechanism.

    Attributes:
        protocol_version: URP protocol version this declaration targets.
        agent: Identity of the declaring agent.
        supported_claim_types: ClaimType values this agent handles (assertion, request).
        supported_claim_kinds: ClaimKind values this agent can verify.
        accepted_evidence_types: EvidenceType values this agent accepts.
        minimum_evidence_strength: Weakest EvidenceStrength this agent will consider.
        stake_policy: Stake requirements for incoming claims.
        compatible_protocol_versions: Protocol versions this agent supports.
        expires_at: Optional ISO 8601 expiry timestamp for this declaration.
        refresh_url: Optional URL to fetch an updated declaration.
        signatures: Optional list of JWS signatures over this declaration.
        metadata: Optional provider-specific metadata.
    """
    protocol_version: str
    agent: AgentIdentity
    supported_claim_types: list[ClaimType]
    supported_claim_kinds: list[ClaimKind]
    accepted_evidence_types: list[EvidenceType]
    minimum_evidence_strength: EvidenceStrength
    stake_policy: StakePolicy
    compatible_protocol_versions: list[str]
    expires_at: Optional[str] = None
    refresh_url: Optional[str] = None
    signatures: Optional[list[JWSSignature]] = None
    metadata: Optional[dict] = None

    def __post_init__(self) -> None:
        if not self.supported_claim_types:
            raise ValueError("supported_claim_types must not be empty")
        if not self.supported_claim_kinds:
            raise ValueError("supported_claim_kinds must not be empty")
        if not self.accepted_evidence_types:
            raise ValueError("accepted_evidence_types must not be empty")
        if not self.compatible_protocol_versions:
            raise ValueError("compatible_protocol_versions must not be empty")

    def to_dict(self) -> dict:
        d: dict = {
            "protocol_version": self.protocol_version,
            "agent": self.agent.to_dict(),
            "supported_claim_types": [t.value for t in self.supported_claim_types],
            "supported_claim_kinds": [k.value for k in self.supported_claim_kinds],
            "accepted_evidence_types": [e.value for e in self.accepted_evidence_types],
            "minimum_evidence_strength": self.minimum_evidence_strength.value,
            "stake_policy": self.stake_policy.to_dict(),
            "compatible_protocol_versions": self.compatible_protocol_versions,
        }
        if self.expires_at is not None:
            d["expires_at"] = self.expires_at
        if self.refresh_url is not None:
            d["refresh_url"] = self.refresh_url
        if self.signatures is not None:
            d["signatures"] = [s.to_dict() for s in self.signatures]
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d

    @classmethod
    def from_dict(cls, data: dict) -> AgentCapability:
        return cls(
            protocol_version=data["protocol_version"],
            agent=AgentIdentity.from_dict(data["agent"]),
            supported_claim_types=[ClaimType(v) for v in data["supported_claim_types"]],
            supported_claim_kinds=[ClaimKind(v) for v in data["supported_claim_kinds"]],
            accepted_evidence_types=[EvidenceType(v) for v in data["accepted_evidence_types"]],
            minimum_evidence_strength=EvidenceStrength(data["minimum_evidence_strength"]),
            stake_policy=StakePolicy.from_dict(data["stake_policy"]),
            compatible_protocol_versions=data["compatible_protocol_versions"],
            expires_at=data.get("expires_at"),
            refresh_url=data.get("refresh_url"),
            signatures=[JWSSignature.from_dict(s) for s in data["signatures"]] if data.get("signatures") else None,
            metadata=data.get("metadata"),
        )
