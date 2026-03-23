"""Tests for trp/a2a_adapter.py — A2A AgentCard ↔ TRP AgentCapability."""

import pytest

from trp.core import (
    AgentCapability,
    AgentIdentity,
    ClaimKind,
    ClaimType,
    EvidenceStrength,
    EvidenceType,
    StakePolicy,
)
from trp.a2a_adapter import (
    TRP_EXTENSION_URI,
    a2a_card_to_trp_capability,
    merge_discovery,
    trp_capability_to_a2a_card,
)


# ---------- Helpers ----------

def _make_capability(**overrides) -> AgentCapability:
    defaults = dict(
        protocol_version="0.6.0",
        agent=AgentIdentity(id="test-agent", name="Test Agent", version="0.6.0"),
        supported_claim_types=[ClaimType.ASSERTION],
        supported_claim_kinds=[ClaimKind.TOOL_OUTPUT, ClaimKind.DATA_INTEGRITY],
        accepted_evidence_types=[EvidenceType.TOOL_RECEIPT],
        minimum_evidence_strength=EvidenceStrength.UNSIGNED,
        stake_policy=StakePolicy(required=True, minimum_amount=0.5, currency="URC"),
        compatible_protocol_versions=["0.6.0"],
        metadata={
            "live_url": "https://example.com",
            "source": "https://github.com/example/repo",
        },
    )
    defaults.update(overrides)
    return AgentCapability(**defaults)


# ==========================================================================
# trp_capability_to_a2a_card
# ==========================================================================

class TestUrpToA2a:
    def test_card_has_required_a2a_fields(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert "name" in card
        assert "description" in card
        assert "version" in card
        assert "supportedInterfaces" in card
        assert "capabilities" in card
        assert "defaultInputModes" in card
        assert "defaultOutputModes" in card
        assert "skills" in card

    def test_name_from_agent(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert card["name"] == "Test Agent"

    def test_version_from_agent(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert card["version"] == "0.6.0"

    def test_interface_has_trp_binding(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        iface = card["supportedInterfaces"][0]
        assert iface["protocolBinding"] == "TRP"
        assert iface["protocolVersion"] == "0.6.0"

    def test_interface_url_from_metadata(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert card["supportedInterfaces"][0]["url"] == "https://example.com"

    def test_interface_url_override(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap, base_url="https://custom.com")
        assert card["supportedInterfaces"][0]["url"] == "https://custom.com"

    def test_documentation_url_from_metadata(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert card["documentationUrl"] == "https://github.com/example/repo"

    def test_skills_from_claim_kinds(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        skill_ids = [s["id"] for s in card["skills"]]
        assert "trp.verify.tool_output" in skill_ids
        assert "trp.verify.data_integrity" in skill_ids

    def test_skill_tags_contain_trp_prefixes(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        tags = card["skills"][0]["tags"]
        assert "trp" in tags
        assert any(t.startswith("trp_claim_kind:") for t in tags)
        assert any(t.startswith("trp_claim_type:") for t in tags)
        assert any(t.startswith("trp_evidence:") for t in tags)

    def test_extension_contains_trp_capability_inline(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        extensions = card["capabilities"]["extensions"]
        trp_ext = [e for e in extensions if e["uri"] == TRP_EXTENSION_URI]
        assert len(trp_ext) == 1
        inline = trp_ext[0]["params"]["trpCapabilityInline"]
        assert inline["protocol_version"] == "0.6.0"
        assert inline["agent"]["id"] == "test-agent"

    def test_description_mentions_claim_kinds(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert "tool_output" in card["description"]
        assert "data_integrity" in card["description"]

    def test_description_mentions_stake(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert "0.5" in card["description"]
        assert "URC" in card["description"]

    def test_json_modes(self):
        cap = _make_capability()
        card = trp_capability_to_a2a_card(cap)
        assert card["defaultInputModes"] == ["application/json"]
        assert card["defaultOutputModes"] == ["application/json"]


# ==========================================================================
# a2a_card_to_trp_capability (lossless path)
# ==========================================================================

class TestA2aToUrpLossless:
    def test_round_trip_via_extension(self):
        """TRP → A2A → TRP should produce identical capability."""
        original = _make_capability()
        card = trp_capability_to_a2a_card(original)
        restored = a2a_card_to_trp_capability(card)
        assert restored is not None
        assert restored.protocol_version == original.protocol_version
        assert restored.agent.id == original.agent.id
        assert restored.agent.name == original.agent.name
        assert len(restored.supported_claim_kinds) == len(original.supported_claim_kinds)
        assert restored.stake_policy.minimum_amount == original.stake_policy.minimum_amount

    def test_round_trip_preserves_evidence_types(self):
        original = _make_capability(
            accepted_evidence_types=[EvidenceType.TOOL_RECEIPT, EvidenceType.PROOF_REFERENCE],
        )
        card = trp_capability_to_a2a_card(original)
        restored = a2a_card_to_trp_capability(card)
        assert restored is not None
        assert set(e.value for e in restored.accepted_evidence_types) == {
            "tool_receipt", "proof_reference"
        }


# ==========================================================================
# a2a_card_to_trp_capability (fallback/lossy path)
# ==========================================================================

class TestA2aToUrpFallback:
    def test_returns_none_for_empty_card(self):
        assert a2a_card_to_trp_capability({}) is None

    def test_returns_none_for_no_skills(self):
        card = {"name": "Agent", "skills": []}
        assert a2a_card_to_trp_capability(card) is None

    def test_reconstructs_from_skill_tags(self):
        card = {
            "name": "External Agent",
            "version": "1.0",
            "skills": [
                {
                    "id": "trp.verify.tool_output",
                    "tags": [
                        "trp",
                        "trp_claim_kind:tool_output",
                        "trp_claim_type:assertion",
                        "trp_evidence:tool_receipt",
                    ],
                }
            ],
            "supportedInterfaces": [
                {"url": "https://agent.example.com", "protocolBinding": "TRP", "protocolVersion": "0.6.0"}
            ],
        }
        cap = a2a_card_to_trp_capability(card)
        assert cap is not None
        assert cap.agent.name == "External Agent"
        assert ClaimKind.TOOL_OUTPUT in cap.supported_claim_kinds
        assert ClaimType.ASSERTION in cap.supported_claim_types
        assert cap.protocol_version == "0.6.0"

    def test_fallback_uses_defaults_for_missing_fields(self):
        card = {
            "name": "Minimal Agent",
            "skills": [
                {"id": "x", "tags": ["trp_claim_kind:tool_output"]},
            ],
        }
        cap = a2a_card_to_trp_capability(card)
        assert cap is not None
        # Defaults
        assert cap.minimum_evidence_strength == EvidenceStrength.UNSIGNED
        assert cap.stake_policy.required is False  # StakePolicy default

    def test_ignores_non_trp_tags(self):
        card = {
            "name": "Mixed Agent",
            "skills": [
                {"id": "general", "tags": ["general", "not_trp"]},
                {"id": "trp_skill", "tags": ["trp_claim_kind:data_integrity"]},
            ],
        }
        cap = a2a_card_to_trp_capability(card)
        assert cap is not None
        assert len(cap.supported_claim_kinds) == 1
        assert cap.supported_claim_kinds[0] == ClaimKind.DATA_INTEGRITY


# ==========================================================================
# merge_discovery
# ==========================================================================

class TestMergeDiscovery:
    def test_adds_extension_to_card_without_one(self):
        cap = _make_capability()
        card = {"name": "Existing", "capabilities": {}, "skills": []}
        merged = merge_discovery(cap, card)
        extensions = merged["capabilities"]["extensions"]
        assert len(extensions) == 1
        assert extensions[0]["uri"] == TRP_EXTENSION_URI

    def test_replaces_existing_trp_extension(self):
        cap = _make_capability()
        card = {
            "name": "Existing",
            "capabilities": {
                "extensions": [
                    {"uri": TRP_EXTENSION_URI, "params": {"old": True}},
                    {"uri": "urn:other:ext", "params": {}},
                ]
            },
        }
        merged = merge_discovery(cap, card)
        extensions = merged["capabilities"]["extensions"]
        assert len(extensions) == 2
        trp_ext = [e for e in extensions if e["uri"] == TRP_EXTENSION_URI][0]
        assert "old" not in trp_ext.get("params", {})
        assert "trpCapabilityInline" in trp_ext["params"]

    def test_does_not_mutate_original_card(self):
        cap = _make_capability()
        card = {"name": "Original", "capabilities": {"extensions": []}}
        merged = merge_discovery(cap, card)
        assert len(card["capabilities"]["extensions"]) == 0
        assert len(merged["capabilities"]["extensions"]) == 1

    def test_round_trip_after_merge(self):
        cap = _make_capability()
        card = {"name": "Host", "capabilities": {}, "skills": []}
        merged = merge_discovery(cap, card)
        restored = a2a_card_to_trp_capability(merged)
        assert restored is not None
        assert restored.agent.id == cap.agent.id
