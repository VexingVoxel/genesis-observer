import zmq
import struct
import time

# Simulation Config (Protocol v3)
ADDR = "tcp://127.0.0.1:5555"
MAGIC_BYTE = 0xDEADBEEF
AGENT_COUNT = 100
EXPECTED_PACKET_SIZE = 48 + (128 * 128 * 4) + (AGENT_COUNT * 64)

def send_packet(socket, magic, tick):
    # Header v3: 48 bytes
    header = struct.pack("<IIQqffHHH BBBB I H", 
        magic, 
        0,              # Padding A
        tick, 
        int(time.time() * 1e6), 
        0.15,           # Compute ms
        60.0,           # TPS
        128, 128,       # Res
        AGENT_COUNT,
        0, 0, 0, 0,     # Padding B-E
        0,              # Padding F
        0               # Padding G
    )
    voxels = b'\x01' * (128 * 128 * 4) # Fill with "Dirt" ID
    agents = b'\x00' * (AGENT_COUNT * 64)
    socket.send(header + voxels + agents)

def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(ADDR)
    
    print("--- Binary Sync Test Utility v3 Starting ---")
    print(f"Binding to {ADDR}")
    time.sleep(1)

    tick = 0
    try:
        for _ in range(3):
            # 1. Send Valid Packet
            print(f"[TEST] Sending Valid v3 Packet (Tick {tick})")
            send_packet(socket, MAGIC_BYTE, tick)
            tick += 1
            time.sleep(1)

            # 2. Send Malformed Packet (Wrong Magic)
            print("[TEST] Sending Malformed Packet (Wrong Magic)")
            send_packet(socket, 0xBADBEEF, tick)
            tick += 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("Test stopped.")

if __name__ == "__main__":
    main()