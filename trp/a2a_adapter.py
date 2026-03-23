"""A2A adapter for TRP AgentCapability ↔ A2A AgentCard translation.

Provides schema-to-schema translation between TRP's ``AgentCapability``
discovery primitive and A2A's ``AgentCard`` format. No network fetches,
no verification side effects — pure data mapping.

The adapter embeds the full TRP AgentCapability as an A2A extension
(``urn:trp:agent-capability``) to guarantee lossless round-trips.
A2A skills are generated from TRP ClaimKinds for human discoverability.

Key design decisions:
- TRP-specific fields (stake policy, evidence constraints) live in
  A2A extension params, not shoehorned into A2A native fields.
- Round-trip is lossless when the TRP extension is present.
- Without the TRP extension, A2A→TRP conversion is best-effort from
  skill tags.
- Signing is NOT bridged — A2A uses RFC 8785 JCS, TRP uses sorted-key
  compact JSON. Signatures are kept separate.

Typical usage::

    from trp.a2a_adapter import trp_capability_to_a2a_card, a2a_card_to_trp_capability

    card = trp_capability_to_a2a_card(capability)
    # Serve card at /.well-known/agent-card.json

    capability = a2a_card_to_trp_capability(card)
    # Use for TRP claim routing
"""

from __future__ import annotations

from typing import Any, Optional

from trp.core import (
    AgentCapability,
    AgentIdentity,
    ClaimKind,
    ClaimType,
    EvidenceStrength,
    EvidenceType,
    StakePolicy,
)

# The A2A extension URI for embedded TRP capability.
TRP_EXTENSION_URI = "urn:trp:agent-capability"

# Human-readable descriptions for ClaimKind values.
_CLAIM_KIND_DESCRIPTIONS: dict[str, str] = {
    "tool_output": (
        "Evaluates TRP tool_output claims backed by ToolReceipts "
        "that can be replayed or hash-checked."
    ),
    "factual_assertion": (
        "Evaluates TRP factual_assertion claims using attached "
        "evidence (proof references and/or receipts)."
    ),
    "code_verification": (
        "Evaluates TRP code_verification claims for correctness "
        "of code outputs or test results."
    ),
    "data_integrity": (
        "Evaluates TRP data_integrity claims (format, completeness, "
        "consistency) using provided evidence."
    ),
    "provenance_check": (
        "Evaluates TRP provenance_check claims tracing data or "
        "artifact origins."
    ),
    "policy_compliance": (
        "Evaluates TRP policy_compliance claims against defined "
        "rules or regulations."
    ),
    "safety_check": (
        "Evaluates TRP safety_check claims for harmful content "
        "or unsafe outputs."
    ),
}


def trp_capability_to_a2a_card(
    capability: AgentCapability,
    *,
    base_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
) -> dict[str, Any]:
    """Translate a TRP AgentCapability into an A2A AgentCard dict.

    The full TRP capability is embedded as an A2A extension for lossless
    round-tripping. A2A skills are generated from TRP ClaimKinds.

    Args:
        capability: The TRP AgentCapability to translate.
        base_url: The agent's base URL for the A2A interface entry.
            Falls back to ``capability.metadata["live_url"]`` if present.
        documentation_url: Documentation URL for the card.
            Falls back to ``capability.metadata["source"]`` if present.

    Returns:
        A dict shaped as an A2A AgentCard, ready to serve as JSON.
    """
    meta = capability.metadata or {}

    # Resolve URLs from metadata if not explicitly provided
    if base_url is None:
        base_url = meta.get("live_url", "https://localhost")
    if documentation_url is None:
        documentation_url = meta.get("source")

    # Build description from TRP fields
    kinds_str = ", ".join(k.value for k in capability.supported_claim_kinds)
    evidence_str = ", ".join(e.value for e in capability.accepted_evidence_types)
    stake = capability.stake_policy
    description = (
        f"TRP verifier agent. Supports {kinds_str}. "
        f"Accepts {evidence_str}. "
    )
    if stake.required:
        description += (
            f"Requires stake >= {stake.minimum_amount} {stake.currency}; "
        )
    description += (
        f"minimum evidence strength: {capability.minimum_evidence_strength.value}."
    )

    # Build skills from ClaimKinds
    skills = []
    for kind in capability.supported_claim_kinds:
        # Build tags
        tags = ["trp", f"trp_claim_kind:{kind.value}"]
        for ct in capability.supported_claim_types:
            tags.append(f"trp_claim_type:{ct.value}")
        for et in capability.accepted_evidence_types:
            tags.append(f"trp_evidence:{et.value}")
        tags.append(
            f"trp_min_evidence_strength:{capability.minimum_evidence_strength.value}"
        )
        if stake.required:
            tags.append("trp_stake_required:true")

        skill_desc = _CLAIM_KIND_DESCRIPTIONS.get(
            kind.value,
            f"Evaluates TRP {kind.value} claims.",
        )

        skills.append({
            "id": f"trp.verify.{kind.value}",
            "name": f"TRP {kind.value.replace('_', ' ').title()} Verification",
            "description": skill_desc,
            "tags": tags,
        })

    # Build the A2A card
    card: dict[str, Any] = {
        "name": capability.agent.name,
        "description": description,
        "version": capability.agent.version,
        "supportedInterfaces": [
            {
                "url": base_url,
                "protocolBinding": "TRP",
                "protocolVersion": capability.protocol_version,
            }
        ],
        "capabilities": {
            "extensions": [
                {
                    "uri": TRP_EXTENSION_URI,
                    "description": (
                        "Embeds TRP AgentCapability for TRP-aware A2A routing."
                    ),
                    "required": False,
                    "params": {
                        "trpCapabilityUrl": "/.well-known/trp-capability.json",
                        "trpCapabilityInline": capability.to_dict(),
                        "trpAgentId": capability.agent.id,
                    },
                }
            ]
        },
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": skills,
    }

    if documentation_url:
        card["documentationUrl"] = documentation_url

    return card


def a2a_card_to_trp_capability(card: dict[str, Any]) -> Optional[AgentCapability]:
    """Extract a TRP AgentCapability from an A2A AgentCard dict.

    Preferred path: find the TRP extension and parse the inline capability.
    Fallback: attempt best-effort reconstruction from A2A skills and tags.

    Args:
        card: An A2A AgentCard dict.

    Returns:
        An AgentCapability if one could be extracted, or None if the card
        has no TRP extension and insufficient data for reconstruction.
    """
    # Try the lossless path first: TRP extension with inline capability
    extensions = (
        card.get("capabilities", {}).get("extensions", [])
    )
    for ext in extensions:
        if ext.get("uri") == TRP_EXTENSION_URI:
            params = ext.get("params", {})
            inline = params.get("trpCapabilityInline")
            if inline is not None:
                return AgentCapability.from_dict(inline)

    # Fallback: reconstruct from A2A fields (lossy)
    return _reconstruct_from_a2a(card)


def _reconstruct_from_a2a(card: dict[str, Any]) -> Optional[AgentCapability]:
    """Best-effort reconstruction of AgentCapability from A2A native fields.

    This is lossy — stake policy, evidence constraints, and protocol
    versions cannot be inferred from A2A fields alone.

    Returns None if insufficient data exists.
    """
    skills = card.get("skills", [])
    if not skills:
        return None

    # Extract ClaimKinds from skill tags
    claim_kinds: list[ClaimKind] = []
    claim_types: list[ClaimType] = []
    evidence_types: list[EvidenceType] = []

    for skill in skills:
        tags = skill.get("tags", [])
        for tag in tags:
            if tag.startswith("trp_claim_kind:"):
                value = tag.split(":", 1)[1]
                try:
                    claim_kinds.append(ClaimKind(value))
                except ValueError:
                    pass
            elif tag.startswith("trp_claim_type:"):
                value = tag.split(":", 1)[1]
                try:
                    ct = ClaimType(value)
                    if ct not in claim_types:
                        claim_types.append(ct)
                except ValueError:
                    pass
            elif tag.startswith("trp_evidence:"):
                value = tag.split(":", 1)[1]
                try:
                    et = EvidenceType(value)
                    if et not in evidence_types:
                        evidence_types.append(et)
                except ValueError:
                    pass

    # Need at least claim kinds to build a capability
    if not claim_kinds:
        return None

    # Defaults for fields we can't infer
    if not claim_types:
        claim_types = [ClaimType.ASSERTION]
    if not evidence_types:
        evidence_types = [EvidenceType.TOOL_RECEIPT]

    # Extract identity
    name = card.get("name", "Unknown Agent")
    version = card.get("version", "unknown")

    # Try to get agent ID from interface URL
    interfaces = card.get("supportedInterfaces", [])
    agent_id = "unknown"
    if interfaces:
        url = interfaces[0].get("url", "")
        if url:
            agent_id = url.split("//")[-1].split("/")[0]

    # Extract protocol version from TRP interface if present
    protocol_version = "0.3.0"
    for iface in interfaces:
        if iface.get("protocolBinding") == "TRP":
            protocol_version = iface.get("protocolVersion", "0.3.0")
            break

    return AgentCapability(
        protocol_version=protocol_version,
        agent=AgentIdentity(id=agent_id, name=name, version=version),
        supported_claim_types=claim_types,
        supported_claim_kinds=claim_kinds,
        accepted_evidence_types=evidence_types,
        minimum_evidence_strength=EvidenceStrength.UNSIGNED,
        stake_policy=StakePolicy(),  # defaults — can't infer from A2A
        compatible_protocol_versions=[protocol_version],
    )


def merge_discovery(
    trp_capability: AgentCapability,
    a2a_card: dict[str, Any],
) -> dict[str, Any]:
    """Merge a TRP AgentCapability into an existing A2A AgentCard.

    Adds or replaces the TRP extension in the card's capabilities,
    and updates skills to reflect TRP claim kinds.

    Args:
        trp_capability: The TRP capability to embed.
        a2a_card: An existing A2A AgentCard dict.

    Returns:
        A new A2A AgentCard dict with the TRP extension merged.
    """
    # Deep copy to avoid mutating the input
    import copy
    merged = copy.deepcopy(a2a_card)

    # Build the TRP extension
    trp_ext = {
        "uri": TRP_EXTENSION_URI,
        "description": "Embeds TRP AgentCapability for TRP-aware A2A routing.",
        "required": False,
        "params": {
            "trpCapabilityUrl": "/.well-known/trp-capability.json",
            "trpCapabilityInline": trp_capability.to_dict(),
            "trpAgentId": trp_capability.agent.id,
        },
    }

    # Replace or add the TRP extension
    caps = merged.setdefault("capabilities", {})
    extensions = caps.setdefault("extensions", [])
    replaced = False
    for i, ext in enumerate(extensions):
        if ext.get("uri") == TRP_EXTENSION_URI:
            extensions[i] = trp_ext
            replaced = True
            break
    if not replaced:
        extensions.append(trp_ext)

    return merged
