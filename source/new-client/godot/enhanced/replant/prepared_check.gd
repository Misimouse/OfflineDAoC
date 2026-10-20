extends SceneTree
## A playing client may load prepared positions, but must never generate candidates.
var args := {}
func _initialize() -> void:
	Engine.max_fps = 60
	for arg in OS.get_cmdline_user_args():
		var pair := arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2: args[pair[0]]=pair[1]
	run.call_deferred()

func run() -> void:
	var world := Node3D.new()
	root.add_child(world)
	var zone = load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	var viewer := Node3D.new()
	zone.add_child(viewer)
	viewer.position=Vector3(1302.4,zone.height_at(1302.4,1231.225)+2,1231.225)
	await physics_frame
	await physics_frame
	var clutter = load("res://enhanced/replant/replant_clutter.gd").new()
	clutter.override_bundle=args.bundle
	zone.add_child(clutter)
	if not clutter.setup(zone,viewer) or clutter.plan.is_empty():
		quit(3)
		return
	assert(not clutter.allow_generation)
	var report := {"positions":[]}
	# Both supplied locations, then a far-away, unprepared place, then return.
	for point in [Vector2(1302.4,1231.225),Vector2(1275.65,1216.45),Vector2(50,50),Vector2(1302.4,1231.225)]:
		var before_hits: int=clutter.cache_hits
		var before_misses: int=clutter.cache_misses
		viewer.position=Vector3(point.x,zone.height_at(point.x,point.y)+2,point.y)
		var samples: Array[float]=[]
		var started:=Time.get_ticks_usec()
		var previous:=started
		for frame in 180:
			await process_frame
			var now:=Time.get_ticks_usec()
			samples.append((now-previous)/1000.0)
			previous=now
			assert(clutter._job.is_empty() or clutter._job.cached, "Client started generating new candidates")
			if frame>10 and clutter.is_settled():break
		assert(clutter.is_settled())
		var record: Dictionary={"x":point.x,"z":point.y,"seconds":(Time.get_ticks_usec()-started)/1000000.0,"max_cpu_frame_ms":samples.max(),"chunks":clutter.chunk_plants.size(),"hits":clutter.cache_hits-before_hits,"misses":clutter.cache_misses-before_misses}
		if point.x==50:
			assert(clutter.chunk_plants.is_empty() and not clutter._chunks.is_empty())
			assert(record.misses>0)
		else:
			assert(clutter.chunk_plants.size()==9 and record.misses==0)
		report.positions.append(record)
	clutter.set_enhanced(false)
	assert(clutter.chunk_plants.is_empty() and clutter._ready_image.get_data().count(0)==65536)
	report.no_runtime_generation=true
	report.original_fallback_and_AB=true
	var file:=FileAccess.open(String(args.out),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print("PREPARED_CLIENT_CHECK_OK ",JSON.stringify(report))
	quit()
