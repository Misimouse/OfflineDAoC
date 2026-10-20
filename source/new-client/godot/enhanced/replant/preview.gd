extends SceneTree
var world: Node3D
var zone
var cam: Camera3D
var clutter
var sky
var label: Label
var args := {}
var enabled := true
var elapsed := 0.0
var move := true
func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		var pair := a.trim_prefix("--").split("=", true, 1)
		args[pair[0]] = pair[1] if pair.size() > 1 else ""
	run.call_deferred()
func run() -> void:
	root.size = Vector2i(3840, 2160) if args.has("4k") else Vector2i(1280, 800)
	root.title = "Enhanced - Vista previa Hibernia (sin ToA)"
	Engine.max_fps = 60
	var bundle := String(args.get("bundle", ""))
	var file := FileAccess.open(bundle.path_join("zone%03d/plan.json" % int(args.get("zone", 207))), FileAccess.READ)
	if file == null:
		push_error("No prepared plan for requested zone")
		quit(2)
		return
	var plan: Dictionary = JSON.parse_string(file.get_as_text())
	if int(plan.get("region", -1)) not in [181, 200]:
		quit(3)
		return
	world = Node3D.new()
	root.add_child(world)
	zone = load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone(plan.source, "blend", "x4plus")
	cam = Camera3D.new()
	cam.fov = 60
	cam.far = 1200
	world.add_child(cam)
	cam.make_current()
	var point: Dictionary = plan.preview_points[0] if not plan.preview_points.is_empty() else {"x": 800, "z": 800}
	var x := float(args.get("x", point.x))
	var z := float(args.get("z", point.z))
	var target := Vector3(x, zone.height_at(x, z) + 0.15, z)
	cam.position = target + Vector3(1.5, 1.6, 4.5)
	cam.position.y = maxf(cam.position.y, zone.height_at(cam.position.x, cam.position.z) + 1.4)
	cam.look_at(target)
	sky = load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone, cam, "x4plus")
	sky.set_hour(14)
	sky.time_scale = 0
	sky.storm_forced = 0
	sky.set_process(false)
	await physics_frame
	await physics_frame
	clutter = load("res://enhanced/replant/replant_clutter.gd").new()
	clutter.override_bundle = bundle
	zone.add_child(clutter)
	clutter.setup(zone, cam)
	var layer := CanvasLayer.new()
	world.add_child(layer)
	label = Label.new()
	label.position = Vector2(20, 18)
	label.add_theme_font_size_override("font_size", 18)
	label.add_theme_color_override("font_shadow_color", Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size", 6)
	layer.add_child(label)
	var buttons := HBoxContainer.new()
	buttons.position = Vector2(20, 95)
	layer.add_child(buttons)
	for entry in [["A - Original", func():toggle(false)], ["B - Replantado", func():toggle(true)], ["Salir", func():quit()]]:
		var b := Button.new()
		b.text = entry[0]
		b.custom_minimum_size = Vector2(140, 38)
		b.pressed.connect(entry[1])
		buttons.add_child(b)
	print("REPLANT_PREVIEW_READY zone=", zone.info.id, " valid_plan=", not clutter.plan.is_empty())
	if args.has("capture"):
		move = false
		var output := String(args.get("out", OS.get_user_data_dir()))
		DirAccess.make_dir_recursive_absolute(output)
		var record := {"bundle": bundle, "viewport": [root.size.x, root.size.y], "fps_cap": Engine.max_fps, "options": clutter.options, "zone": int(zone.info.id), "valid_plan": not clutter.plan.is_empty(), "camera": [cam.position.x, cam.position.y, cam.position.z], "measurements": []}
		for b in [false, true]:
			toggle(b)
			for f in 100:
				await process_frame
			var settle_deadline := Time.get_ticks_msec() + 60000
			while not clutter.is_settled() and Time.get_ticks_msec() < settle_deadline:
				await process_frame
			if not clutter.is_settled():
				push_error("Vegetation did not finish preparing within the capture warmup")
				quit(5)
				return
			var started := Time.get_ticks_usec()
			for f in 120:
				await process_frame
			var elapsed_us := Time.get_ticks_usec() - started
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(output.path_join("zone%d_%s.png" % [zone.info.id, "B" if b else "A"]))
			var count := 0
			for patch in clutter.chunk_plants.values():
				count += int(patch.get_meta("instances", 0))
			record.measurements.append({"enhanced": b, "instances": count, "fps": 120000000.0 / elapsed_us, "removed": clutter.removed_counts.duplicate()})
		var f := FileAccess.open(output.path_join("zone%d_report.json" % zone.info.id), FileAccess.WRITE)
		f.store_string(JSON.stringify(record, "  "))
		quit(0 if not clutter.plan.is_empty() else 4)
func toggle(value: bool) -> void:
	enabled = value
	clutter.set_enhanced(value)
func _process(delta: float) -> bool:
	if cam == null or label == null or clutter == null:
		return false
	elapsed += delta
	if move:
		var dir := Vector3.ZERO
		if Input.is_physical_key_pressed(KEY_W): dir.z -= 1
		if Input.is_physical_key_pressed(KEY_S): dir.z += 1
		if Input.is_physical_key_pressed(KEY_A): dir.x -= 1
		if Input.is_physical_key_pressed(KEY_D): dir.x += 1
		if Input.is_physical_key_pressed(KEY_Q): dir.y -= 1
		if Input.is_physical_key_pressed(KEY_E): dir.y += 1
		cam.position += cam.basis * dir * delta * (15 if Input.is_physical_key_pressed(KEY_SHIFT) else 4)
		cam.position.y = maxf(cam.position.y, zone.height_at(cam.position.x, cam.position.z) + 0.5)
	var count := 0
	for patch in clutter.chunk_plants.values():
		if is_instance_valid(patch): count += int(patch.get_meta("instances", 0))
	label.text = "%s | %s | %d plantas | %s | %.0f FPS\nWASD mover Â· Q/E altura Â· Boton derecho mirar Â· Espacio A/B Â· Esc salir" % [zone.info.get("name", str(zone.info.id)), "B - Replantado" if enabled else "A - Original", count, ("Falta preparar plantas" if clutter.cache_misses > 0 else ("Listo" if clutter.is_settled() else "Cargando plantas")), Engine.get_frames_per_second()]
	return false
func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE: quit()
		if event.keycode == KEY_SPACE and clutter != null: toggle(not enabled)
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if event.pressed else Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		cam.rotation.y -= event.relative.x * 0.003
		cam.rotation.x = clampf(cam.rotation.x - event.relative.y * 0.003, -1.4, 1.4)
