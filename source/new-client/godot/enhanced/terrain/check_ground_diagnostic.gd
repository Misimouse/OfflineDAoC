extends SceneTree
func _initialize() -> void:call_deferred("run")
func run() -> void:
	assert(load("res://enhanced/godot_tools/inspector_bridge.gd").can_instantiate())
	var world=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus")
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	var ground=load("res://enhanced/terrain/ground_patterns.gd").new();world.add_child(ground);assert(ground.attach(region))
	var d=ground.diagnostic();assert(d.revision=="smooth-source-masks");assert(d.atlas_format=="rgba16f");assert(d.replacement_meshes==4);assert(d.actual_shaders.size()==1);assert(String(d.actual_shaders[0]).ends_with("ground_patterns_smooth.gdshader"));assert(ground.label.text.contains("R3"));assert(ground.label.text.contains("4/4"))
	ground.set_enabled(false);assert(ground.diagnostic().replacement_meshes==0)
	ground.set_enabled(true);zone.set_terrain_set("lod_x4plus");ground._process(0);assert(not ground.diagnostic().blend_mode);assert(ground.diagnostic().replacement_meshes==0)
	ground.restore();region.free();world.queue_free();await process_frame;await process_frame;print("GROUND_DIAGNOSTIC_OK ",JSON.stringify(d));quit()
