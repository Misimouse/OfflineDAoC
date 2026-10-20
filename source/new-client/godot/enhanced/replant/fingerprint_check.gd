extends SceneTree
## Stable per-chunk placement fingerprint, independent of chunk build order.
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
	if args.get("npc-picks", "") == "true":
		for i in 12:
			var pick := StaticBody3D.new()
			pick.collision_layer = 1 << 9
			pick.collision_mask = 0
			var shape := CollisionShape3D.new()
			var capsule := CapsuleShape3D.new()
			capsule.radius = 0.6
			capsule.height = 2
			shape.shape = capsule
			pick.add_child(shape)
			var x := 1188.0 + float(i % 4) * 2
			var z := 1177.0 + float(i / 4) * 2
			zone.add_child(pick)
			pick.position = Vector3(x, zone.height_at(x, z) + 1, z)
	await physics_frame
	await physics_frame
	var clutter = load("res://enhanced/replant/replant_clutter.gd").new()
	clutter.override_bundle = args.get("bundle", "")
	zone.add_child(clutter)
	if not clutter.setup(zone, viewer) or clutter.plan.is_empty():
		quit(3)
		return
	var checks := {}
	if args.get("toggle", "") == "true":
		for frame in 10: await process_frame
		clutter.set_enhanced(false)
		assert(clutter._job.is_empty() and clutter.chunk_plants.is_empty())
		var bytes: PackedByteArray = clutter._ready_image.get_data()
		assert(bytes.count(0) == bytes.size())
		assert(not clutter._chunks.is_empty())
		checks.pending_job_cancelled_original_retained = true
		await process_frame
		clutter.set_enhanced(true)
	var deadline := Time.get_ticks_msec() + 120000
	while clutter.chunk_plants.size() < 9 and Time.get_ticks_msec() < deadline: await process_frame
	if clutter.chunk_plants.size() < 9:
		quit(4)
		return
	clutter.set_process(false)
	var result := {"chunks": {}, "instances": 0, "checks": checks, "npc_pick_volumes": 12 if args.get("npc-picks", "") == "true" else 0}
	for c in clutter.chunk_plants:
		var context := HashingContext.new()
		context.start(HashingContext.HASH_SHA256)
		var patch: Node3D = clutter.chunk_plants[c]
		var batches: Array = patch.get_children().filter(func(n):return n is MultiMeshInstance3D)
		batches.sort_custom(func(a, b):return String(a.name) < String(b.name))
		for batch in batches:
			context.update(String(batch.name).to_utf8_buffer())
			for i in batch.multimesh.instance_count:
				context.update(var_to_bytes([batch.multimesh.get_instance_transform(i), batch.multimesh.get_instance_custom_data(i)]))
				result.instances += 1
		result.chunks["%d,%d" % [c.x, c.y]] = context.finish().hex_encode()
	var f := FileAccess.open(String(args.out), FileAccess.WRITE)
	f.store_string(JSON.stringify(result, "  "))
	print("PLACEMENT_FINGERPRINT instances=", result.instances)
	quit()
