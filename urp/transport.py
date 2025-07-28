import asyncio
import websockets
from urp.message import URPMessage

class AgentServer:
    def __init__(self, agent, host="localhost", port=8000):
        self.agent = agent
        self.uri = f"ws://{host}:{port}"
        self.clients = set()

    async def handler(self, websocket, path):
        self.clients.add(websocket)
        async for msg in websocket:
            # Deserialize incoming message
            incoming = URPMessage.from_json(msg, payload_cls=... )
            # Let your agent process it (you’ll define process_message)
            response = await self.agent.process_message(incoming)
            if response:
                # Send back any response message
                await websocket.send(response.to_json(compact=True))
        self.clients.remove(websocket)

    def start(self):
        return websockets.serve(self.handler, *self.uri.replace("ws://","").split(":"))

class AgentClient:
    def __init__(self, sender_name, target_uri):
        self.sender = sender_name
        self.target = target_uri

    async def send(self, urp_msg: URPMessage):
        async with websockets.connect(self.target) as ws:
            await ws.send(urp_msg.to_json(compact=True))
            # Optionally wait for a reply
            reply = await ws.recv()
            return URPMessage.from_json(reply, payload_cls=...)

