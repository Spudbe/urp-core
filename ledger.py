"""A minimal ledger for tracking URP credit balances and stakes.

This module provides a simple in‑memory ledger class. It keeps track of
agents' balances and manages stakes for claims and challenges. In a
production system, the ledger would likely be implemented as a smart
contract or an external accounting service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Ledger:
    """In‑memory ledger of agent balances."""

    balances: Dict[str, float] = field(default_factory=dict)

    def deposit(self, agent: str, amount: float) -> None:
        """Increase an agent's balance by `amount`."""
        if amount < 0:
            raise ValueError("Cannot deposit a negative amount")
        self.balances[agent] = self.balances.get(agent, 0.0) + amount

    def withdraw(self, agent: str, amount: float) -> None:
        """Decrease an agent's balance by `amount`.

        Raises a ValueError if the agent does not have sufficient funds.
        """
        if amount < 0:
            raise ValueError("Cannot withdraw a negative amount")
        current = self.balances.get(agent, 0.0)
        if current < amount:
            raise ValueError(f"Insufficient funds for {agent}: {current} < {amount}")
        self.balances[agent] = current - amount

    def transfer(self, sender: str, recipient: str, amount: float) -> None:
        """Transfer `amount` from `sender` to `recipient`."""
        self.withdraw(sender, amount)
        self.deposit(recipient, amount)

    def get_balance(self, agent: str) -> float:
        """Return the balance of `agent`."""
        return self.balances.get(agent, 0.0)
