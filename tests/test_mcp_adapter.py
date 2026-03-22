"""Tests for urp/mcp_adapter.py — MCP integration utilities."""

import json

import pytest

from urp.core import (
    EvidenceStrength,
    NondeterminismClass,
    ReplayClass,
    SideEffectClass,
    ToolReceipt,
)
from urp.mcp_adapter import (
    URP_META_KEY,
    extract_tool_receipt,
    wrap_mcp_tool_result,
    wrap_tool_call,
)


# ---------- wrap_tool_call ----------

class TestWrapToolCall:
    """The convenience function for creating a ToolReceipt from a tool invocation."""

    def test_happy_path_fibonacci(self):
        receipt = wrap_tool_call(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        assert receipt.tool_name == "compute_fibonacci"
        assert receipt.tool_version == "1.0.0"
        assert receipt.input_inline == {"n": 10}
        assert receipt.output_inline == {"input": 10, "result": 55, "algorithm": "iterative"}

    def test_hashes_are_computed(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={"n": 10},
            output={"result": 55},
        )
        assert receipt.input_sha256 == ToolReceipt.make_input_hash({"n": 10})
        assert receipt.output_sha256 == ToolReceipt.make_output_hash({"result": 55})

    def test_receipt_id_auto_generated(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
        )
        assert receipt.receipt_id  # not empty
        assert len(receipt.receipt_id) == 36  # UUID format

    def test_timestamp_populated(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
        )
        assert receipt.started_at  # not empty
        assert "T" in receipt.started_at  # ISO format

    def test_default_classifications(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
        )
        assert receipt.nondeterminism_class == NondeterminismClass.DETERMINISTIC
        assert receipt.side_effect_class == SideEffectClass.NONE
        assert receipt.replay_class == ReplayClass.STRONG
        assert receipt.evidence_strength == EvidenceStrength.UNSIGNED

    def test_custom_classifications(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
            nondeterminism="model_based",
            side_effects="read_only",
            replay="weak",
            strength="caller_signed",
        )
        assert receipt.nondeterminism_class == NondeterminismClass.MODEL_BASED
        assert receipt.side_effect_class == SideEffectClass.READ_ONLY
        assert receipt.replay_class == ReplayClass.WEAK
        assert receipt.evidence_strength == EvidenceStrength.CALLER_SIGNED

    def test_custom_provider_fields(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
            provider_name="my-server",
            provider_id="server-123",
            protocol_family="mcp",
        )
        assert receipt.provider_name == "my-server"
        assert receipt.provider_id == "server-123"
        assert receipt.protocol_family == "mcp"

    def test_invalid_nondeterminism_raises(self):
        with pytest.raises(ValueError, match="nondeterminism"):
            wrap_tool_call("t", "1", {}, {}, nondeterminism="bogus")

    def test_invalid_side_effects_raises(self):
        with pytest.raises(ValueError, match="side_effects"):
            wrap_tool_call("t", "1", {}, {}, side_effects="bogus")

    def test_invalid_replay_raises(self):
        with pytest.raises(ValueError, match="replay"):
            wrap_tool_call("t", "1", {}, {}, replay="bogus")

    def test_invalid_strength_raises(self):
        with pytest.raises(ValueError, match="strength"):
            wrap_tool_call("t", "1", {}, {}, strength="bogus")

    def test_round_trip_to_dict_from_dict(self):
        receipt = wrap_tool_call(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        d = receipt.to_dict()
        restored = ToolReceipt.from_dict(d)
        assert restored.tool_name == receipt.tool_name
        assert restored.input_sha256 == receipt.input_sha256
        assert restored.output_sha256 == receipt.output_sha256
        assert restored.nondeterminism_class == receipt.nondeterminism_class


# ---------- wrap_mcp_tool_result ----------

class TestWrapMcpToolResult:
    """Wrapping a tool call into an MCP CallToolResult-shaped dict."""

    def test_result_shape(self):
        result = wrap_mcp_tool_result(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        assert "content" in result
        assert "structuredContent" in result
        assert "_meta" in result
        assert "isError" in result
        assert result["isError"] is False

    def test_content_is_text_block(self):
        result = wrap_mcp_tool_result(
            tool_name="test",
            tool_version="1.0",
            inputs={"x": 1},
            output={"y": 2},
        )
        content = result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        # Default text is JSON-serialised output
        parsed = json.loads(content[0]["text"])
        assert parsed == {"y": 2}

    def test_custom_text(self):
        result = wrap_mcp_tool_result(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={"y": 2},
            text="Custom summary",
        )
        assert result["content"][0]["text"] == "Custom summary"

    def test_structured_content_is_output(self):
        output = {"input": 10, "result": 55}
        result = wrap_mcp_tool_result(
            tool_name="test",
            tool_version="1.0",
            inputs={"n": 10},
            output=output,
        )
        assert result["structuredContent"] == output

    def test_meta_contains_receipt(self):
        result = wrap_mcp_tool_result(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        meta = result["_meta"]
        assert URP_META_KEY in meta
        receipt_dict = meta[URP_META_KEY]
        assert receipt_dict["tool_name"] == "compute_fibonacci"
        assert "input_sha256" in receipt_dict
        assert "output_sha256" in receipt_dict

    def test_default_protocol_family_is_mcp(self):
        result = wrap_mcp_tool_result(
            tool_name="test",
            tool_version="1.0",
            inputs={},
            output={},
        )
        receipt_dict = result["_meta"][URP_META_KEY]
        assert receipt_dict["protocol_family"] == "mcp"

    def test_receipt_in_meta_round_trips(self):
        """The receipt in _meta should deserialise back into a valid ToolReceipt."""
        result = wrap_mcp_tool_result(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output={"input": 10, "result": 55, "algorithm": "iterative"},
        )
        receipt = ToolReceipt.from_dict(result["_meta"][URP_META_KEY])
        assert receipt.tool_name == "compute_fibonacci"
        assert receipt.replay_class == ReplayClass.STRONG


# ---------- extract_tool_receipt ----------

class TestExtractToolReceipt:
    """Extracting a ToolReceipt from MCP _meta."""

    def test_extracts_valid_receipt(self):
        receipt = wrap_tool_call(
            tool_name="test",
            tool_version="1.0",
            inputs={"a": 1},
            output={"b": 2},
        )
        meta = {URP_META_KEY: receipt.to_dict()}
        extracted = extract_tool_receipt(meta)
        assert extracted is not None
        assert extracted.tool_name == "test"
        assert extracted.input_sha256 == receipt.input_sha256

    def test_returns_none_for_none_meta(self):
        assert extract_tool_receipt(None) is None

    def test_returns_none_for_empty_meta(self):
        assert extract_tool_receipt({}) is None

    def test_returns_none_for_missing_key(self):
        assert extract_tool_receipt({"other_key": "value"}) is None

    def test_end_to_end_wrap_and_extract(self):
        """Full round trip: wrap → extract → verify fields match."""
        result = wrap_mcp_tool_result(
            tool_name="math_eval",
            tool_version="2.0",
            inputs={"expression": "2 + 3"},
            output={"expression": "2 + 3", "result": 5, "algorithm": "ast_eval"},
            provider_name="my-mcp-server",
        )
        extracted = extract_tool_receipt(result["_meta"])
        assert extracted is not None
        assert extracted.tool_name == "math_eval"
        assert extracted.provider_name == "my-mcp-server"
        assert extracted.protocol_family == "mcp"
        assert extracted.output_sha256 == ToolReceipt.make_output_hash(
            {"expression": "2 + 3", "result": 5, "algorithm": "ast_eval"}
        )

    def test_extract_then_verify(self):
        """Extract a receipt from _meta, then verify it with ToolReceiptVerifier."""
        from urp.deterministic_tools import BUILTIN_TOOLS
        from urp.verify import ToolReceiptVerifier, VerificationStatus

        # Server side: wrap the tool result
        output = {"input": 10, "result": 55, "algorithm": "iterative"}
        result = wrap_mcp_tool_result(
            tool_name="compute_fibonacci",
            tool_version="1.0.0",
            inputs={"n": 10},
            output=output,
        )

        # Client side: extract and verify
        receipt = extract_tool_receipt(result["_meta"])
        assert receipt is not None

        verifier = ToolReceiptVerifier()
        for name, fn in BUILTIN_TOOLS.items():
            verifier.register(name, fn)

        verification = verifier.verify(receipt)
        assert verification.status == VerificationStatus.VERIFIED_EXACT
