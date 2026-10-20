extends SceneTree
## Automated protocol checks against a deliberately isolated local server; never port 10300.
var config := {}
var client
var logged := false
var login_code := 0
var characters: Array = []
var got_characters := false
var world_events := {}
var raw_packets := {}
var position := {}
var npcs := {}
var messages: Array = []
var report := {"steps": [], "errors": []}
var output := ""

func _initialize() -> void:
	Engine.max_fps = 60
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--probe-config="):
			var f := FileAccess.open(arg.trim_prefix("--probe-config="), FileAccess.READ)
			if f != null:
				var data = JSON.parse_string(f.get_as_text())
				if data is Dictionary: config = data
	run.call_deferred()

func until(predicate: Callable, seconds: float) -> bool:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000)
	while not predicate.call() and Time.get_ticks_msec() < deadline:
		await process_frame
	return predicate.call()

func run() -> void:
	if config.get("host") != "127.0.0.1" or int(config.get("port", 10300)) == 10300:
		push_error("Compatibility probe requires an isolated loopback endpoint")
		quit(2)
		return
	output = String(config.get("report", ""))
	report.endpoint = {"host": config.host, "port": config.port}
	client = load("res://game/net/DaocClient.cs").new()
	if not client.SetProtocolProfile(String(config.get("profile", "offline"))):
		finish("invalid_protocol_profile")
		return
	report.profile = client.ProtocolProfile
	root.add_child(client)
	client.LoggedIn.connect(func(_account: String, _server: String):logged = true)
	client.LoginFailed.connect(func(code: int):login_code = code)
	client.Characters.connect(func(realm: int, rows: Array):
		if realm == 3:
			characters = rows
			got_characters = true)
	client.World.connect(func(kind: String, data: Dictionary):
		world_events[kind] = int(world_events.get(kind, 0)) + 1
		if kind == "you": position = data
		if kind == "npc": npcs[int(data.oid)] = data
		if kind == "message": messages.append(data.duplicate()))
	client.Packet.connect(func(code: int, _bytes: PackedByteArray):raw_packets[str(code)] = int(raw_packets.get(str(code), 0)) + 1)
	if not client.OpenAt(config.host, int(config.port)):
		finish("connection_failed")
		return
	report.steps.append("connected_to_isolated_port")
	client.Login(config.account, config.password)
	if not await until(func():return logged or login_code != 0, 20):
		finish("login_timeout")
		return
	if login_code != 0:
		report.login_error_code = login_code
		finish("login_rejected")
		return
	report.steps.append("login_accepted")
	client.RequestCharacters(3)
	if not await until(func():return got_characters, 20):
		finish("character_list_timeout")
		return
	report.character_count = characters.size()
	report.steps.append("hibernia_character_list_received")
	if config.get("create", false) and characters.is_empty():
		client.CreateCharacter({"realm": 3, "slot": 0, "name": config.character, "class_id": 47, "race": 9, "gender": 0,
			"model": 302, "face": [68, 68, 0, 0, 0, 0, 0], "stats": [70, 60, 70, 60, 60, 60, 70, 60]})
		# Creation is acknowledged by another login grant. Requesting the list after a short bounded wait also
		# handles servers whose creation reply has no separate operation signal.
		var deadline := Time.get_ticks_msec() + 2000
		while Time.get_ticks_msec() < deadline: await process_frame
		got_characters = false
		client.RequestCharacters(3)
		if not await until(func():return got_characters, 20) or characters.is_empty():
			finish("character_creation_failed")
			return
		report.steps.append("synthetic_character_created")
		report.character_count = characters.size()
	if config.get("enter_world", false):
		if characters.is_empty():
			finish("no_character")
			return
		var chosen: Dictionary = characters[0]
		client.EnterWorld(3, int(chosen.get("slot", 0)), String(chosen.get("name", "")))
		if not await until(func():return not position.is_empty(), 30):
			finish("world_position_timeout")
			return
		report.steps.append("world_position_received")
		client.PlayerInit()
		client.GameOpen()
		var deadline := Time.get_ticks_msec() + 6000
		while Time.get_ticks_msec() < deadline:
			await process_frame
		report.steps.append("world_initialized_over_tcp")
		report.position = position
		report.npcs = npcs.values()
		if config.has("interact_name"):
			var target := {}
			for npc in npcs.values():
				if String(npc.get("name", "")) == String(config.interact_name):
					target = npc
					break
			if target.is_empty():
				finish("interaction_npc_not_received")
				return
			var prior_messages := messages.size()
			var prior_trainer := int(world_events.get("trainer", 0))
			client.Target(int(target.oid), 0)
			client.Interact(int(target.oid), int(position.x), int(position.y))
			var reply_deadline := Time.get_ticks_msec() + 3000
			while Time.get_ticks_msec() < reply_deadline: await process_frame
			report.interaction = {"npc": target.name, "messages": messages.slice(prior_messages),
				"trainer_replies": int(world_events.get("trainer", 0)) - prior_trainer}
			if config.get("expect_interaction_reply", false) and messages.size() == prior_messages and int(report.interaction.trainer_replies) == 0:
				finish("npc_interaction_no_reply")
				return
			report.steps.append("npc_interaction_requested")
		if config.has("move_zone"):
			var moved := {"x": float(position.x) + 80, "y": float(position.y), "z": float(position.z)}
			client.Position(moved.x, moved.y, moved.z, 80.0, 0.0, int(config.move_zone), 0, true, int(position.heading), 0, 100, int(position.oid))
			report.movement_target = moved
			report.steps.append("two_metre_movement_sent")
			var move_deadline := Time.get_ticks_msec() + 2000
			while Time.get_ticks_msec() < move_deadline: await process_frame
	report.world_events = world_events
	report.raw_packet_counts = raw_packets
	finish("")

func finish(error: String) -> void:
	if not error.is_empty(): report.errors.append(error)
	report.ok = error.is_empty()
	if client != null: client.Close()
	if not output.is_empty():
		var f := FileAccess.open(output, FileAccess.WRITE)
		if f != null: f.store_string(JSON.stringify(report, "  "))
	print("COMPATIBILITY_PROBE ok=", report.ok, " steps=", report.steps, " errors=", report.errors)
	quit(0 if report.ok else 3)
