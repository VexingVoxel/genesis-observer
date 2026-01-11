import zmq
import struct
import time

# Simulation Config
ADDR = "tcp://127.0.0.1:5555"
MAGIC_BYTE = 0xDEADBEEF
EXPECTED_PACKET_SIZE = 40 + (128 * 128 * 4)

def send_packet(socket, magic, tick):
    header = struct.pack("<IIQQffHH I", 
        magic, 
        0,              # Padding A
        tick, 
        int(time.time() * 1e6), 
        0.15,           # Compute ms
        60.0,           # TPS
        128, 128,       # Res
        0               # Padding B
    )
    payload = b'\x01' * (128 * 128 * 4) # Fill with "Dirt" ID
    socket.send(header + payload)

def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(ADDR)
    
    print("--- Binary Sync Test Utility Starting ---")
    print(f"Binding to {ADDR}")
    time.sleep(1)

    tick = 0
    try:
        for _ in range(3):
            # 1. Send Valid Packet
            print(f"[TEST] Sending Valid Packet (Tick {tick})")
            send_packet(socket, MAGIC_BYTE, tick)
            tick += 1
            time.sleep(1)

            # 2. Send Malformed Packet (Wrong Magic)
            print("[TEST] Sending Malformed Packet (Wrong Magic)")
            send_packet(socket, 0xBADBEEF, tick)
            tick += 1
            time.sleep(1)

            # 3. Send Wrong Size Packet
            print("[TEST] Sending Malformed Packet (Wrong Size)")
            socket.send(b"SMALL_PACKET")
            time.sleep(1)

    except KeyboardInterrupt:
        print("Test stopped.")

if __name__ == "__main__":
    main()
