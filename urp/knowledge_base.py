"""A knowledge base interface and default implementation for URP.

This module defines an abstract `KnowledgeBase` ABC with a `query` method,
a concrete `InMemoryKnowledgeBase` backed by a dictionary, and a
backwards-compatible `get_fact()` module-level function.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional


class KnowledgeBase(ABC):
    """Abstract base class for knowledge bases."""

    @abstractmethod
    def query(self, question: str) -> Optional[str]:
        """Return the answer to *question* if known, else ``None``."""


class InMemoryKnowledgeBase(KnowledgeBase):
    """Simple in-memory knowledge base backed by a dictionary."""

    def __init__(self, facts: Optional[Dict[str, str]] = None) -> None:
        self._facts: Dict[str, str] = dict(facts) if facts else {
            "boiling point of water at sea level": "100°C",
            "freezing point of water": "0°C",
            "earth gravity": "9.81 m/s²",
        }

    def query(self, question: str) -> Optional[str]:
        key = question.lower().strip()
        return self._facts.get(key)


# Module-level default instance used by the backwards-compatible helper.
_default_kb = InMemoryKnowledgeBase()


def get_fact(question: str) -> Optional[str]:
    """Return the factual answer to a question if known, else None.

    This function preserves the original module-level API so that existing
    callers (e.g. ``from urp.knowledge_base import get_fact``) continue to
    work without changes.
    """
    return _default_kb.query(question)
