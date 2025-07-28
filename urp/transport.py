# urp/transport.py

import asyncio
import websockets
import json
from urp.message import URPMessage
from urp.core import Claim, Response


class AgentServer:
    """
    A WebSocket server that wraps an Agent instance.
    Listens for URPMessage JSON, deserializes into Claim/Response,
    invokes the agent, then sends back a URPMessage reply.
    """
    def __init__(self, agent, host: str = "localhost", port: int = 8000):
        self.agent = agent
        self.host = host
        self.port = port

    async def handler(self, websocket, path):
        try:
            async for raw in websocket:
                # Peek at type to choose payload class
                data = json.loads(raw)
                msg_type = data.get("type")
                payload_cls = Claim if msg_type == "claim" else Response

                # Reconstruct URPMessage
                incoming = URPMessage.from_json(raw, payload_cls=payload_cls)

                # Dispatch based on message type
                if incoming.type == "claim":
                    # Claim → Verifier/Challenger logic
                    response = await self.agent.evaluate_claim(incoming.payload)
                    reply = URPMessage("response", response, self.agent.name)
                    await websocket.send(reply.to_json(compact=True))

                elif incoming.type == "response":
                    # Agents that need to handle responses can override process_message()
                    processed = await self.agent.process_message(incoming)
                    if processed:
                        await websocket.send(processed.to_json(compact=True))

                # Add more branches (e.g. "settlement") as needed

        except Exception as e:
            print(f"Connection handler error: {e}")

    def start(self):
        """
        Launch the WebSocket server. Returns a coroutine you can await:
            await websockets.serve(self.handler, self.host, self.port)
        """
        return websockets.serve(self.handler, self.host, self.port)


class AgentClient:
    """
    A simple WebSocket client for sending a single URPMessage
    and waiting for one reply.
    """
    def __init__(self, sender_name: str, target_uri: str):
        self.sender = sender_name
        self.target_uri = target_uri

    async def send(self, urp_msg: URPMessage) -> URPMessage:
        """
        Connect to the target URI, send the URPMessage (compact JSON),
        then await and return a single URPMessage reply.
        """
        async with websockets.connect(self.target_uri) as ws:
            await ws.send(urp_msg.to_json(compact=True))
            raw = await ws.recv()

            # Determine payload class from incoming JSON
            data = json.loads(raw)
            msg_type = data.get("type")
            payload_cls = Claim if msg_type == "claim" else Response

            return URPMessage.from_json(raw, payload_cls=payload_cls)
