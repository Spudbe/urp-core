# trp/transport.py

import asyncio
import websockets
import json
from trp.message import TRPMessage
from trp.core import Claim, Response


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

                incoming = TRPMessage.from_json(raw, payload_cls=Claim)
                response: Response = self.agent.evaluate_claim(incoming.payload)
                reply = TRPMessage("response", response, self.agent.name)
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
    A WebSocket client that sends one TRPMessage and waits for one reply.
    """
    def __init__(self, sender_name: str, target_uri: str):
        self.sender = sender_name
        self.target_uri = target_uri
        self._ws = None

    async def __aenter__(self):
        self._ws = await websockets.connect(self.target_uri)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        return False

    async def send(self, trp_msg: TRPMessage) -> TRPMessage:
        if self._ws is not None:
            ws = self._ws
        else:
            ws = await websockets.connect(self.target_uri)
        try:
            await ws.send(trp_msg.to_json(compact=True))
            raw = await ws.recv()
            return TRPMessage.from_json(raw, payload_cls=Response)
        finally:
            if self._ws is None:
                await ws.close()
