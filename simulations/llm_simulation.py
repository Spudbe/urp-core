"""Groq-backed URP simulation using real LLM agents.

Requires GROQ_API_KEY to be set in the environment.
Install the groq package: pip install groq
"""

import hashlib
import json
import logging
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.core import Claim, ClaimType, Decision, ProofReference, Response, Stake
from urp.ledger import Ledger
from urp.llm import GroqAdapter
from urp.message import URPMessage

logging.basicConfig(level=logging.INFO, format="%(message)s")


class ResearcherLLM:
    """Agent that uses an LLM to generate a claim with reasoning."""

    def __init__(self, name: str, llm: GroqAdapter) -> None:
        self.name = name
        self.llm = llm

    def create_claim(self, query: str) -> Claim:
        system_prompt = (
            "You are a research agent in a verification protocol. "
            "Given a question, provide a concise factual answer and a brief "
            "reasoning summary (2-3 sentences). Reply in this exact format:\n"
            "ANSWER: <your answer>\n"
            "REASONING: <your reasoning>"
        )
        raw = self.llm.complete(system_prompt, query)

        answer = raw
        reasoning = raw
        for line in raw.splitlines():
            if line.strip().upper().startswith("ANSWER:"):
                answer = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        proof_hash = hashlib.sha256(reasoning.encode()).hexdigest()
        proof = ProofReference(
            hash=proof_hash,
            location="llm://groq/llama3-8b-8192",
            summary=answer,
            confidence_score=0.8,
        )
        stake = Stake(amount=0.5)
        return Claim(
            id=str(uuid.uuid4()),
            statement=query,
            type=ClaimType.ASSERTION,
            proof_ref=proof,
            stake=stake,
        )


class ChallengerLLM:
    """Agent that uses an LLM to evaluate a claim and decide accept or challenge."""

    def __init__(self, name: str, llm: GroqAdapter) -> None:
        self.name = name
        self.llm = llm

    def evaluate_claim(self, claim: Claim) -> Response:
        system_prompt = (
            "You are a challenger agent in a verification protocol. "
            "You are given a claim statement and the proof summary provided by the researcher. "
            "Evaluate whether the proof supports the claim. "
            "Reply in this exact format:\n"
            "DECISION: accept OR challenge\n"
            "REASON: <one sentence explanation>"
        )
        user_prompt = (
            f"Claim: {claim.statement}\n"
            f"Proof summary: {claim.proof_ref.summary}\n"
            f"Proof confidence: {claim.proof_ref.confidence_score}"
        )
        raw = self.llm.complete(system_prompt, user_prompt)

        decision = Decision.CHALLENGE
        for line in raw.splitlines():
            if line.strip().upper().startswith("DECISION:"):
                value = line.split(":", 1)[1].strip().lower()
                if value == "accept":
                    decision = Decision.ACCEPT
                else:
                    decision = Decision.CHALLENGE

        challenge_stake = Stake(amount=0.3) if decision == Decision.CHALLENGE else None
        return Response(
            claim_id=claim.id,
            decision=decision,
            proof_ref=None,
            stake=challenge_stake,
        )


class VerifierLLM:
    """Agent that uses an LLM to make a final decision on a claim."""

    def __init__(self, name: str, llm: GroqAdapter) -> None:
        self.name = name
        self.llm = llm

    def evaluate_claim(self, claim: Claim) -> Response:
        system_prompt = (
            "You are a verifier agent in a verification protocol. "
            "You are given a claim and its proof summary. "
            "Determine whether the claim is factually correct based on the evidence. "
            "Reply in this exact format:\n"
            "DECISION: accept OR reject\n"
            "REASON: <one sentence explanation>"
        )
        user_prompt = (
            f"Claim: {claim.statement}\n"
            f"Proof summary: {claim.proof_ref.summary}\n"
            f"Proof hash: {claim.proof_ref.hash}\n"
            f"Proof confidence: {claim.proof_ref.confidence_score}"
        )
        raw = self.llm.complete(system_prompt, user_prompt)

        decision = Decision.REJECT
        for line in raw.splitlines():
            if line.strip().upper().startswith("DECISION:"):
                value = line.split(":", 1)[1].strip().lower()
                if value == "accept":
                    decision = Decision.ACCEPT
                else:
                    decision = Decision.REJECT

        return Response(
            claim_id=claim.id,
            decision=decision,
            proof_ref=None,
            stake=None,
        )


def run_llm_simulation() -> None:
    query = "What is the speed of light in a vacuum?"

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

    # 1) Researcher creates a claim
    logging.info("\n--- Step 1: Researcher creates claim ---")
    claim = researcher.create_claim(query)
    msg_claim = URPMessage("claim", claim, researcher.name)
    logging.info(msg_claim.to_json(compact=False))
    ledger.withdraw(researcher.name, claim.stake.amount)

    # 2) Challenger evaluates the claim
    logging.info("\n--- Step 2: Challenger evaluates claim ---")
    challenge_resp = challenger.evaluate_claim(claim)
    msg_challenge = URPMessage("response", challenge_resp, challenger.name)
    logging.info(msg_challenge.to_json(compact=False))
    if challenge_resp.stake:
        ledger.withdraw(challenger.name, challenge_resp.stake.amount)

    # 3) Verifier makes final decision
    logging.info("\n--- Step 3: Verifier makes final decision ---")
    final_resp = verifier.evaluate_claim(claim)
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
    run_llm_simulation()
