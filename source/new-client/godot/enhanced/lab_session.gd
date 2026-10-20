extends SceneTree
## Local developer entry point. Credentials stay in a private file, never process arguments.
var config := {}
var server
var state_file := ""
var quit_file := ""
var quitting := false
var ready := false
var quit_ack_at := -1
var finishing := false

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--session-config="):
			var f := FileAccess.open(arg.trim_prefix("--session-config="), FileAccess.READ)
			if f != null:
				var data = JSON.parse_string(f.get_as_text())
				if data is Dictionary: config = data
	run.call_deferred()
	if config.get("self_test", false): Engine.max_fps = 60

func status(stage: String, message: String) -> void:
	if state_file.is_empty(): return
	var f := FileAccess.open(state_file, FileAccess.WRITE)
	if f != null: f.store_string(JSON.stringify({"stage": stage, "message": message}, "  "))

func until(predicate: Callable, seconds: float) -> bool:
	var deadline := Time.get_ticks_msec() + int(seconds * 1000)
	while not predicate.call() and Time.get_ticks_msec() < deadline:
		await process_frame
	return predicate.call()

func fail(message: String) -> void:
	status("error", message)
	if server != null and server.client != null: server.client.Close()
	quit(3)

func run() -> void:
	server = root.get_node("Server")
	state_file = String(config.get("state_file", ""))
	quit_file = String(config.get("quit_file", ""))
	if config.get("host") != "127.0.0.1" or int(config.get("port", 0)) != 10310 or config.get("profile") != "lab":
		fail("El acceso requiere la copia local del LAB en su puerto de pruebas.")
		return
	if server.active or server.client != null:
		fail("Ya existe otra conexión en este cliente.")
		return
	server.host = config.host
	server.server_port = int(config.port)
	server.protocol_profile = "lab"
	server.account = config.account
	server.password = config.password
	server.active = true
	server._ready()
	# This standalone entry point owns final shutdown, instead of returning to the character screen.
	server.client.World.disconnect(server._on_world)
	server.client.World.connect(on_world)
	server.login_failed.connect(func(why: String):status("error", "El LAB ha rechazado el acceso: " + why))
	status("login", "Conectando con nuestra cuenta de pruebas…")
	server.start()
	if not await until(func():return server.logged, 30):
		fail("No se ha completado el acceso al LAB.")
		return
	server.request_characters("hib")
	if not await until(func():return not server.characters_in("hib").is_empty(), 30):
		fail("No se ha recibido el personaje de Hibernia.")
		return
	var chosen := {}
	for character in server.characters_in("hib"):
		if character.name == config.character: chosen = character
	if chosen.is_empty():
		fail("No se encuentra el personaje de pruebas esperado.")
		return
	status("world", "Cargando Ardee y sus habitantes…")
	server.enter_world(chosen)
	if not await until(func():return server.playing and current_scene != null, 180):
		fail("No se ha completado la carga de Ardee.")
		return
	if int(server.entry.get("zone", -1)) != 207:
		server.quit_world(true)
		status("error", "El personaje está fuera de Connacht. Hay que devolverlo a Ardee en la copia de pruebas.")
		return
	# Server.playing becomes true before the loading overlay has finished fading.
	if not await until(func():return not is_instance_valid(current_scene.get("loading")), 30):
		fail("La escena no ha terminado de retirar la pantalla de carga.")
		return
	var tree_trial = load("res://enhanced/trees/elm_trial.gd").new()
	current_scene.add_child(tree_trial)
	tree_trial.attach(current_scene.get("region"))
	root.title = "DAoC Enhanced — Ardee LAB (copia de pruebas)"
	ready = true
	status("ready", "Ardee lista. Al salir se cerrará también el servidor de pruebas.")

func on_world(kind: String, data: Dictionary) -> void:
	if kind != "quit":
		server._on_world(kind, data)
		return
	quit_ack_at = Time.get_ticks_msec()
	server.playing = false
	server.client.Close()
	finish_session.call_deferred()

func finish_session() -> void:
	if finishing: return
	finishing = true
	status("closing", "Salida confirmada. Cerrando la escena…")
	# Drain scene resources while the render loop is alive; pending vegetation work is cancelled first.
	if current_scene != null:
		var scene := current_scene
		status("closing", "Salida confirmada. Terminando las cargas pendientes…")
		if is_instance_valid(scene.get("npcs")): await scene.npcs.prepare_shutdown()
		if is_instance_valid(scene.get("region")): await scene.region.prepare_shutdown()
		if scene.get("clutters") is Dictionary:
			for clutter in scene.clutters.values():
				if clutter.has_method("set_enhanced"): clutter.set_enhanced(false)
		current_scene = null
		scene.queue_free()
	await process_frame
	await process_frame
	status("closed", "El servidor ha confirmado la salida del personaje.")
	quit()

func _process(_delta: float) -> bool:
	if not quitting and not quit_file.is_empty() and FileAccess.file_exists(quit_file):
		quitting = true
		status("closing", "Guardando el personaje y cerrando la prueba…")
		if server != null and server.playing: server.quit_world(true)
		else: quit()
	return false
