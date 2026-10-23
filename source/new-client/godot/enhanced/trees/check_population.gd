extends SceneTree
var out:=""
func _initialize() -> void:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--out="):out=argument.trim_prefix("--out=")
	call_deferred("run")
func fingerprint(zone) -> String:
	var records:Array=[]
	for node in zone.get_children():
		if node is MultiMeshInstance3D:
			for index in node.multimesh.instance_count:records.append([String(node.name),index,node.multimesh.get_instance_transform(index)])
	return var_to_bytes(records).hex_encode().sha256_text()
func run() -> void:
	assert(not out.is_empty());DirAccess.make_dir_recursive_absolute(out)
	assert(load("res://enhanced/lab_session.gd").can_instantiate())
	assert(load("res://enhanced/godot_tools/inspector_bridge.gd").can_instantiate())
	Engine.max_fps=0;root.size=Vector2i(1440,900)
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus")
	await physics_frame
	var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size();var original:=fingerprint(zone)
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	var forest=load("res://enhanced/trees/forest_population.gd").new();world.add_child(forest)
	forest.override_manifest="res://.enhanced-session/forest_population/manifest.json"
	var before_taa:=root.use_taa;var before_msaa:=root.msaa_3d
	assert(forest.attach(region) and forest.planted.size()==1404)
	await process_frame
	var seen:Dictionary={};var gaps:Array=[]
	for tree in forest.planted:
		assert(not seen.has(tree.id));seen[tree.id]=true
		var fixture:Dictionary={}
		for f in zone.info.fixtures:
			if int(f.id)==tree.id:fixture=f;break
		assert(tree.holder.position.is_equal_approx(Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2])))
		for stem in tree.asset.find_children("*root_*","Node3D",true,false):
			var at:Vector3=zone.to_local(stem.global_position);var gap:float=at.y-zone.height_at(at.x,at.z)
			assert(absf(gap+.045)<.003);gaps.append(gap)
		assert(not forest.model_file_for(tree.file).is_empty())
	forest.set_enabled(false);assert(fingerprint(zone)==original);forest.set_enabled(true)
	assert(collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	print("POPULATION_PLACEMENTS_CHECKED roots=",gaps.size())
	var ivy=load("res://enhanced/terrain/stone_ivy_trial.gd").new();world.add_child(ivy);ivy.override_manifest="res://.enhanced-session/stone_ivy/detail_20261023/manifest.json";ivy.attach(region);assert(ivy.assets.size()==8)
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.far=1500;camera.fov=65
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,camera,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	var views:Array=[{"at":Vector3(1395,136,1360),"look":Vector3(1350,137,1300)},{"at":Vector3(1080,150,1090),"look":Vector3(1110,145,1010)},{"at":Vector3(1450,185,1450),"look":Vector3(1250,140,1250)}]
	var results:Array=[]
	for index in views.size():
		camera.position=views[index].at;camera.position.y=maxf(camera.position.y,zone.height_at(camera.position.x,camera.position.z)+3);camera.look_at(views[index].look)
		forest.update_lods(camera)
		for enabled in [false,true]:
			forest.set_enabled(enabled)
			for frame in 24:await process_frame
			var start:=Time.get_ticks_usec()
			for frame in 36:await process_frame
			var elapsed:float=(Time.get_ticks_usec()-start)/36000.0
			results.append({"view":index,"new_forest":enabled,"mean_ms":elapsed,"triangles":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)})
			await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join("bosque_%d_%s.png"%[index,"nuevo" if enabled else "original"]))
			print("POPULATION_VIEW ",JSON.stringify(results[-1]))
	# Ivy surface close-up, then the original approved stone body with old leaf material.
	var target:=Vector3(1254.4,132.4,1273.6);camera.position=Vector3(1259.3,132.8,1280.4);camera.look_at(target)
	for frame in 24:await process_frame
	await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join("hiedra_detalle.png"))
	for tree in forest.planted:
		if tree.id!=366:continue
		var at:Vector3=tree.holder.position;camera.position=at+Vector3(7,4,8);camera.look_at(at+Vector3(0,1,4));forest.update_lods(camera)
		for frame in 24:await process_frame
		await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join("log_replantado.png"))
	ivy.restore();forest.restore();await process_frame;await process_frame
	assert(fingerprint(zone)==original and collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	assert(root.use_taa==before_taa and root.msaa_3d==before_msaa)
	assert(forest.apply_zone(zone));region.zone_removing.emit(zone);await process_frame
	assert(forest.planted.is_empty() and fingerprint(zone)==original)
	region.zone_added.emit(zone);await process_frame;assert(forest.planted.size()==1404)
	zone.set("view_mult",.5);zone.apply_view(.5);forest._process(0)
	for tree in forest.planted:
		for mesh in tree.meshes:assert(mesh.visibility_range_end<=float(tree.far)*.5+.001)
	zone.set("view_mult",1.0);zone.apply_view(1.0);forest._process(0)
	forest.restore();ivy.restore();region.free()
	assert(fingerprint(zone)==original)
	var file:=FileAccess.open(out.path_join("population_checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"total":1404,"tree_count":1396,"woody_props":8,"fixture_positions_unchanged":true,"unique_fixture_ids":seen.size(),"seated_roots":gaps.size(),"collision_count_unchanged":true,"exact_restoration":true,"region_unload_reload":true,"taa_msaa_restored":true,"view_distance_followed":true,"ivy_targets":8,"measurements":results,"note":"Isolated renderer at 1440x900; not a live gameplay FPS guarantee."},"  "));file.close()
	print("FOREST_POPULATION_CHECK_OK");quit()
