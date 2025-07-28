"""Run a simple URP simulation with three agents.

This script creates one ResearcherAgent, one ChallengerAgent and one
VerifierAgent. The Researcher submits a claim based on an input query,
the Challenger evaluates it and either accepts or challenges, and the
Verifier makes a final decision. Results are printed to stdout.
"""

from __future__ import annotations

import logging

from urp.agent import ResearcherAgent, ChallengerAgent, VerifierAgent


logging.basicConfig(level=logging.INFO, format="%(message)s")


def run_simulation() -> None:
    query = "What is the boiling point of water at sea level?"
    researcher = ResearcherAgent(name="Researcher")
    challenger = ChallengerAgent(name="Challenger")
    verifier = VerifierAgent(name="Verifier")

    # Researcher creates a claim
    claim = researcher.create_claim(query)
    logging.info(f"{researcher} created claim {claim.id} with stake {claim.stake.amount} URC")

    # Challenger evaluates the claim
    resp_challenger = challenger.evaluate_claim(claim)
    logging.info(f"{challenger} responded: {resp_challenger.decision.value}")

    # If the challenger challenges, we augment the claim's stake for the verifier
    # In this simple prototype we ignore staking mechanics and move to verification
    # Verifier evaluates the claim
    resp_verifier = verifier.evaluate_claim(claim)
    logging.info(f"{verifier} final decision: {resp_verifier.decision.value}")

    if resp_verifier.decision == resp_challenger.decision or resp_challenger.decision == "accept":
        logging.info("Claim accepted")
    else:
        logging.info("Claim rejected")


if __name__ == "__main__":
    run_simulation()
