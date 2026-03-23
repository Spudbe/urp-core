"""RFC 8785 JSON Canonicalization Scheme (JCS) for TRP.

All hash computation and signing in TRP uses JCS for deterministic
byte representation. This replaces the previous sorted-key compact
JSON approach and aligns with A2A's signing requirements.

See: https://www.rfc-editor.org/rfc/rfc8785
"""

import hashlib
import jcs


def canonical_bytes(obj) -> bytes:
    """Return RFC 8785 JCS canonical bytes for a JSON-serialisable object."""
    return jcs.canonicalize(obj)


def canonical_str(obj) -> str:
    """Return RFC 8785 JCS canonical string for a JSON-serialisable object."""
    return canonical_bytes(obj).decode("utf-8")


def sha256_hex(obj) -> str:
    """Return 'sha256:<hex>' of JCS canonical bytes."""
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()
