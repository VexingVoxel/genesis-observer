import zmq
import asyncio
import websockets
import struct
import time
import socket
import sys

# Constants from Phase 3 Plan (Protocol v3)
NODE1_IP = "192.168.50.29"
ZMQ_ADDR = f"tcp://{NODE1_IP}:5555"
MAGIC_BYTE = 0xDEADBEEF
VOXEL_PAYLOAD_SIZE = 128 * 128 * 4
AGENT_COUNT = 5
AGENT_PAYLOAD_SIZE = AGENT_COUNT * 64
EXPECTED_PACKET_SIZE = 48 + VOXEL_PAYLOAD_SIZE + AGENT_PAYLOAD_SIZE

# MVT State
connected_clients = set()
node2_online = False
node2_last_seen = 0
total_bytes_received = 0
last_telemetry_time = time.time()
debug_packet_count = 0

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
        
        if now - node2_last_seen > 5.0:
            node2_online = False
            
        print(f"[MVT] Throughput: {mbps:.2f} Mbps | Node 2: {'ONLINE' if node2_online else 'OFFLINE'}", flush=True)
        total_bytes_received = 0
        last_telemetry_time = now

async def zmq_subscriber_task():
    global total_bytes_received, debug_packet_count
    print(f"--- Bridge ZMQ Thread Active ---", flush=True)
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.CONFLATE, 1)
    subscriber.connect(ZMQ_ADDR)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    
    while True:
        try:
            packet = subscriber.recv(flags=zmq.NOBLOCK)
            total_bytes_received += len(packet)
            
            if debug_packet_count < 10:
                print(f"DEBUG: Bridge RECV {len(packet)} bytes (Target: {EXPECTED_PACKET_SIZE})", flush=True)
                debug_packet_count += 1

            if len(packet) != EXPECTED_PACKET_SIZE:
                if debug_packet_count < 20:
                    print(f"DEBUG: Size Mismatch! Got {len(packet)}", flush=True)
                    debug_packet_count += 1
                continue

            magic = struct.unpack("<I", packet[0:4])[0]
            if magic != MAGIC_BYTE:
                continue

            # Inject Node 2 Status
            packet_mutable = bytearray(packet)
            packet_mutable[4] = 1 if node2_online else 0
            
            if connected_clients:
                await asyncio.gather(*[client.send(packet_mutable) for client in connected_clients], return_exceptions=True)
                
        except zmq.Again:
            pass
        except Exception as e:
            print(f"ZMQ ERR: {e}", flush=True)
        
        await asyncio.sleep(0.001)

async def handler(websocket):
    print(f"Godot Client Connected!", flush=True)
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"Godot Client Disconnected.", flush=True)

async def main():
    print("--- Genesis HIFI Bridge Starting (Phase 3) ---", flush=True)
    loop = asyncio.get_running_loop()
    
    # UDP Presence Listener
    await loop.create_datagram_endpoint(
        lambda: Node2PresenceProtocol(),
        local_addr=('0.0.0.0', 5558)
    )

    asyncio.create_task(zmq_subscriber_task())
    asyncio.create_task(telemetry_reporter_task())
    
    async with websockets.serve(handler, "localhost", 8080):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
