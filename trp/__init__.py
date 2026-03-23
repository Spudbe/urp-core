"""TRP — Tool Receipt Protocol.

Verifiable tool call accountability for AI agents.
"""

__version__ = "0.6.0"

from trp.core import (
    Claim,
    ClaimKind,
    ClaimType,
    ToolReceipt,
    AgentCapability,
    SettlementMessage,
    EvidenceStrength,
    NondeterminismClass,
    SideEffectClass,
    ReplayClass,
)
from trp.structured_claim import (
    StructuredClaim,
    ToolOutputEquals,
    ValueComparison,
    Compound,
)
from trp.verify import ToolReceiptVerifier
from trp.claim_verifier import match_claim
from trp.message import TRPMessage
