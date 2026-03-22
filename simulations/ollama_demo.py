"""Ollama-backed URP simulation using local models.

Requires Ollama to be running locally. No API key needed.
Install Ollama from https://ollama.com, then: ollama pull llama3
"""

import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.core import Decision
from urp.ledger import Ledger
from urp.llm import OllamaAdapter
from urp.llm_agents import ChallengerLLM, ResearcherLLM, VerifierLLM
from urp.message import URPMessage

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    try:
        llm = OllamaAdapter()
    except Exception as e:
        logging.error(f"Failed to create OllamaAdapter: {e}")
        return

    researcher = ResearcherLLM("Researcher-LLM", llm)
    challenger = ChallengerLLM("Challenger-LLM", llm)
    verifier = VerifierLLM("Verifier-LLM", llm)

    ledger = Ledger()
    for name in (researcher.name, challenger.name, verifier.name):
        ledger.deposit(name, 5.0)

    logging.info("=== Initial Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"  {name}: {bal:.2f} URC")

    query = "Is the speed of light constant in all reference frames?"

    logging.info(f"\n{'=' * 60}")
    logging.info(f"  Query: \"{query}\"")
    logging.info(f"{'=' * 60}")

    # 1) Researcher creates a claim
    logging.info("\n--- Step 1: Researcher creates claim ---")
    try:
        claim = researcher.create_claim(query)
    except RuntimeError as e:
        logging.error(f"\nOllama error: {e}")
        logging.error("Make sure Ollama is running: ollama serve")
        logging.error("And you have a model pulled: ollama pull llama3")
        return

    msg_claim = URPMessage("claim", claim, researcher.name)
    logging.info(msg_claim.to_json(compact=False))
    ledger.withdraw(researcher.name, claim.stake.amount)

    # 2) Challenger evaluates the claim
    logging.info("\n--- Step 2: Challenger evaluates claim ---")
    try:
        challenge_resp, _ = challenger.evaluate_claim(claim)
    except RuntimeError as e:
        logging.error(f"\nOllama error: {e}")
        return

    msg_challenge = URPMessage("response", challenge_resp, challenger.name)
    logging.info(msg_challenge.to_json(compact=False))
    if challenge_resp.stake:
        ledger.withdraw(challenger.name, challenge_resp.stake.amount)

    # 3) Verifier makes final decision
    logging.info("\n--- Step 3: Verifier makes final decision ---")
    try:
        final_resp, _ = verifier.evaluate_claim(claim)
    except RuntimeError as e:
        logging.error(f"\nOllama error: {e}")
        return

    msg_final = URPMessage("response", final_resp, verifier.name)
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

    logging.info("\n=== Final Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"  {name}: {bal:.2f} URC")


if __name__ == "__main__":
    main()
