# urp/transport.py

import asyncio
import websockets
import json
from urp.message import URPMessage
from urp.core import Claim, Response


class AgentServer:
    """
    A WebSocket server wrapping an Agent.
    Listens for URPMessage JSON, deserializes into Claim/Response,
    invokes the agent, then sends back a URPMessage reply.
    """
    def __init__(self, agent, host: str = "localhost", port: int = 8000):
        self.agent = agent
        self.host = host
        self.port = port

    async def handler(self, websocket):
        """Handle incoming WebSocket connections and dispatch URP messages."""
        try:
            async for raw in websocket:
                data = json.loads(raw)
                msg_type = data.get("type")
                payload_cls = Claim if msg_type == "claim" else Response

                incoming = URPMessage.from_json(raw, payload_cls=payload_cls)

                if incoming.type == "claim":
                    # CALL SYNC method directly (no await)
                    response = self.agent.evaluate_claim(incoming.payload)
                    reply = URPMessage("response", response, self.agent.name)
                    await websocket.send(reply.to_json(compact=True))

                elif incoming.type == "response":
                    # process_message may be sync or async; handle both
                    proc = self.agent.process_message(incoming)
                    if asyncio.iscoroutine(proc):
                        proc = await proc
                    if proc:
                        await websocket.send(proc.to_json(compact=True))

                # Add other message types here...

        except Exception as e:
            print(f"Connection handler error: {e}")

    def start(self):
        """
        Launch the WebSocket server. Usage:
            await websockets.serve(self.handler, self.host, self.port)
        """
        return websockets.serve(self.handler, self.host, self.port)


class AgentClient:
    """
    A simple WebSocket client for sending one URPMessage
    and waiting for one reply.
    """
    def __init__(self, sender_name: str, target_uri: str):
        self.sender = sender_name
        self.target_uri = target_uri

    async def send(self, urp_msg: URPMessage) -> URPMessage:
        """
        Connect, send the URPMessage (compact JSON), await one reply,
        and return the reconstructed URPMessage.
        """
        async with websockets.connect(self.target_uri) as ws:
            await ws.send(urp_msg.to_json(compact=True))
            raw = await ws.recv()
            data = json.loads(raw)
            msg_type = data.get("type")
            payload_cls = Claim if msg_type == "claim" else Response
            return URPMessage.from_json(raw, payload_cls=payload_cls)
