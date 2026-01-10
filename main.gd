extends Control

@onready var status_label = $VBoxContainer/Status
@onready var tick_label = $VBoxContainer/Tick
@onready var host_label = $VBoxContainer/Host

var socket = WebSocketPeer.new()

func _ready():
	print("Connecting to bridge...")
	socket.connect_to_url("ws://localhost:8080")

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		status_label.text = "Bridge Status: ONLINE"
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			var json_str = packet.get_string_from_utf8()
			var data = JSON.parse_string(json_str)
			if data:
				tick_label.text = "Current Tick: " + str(data["tick"])
				host_label.text = "Source Node: " + str(data["node_name"])
	elif state == WebSocketPeer.STATE_CLOSED:
		status_label.text = "Bridge Status: OFFLINE (Reconnecting...)"
		socket.connect_to_url("ws://localhost:8080")
