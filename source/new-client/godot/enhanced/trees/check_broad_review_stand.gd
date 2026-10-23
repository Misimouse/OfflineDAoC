extends SceneTree
func _initialize() -> void:
	call_deferred("run")
func run() -> void:
	var out:=""
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--out="):out=argument.trim_prefix("--out=")
	assert(not out.is_empty())
	Engine.max_fps=60
	root.size=Vector2i(1440,900)
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	await physics_frame
	var collision_count:int=zone.find_children("*","CollisionShape3D",true,false).size()
	var region=load("res://game/world/region_world.gd").new()
	region.zones[207]=zone
	var trees=load("res://enhanced/trees/elm_trial.gd").new();world.add_child(trees)
	assert(trees.configure() and trees.apply_zone(zone))
	var stand=load("res://enhanced/trees/elm_review_stand.gd").new();world.add_child(stand)
	var taa_before:=root.use_taa
	assert(stand.attach(region,trees))
	assert(stand.rows.size()==2 and stand.hidden.size()>=2)
	assert(stand.hidden.size()==stand.hidden_positions.size()*2)
	var hidden_parts:int=stand.hidden.size()
	var cleared_trees:int=stand.hidden_positions.size()
	if stand.config.get("temporal_aa",false):
		assert(root.use_taa)
		stand.toggle_leaf_smoothing();assert(not root.use_taa)
		stand.toggle_leaf_smoothing();assert(root.use_taa)
	trees.set_enabled(false)
	await process_frame
	await process_frame
	assert(not stand.display.visible)
	trees.set_enabled(true)
	await process_frame
	await process_frame
	assert(stand.display.visible)
	assert(collision_count==zone.find_children("*","CollisionShape3D",true,false).size())
	var cam:=Camera3D.new();world.add_child(cam);cam.make_current();cam.far=1200
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky)
	sky.setup(zone,cam,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	for index in 2:
		var item:Dictionary=stand.rows[index]
		var at:=Vector3(item.position[0],item.position[1],item.position[2])
		var height:float=float(stand.config.trees[index].get("review_height",13.0))
		cam.position=at+(Vector3(24,11,24) if index==0 else Vector3(11,5,12));cam.look_at(at+Vector3.UP*height)
		for frame in 30:await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("mapa_olmo%d.png"%(index+1)))
	var positions=stand.rows.duplicate(true)
	stand.restore()
	assert(root.use_taa==taa_before)
	assert(stand.rows.is_empty() and stand.hidden.is_empty())
	stand.apply_zone(zone)
	assert(stand.rows.size()==2 and stand.hidden.size()>=2)
	stand.restore();trees.restore();region.free()
	var file:=FileAccess.open(out.path_join("stand_checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"two_models":true,"hidden_old_tree_parts":hidden_parts,"cleared_tree_count":cleared_trees,"temporal_aa_restored":true,"collision_count_unchanged":true,"restoration_and_reload":true,"inspector_destinations":positions},"  "));file.close()
	print("ELM_STAND_CHECK_OK")
	quit()
