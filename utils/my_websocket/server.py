import asyncio
import websockets

class WebSocketServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.server = None

    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                # 在这里处理从客户端接收的消息
                print(f"Received message: {message}")
                await self.broadcast_message(message)
        except websockets.exceptions.ConnectionClosedError:
            pass
        finally:
            self.clients.remove(websocket)

    async def broadcast_message(self, message):
        if self.clients:
            await asyncio.gather(*(client.send(message) for client in self.clients))

    async def start(self):
        self.server = await websockets.serve(self.handle_client, self.host, self.port)
        await self.server.wait_closed()

    async def stop(self):
        if self.server:
            self.server.close()

if __name__ == "__main__":
    # 实例化WebSocketServer类
    server = WebSocketServer("localhost", 8765)
    
    try:
        asyncio.get_event_loop().run_until_complete(server.start())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.get_event_loop().run_until_complete(server.stop())
