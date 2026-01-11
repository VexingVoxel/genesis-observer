extends Control

@onready var status_label = $VBoxContainer/Status
@onready var tick_label = $VBoxContainer/Tick
@onready var tps_label = $VBoxContainer/TPS
@onready var compute_label = $VBoxContainer/Compute
@onready var int_label = $VBoxContainer/INT
@onready var texture_rect = $TextureDisplay

var socket = WebSocketPeer.new()
var world_texture: ImageTexture

func _ready():
	print("Connecting to HIFI bridge...")
	socket.inbound_buffer_size = 1024 * 1024 # 1MB Buffer
	socket.max_queued_packets = 64
	socket.connect_to_url("ws://localhost:8080")
	
	# Initialize the Texture Display
	var img = Image.create(128, 128, false, Image.FORMAT_RGBA8)
	world_texture = ImageTexture.create_from_image(img)
	texture_rect.texture = world_texture
	texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		status_label.text = "Bridge: ONLINE"
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			if packet.size() == 40 + (128 * 128 * 4):
				parse_and_render(packet)
					
	elif state == WebSocketPeer.STATE_CLOSED:
		status_label.text = "Bridge: OFFLINE"

func parse_and_render(data: PackedByteArray):
	# 1. Parse Header
	var node2_status = data.decode_u32(4)
	var tick = data.decode_u64(8)
	var compute_ms = data.decode_float(24)
	var tps = data.decode_float(28)
	
	# 2. Update HUD
	tick_label.text = "World Tick: " + str(tick)
	tps_label.text = "Sim Speed: %.2f TPS" % tps
	compute_label.text = "GPU Latency: %.2f ms" % compute_ms
	
	if node2_status == 1:
		int_label.text = "Intelligence: ONLINE"
		int_label.modulate = Color.GREEN
	else:
		int_label.text = "Intelligence: OFFLINE"
		int_label.modulate = Color.RED
	
	# 3. Extract and Render
	var payload = data.slice(40)
	var img = Image.create_from_data(128, 128, false, Image.FORMAT_RGBA8, payload)
	world_texture.update(img)
