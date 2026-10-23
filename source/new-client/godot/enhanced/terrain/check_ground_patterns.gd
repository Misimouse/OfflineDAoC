extends SceneTree
var out:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")
func capture(camera:Camera3D,at:Vector3,target:Vector3,name:String) -> void:
	camera.position=at;camera.look_at(target)
	for i in 24:await process_frame
	await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join(name+".png"))
func run() -> void:
	assert(load("res://enhanced/lab_session.gd").can_instantiate());assert(load("res://enhanced/godot_tools/inspector_bridge.gd").can_instantiate())
	root.size=Vector2i(1440,900);root.use_taa=true;root.msaa_3d=Viewport.MSAA_4X;Engine.max_fps=0
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus");await physics_frame
	var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size();var geometry:Dictionary={}
	for node in zone.get_children():
		if node is MeshInstance3D and String(node.name).begins_with("Terrain_"):geometry[String(node.name)]=node.mesh.get_rid()
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	var forest=load("res://enhanced/trees/forest_population.gd").new();world.add_child(forest);assert(forest.attach(region))
	var mushrooms=load("res://enhanced/trees/mushroom_trial.gd").new();world.add_child(mushrooms);assert(mushrooms.attach(region))
	var ground=load("res://enhanced/terrain/ground_patterns.gd").new();world.add_child(ground);ground.override_manifest="res://.enhanced-session/ground_patterns/ardeeladeras_20261023/manifest.json";assert(ground.attach(region));assert(ground.bindings.size()==4)
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.far=1500;camera.fov=65
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,camera,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	var sites:Array=[{"name":"ardee","p":Vector3(1357.425,130,1258.15),"look":Vector3(-14,-.8,-19)},{"name":"ladera","p":Vector3(1100,0,1090),"look":Vector3(35,-12,60)},{"name":"pedregoso","p":Vector3(1316,0,1148),"look":Vector3(-10,-1,-18)},{"name":"panoramica","p":Vector3(1250,175,1280),"look":Vector3(0,-35,-110)}]
	var performance:Array=[]
	for site in sites:
		var p:Vector3=site.p
		if site.name!="panoramica":p.y=zone.height_at(p.x,p.z)+2.0
		camera.position=p;camera.look_at(p+site.look)
		for enabled in [false,true]:
			ground.set_enabled(enabled)
			await capture(camera,p,p+site.look,site.name+("_nuevo" if enabled else "_anterior"))
			var start:=Time.get_ticks_usec()
			for i in 36:await process_frame
			performance.append({"site":site.name,"new":enabled,"mean_ms":(Time.get_ticks_usec()-start)/36000.0,"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)})
	# Inspect an internal parcel boundary from both sides and the smooth pilot boundary.
	for site in [{"name":"union_interna","p":Vector3(1228.8,0,1270)},{"name":"borde_prueba","p":Vector3(1410,0,1258)}]:
		var p:Vector3=site.p;p.y=zone.height_at(p.x,p.z)+8;await capture(camera,p+Vector3(6,0,8),p+Vector3(0,-7,0),site.name)
	for node in zone.get_children():
		if node is MeshInstance3D and String(node.name).begins_with("Terrain_"):assert(geometry[String(node.name)]==node.mesh.get_rid())
	assert(collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	ground.set_enabled(false)
	for binding in ground.bindings:assert(binding.mesh.material_override==binding.baseline)
	ground.set_enabled(true);zone.set_terrain_set("lod_x4plus");ground._process(0)
	for binding in ground.bindings:assert(binding.mesh.material_override==null)
	zone.set_terrain_set("blend");ground._process(0)
	for binding in ground.bindings:assert(binding.mesh.material_override==binding.replacement)
	ground.restore()
	for key in ["5_5","5_6","6_5","6_6"]:assert(zone.get_node("Terrain_"+key).material_override==null)
	assert(ground.apply_zone(zone));ground.restore()
	var report:Dictionary={"patches":4,"geometry_identical":true,"collisions_identical":true,"baseline_comparison_exact":true,"restore_exact":true,"reload":true,"painted_mode_respected":true,"forest_unchanged":forest.planted.size()==1404,"mushrooms_unchanged":mushrooms.mushrooms.size()==82,"performance":performance}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("GROUND_PATTERNS_CHECK_OK ",JSON.stringify(report))
	mushrooms.restore();forest.restore();region.free();world.queue_free();await process_frame;await process_frame;quit()
