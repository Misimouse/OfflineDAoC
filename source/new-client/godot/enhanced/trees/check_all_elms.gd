extends SceneTree
## Rendered, offline whole-zone replacement and restoration check. No account or server.
var zone
var trial
var out:=""

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")

func fixtures() -> String:
	var context:=HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		context.update(String(child.name).to_utf8_buffer())
		for i in child.multimesh.instance_count:context.update(var_to_bytes(child.multimesh.get_instance_transform(i)))
	return context.finish().hex_encode()

func physics() -> String:
	var data:=[]
	for shape in zone.find_children("*","CollisionShape3D",true,false):
		data.append([str(shape.get_path()),shape.transform,shape.shape.get_instance_id(),shape.disabled])
	return var_to_bytes(data).hex_encode().sha256_text()

func run() -> void:
	assert(not out.is_empty())
	DirAccess.make_dir_recursive_absolute(out)
	Engine.max_fps=60
	root.size=Vector2i(1440,900)
	var world:=Node3D.new()
	root.add_child(world)
	zone=load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	var cam:=Camera3D.new()
	world.add_child(cam)
	cam.far=4000
	cam.make_current()
	var sky=load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone,cam,"x4plus")
	sky.set_hour(14)
	sky.time_scale=0
	sky.storm_forced=0
	sky.set_process(false)
	await physics_frame
	await physics_frame
	var before:=fixtures()
	var shapes:=physics()
	trial=load("res://enhanced/trees/elm_trial.gd").new()
	world.add_child(trial)
	trial.override_manifest="res://.enhanced-session/elm_trial/bundles/all_connacht_20261021/manifest.json"
	assert(trial.configure())
	var start:=Time.get_ticks_usec()
	assert(trial.apply_zone(zone))
	var build_ms:=(Time.get_ticks_usec()-start)/1000.0
	assert(trial.originals.size()==661)
	assert(trial.batch_links.size()>2)
	var batch_count:int=trial.batch_links.size()
	var new_instances:=0
	for link in trial.batch_links:
		new_instances+=link.batch.multimesh.instance_count
		assert(link.batch.multimesh.instance_count==link.reference.multimesh.instance_count)
		assert(link.batch.visibility_range_end==link.reference.visibility_range_end)
		assert(link.batch.visibility_range_fade_mode==link.reference.visibility_range_fade_mode)
	assert(new_instances==1322)
	assert(shapes==physics())
	trial.set_enabled(false)
	assert(before==fixtures())
	for mult in [2.0,1.0]:
		zone.set("view_mult",mult)
		zone.apply_view(mult)
		trial._process(0.0)
		for link in trial.batch_links:
			assert(link.batch.visibility_range_end==link.reference.visibility_range_end)
			assert(link.batch.visibility_range_end_margin==link.reference.visibility_range_end_margin)
	var region=load("res://game/world/region_world.gd").new()
	region.zones[207]=zone
	trial.restore()
	assert(before==fixtures())
	trial.set_enabled(true)
	trial.attach(region)
	assert(trial.originals.size()==661)
	region.zone_removing.emit(zone)
	assert(before==fixtures())
	region.zone_added.emit(zone)
	assert(trial.originals.size()==661 and trial.enabled)
	var measurements:=[]
	# Same route for original/new, from close to distant and back; render-engine timings, no server/NPCs.
	for use_new in [false,true]:
		trial.set_enabled(use_new)
		cam.position=Vector3(1412.2,134,1324.4)
		cam.look_at(Vector3(1395.2,148,1302.4))
		for frame in 45:await process_frame
		var frames:Array=[]
		for leg in [0,1]:
			for step in 120:
				var t:=float(step)/119.0
				if leg==1:t=1.0-t
				cam.position=Vector3(1412.2,134,1324.4).lerp(Vector3(820,310,1630),t)
				cam.look_at(Vector3(1000,135,1000))
				var at:=Time.get_ticks_usec()
				await process_frame
				frames.append((Time.get_ticks_usec()-at)/1000.0)
		cam.position=Vector3(820,310,1630)
		cam.look_at(Vector3(1000,135,1000))
		for frame in 35:await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("all_elms_%s.png"%["new"if use_new else"original"]))
		frames.sort()
		var sum:=0.0
		for ms in frames:sum+=ms
		measurements.append({"new":use_new,"frames":frames.size(),"mean_ms":sum/frames.size(),"p95_ms":frames[int(frames.size()*0.95)],"max_ms":frames.back(),"render_primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)})
	trial.restore()
	assert(before==fixtures() and shapes==physics())
	# Deliberately fail fixture-count validation: nothing may be hidden on an incomplete match.
	trial.manifest.total=662
	assert(not trial.apply_zone(zone))
	assert(before==fixtures())
	region.free()
	var report={"zone":207,"trees":661,"elm":326,"elm2":335,"new_mesh_instances":new_instances,"build_ms":build_ms,"cell_batches":batch_count,"viewport":[root.size.x,root.size.y],"collision_unchanged":true,"exact_original_restoration":true,"view_setting_sync":true,"region_reload":true,"partial_match_retains_originals":true,"measurements":measurements,"note":"Standalone zone on actual renderer, no server/NPCs. Prototype art and shadows unchanged; no distance LODs added."}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print("ALL_ELMS_RENDER_CHECK_OK trees=661 original_restoration=true physics_unchanged=true")
	quit()
