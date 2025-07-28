# urp/transport.py

import asyncio
import websockets
import json
from urp.message import URPMessage
from urp.core import Claim, Response


class AgentServer:
    """
    A WebSocket server wrapping an Agent.
    Only handles incoming 'claim' messages and returns a 'response'.
    """
    def __init__(self, agent, host: str = "localhost", port: int = 8000):
        self.agent = agent
        self.host = host
        self.port = port

    async def handler(self, websocket):
        """Receive JSON, parse as Claim, call evaluate_claim, send back a Response."""
        try:
            async for raw in websocket:
                data = json.loads(raw)
                if data.get("type") != "claim":
                    continue

                incoming = URPMessage.from_json(raw, payload_cls=Claim)
                response: Response = self.agent.evaluate_claim(incoming.payload)
                reply = URPMessage("response", response, self.agent.name)
                await websocket.send(reply.to_json(compact=True))

        except Exception as e:
            print(f"Connection handler error: {e}")

    def start(self):
        """
        Launch the WebSocket server:
            await websockets.serve(self.handler, self.host, self.port)
        """
        return websockets.serve(self.handler, self.host, self.port)


class AgentClient:
    """
    A WebSocket client that sends one URPMessage and waits for one reply.
    """
    def __init__(self, sender_name: str, target_uri: str):
        self.sender = sender_name
        self.target_uri = target_uri

    async def send(self, urp_msg: URPMessage) -> URPMessage:
        async with websockets.connect(self.target_uri) as ws:
            await ws.send(urp_msg.to_json(compact=True))
            raw = await ws.recv()
            return URPMessage.from_json(raw, payload_cls=Response)
