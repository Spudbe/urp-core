import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from urp.agent import ResearcherAgent, ChallengerAgent, VerifierAgent
from urp.ledger import Ledger
from urp.message import URPMessage
from urp.transport import AgentServer, AgentClient

async def networked_simulation():
    # Instantiate agents
    researcher = ResearcherAgent("Researcher")
    challenger = ChallengerAgent("Challenger")
    verifier = VerifierAgent("Verifier")

    # Start each agent's WS server
    srv1 = AgentServer(researcher, port=8001)
    srv2 = AgentServer(challenger, port=8002)
    srv3 = AgentServer(verifier, port=8003)

    # Run all servers concurrently
    await asyncio.gather(srv1.start(), srv2.start(), srv3.start())

    # Allow servers time to bind
    await asyncio.sleep(0.5)

    # Set up ledger
    ledger = Ledger()
    for name in (researcher.name, challenger.name, verifier.name):
        ledger.deposit(name, 1.0)

    # Researcher creates a claim and sends it to Challenger for evaluation
    claim = researcher.create_claim("What is the boiling point of water at sea level?")
    msg = URPMessage("claim", claim, researcher.name)
    async with AgentClient(researcher.name, "ws://localhost:8002") as client:
        challenger_resp = await client.send(msg)

    print("Challenger decision:", challenger_resp.payload.decision)

    # Send the original claim to the Verifier for final evaluation
    async with AgentClient(researcher.name, "ws://localhost:8003") as client_v:
        verifier_resp = await client_v.send(msg)

    # Display the final response
    print("Verifier decision:", verifier_resp.payload.decision)
    print("Final decision payload:", verifier_resp.payload)

if __name__ == "__main__":
    asyncio.run(networked_simulation())
