"""Run a simple URP simulation with three agents.

This script creates one ResearcherAgent, one ChallengerAgent and one
VerifierAgent. The Researcher submits a claim based on an input query,
the Challenger evaluates it and either accepts or challenges, and the
Verifier makes a final decision. Results are printed to stdout.
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure the parent directory is on the module search path so that
# `import urp` works when this script is run directly with
# `python simulations/simple_simulation.py`. Without this, Python will not
# find the sibling package because it only adds the script's directory to
# sys.path by default.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.agent import ResearcherAgent, ChallengerAgent, VerifierAgent
from urp.ledger import Ledger


logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_simulation() -> None:
    """Run a simulation with balances and staking."""
    query = "What is the boiling point of water at sea level?"
    researcher = ResearcherAgent(name="Researcher")
    challenger = ChallengerAgent(name="Challenger")
    verifier = VerifierAgent(name="Verifier")

    # Set up a ledger and deposit initial balances
    ledger = Ledger()
    for agent in (researcher.name, challenger.name, verifier.name):
        ledger.deposit(agent, 1.0)  # each starts with 1 URC

    logging.info("Initial balances:")
    for agent in ledger.balances:
        logging.info(f"  {agent}: {ledger.get_balance(agent):.2f} URC")

    # Researcher creates a claim and stakes some credits
    claim = researcher.create_claim(query)
    logging.info(f"\n{researcher} created claim {claim.id} with stake {claim.stake.amount:.2f} URC")
    try:
        ledger.withdraw(researcher.name, claim.stake.amount)
    except ValueError as e:
        logging.error(e)
        return

    # Challenger evaluates the claim
    resp_challenger = challenger.evaluate_claim(claim)
    logging.info(f"{challenger} responded: {resp_challenger.decision.value}")
    if resp_challenger.decision == "challenge" and resp_challenger.stake:
        try:
            ledger.withdraw(challenger.name, resp_challenger.stake.amount)
        except ValueError as e:
            logging.error(e)
            return

    # Verifier evaluates the claim
    resp_verifier = verifier.evaluate_claim(claim)
    logging.info(f"{verifier} final decision: {resp_verifier.decision.value}\n")

    # Settlement logic
    if resp_verifier.decision == "accept":
        # Researcher gets stake back and collects challenger's stake if any
        ledger.deposit(researcher.name, claim.stake.amount)
        if resp_challenger.decision == "challenge" and resp_challenger.stake:
            ledger.deposit(researcher.name, resp_challenger.stake.amount)
            logging.info("Claim accepted; Researcher keeps their stake and wins Challenger's stake.")
        else:
            logging.info("Claim accepted; Researcher keeps their stake.")
    else:
        # Stake is forfeited to challenger or burnt
        if resp_challenger.decision == "challenge" and resp_challenger.stake:
            # Challenger wins both stakes
            ledger.deposit(challenger.name, claim.stake.amount + resp_challenger.stake.amount)
            logging.info("Claim rejected; Challenger collects both stakes.")
        else:
            # No challenger; stakes are burnt (do nothing)
            logging.info("Claim rejected; Researcher's stake is burnt.")

    logging.info("\nFinal balances:")
    for agent, balance in ledger.balances.items():
        logging.info(f"  {agent}: {balance:.2f} URC")


if __name__ == "__main__":
    run_simulation()
