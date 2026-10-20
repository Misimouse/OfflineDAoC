extends SceneTree
## Headless CPU/physics streaming check over 72 metres in Connacht; not a GPU/FPS benchmark.
var args := {}
func _initialize() -> void:
	Engine.max_fps = 60
	for arg in OS.get_cmdline_user_args():
		var pair := arg.trim_prefix("--").split("=", true, 1)
		if pair.size() == 2: args[pair[0]] = pair[1]
	run.call_deferred()
func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var zone = load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207", "blend", "x4plus")
	var viewer := Node3D.new()
	zone.add_child(viewer)
	viewer.position = Vector3(1190, zone.height_at(1190, 1180) + 2, 1180)
	await physics_frame
	await physics_frame
	var clutter = load(String(args.get("clutter-script", "res://enhanced/replant/replant_clutter.gd"))).new()
	clutter.override_bundle = args.get("bundle", "")
	zone.add_child(clutter)
	if not clutter.setup(zone, viewer) or clutter.plan.is_empty():
		quit(3)
		return
	var samples: Array[float] = []
	var cold_samples: Array[float] = []
	var maximum_chunks := 0
	var maximum_instances := 0
	var marker := Time.get_ticks_usec()
	var warm_deadline := Time.get_ticks_msec() + 120000
	while clutter.chunk_plants.size() < 9 and Time.get_ticks_msec() < warm_deadline:
		await process_frame
		var now := Time.get_ticks_usec()
		cold_samples.append(float(now - marker) / 1000.0)
		marker = now
	if clutter.chunk_plants.size() < 9:
		quit(5)
		return
	var start := Time.get_ticks_usec()
	var cold_seconds := float(start - (warm_deadline - 120000) * 1000) / 1000000.0
	while float(Time.get_ticks_usec() - start) / 1000000.0 < 18:
		var distance := minf(72, float(Time.get_ticks_usec() - start) / 1000000.0 * 4)
		var x := 1190.0 + distance
		viewer.position = Vector3(x, zone.height_at(x, 1180) + 2, 1180)
		await process_frame
		var now := Time.get_ticks_usec()
		samples.append(float(now - marker) / 1000.0)
		marker = now
		maximum_chunks = maxi(maximum_chunks, clutter.chunk_plants.size())
		var count := 0
		for patch in clutter.chunk_plants.values():
			if is_instance_valid(patch): count += int(patch.get_meta("instances", 0))
		maximum_instances = maxi(maximum_instances, count)
	samples.sort()
	cold_samples.sort()
	var result := {"zone": 207, "route_metres": 72, "headless_cpu_check": true, "fps_cap": 60,
		"walking_mps": 4, "cold_seconds_to_nine_parcels": cold_seconds, "cold_max_frame_ms": cold_samples[-1],
		"max_new_chunks": maximum_chunks, "max_instances": maximum_instances,
		"max_frame_ms": samples[-1], "p95_frame_ms": samples[int(samples.size() * 0.95)],
		"frames_over_50ms": samples.filter(func(ms):return ms > 50).size(),
		"bounded": maximum_chunks <= 9 and maximum_instances <= 9 * int(clutter.options.get("chunk_budget", 20000))}
	var f := FileAccess.open(String(args.get("out", "user://traversal_report.json")), FileAccess.WRITE)
	f.store_string(JSON.stringify(result, "  "))
	print("TRAVERSAL_CHECK ", JSON.stringify(result))
	quit(0 if result.bounded else 4)
