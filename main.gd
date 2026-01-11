extends Control

@onready var status_label = $VBoxContainer/Status
@onready var tick_label = $VBoxContainer/Tick
@onready var tps_label = $VBoxContainer/TPS
@onready var compute_label = $VBoxContainer/Compute
@onready var texture_rect = $TextureDisplay

var socket = WebSocketPeer.new()
var world_texture: ImageTexture

func _ready():
	print("Connecting to HIFI bridge...")
	socket.inbound_buffer_size = 1024 * 1024 # 1MB Buffer
	socket.max_queued_packets = 64
	socket.connect_to_url("ws://localhost:8080")
	
	# Initialize the Texture Display
	# We use 128x128 to match the full simulation slice
	var img = Image.create(128, 128, false, Image.FORMAT_RGBA8)
	world_texture = ImageTexture.create_from_image(img)
	texture_rect.texture = world_texture
	
	# Ensure the TextureRect is set to "Nearest" filtering to see raw voxels
	texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		status_label.text = "Bridge: ONLINE"
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			
			# Protocol Phase 2.5: 40-byte header + (128*128*4) payload
			if packet.size() == 40 + (128 * 128 * 4):
				parse_and_render(packet)
			else:
				print("Unexpected packet size: ", packet.size())
					
	elif state == WebSocketPeer.STATE_CLOSED:
		status_label.text = "Bridge: OFFLINE"
		# Optional: Auto-reconnect
		# socket.connect_to_url("ws://localhost:8080")

func parse_and_render(data: PackedByteArray):
	# 1. Parse Header (Offsets from Plan)
	# magic = data.decode_u32(0) 
	var tick = data.decode_u64(8)
	# var timestamp = data.decode_s64(16)
	var compute_ms = data.decode_float(24)
	var tps = data.decode_float(28)
	
	# 2. Update HUD
	tick_label.text = "World Tick: " + str(tick)
	tps_label.text = "Sim Speed: %.2f TPS" % tps
	compute_label.text = "GPU Latency: %.2f ms" % compute_ms
	
	# 3. Extract Voxel Payload (Starting at offset 40)
	var payload = data.slice(40)
	
	# 4. Inject into GPU Texture
	var img = Image.create_from_data(128, 128, false, Image.FORMAT_RGBA8, payload)
	world_texture.update(img)