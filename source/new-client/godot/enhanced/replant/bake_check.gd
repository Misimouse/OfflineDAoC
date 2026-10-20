extends SceneTree
## Precompute a bounded development area with real zone collisions, without a server.
var args := {}
func _initialize() -> void:
	Engine.max_fps = 120
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
	await physics_frame
	await physics_frame
	var clutter = load("res://enhanced/replant/replant_clutter.gd").new()
	clutter.allow_generation = true
	clutter.override_bundle = args.bundle
	zone.add_child(clutter)
	if not clutter.setup(zone, viewer) or clutter.plan.is_empty():
		quit(3)
		return
	clutter.set_process(false)
	var chunks := []
	var started := Time.get_ticks_msec()
	for z in range(int(args.get("z0", 35)), int(args.get("z1", 42)) + 1):
		for x in range(int(args.get("x0", 36)), int(args.get("x1", 45)) + 1):
			var c := Vector2i(x,z)
			clutter._start_job(c)
			while not clutter._job.is_empty():
				clutter._advance_job()
				await process_frame
			var cached: Dictionary = clutter._read_cached(c)
			if cached.is_empty():
				push_error("Prepared chunk was not cached: " + str(c))
				quit(5)
				return
			chunks.append({"x":x,"z":z,"instances":cached.accepted})
			clutter.chunk_plants[c].queue_free()
			clutter.chunk_plants.erase(c)
			clutter.chunk_cells.erase(c)
			print("BAKED ", chunks.size(), " ", c, " instances=", cached.accepted)
			write_status("working", "Preparadas %d parcelas de Ardee..." % chunks.size())
	var report := {"cache_namespace":clutter.cache_namespace,"chunks":chunks,"hits":clutter.cache_hits,"misses":clutter.cache_misses,"seconds":(Time.get_ticks_msec()-started)/1000.0}
	var file := FileAccess.open(String(args.out),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	write_status("done", "%d parcelas de Ardee preparadas fuera del juego." % chunks.size())
	print("BAKE_CHECK_OK ",chunks.size())
	quit()

func write_status(state: String, message: String) -> void:
	if not args.has("status"): return
	var f:=FileAccess.open(String(args.status),FileAccess.WRITE)
	if f != null: f.store_string(JSON.stringify({"status":state,"message":message}))
