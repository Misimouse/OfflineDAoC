extends SceneTree
## A bounded visual check of the normal game scene against an isolated local server.
var config := {}
var output := ""
var report := {"errors": [], "checks": []}
var freeze_light := false
var server

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
	server = root.get_node("Server")
	output = String(config.get("output", ""))
	if config.get("host") != "127.0.0.1" or int(config.get("port", 10300)) == 10300 or output.is_empty():
		push_error("Gameplay check requires an isolated loopback endpoint and an output directory")
		quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output)
	root.size = Vector2i(1600, 900)
	if server.active or server.client != null:
		fail("unexpected_existing_connection")
		return
	# The ordinary autoload returned early because no --server was supplied. Initialize that normal path
	# using the disposable account file, so its password never appears in a process argument or report.
	server.host = config.host
	server.server_port = int(config.port)
	server.protocol_profile = String(config.get("profile", "offline"))
	server.account = config.account
	server.password = config.password
	server.active = true
	server._ready()
	server.client.Realm.connect(func(realm_id: int):report["realm_reply"] = realm_id)
	server.start()
	if not await until(func():return server.logged, 30):
		fail("login_timeout")
		return
	# Select Hibernia as the normal realm screen does; LAB must not prefetch another realm and assign it.
	if server.protocol_profile == "lab": server.request_characters("hib")
	if not await until(func():return not server.characters_in("hib").is_empty(), 30):
		fail("login_or_character_list_timeout")
		return
	report.checks.append("normal_server_autoload_logged_in")
	server.enter_world(server.characters_in("hib")[0])
	if not await until(func():return server.playing and current_scene != null, 180):
		fail("normal_zone_scene_timeout")
		return
	root.title = "Enhanced - Ardee - servidor aislado 10310"
	report.checks.append("normal_zone_scene_loaded")
	report.zone = int(server.entry.get("zone", -1))
	var scene = current_scene
	freeze_light = true
	if report.zone != 207:
		fail("unexpected_zone")
		return
	var warmup := Time.get_ticks_msec() + 20000
	while Time.get_ticks_msec() < warmup: await process_frame
	if config.get("dismiss_startup_dialogs", false):
		# Disposable LAB account only: decline its startup teleport, then hide the welcome text for the A/B.
		var declined := 0
		for button in root.find_children("*", "Button", true, false):
			if button.is_visible_in_tree() and button.text == "DECLINE":
				button.pressed.emit()
				declined += 1
		if scene.ui.windows.has("info"): scene.ui.windows.info.hide()
		report.startup_dialogs = {"declined": declined, "info_window_hidden": true}
	var photos: Array = []
	for enabled in [false, true]:
		for clutter in scene.clutters.values():
			if clutter.has_method("set_enhanced"): clutter.set_enhanced(enabled)
		var warm := Time.get_ticks_msec() + 6000
		while Time.get_ticks_msec() < warm: await process_frame
		var settle_deadline := Time.get_ticks_msec() + 90000
		var settled := false
		while not settled and Time.get_ticks_msec() < settle_deadline:
			settled = true
			for clutter in scene.clutters.values():
				if clutter.has_method("is_settled") and not clutter.is_settled(): settled = false
			if not settled: await process_frame
		if not settled:
			fail("vegetation_preparation_timeout")
			return
		await RenderingServer.frame_post_draw
		var name := "Ardee_jugable_%s.png" % ("B" if enabled else "A")
		root.get_texture().get_image().save_png(output.path_join(name))
		var plants := 0
		var plans := 0
		for clutter in scene.clutters.values():
			if not clutter.plan.is_empty(): plans += 1
			for patch in clutter.chunk_plants.values():
				if is_instance_valid(patch): plants += int(patch.get_meta("instances", 0))
		photos.append({"enhanced": enabled, "file": name, "new_plant_groups": plants, "loaded_plans": plans,
			"npc_states": scene.npcs.states.size(), "fps_instantaneous": Engine.get_frames_per_second()})
	report.photos = photos
	report.checks.append("normal_scene_A_B_captured")
	report.checks.append("server_quit_requested")
	write_report()
	server.quit_world(true)
	var deadline := Time.get_ticks_msec() + 35000
	while Time.get_ticks_msec() < deadline:
		await process_frame
	fail("graceful_quit_timeout")

func _process(_delta: float) -> bool:
	if freeze_light:
		server.game_time_ms = 14 * 3600000
		server.game_time_at = Time.get_ticks_msec()
		server.day_increment = 0
	return false

func write_report() -> void:
	var f := FileAccess.open(output.path_join("gameplay_report.json"), FileAccess.WRITE)
	if f != null: f.store_string(JSON.stringify(report, "  "))

func fail(reason: String) -> void:
	report.errors.append(reason)
	report.server_state = {"logged": server.logged, "allowed_realm": server.allowed_realm,
		"asking": server._asking, "profile": server.protocol_profile,
		"character_realms": server.characters.keys(), "raw_packets": server.raw_seen,
		"last_error": server.last_error}
	if not output.is_empty(): write_report()
	if server.client != null: server.client.Close()
	quit(3)
