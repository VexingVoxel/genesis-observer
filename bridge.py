import zmq
import asyncio
import websockets
import json

# ZMQ Config
NODE1_IP = "192.168.50.29"
ZMQ_ADDR = f"tcp://{NODE1_IP}:5555"

async def bridge(websocket):
    print(f"Godot connected to bridge!")
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(ZMQ_ADDR)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    
    print(f"Subscribed to Node 1: {ZMQ_ADDR}")

    while True:
        if subscriber.poll(100):
            message = subscriber.recv_string()
            # Forward directly to Godot
            await websocket.send(message)
        await asyncio.sleep(0.01)

async def main():
    print("--- Genesis Godot Bridge Starting (WS Port 8080) ---")
    async with websockets.serve(bridge, "localhost", 8080):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
