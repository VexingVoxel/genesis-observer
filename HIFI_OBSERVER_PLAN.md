# Engineering Plan: High-Fidelity Binary Observer & Telemetry (Phase 2.5)

## I. Objective
Transition the **Project Genesis** communication protocol from JSON-based messaging to a high-performance **Zero-Copy Binary Stream**. This leverages the 1Gb LAN infrastructure and RTX-tier GPUs to render the entire world at 60 FPS while integrating **Minimal Viable Telemetry (MVT)** for real-time cluster health monitoring.

## II. Pre-Requirements & Constraints
- **Bandwidth Budget:** 64 KB per frame @ 60 FPS = **3.8 MB/s** (~3.1% of 1Gb LAN capacity).
- **Endianness:** **Little-Endian (LE)** mandatory across all nodes.
- **VRAM Budget:** ~64 KB per texture slice; negligible impact on RTX 4070.
- **Visual Target:** 60Hz real-time update of $128 \times 128$ voxel world.

## III. Technical Specifications

### 1. The Binary Protocol (Aligned & Signed)
A fixed 40-byte header (Little-Endian) will precede the voxel data. This ensures the voxel payload starts on an 8-byte boundary for optimal GPU performance.
- `[00-03]` : **Magic Byte** (`0xDEADBEEF`)
- `[04-07]` : **Padding A** (Alignment)
- `[08-15]` : **Tick Count** (uint64)
- `[16-23]` : **Timestamp** (int64, microseconds)
- `[24-27]` : **Compute Latency** (float32)
- `[28-31]` : **TPS** (float32)
- `[32-33]` : **Width** (uint16)
- `[34-35]` : **Height** (uint16)
- `[36-39]` : **Padding B** (Alignment) - **Ensures payload starts at offset 40.**
- `[40-...]` : **Raw Voxel Data** ($128 \times 128 \times 4$ bytes)


### 2. Voxel-to-Pixel Mapping (Image.FORMAT_RGBA8)
The 32-bit `Voxel` struct is interpreted directly as an RGBA8 pixel in the Godot GPU:
- **Red (R)**: Voxel ID (Material Index).
- **Green (G)**: Dynamic State (Biological age/status).
- **Blue (B)**: Thermal Data (0-255 mapped temperature).
- **Alpha (A)**: Light/Visibility data.

## IV. Detailed Execution Roadmap

### Step 1: Simulation Core (Node: `genesis-compute`)
- **Telemetry Logic:** Wrap `queue.submit()` and `wait()` in high-resolution timers.
- **Messaging:** Configure `ZMQ_CONFLATE=1` and `ZMQ_SNDHWM=1` to prevent "stutter" during lag.
- **Zero-Copy:** Use `std::slice::from_raw_parts` to cast the GPU-readback buffer into the byte stream.
- **Path:** `/home/admin/core/src/main.rs`

### Step 2: Protocol Bridge (Node: `pop-os`)
- **Sync Engine:** Implement a "sliding window" check for `0xDEADBEEF`. If sync is lost, scan the stream until the next magic byte.
- **MVT:** Track `bytes_received` per second and send a periodic "Network Health" JSON packet to Godot.
- **Presence:** Listen for a UDP heartbeat from `node2` (Intelligence) to confirm the AI is online.
- **Path:** `projects/genesis/observer/bridge.py`

### Step 3: Observer UI (Node: `pop-os`)
- **Header Parsing:** Use `data.slice(0, 40)` to extract telemetry and `data.slice(40)` for the payload.
- **GPU Upload:** Use `Image.create_from_data()` followed by `ImageTexture.update()`.
- **HUD Design:** Create a dedicated `CanvasLayer` with labels for `TPS`, `LATENCY`, and `NET_MBPS`.
- **Shader:** Write a GLSL fragment shader that uses `texture(tex, uv).r` as an index into a `Color` array.

## V. Testing Infrastructure (Automated)

1.  **Rust Unit Tests:**
    - `test_header_size`: `assert_eq!(size_of::<TelemetryHeader>(), 40)`.
    - `test_byte_order`: Confirm `0xDEADBEEF` is stored as `[0xEF, 0xBE, 0xAD, 0xDE]`.
2.  **Python Integration Tests:**
    - `test_sync.py`: Send a buffer with random garbage followed by a valid packet; verify the bridge re-aligns.
3.  **Godot Assertions:**
    - `assert(packet.size() == 40 + (128 * 128 * 4))` before rendering.

## VI. Hard Stop Checkpoints

### [STOP 1] Protocol Handshake
**Validation:** `tail -f bridge.log` shows `Tick: 5000 | Latency: 0.21ms | Sync: OK`.
**Status:** REQUIRED before Godot UI changes.

### [STOP 2] Network Saturation Check
**Validation:** `nload` on laptop confirms ~4MB/s. If > 10MB/s, check for redundant packet copies.

### [STOP 3] Visual Fidelity Audit
**Validation:** Visual confirmation of smooth Green (Grass) growth patterns and readable HUD telemetry.

## VII. Redesign Policy (Binary Mandatory)

There is no fallback to JSON or Base64. High-performance binary transmission is a core requirement. If binary synchronization or parsing fails, we will halt all development to perform a **Root Cause Analysis (RCA)** and redesign the protocol/buffer management until 60Hz stability is achieved.



## VIII. Operational Protocol (Halt & Report)

If any significant deviation from this plan is detected during implementation—including changes to the byte header layout, network topology, or rendering logic—work must **HALT immediately**. 



The agent must inform the user, explain the reason for the deviation, and wait for explicit confirmation before attempting a new course of action. This ensures total alignment with the lab's performance and architectural goals.


