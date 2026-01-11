import zmq
import asyncio
import websockets
import subprocess
import os
import sys
import time
import threading
import signal

# --- CONFIG ---
NODE1_IP = "192.168.50.29"
ZMQ_ADDR = f"tcp://{NODE1_IP}:5555"
WS_PORT = 8080
BASE_DIR = "/home/scott.johnson/home-lab"
GODOT_BIN = f"{BASE_DIR}/bin/godot"
PROJECT_DIR = f"{BASE_DIR}/projects/genesis/observer"

connected_clients = set()
godot_process = None

def log(msg):
    print(f"[*] {msg}", flush=True)

def cleanup_stray_processes():
    log("Cleaning up existing observer processes...")
    subprocess.run(["fuser", "-k", f"{WS_PORT}/tcp"], capture_output=True)
    subprocess.run(["pkill", "-f", f"{GODOT_BIN}"], capture_output=True)
    time.sleep(1)

async def zmq_subscriber_task():
    log(f"ZMQ Subscriber connecting to {ZMQ_ADDR}...")
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect(ZMQ_ADDR)
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    
    log("ZMQ Subscriber Thread Active.")
    
    while True:
        if subscriber.poll(100):
            try:
                message = subscriber.recv_string()
                # log(f"DEBUG: Received packet from ZMQ") # Highly verbose
                if connected_clients:
                    await asyncio.gather(*[client.send(message) for client in connected_clients], return_exceptions=True)
            except Exception as e:
                log(f"ZMQ Error: {e}")
        await asyncio.sleep(0.001)

async def ws_handler(websocket):
    log("Godot Client Connected to WebSocket!")
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        log("Godot Client Disconnected.")

async def start_server():
    asyncio.create_task(zmq_subscriber_task())
    log(f"Starting WebSocket Server on {WS_PORT}...")
    async with websockets.serve(ws_handler, "localhost", WS_PORT):
        await asyncio.Future()

def run_bridge():
    try:
        asyncio.run(start_server())
    except Exception as e:
        log(f"Bridge Thread Error: {e}")

def signal_handler(sig, frame):
    log("Shutdown signal received. Cleaning up...")
    if godot_process:
        godot_process.terminate()
    sys.exit(0)

if __name__ == "__main__":
    log("--- Genesis Master Launcher starting ---")
    
    cleanup_stray_processes()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bridge_thread = threading.Thread(target=run_bridge, daemon=True)
    bridge_thread.start()
    
    env = os.environ.copy()
    env["DISPLAY"] = ":1"
    env["XAUTHORITY"] = "/run/user/1000/gdm/Xauthority"
    
    log("Launching Godot UI...")
    godot_process = subprocess.Popen(
        [GODOT_BIN, "--path", PROJECT_DIR],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    log("Launcher ACTIVE. Close Godot to exit.")
    
    try:
        while godot_process.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
        
    log("Godot closed. Exiting.")
    if godot_process:
        godot_process.terminate()
    sys.exit(0)
