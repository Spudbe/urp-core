"""FastAPI server that streams TRP simulation progress via Server-Sent Events."""

import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from trp.core import (
    AgentCapability,
    AgentIdentity,
    ClaimKind,
    ClaimType,
    Decision,
    EvidenceStrength,
    EvidenceType,
    SettlementMessage,
    SettlementOutcome,
    StakePolicy,
)
from trp.deterministic_tools import BUILTIN_TOOLS, compute_fibonacci
from trp.ledger import Ledger
from trp.llm import GroqAdapter
from trp.llm_agents import ChallengerLLM, ResearcherLLM, VerifierLLM
from trp.message import PROTOCOL_VERSION, TRPMessage
from trp.structured_claim import StructuredClaim, ToolOutputEquals, ValueComparison, Compound, LogicalOp, ComparisonOp
from trp.claim_verifier import match_claim, PropStatus
from trp.a2a_adapter import trp_capability_to_a2a_card
from trp.verify import ToolReceiptVerifier, VerificationStatus

app = FastAPI(title="TRP Simulation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- SSE helpers ----------

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------- Rate limiting and validation ----------

MAX_CONCURRENT_SIMULATIONS = 5
MAX_CLAIM_LENGTH = 2000
_simulation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SIMULATIONS)


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
    msg_claim = TRPMessage("claim", claim, researcher.name)
    yield _sse("trp_message", {
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
    msg_challenge = TRPMessage("response", challenge_resp, challenger.name)
    yield _sse("trp_message", {
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
    msg_final = TRPMessage("response", final_resp, verifier.name)
    yield _sse("trp_message", {
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

    if not os.getenv("GROQ_API_KEY"):
        yield _sse("error", {
            "code": "missing_groq_api_key",
            "message": (
                "GROQ_API_KEY is not set. Set it in Railway Variables or your local environment "
                "before calling /run-simulation. Create a key at https://console.groq.com/keys."
            ),
        })
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


# ---------- Deterministic demo (no API key) ----------

def _build_deterministic_verifier() -> ToolReceiptVerifier:
    """Create a ToolReceiptVerifier with all built-in tools registered."""
    verifier = ToolReceiptVerifier()
    for name, fn in BUILTIN_TOOLS.items():
        verifier.register(name, fn)
    return verifier


async def _run_deterministic_demo():
    """Stream a deterministic verification scenario via SSE.

    No LLM, no API key. The full cycle is:
    1. Researcher creates a claim with a deterministic ToolReceipt
    2. Challenger replays the tool and verifies (or challenges on mismatch)
    3. Verifier replays independently and finalises
    4. SettlementMessage emitted as a first-class TRPMessage
    """
    import hashlib
    from datetime import datetime, timezone

    from trp.core import (
        Claim,
        ClaimType,
        EvidenceStrength,
        NondeterminismClass,
        ProofReference,
        ReplayClass,
        Response,
        SideEffectClass,
        Stake,
        ToolReceipt,
    )

    yield _sse("ping", {"status": "connected"})

    verifier_engine = _build_deterministic_verifier()

    # --- Agents and ledger ---
    researcher_name = "Deterministic-Researcher"
    challenger_name = "Deterministic-Challenger"
    verifier_name = "Deterministic-Verifier"

    ledger = Ledger()
    for name in (researcher_name, challenger_name, verifier_name):
        ledger.deposit(name, 5.0)

    balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
    yield _sse("balances", {"balances": balances, "label": "Initial Balances"})

    yield _sse("scenario", {
        "num": 1,
        "title": "Deterministic Verification (no API key)",
        "query": "The 10th Fibonacci number is 55",
    })

    # --- Step 1: Researcher creates claim with ToolReceipt ---
    yield _sse("step", {"scenario": 1, "step": 1, "label": "Researcher computes Fibonacci(10) and creates ToolReceipt"})
    await asyncio.sleep(0.1)

    inputs = {"n": 10}
    output = compute_fibonacci(inputs)

    receipt = ToolReceipt(
        receipt_id="",
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        provider_name="local_python",
        provider_id="trp-demo",
        protocol_family="local_python",
        started_at=datetime.now(timezone.utc).isoformat(),
        side_effect_class=SideEffectClass.NONE,
        nondeterminism_class=NondeterminismClass.DETERMINISTIC,
        replay_class=ReplayClass.STRONG,
        evidence_strength=EvidenceStrength.UNSIGNED,
        input_inline=inputs,
        output_inline=output,
    )

    proof_hash = hashlib.sha256(
        json.dumps(output, sort_keys=True).encode()
    ).hexdigest()
    claim = Claim(
        id="det-claim-001",
        statement="The 10th Fibonacci number is 55",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(
            hash=proof_hash,
            location="local://compute_fibonacci",
            summary=f"Fibonacci(10) = {output['result']}",
            confidence_score=1.0,
        ),
        stake=Stake(amount=1.0),
        evidence=[receipt],
    )

    msg_claim = TRPMessage("claim", claim, researcher_name)
    yield _sse("trp_message", {
        "scenario": 1,
        "sender": researcher_name,
        "role": "researcher",
        "reasoning": f"compute_fibonacci(10) = {output['result']} (replay_class=strong, deterministic)",
        "message": json.loads(msg_claim.to_json(compact=False)),
    })
    ledger.withdraw(researcher_name, claim.stake.amount)

    # --- StructuredClaim: machine-parseable proposition ---
    sc = StructuredClaim(
        sc_version="0.5",
        kind="tool_output",
        proposition=ToolOutputEquals(
            tool_name="compute_fibonacci",
            input=inputs,
            expected_output=output,
        ),
    )
    yield _sse("structured_claim", {
        "scenario": 1,
        "claim": sc.to_dict(),
        "fingerprint": sc.fingerprint(),
        "statement": sc.render_statement(),
    })

    # --- Step 2: Challenger replays the tool ---
    yield _sse("step", {"scenario": 1, "step": 2, "label": "Challenger replays tool from ToolReceipt"})
    await asyncio.sleep(0.1)

    challenger_result = verifier_engine.verify(receipt)
    if challenger_result.status == VerificationStatus.VERIFIED_EXACT:
        challenger_decision = Decision.ACCEPT
        challenger_reason = (
            f"Replay verified: output hash matches receipt "
            f"({challenger_result.actual_output_hash})"
        )
    else:
        challenger_decision = Decision.CHALLENGE
        challenger_reason = f"Replay failed: {challenger_result.detail}"

    challenge_stake = Stake(amount=0.3) if challenger_decision == Decision.CHALLENGE else None
    challenge_resp = Response(
        claim_id=claim.id,
        decision=challenger_decision,
        stake=challenge_stake,
    )
    msg_challenge = TRPMessage("response", challenge_resp, challenger_name)
    yield _sse("trp_message", {
        "scenario": 1,
        "sender": challenger_name,
        "role": "challenger",
        "reasoning": challenger_reason,
        "message": json.loads(msg_challenge.to_json(compact=False)),
    })
    if challenge_resp.stake:
        ledger.withdraw(challenger_name, challenge_resp.stake.amount)

    # --- Step 3: Verifier replays independently ---
    yield _sse("step", {"scenario": 1, "step": 3, "label": "Verifier replays tool independently for final decision"})
    await asyncio.sleep(0.1)

    verifier_result = verifier_engine.verify(receipt)
    if verifier_result.status == VerificationStatus.VERIFIED_EXACT:
        final_decision = Decision.ACCEPT
        verifier_reason = (
            f"Independent replay confirmed: hash {verifier_result.actual_output_hash} "
            f"matches receipt. Claim verified mechanically."
        )
    else:
        final_decision = Decision.REJECT
        verifier_reason = f"Independent replay failed: {verifier_result.detail}"

    final_resp = Response(claim_id=claim.id, decision=final_decision)
    msg_final = TRPMessage("response", final_resp, verifier_name)
    yield _sse("trp_message", {
        "scenario": 1,
        "sender": verifier_name,
        "role": "verifier",
        "reasoning": verifier_reason,
        "message": json.loads(msg_final.to_json(compact=False)),
    })

    # --- Claim-to-evidence matching via StructuredClaim ---
    claim_match = match_claim(sc, claim.evidence)
    yield _sse("claim_match", {
        "scenario": 1,
        "status": claim_match.overall_status.value,
        "summary": claim_match.summary,
        "fingerprint": claim_match.claim_fingerprint,
    })

    # --- Settlement as first-class SettlementMessage ---
    if final_decision == Decision.ACCEPT:
        ledger.deposit(researcher_name, claim.stake.amount)
        r_delta = 0.0  # stake returned, net zero
        c_delta = 0.0
        if challenger_decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(researcher_name, challenge_resp.stake.amount)
            r_delta = challenge_resp.stake.amount
            c_delta = -challenge_resp.stake.amount
        outcome_text = "Claim ACCEPTED. Verified by deterministic replay — no LLM opinion required."
        settlement_outcome = SettlementOutcome.ACCEPTED
    else:
        r_delta = -claim.stake.amount
        c_delta = 0.0
        if challenger_decision == Decision.CHALLENGE and challenge_resp.stake:
            ledger.deposit(challenger_name, claim.stake.amount + challenge_resp.stake.amount)
            c_delta = claim.stake.amount
        outcome_text = "Claim REJECTED. Replay verification failed."
        settlement_outcome = SettlementOutcome.REJECTED

    settlement = SettlementMessage(
        settlement_id="",
        claim_id=claim.id,
        outcome=settlement_outcome,
        researcher_delta=r_delta,
        challenger_delta=c_delta,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=outcome_text,
    )
    msg_settlement = TRPMessage("settlement", settlement, verifier_name)

    balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
    yield _sse("settlement", {
        "scenario": 1,
        "outcome": outcome_text,
        "balances": balances,
    })
    yield _sse("trp_message", {
        "scenario": 1,
        "sender": verifier_name,
        "role": "verifier",
        "reasoning": "SettlementMessage emitted as first-class TRPMessage",
        "message": json.loads(msg_settlement.to_json(compact=False)),
    })

    # =====================================================================
    # Scenario 2: Tampered receipt — replay detects the manipulation
    # =====================================================================
    yield _sse("scenario", {
        "num": 2,
        "title": "Tampered Receipt (expect: reject)",
        "query": "The 10th Fibonacci number is 99 [TAMPERED]",
    })

    # --- Step 1: Researcher submits a tampered claim ---
    yield _sse("step", {"scenario": 2, "step": 1, "label": "Researcher submits claim with tampered ToolReceipt"})
    await asyncio.sleep(0.1)

    tampered_output = {"input": 10, "result": 99, "algorithm": "iterative"}
    tampered_receipt = ToolReceipt(
        receipt_id="",
        tool_name="compute_fibonacci",
        tool_version="1.0.0",
        provider_name="local_python",
        provider_id="trp-demo",
        protocol_family="local_python",
        started_at=datetime.now(timezone.utc).isoformat(),
        side_effect_class=SideEffectClass.NONE,
        nondeterminism_class=NondeterminismClass.DETERMINISTIC,
        replay_class=ReplayClass.STRONG,
        evidence_strength=EvidenceStrength.UNSIGNED,
        input_inline={"n": 10},
        output_inline=tampered_output,
    )

    tampered_proof_hash = hashlib.sha256(
        json.dumps(tampered_output, sort_keys=True).encode()
    ).hexdigest()
    tampered_claim = Claim(
        id="det-claim-002-tampered",
        statement="The 10th Fibonacci number is 99",
        type=ClaimType.ASSERTION,
        proof_ref=ProofReference(
            hash=tampered_proof_hash,
            location="local://compute_fibonacci",
            summary="Fibonacci(10) = 99 [TAMPERED]",
            confidence_score=1.0,
        ),
        stake=Stake(amount=1.0),
        evidence=[tampered_receipt],
    )

    msg_tampered = TRPMessage("claim", tampered_claim, researcher_name)
    yield _sse("trp_message", {
        "scenario": 2,
        "sender": researcher_name,
        "role": "researcher",
        "reasoning": "Submitting tampered receipt: claims Fibonacci(10) = 99",
        "message": json.loads(msg_tampered.to_json(compact=False)),
    })
    ledger.withdraw(researcher_name, tampered_claim.stake.amount)

    # --- StructuredClaim for tampered scenario ---
    sc_tampered = StructuredClaim(
        sc_version="0.5",
        kind="tool_output",
        proposition=ToolOutputEquals(
            tool_name="compute_fibonacci",
            input={"n": 10},
            expected_output=tampered_output,
        ),
    )
    yield _sse("structured_claim", {
        "scenario": 2,
        "claim": sc_tampered.to_dict(),
        "fingerprint": sc_tampered.fingerprint(),
        "statement": sc_tampered.render_statement(),
    })

    # --- Step 2: Challenger replays and detects tampering ---
    yield _sse("step", {"scenario": 2, "step": 2, "label": "Challenger replays tool — detects tampering"})
    await asyncio.sleep(0.1)

    tampered_check = verifier_engine.verify(tampered_receipt)
    challenger_decision_2 = Decision.CHALLENGE
    challenger_reason_2 = f"Replay FAILED: {tampered_check.detail}"

    challenge_resp_2 = Response(
        claim_id=tampered_claim.id,
        decision=challenger_decision_2,
        stake=Stake(amount=0.3),
    )
    msg_challenge_2 = TRPMessage("response", challenge_resp_2, challenger_name)
    yield _sse("trp_message", {
        "scenario": 2,
        "sender": challenger_name,
        "role": "challenger",
        "reasoning": challenger_reason_2,
        "message": json.loads(msg_challenge_2.to_json(compact=False)),
    })
    ledger.withdraw(challenger_name, 0.3)

    # --- Step 3: Verifier confirms rejection ---
    yield _sse("step", {"scenario": 2, "step": 3, "label": "Verifier confirms replay failure — claim rejected"})
    await asyncio.sleep(0.1)

    verifier_check_2 = verifier_engine.verify(tampered_receipt)
    verifier_reason_2 = f"Independent replay confirms tampering: {verifier_check_2.detail}"

    final_resp_2 = Response(claim_id=tampered_claim.id, decision=Decision.REJECT)
    msg_final_2 = TRPMessage("response", final_resp_2, verifier_name)
    yield _sse("trp_message", {
        "scenario": 2,
        "sender": verifier_name,
        "role": "verifier",
        "reasoning": verifier_reason_2,
        "message": json.loads(msg_final_2.to_json(compact=False)),
    })

    # --- Claim-to-evidence matching (tampered) ---
    tampered_match = match_claim(sc_tampered, tampered_claim.evidence)
    yield _sse("claim_match", {
        "scenario": 2,
        "status": tampered_match.overall_status.value,
        "summary": tampered_match.summary,
        "fingerprint": tampered_match.claim_fingerprint,
    })

    # --- Settlement for tampered claim ---
    ledger.deposit(challenger_name, tampered_claim.stake.amount + 0.3)
    outcome_text_2 = "Claim REJECTED. Replay detected tampered output — challenger collects both stakes."

    settlement_2 = SettlementMessage(
        settlement_id="",
        claim_id=tampered_claim.id,
        outcome=SettlementOutcome.REJECTED,
        researcher_delta=-tampered_claim.stake.amount,
        challenger_delta=tampered_claim.stake.amount,
        timestamp=datetime.now(timezone.utc).isoformat(),
        notes=outcome_text_2,
    )
    msg_settlement_2 = TRPMessage("settlement", settlement_2, verifier_name)

    balances = {n: f"{b:.2f}" for n, b in ledger.balances.items()}
    yield _sse("settlement", {
        "scenario": 2,
        "outcome": outcome_text_2,
        "balances": balances,
    })
    yield _sse("trp_message", {
        "scenario": 2,
        "sender": verifier_name,
        "role": "verifier",
        "reasoning": "SettlementMessage: tampered claim rejected by mechanical replay",
        "message": json.loads(msg_settlement_2.to_json(compact=False)),
    })

    yield _sse("complete", {"message": "Deterministic verification complete."})


# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    import pathlib
    try:
        html = pathlib.Path("static/index.html").read_text(encoding="utf-8")
    except FileNotFoundError:
        html = "<html><body><h1>TRP Simulation Server</h1><p>Running. static/index.html not found.</p></body></html>"
    return HTMLResponse(content=html)


@app.get("/debug-env")
async def debug_env():
    """Return environment diagnostics. Only available when DEBUG=true."""
    if os.getenv("DEBUG", "").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")
    key = os.getenv("GROQ_API_KEY")
    return {
        "GROQ_API_KEY_set": key is not None and len(key) > 0,
        "GROQ_API_KEY_prefix": key[:4] + "..." if key else None,
        "RAILWAY_ENVIRONMENT_NAME": os.getenv("RAILWAY_ENVIRONMENT_NAME"),
        "RAILWAY_SERVICE_NAME": os.getenv("RAILWAY_SERVICE_NAME"),
        "RAILWAY_PUBLIC_DOMAIN": os.getenv("RAILWAY_PUBLIC_DOMAIN"),
    }


@app.get("/run-simulation")
async def run_simulation(claim: Optional[str] = Query(default=None)):
    """Stream a TRP simulation via SSE.

    Enforces a maximum of MAX_CONCURRENT_SIMULATIONS concurrent runs and
    rejects custom claims longer than MAX_CLAIM_LENGTH characters.
    """
    if claim is not None and len(claim) > MAX_CLAIM_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Claim exceeds maximum length of {MAX_CLAIM_LENGTH} characters.",
        )
    if _simulation_semaphore.locked():
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent simulations. Please try again shortly.",
        )

    async def _guarded_stream():
        async with _simulation_semaphore:
            async for event in _run_simulation(custom_claim=claim):
                yield event

    return StreamingResponse(
        _guarded_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@app.get("/run-deterministic")
async def run_deterministic():
    """Stream a deterministic ToolReceipt verification demo via SSE.

    No API key required. Uses ToolReceiptVerifier with replay verification.
    Subject to the same concurrency limits as /run-simulation.
    """
    if _simulation_semaphore.locked():
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent simulations. Please try again shortly.",
        )

    async def _guarded_stream():
        async with _simulation_semaphore:
            async for event in _run_deterministic_demo():
                yield event

    return StreamingResponse(
        _guarded_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/.well-known/trp-capability.json")
async def trp_capability():
    """Serve an AgentCapability declaration for this TRP instance.

    This is a discovery endpoint. Protocol-aware clients can fetch it to
    learn what claim types, evidence types, and protocol versions this
    agent supports before submitting claims.
    """
    capability = AgentCapability(
        protocol_version=PROTOCOL_VERSION,
        agent=AgentIdentity(
            id="trp-demo-server",
            name="TRP Demo Server",
            version=PROTOCOL_VERSION,
        ),
        supported_claim_types=[ClaimType.ASSERTION],
        supported_claim_kinds=[
            ClaimKind.TOOL_OUTPUT,
            ClaimKind.FACTUAL_ASSERTION,
            ClaimKind.DATA_INTEGRITY,
        ],
        accepted_evidence_types=[
            EvidenceType.TOOL_RECEIPT,
            EvidenceType.PROOF_REFERENCE,
        ],
        minimum_evidence_strength=EvidenceStrength.UNSIGNED,
        stake_policy=StakePolicy(
            required=True,
            minimum_amount=0.1,
            currency="URC",
        ),
        compatible_protocol_versions=["0.2.0", "0.3.0"],
        metadata={
            "demo": True,
            "deterministic_tools": list(BUILTIN_TOOLS.keys()),
            "live_url": "https://urp-core-production.up.railway.app",
            "source": "https://github.com/Spudbe/urp-core",
        },
    )
    return JSONResponse(content=capability.to_dict())


def _build_capability() -> AgentCapability:
    """Build the server's AgentCapability declaration (shared by both endpoints)."""
    return AgentCapability(
        protocol_version=PROTOCOL_VERSION,
        agent=AgentIdentity(
            id="trp-demo-server",
            name="TRP Demo Server",
            version=PROTOCOL_VERSION,
        ),
        supported_claim_types=[ClaimType.ASSERTION],
        supported_claim_kinds=[
            ClaimKind.TOOL_OUTPUT,
            ClaimKind.FACTUAL_ASSERTION,
            ClaimKind.DATA_INTEGRITY,
        ],
        accepted_evidence_types=[
            EvidenceType.TOOL_RECEIPT,
            EvidenceType.PROOF_REFERENCE,
        ],
        minimum_evidence_strength=EvidenceStrength.UNSIGNED,
        stake_policy=StakePolicy(
            required=True,
            minimum_amount=0.1,
            currency="URC",
        ),
        compatible_protocol_versions=["0.2.0", "0.3.0"],
        metadata={
            "demo": True,
            "deterministic_tools": list(BUILTIN_TOOLS.keys()),
            "live_url": "https://urp-core-production.up.railway.app",
            "source": "https://github.com/Spudbe/urp-core",
        },
    )


@app.get("/.well-known/agent-card.json")
async def agent_card():
    """Serve an A2A-compatible AgentCard for this TRP instance.

    Translates the server's AgentCapability into the A2A AgentCard format,
    enabling discovery by A2A-compatible clients.
    """
    capability = _build_capability()
    card = trp_capability_to_a2a_card(capability)
    return JSONResponse(content=card)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
