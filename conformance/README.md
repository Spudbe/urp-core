# TRP Conformance Test Vectors

These files contain deterministic test vectors for TRP implementations.
Any compliant implementation must produce identical results for these inputs.

## Files

- `canonical_json_vectors.json` — RFC 8785 JCS canonical form and expected SHA-256 hashes
- `receipt_hash_vectors.json` — ToolReceipt inputs/outputs and expected input_sha256/output_sha256
- `signature_vectors.json` — Known keypair + receipt and expected JWS signature verification result
- `claim_match_vectors.json` — StructuredClaim + evidence and expected match result (true/false/unknown)
