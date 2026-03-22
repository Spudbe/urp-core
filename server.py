"""FastAPI server that streams URP simulation progress via Server-Sent Events."""

import asyncio
import hashlib
import json
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from urp.core import Claim, ClaimType, Decision, ProofReference, Response, Stake
from urp.ledger import Ledger
from urp.llm import GroqAdapter
from urp.message import URPMessage

app = FastAPI(title="URP Simulation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- LLM agent helpers (sync, run in threadpool) ----------

def _researcher_create_claim(llm: GroqAdapter, query: str) -> Claim:
    system_prompt = (
        "You are a research agent in a verification protocol. "
        "Given a question or statement, provide a concise factual answer and a brief "
        "reasoning summary (2-3 sentences). You must always produce an answer, even if "
        "the statement is incorrect — state what you believe to be true. "
        "Reply in this exact format:\n"
        "ANSWER: <your answer>\n"
        "REASONING: <your reasoning>"
    )
    raw = llm.complete(system_prompt, query)
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
    return Claim(
        id=str(uuid.uuid4()),
        statement=query,
        type=ClaimType.ASSERTION,
        proof_ref=proof,
        stake=Stake(amount=0.5),
    )


def _challenger_evaluate(llm: GroqAdapter, claim: Claim, sceptical: bool) -> Response:
    if sceptical:
        system_prompt = (
            "You are a highly sceptical challenger agent in a verification protocol. "
            "Your job is to find flaws, oversimplifications, or misleading aspects "
            "in the claim. Look for nuance that the claim ignores. Be critical. "
            "If there is ANY reason to doubt the claim, you MUST challenge it and "
            "provide a counter-argument. "
            "Reply in this exact format:\n"
            "DECISION: accept OR challenge\n"
            "REASON: <one sentence explanation>"
        )
    else:
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
    raw = llm.complete(system_prompt, user_prompt)
    decision = Decision.CHALLENGE
    for line in raw.splitlines():
        if line.strip().upper().startswith("DECISION:"):
            value = line.split(":", 1)[1].strip().lower()
            if value == "accept":
                decision = Decision.ACCEPT
            else:
                decision = Decision.CHALLENGE
    challenge_stake = Stake(amount=0.3) if decision == Decision.CHALLENGE else None
    return Response(claim_id=claim.id, decision=decision, proof_ref=None, stake=challenge_stake)


def _verifier_evaluate(llm: GroqAdapter, claim: Claim) -> Response:
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
    raw = llm.complete(system_prompt, user_prompt)
    decision = Decision.REJECT
    for line in raw.splitlines():
        if line.strip().upper().startswith("DECISION:"):
            value = line.split(":", 1)[1].strip().lower()
            if value == "accept":
                decision = Decision.ACCEPT
            else:
                decision = Decision.REJECT
    return Response(claim_id=claim.id, decision=decision, proof_ref=None, stake=None)


# ---------- SSE helpers ----------

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------- Scenario runner (generator) ----------

SCENARIOS = [
    {
        "num": 1,
        "title": "Easy Claim (expect: accept)",
        "query": "What is the speed of light in a vacuum?",
        "sceptical": False,
    },
    {
        "num": 2,
        "title": "Contested Claim (expect: challenge)",
        "query": "Is Python faster than C++ for numerical computing?",
        "sceptical": True,
    },
    {
        "num": 3,
        "title": "False Claim (expect: reject)",
        "query": "The Earth is approximately 100 years old.",
        "sceptical": True,
    },
]


async def _run_simulation():
    loop = asyncio.get_event_loop()
    llm = GroqAdapter()

    ledger = Ledger()
    agents = ["Researcher-LLM", "Challenger-LLM", "Verifier-LLM"]
    for name in agents:
        ledger.deposit(name, 5.0)

    balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
    yield _sse("balances", {"balances": balances, "label": "Initial Balances"})

    for sc in SCENARIOS:
        num, title, query, sceptical = sc["num"], sc["title"], sc["query"], sc["sceptical"]

        yield _sse("scenario", {"num": num, "title": title, "query": query})

        # Step 1 — Researcher
        yield _sse("step", {"scenario": num, "step": 1, "label": "Researcher creates claim"})
        claim = await loop.run_in_executor(None, _researcher_create_claim, llm, query)
        msg_claim = URPMessage("claim", claim, "Researcher-LLM")
        yield _sse("urp_message", {
            "scenario": num,
            "sender": "Researcher-LLM",
            "role": "researcher",
            "message": json.loads(msg_claim.to_json(compact=False)),
        })
        ledger.withdraw("Researcher-LLM", claim.stake.amount)

        # Step 2 — Challenger
        yield _sse("step", {"scenario": num, "step": 2, "label": "Challenger evaluates claim"})
        challenge_resp = await loop.run_in_executor(
            None, _challenger_evaluate, llm, claim, sceptical
        )
        msg_challenge = URPMessage("response", challenge_resp, "Challenger-LLM")
        yield _sse("urp_message", {
            "scenario": num,
            "sender": "Challenger-LLM",
            "role": "challenger",
            "message": json.loads(msg_challenge.to_json(compact=False)),
        })
        if challenge_resp.stake:
            ledger.withdraw("Challenger-LLM", challenge_resp.stake.amount)

        # Step 3 — Verifier
        yield _sse("step", {"scenario": num, "step": 3, "label": "Verifier makes final decision"})
        final_resp = await loop.run_in_executor(None, _verifier_evaluate, llm, claim)
        msg_final = URPMessage("response", final_resp, "Verifier-LLM")
        yield _sse("urp_message", {
            "scenario": num,
            "sender": "Verifier-LLM",
            "role": "verifier",
            "message": json.loads(msg_final.to_json(compact=False)),
        })

        # Settlement
        if final_resp.decision == Decision.ACCEPT:
            ledger.deposit("Researcher-LLM", claim.stake.amount)
            if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
                ledger.deposit("Researcher-LLM", challenge_resp.stake.amount)
                outcome = "Claim ACCEPTED. Researcher recovers stake and wins challenger's stake."
            else:
                outcome = "Claim ACCEPTED. Researcher recovers stake."
        else:
            if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
                ledger.deposit("Challenger-LLM", claim.stake.amount + challenge_resp.stake.amount)
                outcome = "Claim REJECTED. Challenger collects both stakes."
            else:
                outcome = "Claim REJECTED. Researcher's stake is burnt."

        balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
        yield _sse("settlement", {
            "scenario": num,
            "outcome": outcome,
            "balances": balances,
        })

    yield _sse("complete", {"message": "Simulation complete."})


# ---------- Routes ----------

@app.get("/run-simulation")
async def run_simulation():
    return StreamingResponse(
        _run_simulation(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
