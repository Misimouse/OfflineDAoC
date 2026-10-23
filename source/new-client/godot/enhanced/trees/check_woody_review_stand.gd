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
	var msaa_before:=root.msaa_3d
	assert(stand.attach(region,trees))
	print("WOODY_STAND_ATTACHED");await process_frame;await process_frame
	assert(stand.rows.size()==11 and stand.hidden.size()>=2)
	assert(stand.hidden.size()==stand.hidden_positions.size()*2)
	var hidden_parts:int=stand.hidden.size()
	var cleared_trees:int=stand.hidden_positions.size()
	if stand.config.get("temporal_aa",false):
		assert(root.use_taa)
		stand.toggle_leaf_smoothing();assert(not root.use_taa)
		await process_frame;await process_frame
		stand.toggle_leaf_smoothing();assert(root.use_taa)
		await process_frame;await process_frame
	print("WOODY_AA_CHECKED")
	trees.set_enabled(false)
	await process_frame
	await process_frame
	assert(not stand.display.visible)
	trees.set_enabled(true)
	await process_frame
	await process_frame
	assert(stand.display.visible)
	assert(collision_count==zone.find_children("*","CollisionShape3D",true,false).size())
	print("WOODY_COLLISIONS_CHECKED")
	var cam:=Camera3D.new();world.add_child(cam);cam.make_current();cam.far=1200
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky)
	sky.setup(zone,cam,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	for index in 11:
		var item:Dictionary=stand.rows[index]
		var at:=Vector3(item.position[0],item.position[1],item.position[2])
		var height:float=float(stand.config.trees[index].get("review_height",13.0))
		var distance:float=maxf(15.0,height*2.7)
		if index==9:distance=6.0
		if index==10:distance=23.0
		cam.position=at+Vector3(distance,height*1.05,distance);cam.look_at(at+Vector3.UP*height)
		for frame in 30:await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("mapa_arbol%d.png"%(index+1)))
	var positions=stand.rows.duplicate(true)
	var backup:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/elm_trial/review_stand_oak_low_detail_20261023.json"))
	for i in 2:
		assert(positions[i].id=="review:"+String(backup.trees[i].id))
		assert(absf(float(positions[i].position[0])-float(backup.trees[i].x))<.01)
		assert(absf(float(positions[i].position[2])-float(backup.trees[i].z))<.01)
	for holder in stand.display.get_children():
		if holder is Label3D:continue
		for stem in holder.find_children("*root_*","Node3D",true,false):
			var at:Vector3=zone.to_local(stem.global_position)
			assert(absf(at.y-zone.height_at(at.x,at.z)+.045)<.002)
	stand.restore()
	assert(root.use_taa==taa_before and root.msaa_3d==msaa_before)
	assert(stand.rows.is_empty() and stand.hidden.is_empty())
	stand.apply_zone(zone)
	assert(stand.rows.size()==11 and stand.hidden.size()>=2)
	stand.restore();trees.restore();region.free()
	var file:=FileAccess.open(out.path_join("stand_checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"eleven_models":true,"hidden_old_tree_parts":hidden_parts,"cleared_tree_count":cleared_trees,"temporal_aa_restored":true,"msaa_restored":true,"oak_low_retained_in_place":true,"collision_count_unchanged":true,"restoration_and_reload":true,"inspector_destinations":positions},"  "));file.close()
	print("FOREST_STAND_CHECK_OK")
	quit()
