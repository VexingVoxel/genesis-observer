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
var debug_count = 0

const VOXEL_RES = 128
const AGENT_COUNT = 100
const HEADER_SIZE = 48
const VOXEL_PAYLOAD_SIZE = 128 * 128 * 4

func _ready():
	print("Connecting to HIFI bridge (Phase 3)...")
	socket.inbound_buffer_size = 1024 * 1024 * 4 # 4MB Buffer
	socket.max_queued_packets = 2048
	socket.connect_to_url("ws://localhost:8080")
	
	# Initialize Voxel Texture
	var img = Image.create(VOXEL_RES, VOXEL_RES, false, Image.FORMAT_RGBA8)
	world_texture = ImageTexture.create_from_image(img)
	texture_rect.texture = world_texture
	texture_rect.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	
	# Initialize Agents
	setup_multimesh()

func setup_multimesh():
	var arr_mesh = ArrayMesh.new()
	var vertices = PackedVector2Array([
		Vector2(0, -10),  # Top
		Vector2(6, 8),   # Bottom Right
		Vector2(-6, 8)   # Bottom Left
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
			var expected = HEADER_SIZE + VOXEL_PAYLOAD_SIZE + (AGENT_COUNT * 64)
			if packet.size() == expected:
				parse_and_render(packet)
					
	elif state == WebSocketPeer.STATE_CLOSED:
		status_label.text = "Bridge: OFFLINE"
		status_label.modulate = Color.RED

func parse_and_render(data: PackedByteArray):
	# 1. Parse Header
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
	var texture_size = 512.0
	var scale_factor = texture_size / VOXEL_RES
	
	for i in range(AGENT_COUNT):
		var ptr = agent_offset + (i * 64)
		var px = data.decode_float(ptr)
		var py = data.decode_float(ptr + 4)
		var rot = data.decode_float(ptr + 24)
		
		var screen_pos = Vector2(
			(px * scale_factor) - 256.0,
			(py * scale_factor) - 256.0
		)
		
				var t = Transform2D(rot, screen_pos)
		
				
		
				if i == 0:
		
					mm.set_instance_transform_2d(i, t.scaled(Vector2(1.5, 1.5)))
		
					mm.set_instance_color(i, Color.CYAN) # Cognitive Agent
		
				else:
		
					mm.set_instance_transform_2d(i, t)
		
					mm.set_instance_color(i, Color.WHITE) # Drifting Crowd
		
		