import zmq
import asyncio
import websockets
import struct
import time
import socket
import sys

# Constants from Phase 2.5 Plan
NODE1_IP = "192.168.50.29"
ZMQ_ADDR = f"tcp://{NODE1_IP}:5555"
MAGIC_BYTE = 0xDEADBEEF
EXPECTED_PAYLOAD_SIZE = 128 * 128 * 4
EXPECTED_PACKET_SIZE = 40 + EXPECTED_PAYLOAD_SIZE

# MVT State
connected_clients = set()
node2_online = False
node2_last_seen = 0
total_bytes_received = 0
last_telemetry_time = time.time()

class Node2PresenceProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        global node2_online, node2_last_seen
        if addr[0] == "192.168.50.22": # Node 2 IP
            node2_online = True
            node2_last_seen = time.time()

async def telemetry_reporter_task():
    global total_bytes_received, last_telemetry_time, node2_online
    while True:
        await asyncio.sleep(1.0)
        now = time.time()
        duration = now - last_telemetry_time
        mbps = (total_bytes_received * 8) / (1024 * 1024 * duration)
        
        # Check Node 2 Timeout (5 seconds)
        if now - node2_last_seen > 5.0:
            node2_online = False
            
        print(f"[MVT] Throughput: {mbps:.2f} Mbps | Node 2: {'ONLINE' if node2_online else 'OFFLINE'}", flush=True)
        
        total_bytes_received = 0
        last_telemetry_time = now

async def zmq_subscriber_task():
    global total_bytes_received
    print(f"ZMQ Subscriber Task Starting (Binary Mode)...", flush=True)
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    
    # Apply Conflate to match Node 1 policy
    subscriber.setsockopt(zmq.CONFLATE, 1)
    subscriber.connect(ZMQ_ADDR)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    
    print(f"Connected to ZMQ: {ZMQ_ADDR}", flush=True)

    while True:
        # We use NOBLOCK to stay reactive to client changes
        try:
            packet = subscriber.recv(flags=zmq.NOBLOCK)
            total_bytes_received += len(packet)

            # --- Binary Sync Check ---
            if len(packet) != EXPECTED_PACKET_SIZE:
                print(f"ERR: Packet size mismatch. Got {len(packet)}, expected {EXPECTED_PACKET_SIZE}", flush=True)
                continue

            magic = struct.unpack("<I", packet[0:4])[0]
            if magic != MAGIC_BYTE:
                print(f"ERR: Magic Byte mismatch (Got {hex(magic)}). Dropping frame.", flush=True)
                continue

            # Forward raw binary to all Godot clients
            if connected_clients:
                await asyncio.gather(*[client.send(packet) for client in connected_clients], return_exceptions=True)
                
        except zmq.Again:
            pass # No packet ready
        
        await asyncio.sleep(0.001) # Maintain 1ms responsiveness

async def handler(websocket):
    print(f"Godot Client Connected!", flush=True)
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"Godot Client Disconnected.", flush=True)

async def main():
    print("--- Genesis HIFI Bridge Starting ---", flush=True)
    
    loop = asyncio.get_running_loop()
    
    # Start Presence Listener (UDP Port 5558)
    print("Starting Node 2 Presence Listener on UDP 5558...", flush=True)
    await loop.create_datagram_endpoint(
        lambda: Node2PresenceProtocol(),
        local_addr=('0.0.0.0', 5558)
    )

    # Start Tasks
    asyncio.create_task(zmq_subscriber_task())
    asyncio.create_task(telemetry_reporter_task())
    
    async with websockets.serve(handler, "localhost", 8080):
        print("WebSocket Server Listening on 8080 (Binary Mode)...", flush=True)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)