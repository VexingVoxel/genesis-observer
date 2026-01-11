import subprocess
import os
import sys
import time
import signal

# --- CONFIG ---
BASE_DIR = "/home/scott.johnson/home-lab"
GODOT_BIN = f"{BASE_DIR}/bin/godot"
PROJECT_DIR = f"{BASE_DIR}/projects/genesis/observer"
BRIDGE_SCRIPT = f"{PROJECT_DIR}/bridge.py"
WS_PORT = 8080

godot_process = None
bridge_process = None

def log(msg):
    print(f"[*] {msg}", flush=True)

def cleanup_stray_processes():
    log("Cleaning up existing observer processes...")
    # Use fuser directly if possible, then ssh as backup
    subprocess.run(["fuser", "-k", f"{WS_PORT}/tcp"], capture_output=True)
    subprocess.run(["ssh", "admin@localhost", f"sudo fuser -k {WS_PORT}/tcp"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", f"{GODOT_BIN}"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", f"python3 {BRIDGE_SCRIPT}"], capture_output=True)
    time.sleep(2)

def signal_handler(sig, frame):
    log("Shutdown signal received. Cleaning up...")
    if godot_process:
        godot_process.terminate()
    if bridge_process:
        bridge_process.terminate()
    sys.exit(0)

if __name__ == "__main__":
    log("--- Genesis Master Launcher starting (Phase 2.5) ---")
    
    cleanup_stray_processes()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 1. Start Bridge Process
    log("Starting Protocol Bridge...")
    bridge_process = subprocess.Popen(
        [sys.executable, BRIDGE_SCRIPT],
        stdout=sys.stdout, # Forward bridge output to launcher console for MVT visibility
        stderr=sys.stderr
    )
    
    time.sleep(1) # Wait for bridge to bind
    
    # 2. Start Godot UI
    env = os.environ.copy()
    env["DISPLAY"] = ":1"
    # Ensure X authority is correctly set if needed
    if "XAUTHORITY" not in env:
        env["XAUTHORITY"] = f"/run/user/{os.getuid()}/gdm/Xauthority"
    
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
            # Monitor bridge health
            if bridge_process.poll() is not None:
                log("FATAL: Bridge process died unexpectedly.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
        
    log("Godot closed or interrupt received. Exiting.")
    if godot_process:
        godot_process.terminate()
    if bridge_process:
        bridge_process.terminate()
    sys.exit(0)