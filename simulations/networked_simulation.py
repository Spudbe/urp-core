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

    # Researcher sends a claim to Challenger
    claim = researcher.create_claim("What is the boiling point of water at sea level?")
    msg = URPMessage("claim", claim, researcher.name)
    async with AgentClient(researcher.name, "ws://localhost:8002") as client:
        resp = await client.send(msg)

    # Challenger processes and forwards to Verifier
    async with AgentClient(challenger.name, "ws://localhost:8003") as client_v:
        resp2 = await client_v.send(resp)

    # Display the final response
    print("Final decision payload:", resp2.payload)

if __name__ == "__main__":
    asyncio.run(networked_simulation())
