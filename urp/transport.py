import asyncio
import websockets
from urp.message import URPMessage

class AgentServer:
    def __init__(self, agent, host="localhost", port=8000):
        self.agent = agent
        self.host = host
        self.port = port
        self.url = f"ws://{host}:{port}"

    async def handler(self, websocket, _path):
        async for raw in websocket:
            incoming = URPMessage.from_json(raw, payload_cls=self.agent.payload_cls)
            response_msg = await self.agent.process_message(incoming)
            if response_msg:
                await websocket.send(response_msg.to_json(compact=True))

    def start(self):
        return websockets.serve(self.handler, self.host, self.port)

class AgentClient:
    def __init__(self, sender_name, target_url):
        self.sender = sender_name
        self.target_url = target_url

    async def send(self, urp_msg: URPMessage):
        async with websockets.connect(self.target_url) as ws:
            await ws.send(urp_msg.to_json(compact=True))
            reply = await ws.recv()
            return URPMessage.from_json(reply, payload_cls=urp_msg.payload.__class__)
