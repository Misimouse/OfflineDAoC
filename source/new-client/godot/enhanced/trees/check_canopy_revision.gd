extends SceneTree
var out:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")
func fingerprint(zone) -> String:
	var records:Array=[]
	for node in zone.get_children():
		if node is MultiMeshInstance3D:
			for i in node.multimesh.instance_count:records.append([String(node.name),i,node.multimesh.get_instance_transform(i)])
	return var_to_bytes(records).hex_encode().sha256_text()
func shot(camera:Camera3D,at:Vector3,target:Vector3,name:String) -> void:
	camera.global_position=at;camera.look_at(target)
	for i in 20:await process_frame
	await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join(name+".png"))
func run() -> void:
	assert(not out.is_empty());DirAccess.make_dir_recursive_absolute(out);root.size=Vector2i(1440,900);Engine.max_fps=0
	for path in ["lab_session.gd","godot_tools/inspector_bridge.gd","trees/mushroom_trial.gd","trees/terrain_root_extensions.gd"]:assert(load("res://enhanced/"+path).can_instantiate())
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus");await physics_frame
	var before:=fingerprint(zone);var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size()
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	var forest=load("res://enhanced/trees/forest_population.gd").new();world.add_child(forest);forest.override_manifest="res://.enhanced-session/forest_revision_20261023/manifest.json"
	assert(forest.attach(region));assert(forest.planted.size()==1404)
	assert(forest.root_extensions.report.exposed_lower_vertices==0 and forest.root_extensions.report.skirts>1000)
	var mushroom=load("res://enhanced/trees/mushroom_trial.gd").new();world.add_child(mushroom);mushroom.override_manifest="res://.enhanced-session/forest_revision_20261023/mushroom/manifest.json"
	assert(mushroom.attach(region));assert(mushroom.mushrooms.size()==82);assert(mushroom.originals.size()==9)
	assert(zone.find_children("*","CollisionShape3D",true,false).size()==collisions)
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.far=1400;camera.fov=65
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,camera,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	var elm;var grove;var slope;var best:=-1.0
	for tree in forest.planted:
		var at:Vector3=tree.holder.position
		if tree.file=="models/helm2.gltf" and elm==null and Vector2(at.x-1325,at.z-1236).length()<250:elm=tree
		if tree.file=="models/holdgrove.gltf" and grove==null:grove=tree
		if tree.file=="models/helm.gltf":
			var gradient:float=absf(zone.height_at(at.x+3,at.z)-zone.height_at(at.x-3,at.z))+absf(zone.height_at(at.x,at.z+3)-zone.height_at(at.x,at.z-3))
			if gradient>best:best=gradient;slope=tree
	var e:Vector3=elm.holder.position;await shot(camera,e+Vector3(9,8,12),e+Vector3(0,10,0),"olmo_union")
	await shot(camera,e+Vector3(22,5,27),e+Vector3(0,12,0),"olmo_completo")
	# Isolate one native pine so adjacent trunks cannot obstruct the density comparison.
	forest.anchor.visible=false
	for child in zone.get_children():
		if child is MultiMeshInstance3D:child.visible=false
	var pine:Node3D=load(String(forest.manifest.models[2].scene)).instantiate();world.add_child(pine);pine.position=Vector3(1350,zone.height_at(1350,1300),1300)
	var p:Vector3=pine.position
	await shot(camera,p+Vector3(38,18,48),p+Vector3.UP*23,"pino_cerca")
	for mesh in pine.find_children("*","MeshInstance3D",true,false):mesh.lod_bias=.025
	await shot(camera,p+Vector3(95,22,120),p+Vector3.UP*24,"pino_lejos")
	pine.queue_free();forest.anchor.visible=true
	for child in zone.get_children():
		if child is MultiMeshInstance3D:child.visible=true
	var s:Vector3=slope.holder.position;var offset:=Vector3(9,3,8);offset.y=maxf(offset.y,zone.height_at(s.x+9,s.z+8)-s.y+2)
	await shot(camera,s+offset,s+Vector3.UP*.5,"base_pendiente")
	var g:Vector3=mushroom.mushrooms[-1].global_position;await shot(camera,g+Vector3(13,3,17),g+Vector3.UP*5,"seta_gigante")
	await shot(camera,g+Vector3(4,2,3),g+Vector3.UP*7,"seta_laminas")
	var b:=Vector3(1325.4,130,1236.3);await shot(camera,b+Vector3(7,4,9),b+Vector3.UP*1,"setas_vinculacion")
	var results:Array=[]
	for view in [Vector3(1395,136,1360),Vector3(1450,185,1450)]:
		camera.position=view;camera.look_at(Vector3(1300,140,1300));forest.update_lods(camera)
		for i in 30:await process_frame
		var start:=Time.get_ticks_usec()
		for i in 40:await process_frame
		results.append({"mean_ms":(Time.get_ticks_usec()-start)/40000.0,"triangles":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
	var report:Dictionary={"total_forest":forest.planted.size(),"roots":forest.root_extensions.report.duplicate(true),"small_mushrooms":81,"giant_mushrooms":1,"collision_count_unchanged":true,"performance":results,"slope_fixture":slope.id,"elm_fixture":elm.id,"grove_fixture":grove.id}
	mushroom.restore();forest.restore();assert(fingerprint(zone)==before);report["stock_visual_restore_exact"]=true
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("CANOPY_REVISION_CHECK_OK ",JSON.stringify(report))
	region.free();world.queue_free();await process_frame;await process_frame;quit()
