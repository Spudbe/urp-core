"""Tests for trp/signing.py — JWS signing for ToolReceipts and TRPMessages."""

import json

import pytest

from trp.core import (
    Claim,
    ClaimType,
    EvidenceStrength,
    NondeterminismClass,
    ProofReference,
    ReplayClass,
    SideEffectClass,
    Stake,
    ToolReceipt,
)
from trp.message import TRPMessage
from trp.signing import (
    _update_evidence_strength,
    canonical_json_bytes,
    generate_ed25519_keypair,
    sign_detached,
    sign_message_envelope,
    sign_tool_receipt,
    verify_detached,
    verify_message_envelope,
    verify_tool_receipt_signature,
)


# ---------- Helpers ----------

def _make_receipt(**overrides) -> ToolReceipt:
    defaults = dict(
        receipt_id="test-receipt-001",
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        provider_name="test",
        provider_id="test-provider",
        protocol_family="local_python",
        started_at="2026-03-22T00:00:00Z",
        input_inline={"n": 10},
        output_inline={"input": 10, "result": 55, "algorithm": "iterative"},
    )
    defaults.update(overrides)
    return ToolReceipt(**defaults)


def _make_claim() -> Claim:
    return Claim(
        id="test-claim",
        statement="test",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(hash="h", location="l", summary="s"),
        stake=Stake(amount=0.1),
    )


# ---------- canonical_json_bytes ----------

class TestCanonicalJsonBytes:
    def test_deterministic_ordering(self):
        a = canonical_json_bytes({"z": 1, "a": 2})
        b = canonical_json_bytes({"a": 2, "z": 1})
        assert a == b

    def test_compact_separators(self):
        result = canonical_json_bytes({"key": "value"})
        assert result == b'{"key":"value"}'

    def test_nested_sorting(self):
        result = canonical_json_bytes({"b": {"z": 1, "a": 2}, "a": 1})
        assert result == b'{"a":1,"b":{"a":2,"z":1}}'


# ---------- Key generation ----------

class TestKeyGeneration:
    def test_generates_ed25519_keys(self):
        priv, pub = generate_ed25519_keypair()
        priv_data = json.loads(priv.export())
        pub_data = json.loads(pub.export())
        assert priv_data["kty"] == "OKP"
        assert priv_data["crv"] == "Ed25519"
        assert "d" in priv_data  # private key material
        assert pub_data["kty"] == "OKP"
        assert "d" not in pub_data  # no private key

    def test_kid_propagated(self):
        priv, pub = generate_ed25519_keypair(kid="my-key-1")
        priv_data = json.loads(priv.export())
        assert priv_data["kid"] == "my-key-1"

    def test_no_kid_by_default(self):
        priv, _ = generate_ed25519_keypair()
        priv_data = json.loads(priv.export())
        assert "kid" not in priv_data

    def test_different_keys_each_time(self):
        priv1, _ = generate_ed25519_keypair()
        priv2, _ = generate_ed25519_keypair()
        assert priv1.export() != priv2.export()


# ---------- sign_detached / verify_detached ----------

class TestDetachedSignature:
    def test_sign_and_verify_success(self):
        priv, pub = generate_ed25519_keypair()
        payload = b"hello world"
        sig = sign_detached(payload, priv)
        assert verify_detached(payload, sig, pub)

    def test_wrong_key_fails(self):
        priv1, _ = generate_ed25519_keypair()
        _, pub2 = generate_ed25519_keypair()
        sig = sign_detached(b"data", priv1)
        assert not verify_detached(b"data", sig, pub2)

    def test_tampered_payload_fails(self):
        priv, pub = generate_ed25519_keypair()
        sig = sign_detached(b"original", priv)
        assert not verify_detached(b"tampered", sig, pub)

    def test_signature_has_protected_and_signature(self):
        priv, _ = generate_ed25519_keypair()
        sig = sign_detached(b"data", priv)
        assert sig.protected  # base64url encoded
        assert sig.signature  # base64url encoded

    def test_kid_in_protected_header(self):
        priv, pub = generate_ed25519_keypair(kid="key-42")
        sig = sign_detached(b"data", priv)
        # Decode the protected header
        import base64
        padded = sig.protected + "=" * (-len(sig.protected) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        assert header["kid"] == "key-42"
        assert header["alg"] == "EdDSA"

    def test_typ_in_protected_header(self):
        priv, _ = generate_ed25519_keypair()
        sig = sign_detached(b"data", priv, typ="trp-receipt+jws")
        import base64
        padded = sig.protected + "=" * (-len(sig.protected) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        assert header["typ"] == "trp-receipt+jws"


# ---------- Evidence strength escalation ----------

class TestEvidenceStrengthEscalation:
    def test_unsigned_plus_caller(self):
        assert _update_evidence_strength(EvidenceStrength.UNSIGNED, "caller") == EvidenceStrength.CALLER_SIGNED

    def test_unsigned_plus_provider(self):
        assert _update_evidence_strength(EvidenceStrength.UNSIGNED, "provider") == EvidenceStrength.PROVIDER_SIGNED

    def test_caller_signed_plus_provider(self):
        assert _update_evidence_strength(EvidenceStrength.CALLER_SIGNED, "provider") == EvidenceStrength.DUAL_SIGNED

    def test_provider_signed_plus_caller(self):
        assert _update_evidence_strength(EvidenceStrength.PROVIDER_SIGNED, "caller") == EvidenceStrength.DUAL_SIGNED

    def test_dual_signed_stays_dual(self):
        assert _update_evidence_strength(EvidenceStrength.DUAL_SIGNED, "caller") == EvidenceStrength.DUAL_SIGNED
        assert _update_evidence_strength(EvidenceStrength.DUAL_SIGNED, "provider") == EvidenceStrength.DUAL_SIGNED

    def test_caller_signed_plus_caller_stays(self):
        assert _update_evidence_strength(EvidenceStrength.CALLER_SIGNED, "caller") == EvidenceStrength.CALLER_SIGNED

    def test_provider_signed_plus_provider_stays(self):
        assert _update_evidence_strength(EvidenceStrength.PROVIDER_SIGNED, "provider") == EvidenceStrength.PROVIDER_SIGNED

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError, match="signer_role"):
            _update_evidence_strength(EvidenceStrength.UNSIGNED, "admin")


# ---------- sign_tool_receipt / verify_tool_receipt_signature ----------

class TestToolReceiptSigning:
    def test_sign_and_verify_round_trip(self):
        priv, pub = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv, signer_role="caller")
        assert signed.signature is not None
        assert verify_tool_receipt_signature(signed, pub)

    def test_evidence_strength_updated(self):
        priv, _ = generate_ed25519_keypair()
        receipt = _make_receipt()
        assert receipt.evidence_strength == EvidenceStrength.UNSIGNED
        signed = sign_tool_receipt(receipt, priv, signer_role="caller")
        assert signed.evidence_strength == EvidenceStrength.CALLER_SIGNED

    def test_provider_signing(self):
        priv, pub = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv, signer_role="provider")
        assert signed.evidence_strength == EvidenceStrength.PROVIDER_SIGNED
        assert verify_tool_receipt_signature(signed, pub)

    def test_original_receipt_not_modified(self):
        priv, _ = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv, signer_role="caller")
        assert receipt.signature is None  # original unchanged
        assert receipt.evidence_strength == EvidenceStrength.UNSIGNED

    def test_wrong_key_fails_verification(self):
        priv1, _ = generate_ed25519_keypair()
        _, pub2 = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv1, signer_role="caller")
        assert not verify_tool_receipt_signature(signed, pub2)

    def test_unsigned_receipt_fails_verification(self):
        _, pub = generate_ed25519_keypair()
        receipt = _make_receipt()
        assert not verify_tool_receipt_signature(receipt, pub)

    def test_tampered_receipt_fails_verification(self):
        priv, pub = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv, signer_role="caller")
        # Tamper with the output
        tampered = ToolReceipt(
            receipt_id=signed.receipt_id,
            tool_name=signed.tool_name,
            tool_version=signed.tool_version,
            provider_name=signed.provider_name,
            provider_id=signed.provider_id,
            protocol_family=signed.protocol_family,
            started_at=signed.started_at,
            input_inline=signed.input_inline,
            output_inline={"input": 10, "result": 99, "algorithm": "iterative"},
            input_sha256=signed.input_sha256,
            output_sha256=ToolReceipt.make_output_hash({"input": 10, "result": 99, "algorithm": "iterative"}),
            evidence_strength=signed.evidence_strength,
            signature=signed.signature,
        )
        assert not verify_tool_receipt_signature(tampered, pub)

    def test_signature_field_is_serialised_jws(self):
        priv, _ = generate_ed25519_keypair()
        receipt = _make_receipt()
        signed = sign_tool_receipt(receipt, priv, signer_role="caller")
        sig_data = json.loads(signed.signature)
        assert "protected" in sig_data
        assert "signature" in sig_data


# ---------- sign_message_envelope / verify_message_envelope ----------

class TestMessageEnvelopeSigning:
    def test_sign_and_verify_round_trip(self):
        priv, pub = generate_ed25519_keypair()
        msg = TRPMessage("claim", _make_claim(), "agent-1")
        sig = sign_message_envelope(msg, priv)
        assert verify_message_envelope(msg, sig, pub)

    def test_wrong_key_fails(self):
        priv1, _ = generate_ed25519_keypair()
        _, pub2 = generate_ed25519_keypair()
        msg = TRPMessage("claim", _make_claim(), "agent-1")
        sig = sign_message_envelope(msg, priv1)
        assert not verify_message_envelope(msg, sig, pub2)

    def test_tampered_message_fails(self):
        priv, pub = generate_ed25519_keypair()
        msg = TRPMessage("claim", _make_claim(), "agent-1")
        sig = sign_message_envelope(msg, priv)
        # Tamper with the sender
        msg.sender = "evil-agent"
        assert not verify_message_envelope(msg, sig, pub)

    def test_kid_in_envelope_signature(self):
        priv, _ = generate_ed25519_keypair(kid="envelope-key")
        msg = TRPMessage("claim", _make_claim(), "agent-1")
        sig = sign_message_envelope(msg, priv)
        import base64
        padded = sig.protected + "=" * (-len(sig.protected) % 4)
        header = json.loads(base64.urlsafe_b64decode(padded))
        assert header["kid"] == "envelope-key"
        assert header["typ"] == "trp-message+jws"
