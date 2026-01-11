extends Control

@onready var status_label = $HUD/HBox/Status
@onready var tick_label = $HUD/HBox/Tick
@onready var tps_label = $HUD/HBox/TPS
@onready var compute_label = $HUD/HBox/Compute
@onready var int_label = $HUD/HBox/INT
@onready var texture_rect = $TextureDisplay
@onready var agent_visualizer = $AgentLayer/AgentMultiMesh

var socket = WebSocketPeer.new()
var world_texture: ImageTexture

const VOXEL_RES = 128
const AGENT_COUNT = 100
const HEADER_SIZE = 48
const VOXEL_PAYLOAD_SIZE = 128 * 128 * 4

func _ready():
	print("Connecting to HIFI bridge (Phase 3)...")
	socket.inbound_buffer_size = 1024 * 1024 # 1MB Buffer
	socket.max_queued_packets = 64
	socket.connect_to_url("ws://localhost:8080")
	
	# 1. Initialize the Voxel Texture Display
	var img = Image.create(VOXEL_RES, VOXEL_RES, false, Image.FORMAT_RGBA8)
	world_texture = ImageTexture.create_from_image(img)
	texture_rect.texture = world_texture
	texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	
	# 2. Initialize the Agent MultiMesh
	setup_multimesh()

func setup_multimesh():
	var mesh = PlaceholderMesh.new() # We'll use a simple quad for now
	# Creating a small triangle-like shape
	var arr_mesh = ArrayMesh.new()
	var vertices = PackedVector2Array([
		Vector2(0, -4),  # Top
		Vector2(3, 4),   # Bottom Right
		Vector2(-3, 4)   # Bottom Left
	])
	var arrays = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arr_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	
	var mm = MultiMesh.new()
	mm.mesh = arr_mesh
	mm.use_colors = true
	mm.instance_count = AGENT_COUNT
	agent_visualizer.multimesh = mm

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		status_label.text = "Bridge: ONLINE"
		status_label.modulate = Color.GREEN
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			# Protocol v3 size check
			if packet.size() == HEADER_SIZE + VOXEL_PAYLOAD_SIZE + (AGENT_COUNT * 64):
				parse_and_render(packet)
					
	elif state == WebSocketPeer.STATE_CLOSED:
		status_label.text = "Bridge: OFFLINE"
		status_label.modulate = Color.RED

func parse_and_render(data: PackedByteArray):
	# 1. Parse Header (v3 Offsets)
	var node2_status = data.decode_u32(4)
	var tick = data.decode_u64(8)
	var compute_ms = data.decode_float(24)
	var tps = data.decode_float(28)
	
	# 2. Update HUD
	tick_label.text = "Tick: " + str(tick)
	tps_label.text = "Sim: %.1f TPS" % tps
	compute_label.text = "GPU: %.2f ms" % compute_ms
	
	if node2_status == 1:
		int_label.text = "AI Hub: ONLINE"
		int_label.modulate = Color.GREEN
	else:
		int_label.text = "AI Hub: OFFLINE"
		int_label.modulate = Color.RED
	
	# 3. Extract and Render Voxels
	var voxel_data = data.slice(HEADER_SIZE, HEADER_SIZE + VOXEL_PAYLOAD_SIZE)
	var img = Image.create_from_data(VOXEL_RES, VOXEL_RES, false, Image.FORMAT_RGBA8, voxel_data)
	world_texture.update(img)
	
	# 4. Extract and Render Agents
	var agent_offset = HEADER_SIZE + VOXEL_PAYLOAD_SIZE
	var mm = agent_visualizer.multimesh
	
	# Map world space to screen space
	# TextureRect is centered at offset_left -256, offset_top -200, width 512, height 512
	var world_to_screen_scale = 512.0 / 128.0 
	
	for i in range(AGENT_COUNT):
		var ptr = agent_offset + (i * 64)
		var px = data.decode_float(ptr)
		var py = data.decode_float(ptr + 4)
		# var pz = data.decode_float(ptr + 8)
		var rot = data.decode_float(ptr + 24)
		var vitals = data.decode_u32(ptr + 28)
		var hunger = vitals & 0xFF
		
		# Calculate Transform
		# Position is relative to the TextureDisplay center
		var screen_pos = Vector2(px * world_to_screen_scale - 256, py * world_to_screen_scale - 200)
		var t = Transform2D(rot, screen_pos)
		mm.set_instance_transform_2d(i, t)
		
		# Color based on hunger (White -> Red)
		var h_factor = float(hunger) / 255.0
		mm.set_instance_color(i, Color(1.0, 1.0 - h_factor, 1.0 - h_factor))
