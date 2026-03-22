"""MCP adapter for URP ToolReceipts.

Provides utilities to attach URP ToolReceipts to MCP CallToolResult responses
via the ``_meta`` field, and to extract them on the client side.

MCP's ``CallToolResult._meta`` is an arbitrary dict that clients are encouraged
to preserve through subsequent requests. URP uses it to carry a serialised
ToolReceipt alongside the tool's normal output, enabling downstream consumers
to verify the result by replay or signature without modifying MCP's core
message flow.

Typical server-side usage (wrapping a tool call)::

    from urp.mcp_adapter import wrap_mcp_tool_result

    # Your tool function
    output = compute_fibonacci({"n": 10})

    # Wrap into a dict shaped like CallToolResult with URP receipt in _meta
    result = wrap_mcp_tool_result(
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        inputs={"n": 10},
        output=output,
    )

Typical client-side usage (extracting receipt from a result)::

    from urp.mcp_adapter import extract_tool_receipt

    receipt = extract_tool_receipt(call_tool_result_meta)
    if receipt is not None:
        from urp.verify import ToolReceiptVerifier
        result = verifier.verify(receipt)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from urp.core import (
    EvidenceStrength,
    NondeterminismClass,
    ReplayClass,
    SideEffectClass,
    ToolReceipt,
)


# The key used in CallToolResult._meta to carry the URP receipt.
URP_META_KEY = "urp:tool_receipt"


def wrap_tool_call(
    tool_name: str,
    tool_version: str,
    inputs: dict,
    output: dict,
    *,
    nondeterminism: str = "deterministic",
    side_effects: str = "none",
    replay: str = "strong",
    strength: str = "unsigned",
    provider_name: str = "unknown",
    provider_id: str = "unknown",
    protocol_family: str = "local_python",
) -> ToolReceipt:
    """Create a ToolReceipt from a tool invocation.

    This is the "wrap any tool call" convenience function. It handles
    timestamping, UUID generation, hash computation, and enum validation
    so that MCP server authors can produce a ToolReceipt in one call.

    Args:
        tool_name: Name of the tool that was called.
        tool_version: Version string of the tool.
        inputs: The input dict passed to the tool.
        output: The output dict returned by the tool.
        nondeterminism: One of NondeterminismClass values.
        side_effects: One of SideEffectClass values.
        replay: One of ReplayClass values.
        strength: One of EvidenceStrength values.
        provider_name: Human-readable name of the tool provider.
        provider_id: Identifier for the tool provider.
        protocol_family: Protocol used to invoke the tool.

    Returns:
        A fully constructed ToolReceipt with computed hashes.

    Raises:
        ValueError: If any enum string is not a valid member.
    """
    # Validate enum values eagerly — fail fast with a clear message.
    try:
        nd_class = NondeterminismClass(nondeterminism)
    except ValueError:
        raise ValueError(
            f"Invalid nondeterminism value {nondeterminism!r}. "
            f"Valid: {[e.value for e in NondeterminismClass]}"
        )
    try:
        se_class = SideEffectClass(side_effects)
    except ValueError:
        raise ValueError(
            f"Invalid side_effects value {side_effects!r}. "
            f"Valid: {[e.value for e in SideEffectClass]}"
        )
    try:
        rp_class = ReplayClass(replay)
    except ValueError:
        raise ValueError(
            f"Invalid replay value {replay!r}. "
            f"Valid: {[e.value for e in ReplayClass]}"
        )
    try:
        ev_strength = EvidenceStrength(strength)
    except ValueError:
        raise ValueError(
            f"Invalid strength value {strength!r}. "
            f"Valid: {[e.value for e in EvidenceStrength]}"
        )

    return ToolReceipt(
        receipt_id=str(uuid.uuid4()),
        tool_name=tool_name,
        tool_version=tool_version,
        provider_name=provider_name,
        provider_id=provider_id,
        protocol_family=protocol_family,
        started_at=datetime.now(timezone.utc).isoformat(),
        nondeterminism_class=nd_class,
        side_effect_class=se_class,
        replay_class=rp_class,
        evidence_strength=ev_strength,
        input_inline=inputs,
        output_inline=output,
    )


def wrap_mcp_tool_result(
    tool_name: str,
    tool_version: str,
    inputs: dict,
    output: dict,
    *,
    text: Optional[str] = None,
    nondeterminism: str = "deterministic",
    side_effects: str = "none",
    replay: str = "strong",
    strength: str = "unsigned",
    provider_name: str = "unknown",
    provider_id: str = "unknown",
    protocol_family: str = "mcp",
) -> dict[str, Any]:
    """Create an MCP CallToolResult-shaped dict with a URP receipt in _meta.

    Returns a dict that can be used directly as a CallToolResult or passed
    to the MCP Python SDK's ``CallToolResult`` constructor. The receipt is
    serialised into ``_meta["urp:tool_receipt"]``.

    Args:
        tool_name: Name of the tool.
        tool_version: Version string of the tool.
        inputs: The inputs passed to the tool.
        output: The output returned by the tool.
        text: Optional text summary for the content block. If None, the
            output dict is JSON-serialised as the text content.
        nondeterminism: NondeterminismClass value string.
        side_effects: SideEffectClass value string.
        replay: ReplayClass value string.
        strength: EvidenceStrength value string.
        provider_name: Human-readable name of the tool provider.
        provider_id: Identifier for the tool provider.
        protocol_family: Protocol family (default "mcp").

    Returns:
        A dict shaped like MCP CallToolResult::

            {
                "content": [{"type": "text", "text": "..."}],
                "structuredContent": { ... },
                "_meta": {"urp:tool_receipt": { ... }},
                "isError": False,
            }
    """
    import json

    receipt = wrap_tool_call(
        tool_name=tool_name,
        tool_version=tool_version,
        inputs=inputs,
        output=output,
        nondeterminism=nondeterminism,
        side_effects=side_effects,
        replay=replay,
        strength=strength,
        provider_name=provider_name,
        provider_id=provider_id,
        protocol_family=protocol_family,
    )

    if text is None:
        text = json.dumps(output, sort_keys=True, indent=2)

    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": output,
        "_meta": {URP_META_KEY: receipt.to_dict()},
        "isError": False,
    }


def extract_tool_receipt(meta: Optional[dict]) -> Optional[ToolReceipt]:
    """Extract a URP ToolReceipt from MCP CallToolResult._meta.

    Args:
        meta: The ``_meta`` dict from a CallToolResult. May be None.

    Returns:
        A ToolReceipt if one was found under the ``urp:tool_receipt`` key,
        or None if the key is absent or meta is None.

    Raises:
        ValueError: If the receipt data is present but malformed.
    """
    if meta is None:
        return None
    receipt_data = meta.get(URP_META_KEY)
    if receipt_data is None:
        return None
    return ToolReceipt.from_dict(receipt_data)
