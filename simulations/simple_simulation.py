"""Run a simple URP simulation with JSON messages."""

import logging
import os
import sys

# fix imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.agent import ResearcherAgent, ChallengerAgent, VerifierAgent
from urp.ledger import Ledger
from urp.message import URPMessage

logging.basicConfig(level=logging.INFO, format="%(message)s")

def run_simulation() -> None:
    query = "What is the boiling point of water at sea level?"
    researcher = ResearcherAgent(name="Researcher")
    challenger = ChallengerAgent(name="Challenger")
    verifier = VerifierAgent(name="Verifier")

    ledger = Ledger()
    for name in (researcher.name, challenger.name, verifier.name):
        ledger.deposit(name, 1.0)

    logging.info("=== Initial Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"{name}: {bal:.2f} URC")
    logging.info("")

    # 1) Researcher creates claim
    claim = researcher.create_claim(query)
    msg_claim = URPMessage("claim", claim, researcher.name)
    compact = msg_claim.to_json(compact=True)
    pretty = msg_claim.to_json(compact=False)
    logging.info("Sending CLAIM message (compact):")
    logging.info(compact)
    logging.info("\nReceived CLAIM message (pretty):")
    logging.info(pretty)

    # Simulate withdrawing stake
    ledger.withdraw(researcher.name, claim.stake.amount)

    # 2) Challenger evaluates
    response = challenger.evaluate_claim(claim)
    msg_challenge = URPMessage("response", response, challenger.name)
    logging.info("\nSending CHALLENGE message:")
    logging.info(msg_challenge.to_json(compact=True))

    if response.stake:
        ledger.withdraw(challenger.name, response.stake.amount)

    # 3) Verifier evaluates
    final_resp = verifier.evaluate_claim(claim)
    msg_verifier = URPMessage("response", final_resp, verifier.name)
    logging.info("\nSending VERIFICATION message:")
    logging.info(msg_verifier.to_json(compact=False))

    # Settlement
    if final_resp.decision.value == "accept":
        ledger.deposit(researcher.name, claim.stake.amount)
        if response.decision.value == "challenge" and response.stake:
            ledger.deposit(researcher.name, response.stake.amount)
            logging.info("\nClaim accepted; Researcher wins Challenger’s stake.")
    else:
        if response.decision.value == "challenge" and response.stake:
            ledger.deposit(challenger.name, claim.stake.amount + response.stake.amount)
            logging.info("\nClaim rejected; Challenger collects both stakes.")
        else:
            logging.info("\nClaim rejected; Researcher’s stake is burnt.")

    logging.info("\n=== Final Balances ===")
    for name, bal in ledger.balances.items():
        logging.info(f"{name}: {bal:.2f} URC")

if __name__ == "__main__":
    run_simulation()
