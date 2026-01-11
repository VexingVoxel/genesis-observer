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
# ...
	if state == WebSocketPeer.STATE_OPEN:
		if status_label.text != "Bridge: ONLINE":
			print("WebSocket Connected! State: OPEN")
		status_label.text = "Bridge: ONLINE"
		status_label.modulate = Color.GREEN
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			
			if debug_count < 10:
				print("GODOT RECV Packet ", debug_count, ": ", packet.size(), " bytes")
				debug_count += 1
			
			var expected = HEADER_SIZE + VOXEL_PAYLOAD_SIZE + (AGENT_COUNT * 64)
			if packet.size() != expected:
				if debug_count < 20:
					print("GODOT ERR: Size mismatch! Got ", packet.size(), " expected ", expected)
				debug_count += 1
				continue
			
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
