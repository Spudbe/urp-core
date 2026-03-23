"""Tests for trp/cli.py."""
import json
import os

import pytest

from trp.cli import main
from trp.core import ToolReceipt, EvidenceStrength, NondeterminismClass, SideEffectClass, ReplayClass
from trp.deterministic_tools import compute_fibonacci
from trp.structured_claim import StructuredClaim, ToolOutputEquals


def _make_receipt_file(tmp_path):
    output = compute_fibonacci({"n": 10})
    receipt = ToolReceipt(
        receipt_id="cli-test",
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        provider_name="test",
        provider_id="test",
        protocol_family="local_python",
        started_at="2026-03-23T00:00:00Z",
        side_effect_class=SideEffectClass.NONE,
        nondeterminism_class=NondeterminismClass.DETERMINISTIC,
        replay_class=ReplayClass.STRONG,
        evidence_strength=EvidenceStrength.UNSIGNED,
        input_inline={"n": 10},
        output_inline=output,
    )
    path = os.path.join(str(tmp_path), "receipt.json")
    with open(path, "w") as f:
        json.dump(receipt.to_dict(), f)
    return path


def _make_claim_file(tmp_path):
    output = compute_fibonacci({"n": 10})
    sc = StructuredClaim(
        sc_version="0.6",
        kind="tool_output",
        proposition=ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output=output,
        ),
    )
    path = os.path.join(str(tmp_path), "claim.json")
    with open(path, "w") as f:
        json.dump(sc.to_dict(), f)
    return path


class TestCLIVerify:
    def test_verify_valid_receipt(self, tmp_path, capsys, monkeypatch):
        receipt_path = _make_receipt_file(tmp_path)
        monkeypatch.setattr("sys.argv", ["trp", "verify", receipt_path])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["status"] == "verified_exact"

    def test_verify_returns_nonzero_for_unregistered_tool(self, tmp_path, capsys, monkeypatch):
        path = os.path.join(str(tmp_path), "bad.json")
        with open(path, "w") as f:
            json.dump({
                "receipt_id": "x", "tool_name": "unknown_tool", "tool_version": "1.0",
                "provider_name": "t", "provider_id": "t", "protocol_family": "t",
                "started_at": "2026-01-01T00:00:00Z",
                "input_inline": {}, "output_inline": {},
                "nondeterminism_class": "deterministic", "side_effect_class": "none",
                "replay_class": "strong", "evidence_strength": "unsigned",
            }, f)
        monkeypatch.setattr("sys.argv", ["trp", "verify", path])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1


class TestCLIMatch:
    def test_match_claim_against_receipt(self, tmp_path, capsys, monkeypatch):
        receipt_path = _make_receipt_file(tmp_path)
        claim_path = _make_claim_file(tmp_path)
        monkeypatch.setattr("sys.argv", ["trp", "match", claim_path, receipt_path])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        result = json.loads(out)
        assert result["overall_status"] == "true"


class TestCLIHash:
    def test_hash_json_file(self, tmp_path, capsys, monkeypatch):
        path = os.path.join(str(tmp_path), "test.json")
        with open(path, "w") as f:
            json.dump({"n": 10}, f)
        monkeypatch.setattr("sys.argv", ["trp", "hash", path])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert out.strip().startswith("sha256:")


class TestCLIVersion:
    def test_version(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.argv", ["trp", "version"])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "trp-core" in out
        assert "0.6.0" in out
