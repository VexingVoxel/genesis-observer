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
AGENT_COUNT = 100
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
# ...
    while True:
        try:
            packet = subscriber.recv(flags=zmq.NOBLOCK)
            total_bytes_received += len(packet)
            
            global debug_packet_count
            if debug_packet_count < 10:
                print(f"DEBUG: Bridge Recv ZMQ Packet {debug_packet_count}: {len(packet)} bytes", flush=True)
                debug_packet_count += 1

            # --- Binary Sync Check ---
            if len(packet) != EXPECTED_PACKET_SIZE:
                if debug_packet_count < 20:
                    print(f"ERR: Size mismatch! Got {len(packet)}, expected {EXPECTED_PACKET_SIZE}", flush=True)
                continue

            magic = struct.unpack("<I", packet[0:4])[0]
            if magic != MAGIC_BYTE:
                continue

            # --- Injection: Use padding_a (offset 4) for Node 2 status ---
            packet_mutable = bytearray(packet)
            packet_mutable[4] = 1 if node2_online else 0
            
            # Forward raw binary to all connected clients
            if connected_clients:
                # Use websockets opcode for binary
                await asyncio.gather(*[client.send(packet_mutable) for client in connected_clients], return_exceptions=True)
                
        except zmq.Again:
            pass # No packet ready
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
    
    # Start Presence Listener (UDP Port 5558)
    print("Starting Node 2 Presence Listener on UDP 5558...", flush=True)
    try:
        await loop.create_datagram_endpoint(
            lambda: Node2PresenceProtocol(),
            local_addr=('0.0.0.0', 5558)
        )
    except Exception as e:
        print(f"UDP Listener Error: {e}", flush=True)

    # Start Tasks
    asyncio.create_task(zmq_subscriber_task())
    asyncio.create_task(telemetry_reporter_task())
    
    async with websockets.serve(handler, "localhost", 8080):
        print("WebSocket Server Listening on 8080...", flush=True)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"FATAL ERROR: {e}", flush=True)