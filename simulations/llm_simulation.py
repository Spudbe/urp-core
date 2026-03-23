"""Groq-backed TRP simulation using real LLM agents.

Requires GROQ_API_KEY to be set in the environment.
Install the groq package: pip install groq
"""

import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trp.core import Decision
from trp.ledger import Ledger
from trp.llm import GroqAdapter
from trp.llm_agents import ChallengerLLM, ResearcherLLM, VerifierLLM
from trp.message import TRPMessage

logging.basicConfig(level=logging.INFO, format="%(message)s")

__all__ = [
    "run_scenario",
    "run_llm_simulation",
]


def run_scenario(
    scenario_num: int,
    title: str,
    query: str,
    researcher: ResearcherLLM,
    challenger: ChallengerLLM,
    verifier: VerifierLLM,
    ledger: Ledger,
    sceptical_challenger: bool = False,
) -> None:
    """Run a single claim lifecycle scenario."""

    logging.info(f"\n{'=' * 60}")
    logging.info(f"  SCENARIO {scenario_num}: {title}")
    logging.info(f"  Query: \"{query}\"")
    logging.info(f"{'=' * 60}")

    # 1) Researcher creates a claim
    logging.info("\n--- Step 1: Researcher creates claim ---")
    claim = researcher.create_claim(query)
    msg_claim = TRPMessage("claim", claim, researcher.name)
    logging.info(msg_claim.to_json(compact=False))
    ledger.withdraw(researcher.name, claim.stake.amount)

    # 2) Challenger evaluates the claim
    logging.info("\n--- Step 2: Challenger evaluates claim ---")
    challenge_resp, _ = challenger.evaluate_claim(claim, sceptical=sceptical_challenger)
    msg_challenge = TRPMessage("response", challenge_resp, challenger.name)
    logging.info(msg_challenge.to_json(compact=False))
    if challenge_resp.stake:
        ledger.withdraw(challenger.name, challenge_resp.stake.amount)

    # 3) Verifier makes final decision
    logging.info("\n--- Step 3: Verifier makes final decision ---")
    final_resp, _ = verifier.evaluate_claim(claim)
    msg_final = TRPMessage("response", final_resp, verifier.name)
    logging.info(msg_final.to_json(compact=False))

    # Settlement
    logging.info("\n--- Settlement ---")
    if final_resp.decision == Decision.ACCEPT:
        ledger.deposit(researcher.name, claim.stake.amount)
        if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(researcher.name, challenge_resp.stake.amount)
            logging.info("Claim ACCEPTED. Researcher recovers stake and wins challenger's stake.")
        else:
            logging.info("Claim ACCEPTED. Researcher recovers stake.")
    else:
        if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(challenger.name, claim.stake.amount + challenge_resp.stake.amount)
            logging.info("Claim REJECTED. Challenger collects both stakes.")
        else:
            logging.info("Claim REJECTED. Researcher's stake is burnt.")

    logging.info(f"\n--- Running Balances (after Scenario {scenario_num}) ---")
    for name, bal in ledger.balances.items():
        logging.info(f"  {name}: {bal:.2f} URC")


def run_llm_simulation() -> None:
    llm = GroqAdapter()
    researcher = ResearcherLLM("Researcher-LLM", llm)
    challenger = ChallengerLLM("Challenger-LLM", llm)
    verifier = VerifierLLM("Verifier-LLM", llm)

    ledger = Ledger()
    for name in (researcher.name, challenger.name, verifier.name):
        ledger.deposit(name, 5.0)

    logging.info("=== Initial Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"  {name}: {bal:.2f} URC")

    # Scenario 1 — Easy claim (should be accepted)
    run_scenario(
        scenario_num=1,
        title="Easy Claim (expect: accept)",
        query="What is the speed of light in a vacuum?",
        researcher=researcher,
        challenger=challenger,
        verifier=verifier,
        ledger=ledger,
    )

    # Scenario 2 — Contested claim (should trigger a challenge)
    run_scenario(
        scenario_num=2,
        title="Contested Claim (expect: challenge)",
        query="Is Python faster than C++ for numerical computing?",
        researcher=researcher,
        challenger=challenger,
        verifier=verifier,
        ledger=ledger,
        sceptical_challenger=True,
    )

    # Scenario 3 — False claim (should be rejected)
    run_scenario(
        scenario_num=3,
        title="False Claim (expect: reject)",
        query="The Earth is approximately 100 years old.",
        researcher=researcher,
        challenger=challenger,
        verifier=verifier,
        ledger=ledger,
        sceptical_challenger=True,
    )

    logging.info(f"\n{'=' * 60}")
    logging.info("  SIMULATION COMPLETE")
    logging.info(f"{'=' * 60}")
    logging.info("\n=== Final Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"  {name}: {bal:.2f} URC")


if __name__ == "__main__":
    run_llm_simulation()
