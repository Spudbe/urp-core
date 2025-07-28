"""A simple knowledge base for demonstration purposes.

This module contains a hard‑coded dictionary of factual information. The
VerifierAgent uses it to validate claims. In a real URP network, this
knowledge would be distributed and claims would reference verifiable proofs.
"""

from __future__ import annotations

from typing import Dict, Optional


_FACTS: Dict[str, str] = {
    "boiling point of water at sea level": "100°C",
    "freezing point of water": "0°C",
    "earth gravity": "9.81 m/s²",
}


def get_fact(question: str) -> Optional[str]:
    """Return the factual answer to a question if known, else None."""
    key = question.lower().strip()
    return _FACTS.get(key)
