"""JWS signing utilities for TRP ToolReceipts and TRPMessage envelopes.

Provides Ed25519 key generation, detached JWS signing and verification,
and convenience functions for signing ToolReceipts and TRPMessage envelopes.

v0.4 scope:
- Ed25519 only (OKP key type)
- RFC 8785 JCS canonicalization for deterministic byte representation
- Detached JWS (payload not embedded in the token)
- Evidence strength auto-escalation for receipts

Deferred to future versions:
- DID-based identity and key resolution
- Timestamp authorities
- Zero-knowledge selective disclosure

Requires: jwcrypto >= 1.5.6

Typical usage::

    from trp.signing import generate_ed25519_keypair, sign_tool_receipt, verify_tool_receipt_signature

    priv, pub = generate_ed25519_keypair(kid="agent-1")
    signed = sign_tool_receipt(receipt, priv, signer_role="caller")
    is_valid = verify_tool_receipt_signature(signed, pub)
"""

from __future__ import annotations

import json
from typing import Optional

from jwcrypto import jwk, jws

from trp.canonical import canonical_bytes
from trp.core import EvidenceStrength, JWSSignature, ToolReceipt


def canonical_json_bytes(obj: dict) -> bytes:
    """RFC 8785 JCS canonical bytes for signing.

    Args:
        obj: The dict to serialise.

    Returns:
        UTF-8 encoded canonical JSON bytes.
    """
    return canonical_bytes(obj)


def generate_ed25519_keypair(kid: Optional[str] = None) -> tuple[jwk.JWK, jwk.JWK]:
    """Generate an Ed25519 key pair.

    Args:
        kid: Optional key ID to embed in the JWK. If None, no kid is set.

    Returns:
        A tuple of (private_jwk, public_jwk). The private key contains
        both private and public material. The public key contains only
        public material.
    """
    kwargs = {"kty": "OKP", "crv": "Ed25519"}
    if kid is not None:
        kwargs["kid"] = kid
    private_key = jwk.JWK.generate(**kwargs)
    public_key = jwk.JWK()
    public_key.import_key(**json.loads(private_key.export_public()))
    return private_key, public_key


def sign_detached(
    payload: bytes,
    private_jwk: jwk.JWK,
    kid: Optional[str] = None,
    typ: Optional[str] = None,
) -> JWSSignature:
    """Create a detached JWS signature over a payload.

    The payload is NOT embedded in the JWS token — only the protected
    header and signature are returned.

    Args:
        payload: The bytes to sign.
        private_jwk: An Ed25519 private JWK.
        kid: Optional key ID to include in the protected header.
        typ: Optional type header (e.g. "trp-receipt+jws").

    Returns:
        A JWSSignature with protected header and signature value.
    """
    protected = {"alg": "EdDSA"}
    if kid is not None:
        protected["kid"] = kid
    else:
        key_data = json.loads(private_jwk.export())
        if "kid" in key_data:
            protected["kid"] = key_data["kid"]
    if typ is not None:
        protected["typ"] = typ

    token = jws.JWS(payload)
    token.add_signature(
        private_jwk,
        alg="EdDSA",
        protected=json.dumps(protected),
    )
    serialization = json.loads(token.serialize())

    return JWSSignature(
        protected=serialization["protected"],
        signature=serialization["signature"],
    )


def verify_detached(
    payload: bytes,
    signature: JWSSignature,
    public_jwk: jwk.JWK,
) -> bool:
    """Verify a detached JWS signature.

    Args:
        payload: The original bytes that were signed.
        signature: The JWSSignature to verify.
        public_jwk: The Ed25519 public JWK.

    Returns:
        True if the signature is valid, False otherwise.
    """
    # Reconstruct the full JWS serialization with the payload
    token_dict = {
        "payload": jws.base64url_encode(payload),
        "protected": signature.protected,
        "signature": signature.signature,
    }
    try:
        token = jws.JWS()
        token.deserialize(json.dumps(token_dict))
        token.verify(public_jwk, alg="EdDSA")
        return True
    except (jws.InvalidJWSSignature, jws.InvalidJWSObject, Exception):
        return False


def _update_evidence_strength(
    current: EvidenceStrength,
    signer_role: str,
) -> EvidenceStrength:
    """Compute updated evidence strength after a signing operation.

    Rules:
    - UNSIGNED + caller → CALLER_SIGNED
    - UNSIGNED + provider → PROVIDER_SIGNED
    - CALLER_SIGNED + provider → DUAL_SIGNED
    - PROVIDER_SIGNED + caller → DUAL_SIGNED
    - Already DUAL_SIGNED → DUAL_SIGNED

    Args:
        current: The receipt's current evidence strength.
        signer_role: Either "caller" or "provider".

    Returns:
        The new evidence strength.

    Raises:
        ValueError: If signer_role is not "caller" or "provider".
    """
    if signer_role not in ("caller", "provider"):
        raise ValueError(
            f"signer_role must be 'caller' or 'provider', got {signer_role!r}"
        )

    if current == EvidenceStrength.DUAL_SIGNED:
        return EvidenceStrength.DUAL_SIGNED

    if signer_role == "caller":
        if current == EvidenceStrength.UNSIGNED:
            return EvidenceStrength.CALLER_SIGNED
        if current == EvidenceStrength.PROVIDER_SIGNED:
            return EvidenceStrength.DUAL_SIGNED
        return current  # already CALLER_SIGNED

    # signer_role == "provider"
    if current == EvidenceStrength.UNSIGNED:
        return EvidenceStrength.PROVIDER_SIGNED
    if current == EvidenceStrength.CALLER_SIGNED:
        return EvidenceStrength.DUAL_SIGNED
    return current  # already PROVIDER_SIGNED


def sign_tool_receipt(
    receipt: ToolReceipt,
    private_jwk: jwk.JWK,
    signer_role: str,
    kid: Optional[str] = None,
) -> ToolReceipt:
    """Sign a ToolReceipt and return a new receipt with updated signature.

    The canonical JSON of the receipt (excluding the signature field) is
    signed. The signature is stored as a compact JWS string in the
    receipt's ``signature`` field, and ``evidence_strength`` is updated.

    This is a pure function — the original receipt is not modified.

    Args:
        receipt: The ToolReceipt to sign.
        private_jwk: An Ed25519 private JWK.
        signer_role: Either "caller" or "provider".
        kid: Optional key ID override.

    Returns:
        A new ToolReceipt with signature and updated evidence_strength.
    """
    # Build signable dict (exclude signature field, use new evidence strength)
    new_strength = _update_evidence_strength(receipt.evidence_strength, signer_role)

    signable = receipt.to_dict()
    signable.pop("signature", None)
    signable["evidence_strength"] = new_strength.value
    payload = canonical_json_bytes(signable)

    sig = sign_detached(payload, private_jwk, kid=kid, typ="trp-receipt+jws")

    # Build a new receipt with the signature
    return ToolReceipt(
        receipt_id=receipt.receipt_id,
        tool_name=receipt.tool_name,
        tool_version=receipt.tool_version,
        provider_name=receipt.provider_name,
        provider_id=receipt.provider_id,
        protocol_family=receipt.protocol_family,
        started_at=receipt.started_at,
        status=receipt.status,
        side_effect_class=receipt.side_effect_class,
        nondeterminism_class=receipt.nondeterminism_class,
        input_inline=receipt.input_inline,
        input_sha256=receipt.input_sha256,
        output_inline=receipt.output_inline,
        output_sha256=receipt.output_sha256,
        replay_class=receipt.replay_class,
        evidence_strength=new_strength,
        signature=json.dumps(sig.to_dict()),
    )


def verify_tool_receipt_signature(
    receipt: ToolReceipt,
    public_jwk: jwk.JWK,
) -> bool:
    """Verify a signed ToolReceipt.

    Reconstructs the signable dict (excluding signature), computes
    canonical JSON, and verifies against the stored signature.

    Args:
        receipt: A signed ToolReceipt.
        public_jwk: The Ed25519 public JWK.

    Returns:
        True if the signature is valid, False if invalid or absent.
    """
    if receipt.signature is None:
        return False

    try:
        sig_data = json.loads(receipt.signature)
        sig = JWSSignature.from_dict(sig_data)
    except (json.JSONDecodeError, KeyError, TypeError):
        return False

    # Reconstruct the signable dict
    signable = receipt.to_dict()
    signable.pop("signature", None)
    payload = canonical_json_bytes(signable)

    return verify_detached(payload, sig, public_jwk)


def sign_message_envelope(
    message,  # TRPMessage — not type-hinted to avoid circular import
    private_jwk: jwk.JWK,
    kid: Optional[str] = None,
) -> JWSSignature:
    """Sign a TRPMessage envelope and return a detached JWS signature.

    The signature covers the canonical JSON of the full message dict
    (protocol_version, message_id, timestamp, sender, type, payload).

    The signature is NOT embedded in the message — it is returned
    separately for detached JWS usage.

    Args:
        message: A TRPMessage instance.
        private_jwk: An Ed25519 private JWK.
        kid: Optional key ID override.

    Returns:
        A JWSSignature that can be transmitted alongside the message.
    """
    # Build the message dict the same way to_json does
    from dataclasses import asdict
    wrapper = {
        "protocol_version": message.protocol_version,
        "message_id": message.message_id,
        "timestamp": message.timestamp,
        "sender": message.sender,
        "type": message.type,
        "payload": (
            message.payload.to_dict()
            if hasattr(message.payload, "to_dict")
            else asdict(message.payload)
        ),
    }
    payload = canonical_json_bytes(wrapper)
    return sign_detached(payload, private_jwk, kid=kid, typ="trp-message+jws")


def verify_message_envelope(
    message,  # TRPMessage
    signature: JWSSignature,
    public_jwk: jwk.JWK,
) -> bool:
    """Verify a detached JWS signature over a TRPMessage envelope.

    Args:
        message: The TRPMessage to verify.
        signature: The detached JWSSignature.
        public_jwk: The Ed25519 public JWK.

    Returns:
        True if the signature is valid, False otherwise.
    """
    from dataclasses import asdict
    wrapper = {
        "protocol_version": message.protocol_version,
        "message_id": message.message_id,
        "timestamp": message.timestamp,
        "sender": message.sender,
        "type": message.type,
        "payload": (
            message.payload.to_dict()
            if hasattr(message.payload, "to_dict")
            else asdict(message.payload)
        ),
    }
    payload = canonical_json_bytes(wrapper)
    return verify_detached(payload, signature, public_jwk)
