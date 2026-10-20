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
var patches: Array = []
var site_index := 0
var sites := [Vector2(1364, 1263), Vector2(1190, 1180)]
var life: Array = []

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
	root.title = "Enhanced - Flores, insectos y plantas altas"
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
	original_clutter = load("res://enhanced/selective_clutter.gd").new()
	world.add_child(original_clutter)
	original_clutter.setup(zone, cam)
	await physics_frame
	await physics_frame
	for site in 2:
		var patch = load("res://enhanced/landscape_patch.gd").new()
		patch.centre = sites[site]
		patch.bounds = Rect2(sites[site] - Vector2(7, 11), Vector2(14, 22))
		patch.green_profile = site == 1
		world.add_child(patch)
		patch.build(zone, sites[site], Vector2(6.2, 9.7))
		patch.set_active(false)
		patches.append(patch)
		var insects = load("res://enhanced/flower_insects.gd").new()
		patch.add_child(insects)
		insects.setup(patch, 207991 + site)
		life.append(insects)
	grass = patches[0]
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
	for entry in [["A - Original", func():set_enabled(false)], ["B - Paisaje", func():set_enabled(true)], ["Pozo", func():set_site(0)], ["Ladera", func():set_site(1)], ["Cerca", func():set_view(0)], ["Jugando", func():set_view(1)], ["Conjunto", func():set_view(2)], ["Flores", func():set_view(3)], ["Movimiento", func():motion = not motion], ["Viento", func():grass.animate = not grass.animate], ["Insectos", func():life[site_index].visible = not life[site_index].visible], ["Luz", func():toggle_light()], ["Salir", func():quit(0)]]:
		var button := Button.new()
		button.text = entry[0]
		button.custom_minimum_size = Vector2(100, 42)
		button.focus_mode = Control.FOCUS_NONE
		button.pressed.connect(entry[1])
		buttons.add_child(button)
	set_view(0)
	set_enabled(true)
	print("LANDSCAPE_LAB_READY resolution=", root.size)
	if args.has("detail-capture"):
		set_site(1)
		set_view(3)
		for frame in 90:
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join("detalle_insectos.png"))
		quit(0)
		return
	if args.has("capture"):
		await capture_and_measure()
		if not args.has("keep-open"):
			quit(0)
		else:
			set_view(1)
			set_enabled(true)

func set_enabled(value: bool) -> void:
	enabled = value
	for patch in patches:
		patch.set_active(false)
	grass.set_active(value)
	original_clutter.set_cleanup(value, centre)
	title.text = ("B - COBERTURA BAJA" if enabled else "A - ORIGINAL") + " | " + ["Pozo de Ardee: suelo mixto", "Ladera junto a Ardee: suelo verde original"][site_index] + "\nComparacion local, sin servidor. Pozo y Ladera cambian el entorno."

func set_site(which: int) -> void:
	site_index = which
	centre = sites[which]
	grass = patches[which]
	set_view(view_index)
	set_enabled(enabled)

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
	elif which == 2:
		cam.position = target + Vector3(8, 9, 18)
	else:
		target = life[site_index].actors[0].node.position
		cam.position = target + Vector3(0.5, 0.35, 0.85)
	cam.position.y = maxf(cam.position.y, zone.height_at(cam.position.x, cam.position.z) + (0.4 if which == 3 else 1.65))
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
		cam.position.y = maxf(cam.position.y, zone.height_at(cam.position.x, cam.position.z) + 1.65)
		cam.look_at(target)
	elif view_index == 3 and not life.is_empty():
		var target: Vector3 = life[site_index].actors[0].node.position
		cam.position = target + Vector3(0.5, 0.35, 0.85)
		cam.position.y = maxf(cam.position.y, zone.height_at(cam.position.x, cam.position.z) + 0.4)
		cam.look_at(target)
	if stats != null:
		stats.text = "%d FPS | %s | %d plantas | Viento: %s" % [Engine.get_frames_per_second(), str(root.size), grass.instances if enabled else 0, "si" if grass.animate else "pausado"]
	return false

func capture_and_measure() -> void:
	for patch in patches:
		patch.animate = false
		patch.clock = 1.25
	if original_clutter._material != null:
		original_clutter._material.set_shader_parameter("sway", 0.0)
	for site in [0, 1]:
		set_site(site)
		for view in [0, 1]:
			set_view(view)
			for choice in [false, true, true, false]:
				set_enabled(choice)
				for frame in 45:
					await process_frame
				var frame_times: Array[float] = []
				var started := Time.get_ticks_usec()
				var previous := started
				for frame in 120:
					await process_frame
					var now := Time.get_ticks_usec()
					frame_times.append(float(now - previous) / 1000.0)
					previous = now
				var elapsed := float(Time.get_ticks_usec() - started) / 1000.0
				frame_times.sort()
				var row := {"site": site, "view": view, "grass": choice, "resolution": [root.size.x, root.size.y], "frames": 120, "mean_ms": elapsed / 120.0, "p95_ms": frame_times[int(frame_times.size() * 0.95)], "fps": 120000.0 / elapsed, "instances": grass.instances, "low_cover": grass.low_cover_instances, "triangles_added": grass.triangles}
				measurements.append(row)
				print("COVER_MEASURE=", JSON.stringify(row))
				await RenderingServer.frame_post_draw
				var name := "%s_%s_%s.png" % [["pozo", "ladera"][site], ["cerca", "jugando"][view], "paisaje" if choice else "original"]
				if root.get_texture().get_image().save_png(output.path_join(name)) != OK:
					push_error("Capture failed")
					quit(4)
					return
		# Record actual routes and motion near flowers, with the cleaned scene active.
		set_enabled(true)
		for frame in 60:
			await process_frame
		var motion_before: Dictionary = life[site].snapshot()
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join(["pozo", "ladera"][site] + "_vuelo_antes.png"))
		for frame in 120:
			await process_frame
		var motion_after: Dictionary = life[site].snapshot()
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(output.path_join(["pozo", "ladera"][site] + "_vuelo_despues.png"))
		var ecology_file := FileAccess.open(output.path_join(["pozo", "ladera"][site] + "_vida.json"), FileAccess.WRITE)
		ecology_file.store_string(JSON.stringify({"before": motion_before, "after": motion_after, "removed_undergrowth": original_clutter.removed_counts, "preserved": "All original seed/tall grasses: filter only group 6 undergrowth within 26m"}, "\t"))
		var prefix: String = ["pozo", "ladera"][site]
		grass.coverage.save_png(output.path_join(prefix + "_mascara.png"))
		var placement_file := FileAccess.open(output.path_join(prefix + "_plantas.json"), FileAccess.WRITE)
		placement_file.store_string(JSON.stringify({"counts": grass.counts, "positions": grass.plant_positions, "ground_material_clones": grass.ground_materials.size(), "low_cover": grass.low_cover_instances, "centre": [centre.x, centre.y], "green_profile": grass.green_profile}, "\t"))
	var result := {"measurements": measurements, "note": "Static A/B/B/A at two sites. 45 warmup/120 measured frames per segment. No server/NPCs. Original clutter in both variants. Hillside terrain material is untouched; no brown soil override there.", "gpu": RenderingServer.get_video_adapter_name()}
	var file := FileAccess.open(output.path_join("mediciones.json"), FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "\t"))
	print("COVER_COMPARISON_PASS")
	for patch in patches:
		patch.animate = true
	if original_clutter._material != null:
		original_clutter._material.set_shader_parameter("sway", 0.06)
