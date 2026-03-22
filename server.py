"""FastAPI server that streams URP simulation progress via Server-Sent Events."""

import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from urp.core import Decision
from urp.ledger import Ledger
from urp.llm import GroqAdapter
from urp.llm_agents import ChallengerLLM, ResearcherLLM, VerifierLLM
from urp.message import URPMessage

app = FastAPI(title="URP Simulation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.groq_api_key_available = False
app.state.groq_api_key_error = None


@app.on_event("startup")
async def validate_runtime_config() -> None:
    groq_api_key = os.getenv("GROQ_API_KEY")
    app.state.groq_api_key_available = bool(groq_api_key)
    app.state.groq_api_key_error = None if groq_api_key else (
        "GROQ_API_KEY is not set. Set it in Railway Variables or your local environment "
        "before calling /run-simulation. Create a key at https://console.groq.com/keys."
    )


# ---------- SSE helpers ----------

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------- Scenario runner (generator) ----------

DEFAULT_SCENARIOS = [
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


async def _run_scenario(loop, researcher, challenger, verifier, ledger, num, title, query, sceptical):
    """Run a single scenario and yield SSE events."""
    yield _sse("scenario", {"num": num, "title": title, "query": query})

    # Step 1 — Researcher
    yield _sse("step", {"scenario": num, "step": 1, "label": "Researcher creates claim"})
    await asyncio.sleep(0)
    claim = await loop.run_in_executor(None, researcher.create_claim, query)
    msg_claim = URPMessage("claim", claim, researcher.name)
    yield _sse("urp_message", {
        "scenario": num,
        "sender": researcher.name,
        "role": "researcher",
        "reasoning": claim.proof_ref.summary,
        "message": json.loads(msg_claim.to_json(compact=False)),
    })
    ledger.withdraw(researcher.name, claim.stake.amount)

    # Step 2 — Challenger
    yield _sse("step", {"scenario": num, "step": 2, "label": "Challenger evaluates claim"})
    await asyncio.sleep(0)
    challenge_resp, challenger_reason = await loop.run_in_executor(
        None, challenger.evaluate_claim, claim, sceptical
    )
    msg_challenge = URPMessage("response", challenge_resp, challenger.name)
    yield _sse("urp_message", {
        "scenario": num,
        "sender": challenger.name,
        "role": "challenger",
        "reasoning": challenger_reason,
        "message": json.loads(msg_challenge.to_json(compact=False)),
    })
    if challenge_resp.stake:
        ledger.withdraw(challenger.name, challenge_resp.stake.amount)

    # Step 3 — Verifier
    yield _sse("step", {"scenario": num, "step": 3, "label": "Verifier makes final decision"})
    await asyncio.sleep(0)
    final_resp, verifier_reason = await loop.run_in_executor(
        None, verifier.evaluate_claim, claim
    )
    msg_final = URPMessage("response", final_resp, verifier.name)
    yield _sse("urp_message", {
        "scenario": num,
        "sender": verifier.name,
        "role": "verifier",
        "reasoning": verifier_reason,
        "message": json.loads(msg_final.to_json(compact=False)),
    })

    # Settlement
    if final_resp.decision == Decision.ACCEPT:
        ledger.deposit(researcher.name, claim.stake.amount)
        if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(researcher.name, challenge_resp.stake.amount)
            outcome = "Claim ACCEPTED. Researcher recovers stake and wins challenger's stake."
        else:
            outcome = "Claim ACCEPTED. Researcher recovers stake."
    else:
        if challenge_resp.decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(challenger.name, claim.stake.amount + challenge_resp.stake.amount)
            outcome = "Claim REJECTED. Challenger collects both stakes."
        else:
            outcome = "Claim REJECTED. Researcher's stake is burnt."

    balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
    yield _sse("settlement", {
        "scenario": num,
        "outcome": outcome,
        "balances": balances,
    })


_SSE_HEARTBEAT = ":\n\n"  # SSE comment — clients silently ignore this
_HEARTBEAT_INTERVAL = 5  # seconds


async def _simulation_worker(
    queue: asyncio.Queue,
    custom_claim: Optional[str],
) -> None:
    """Background coroutine that runs scenarios and pushes SSE strings into *queue*.

    Puts ``None`` as a sentinel when finished.
    """
    try:
        loop = asyncio.get_event_loop()
        llm = GroqAdapter()

        researcher = ResearcherLLM("Researcher-LLM", llm)
        challenger = ChallengerLLM("Challenger-LLM", llm)
        verifier = VerifierLLM("Verifier-LLM", llm)

        ledger = Ledger()
        for name in (researcher.name, challenger.name, verifier.name):
            ledger.deposit(name, 5.0)

        balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
        await queue.put(_sse("balances", {"balances": balances, "label": "Initial Balances"}))

        if custom_claim:
            scenarios = [{
                "num": 1,
                "title": "Custom Claim",
                "query": custom_claim,
                "sceptical": True,
            }]
        else:
            scenarios = DEFAULT_SCENARIOS

        for sc in scenarios:
            async for event in _run_scenario(
                loop, researcher, challenger, verifier, ledger,
                sc["num"], sc["title"], sc["query"], sc["sceptical"],
            ):
                await queue.put(event)

        await queue.put(_sse("complete", {"message": "Simulation complete."}))
    except Exception as exc:
        await queue.put(_sse("error", {"code": "simulation_error", "message": str(exc)}))
        await queue.put(_sse("complete", {"message": "Simulation aborted."}))
    finally:
        await queue.put(None)  # sentinel


async def _run_simulation(custom_claim: Optional[str] = None):
    # Immediate ping so Railway proxy sees data within 1 second
    yield _sse("ping", {"status": "connected"})

    if not getattr(app.state, "groq_api_key_available", False):
        yield _sse("error", {"code": "missing_groq_api_key", "message": app.state.groq_api_key_error})
        yield _sse("complete", {"message": "Simulation aborted."})
        return

    queue: asyncio.Queue = asyncio.Queue()
    task = asyncio.create_task(_simulation_worker(queue, custom_claim))

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                # No event within 5s — send a keep-alive comment
                yield _SSE_HEARTBEAT
                continue
            if event is None:
                break
            yield event
    finally:
        if not task.done():
            task.cancel()


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    import pathlib
    html = pathlib.Path("static/index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/run-simulation")
async def run_simulation(claim: Optional[str] = Query(default=None)):
    return StreamingResponse(
        _run_simulation(custom_claim=claim),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
