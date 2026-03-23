"""Tests that verify conformance vectors are self-consistent."""
import json
import os

import pytest

from trp.canonical import canonical_str, sha256_hex
from trp.core import ToolReceipt
from trp.structured_claim import StructuredClaim
from trp.claim_verifier import match_claim

CONFORMANCE_DIR = os.path.join(os.path.dirname(__file__), "..", "conformance")


class TestCanonicalVectors:
    def test_all_canonical_vectors(self):
        path = os.path.join(CONFORMANCE_DIR, "canonical_json_vectors.json")
        with open(path) as f:
            data = json.load(f)
        for v in data["vectors"]:
            assert canonical_str(v["input"]) == v["canonical_form"], f"Failed: {v['description']}"
            assert sha256_hex(v["input"]) == v["sha256"], f"Hash failed: {v['description']}"


class TestReceiptHashVectors:
    def test_all_receipt_hash_vectors(self):
        path = os.path.join(CONFORMANCE_DIR, "receipt_hash_vectors.json")
        with open(path) as f:
            data = json.load(f)
        for v in data["vectors"]:
            assert ToolReceipt.make_input_hash(v["input"]) == v["expected_input_sha256"], f"Input hash failed: {v['description']}"
            assert ToolReceipt.make_output_hash(v["output"]) == v["expected_output_sha256"], f"Output hash failed: {v['description']}"


class TestClaimMatchVectors:
    def test_all_claim_match_vectors(self):
        path = os.path.join(CONFORMANCE_DIR, "claim_match_vectors.json")
        with open(path) as f:
            data = json.load(f)
        for v in data["vectors"]:
            sc = StructuredClaim.from_dict(v["claim"])
            receipts = [ToolReceipt.from_dict(r) for r in v["evidence"]]
            result = match_claim(sc, receipts)
            assert result.overall_status.value == v["expected_status"], f"Match failed: {v['description']}"
