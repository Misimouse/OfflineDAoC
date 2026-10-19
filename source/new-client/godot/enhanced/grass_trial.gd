extends SceneTree
## Standalone Ardee graphics laboratory. Never starts or connects to a server.
var world: Node3D
var zone
var sky
var cam: Camera3D
var grass
var original_clutter
var title: Label
var stats: Label
var enabled := true
var view_index := 0
var centre := Vector2(1364.0, 1263.0)
var args := {}
var output := ""
var measurements: Array = []
var motion := false
var motion_time := 0.0

func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=", true, 1)
		args[kv[0]] = kv[1] if kv.size() > 1 else ""
	output = String(args.get("out", OS.get_user_data_dir()))
	DirAccess.make_dir_recursive_absolute(output)
	run.call_deferred()

func run() -> void:
	root.size = Vector2i(1600, 900)
	if args.has("4k"):
		root.size = Vector2i(3840, 2160)
	root.title = "Enhanced - Hierba 3D en Ardee"
	Engine.max_fps = 0
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	world = Node3D.new()
	root.add_child(world)
	zone = load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207", "blend", "x4plus")
	cam = Camera3D.new()
	cam.fov = 60
	cam.far = 1500
	world.add_child(cam)
	cam.make_current()
	sky = load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone, cam, "x4plus")
	sky.set_hour(14)
	sky.time_scale = 0
	sky.storm_forced = 0
	sky.set_process(false)
	original_clutter = load("res://game/clutter.gd").new()
	world.add_child(original_clutter)
	original_clutter.setup(zone, cam)
	grass = load("res://enhanced/grass_patch.gd").new()
	world.add_child(grass)
	grass.build(zone, centre, Vector2(3.8, 5.0))
	var layer := CanvasLayer.new()
	world.add_child(layer)
	title = Label.new()
	title.position = Vector2(20, 18)
	title.add_theme_font_size_override("font_size", 23)
	title.add_theme_color_override("font_shadow_color", Color.BLACK)
	title.add_theme_constant_override("shadow_outline_size", 5)
	layer.add_child(title)
	stats = Label.new()
	stats.position = Vector2(20, 95)
	stats.add_theme_font_size_override("font_size", 18)
	layer.add_child(stats)
	var buttons := HBoxContainer.new()
	buttons.position = Vector2(20, 135)
	layer.add_child(buttons)
	for entry in [["A - Original", func():set_enabled(false)], ["B - Hierba 3D", func():set_enabled(true)], ["Cerca", func():set_view(0)], ["Jugando", func():set_view(1)], ["Conjunto", func():set_view(2)], ["Movimiento", func():motion = not motion], ["Viento", func():grass.animate = not grass.animate], ["Luz", func():toggle_light()], ["Salir", func():quit(0)]]:
		var button := Button.new()
		button.text = entry[0]
		button.custom_minimum_size = Vector2(140, 42)
		button.focus_mode = Control.FOCUS_NONE
		button.pressed.connect(entry[1])
		buttons.add_child(button)
	set_view(0)
	set_enabled(true)
	print("GRASS_LAB_READY resolution=", root.size)
	if args.has("capture"):
		await capture_and_measure()
		if not args.has("keep-open"):
			quit(0)
		else:
			set_view(1)
			set_enabled(true)

func set_enabled(value: bool) -> void:
	enabled = value
	grass.visible = value
	title.text = ("B - HIERBA 3D" if enabled else "A - ORIGINAL") + " | Ardee, junto al pozo\nMismo escenario, hora 14:00. Parcela experimental; sin servidor."

func set_view(which: int) -> void:
	view_index = which
	motion = false
	motion_time = 0.0
	var h: float = zone.height_at(centre.x, centre.y)
	var target := Vector3(centre.x, h + 0.12, centre.y)
	if which == 0:
		cam.position = target + Vector3(1.5, 1.35, 4.5)
	elif which == 1:
		cam.position = target + Vector3(4.5, 1.7, 10.0)
	else:
		cam.position = target + Vector3(8, 9, 18)
	cam.look_at(target)

func toggle_light() -> void:
	sky.set_hour(17 if sky.game_seconds < 16.0 * 3600 else 14)

func _process(delta: float) -> bool:
	if cam == null or zone == null:
		return false
	if motion:
		motion_time += delta * 0.28
		var h: float = zone.height_at(centre.x, centre.y)
		var target := Vector3(centre.x, h + 0.15, centre.y)
		cam.position = target + Vector3(sin(motion_time) * 7, 1.7, cos(motion_time) * 7)
		cam.look_at(target)
	if stats != null:
		stats.text = "%d FPS | %s | %d grupos de briznas | Viento: %s" % [Engine.get_frames_per_second(), str(root.size), grass.instances if enabled else 0, "si" if grass.animate else "pausado"]
	return false

func capture_and_measure() -> void:
	grass.animate = false
	grass.clock = 1.25
	if original_clutter._material != null:
		original_clutter._material.set_shader_parameter("sway", 0.0)
	for view in [0, 1, 2]:
		set_view(view)
		# Balanced A/B/B/A order reduces the bias of shader/cache warm-up and time drift.
		for choice in [false, true, true, false]:
			set_enabled(choice)
			for frame in 90:
				await process_frame
			var frame_times: Array[float] = []
			var started := Time.get_ticks_usec()
			var previous := started
			for frame in 180:
				await process_frame
				var now := Time.get_ticks_usec()
				frame_times.append(float(now - previous) / 1000.0)
				previous = now
			var elapsed := float(Time.get_ticks_usec() - started) / 1000.0
			frame_times.sort()
			var row := {"view": view, "grass": choice, "resolution": [root.size.x, root.size.y], "frames": 180, "mean_ms": elapsed / 180.0, "p95_ms": frame_times[int(frame_times.size() * 0.95)], "fps": 180000.0 / elapsed, "instances": grass.instances, "triangles_added": grass.triangles}
			measurements.append(row)
			print("GRASS_MEASURE=", JSON.stringify(row))
			await RenderingServer.frame_post_draw
			var file := "%s_%s.png" % [["cerca", "jugando", "conjunto"][view], "hierba" if choice else "original"]
			if root.get_texture().get_image().save_png(output.path_join(file)) != OK:
				push_error("Capture failed")
				quit(4)
				return
	var result := {"measurements": measurements, "note": "Static camera, same sky, no server or NPCs, VSync disabled; not whole-game performance. Original clutter is enabled in both variants. Grass shadows disabled.", "gpu": RenderingServer.get_video_adapter_name()}
	var file := FileAccess.open(output.path_join("mediciones.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t"))
	print("GRASS_COMPARISON_PASS")
	grass.animate = true
	if original_clutter._material != null:
		original_clutter._material.set_shader_parameter("sway", 0.06)
