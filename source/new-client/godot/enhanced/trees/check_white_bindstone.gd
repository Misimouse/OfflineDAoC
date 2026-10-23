extends SceneTree
var out:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")
func fingerprint(zone) -> String:
	var values:Array=[]
	for node in zone.get_children():
		if node is MultiMeshInstance3D:
			for i in node.multimesh.instance_count:values.append([String(node.name),i,node.multimesh.get_instance_transform(i)])
	return var_to_bytes(values).hex_encode().sha256_text()
func run() -> void:
	root.size=Vector2i(1440,900);root.msaa_3d=Viewport.MSAA_4X;root.use_taa=true
	var old:Node3D=load("res://.enhanced-session/finish_revision_20261023/bindstone.scn").instantiate()
	var candidate:Node3D=load("res://.enhanced-session/hibernia_white_marble_20261023/bindstone.scn").instantiate()
	var surfaces:=0
	for mesh in old.find_children("*","MeshInstance3D",true,false):
		var next:MeshInstance3D=candidate.get_node(old.get_path_to(mesh))
		for s in mesh.mesh.get_surface_count():assert(mesh.mesh.surface_get_arrays(s)==next.mesh.surface_get_arrays(s));surfaces+=1
		var mat:ShaderMaterial=next.get_active_material(0);assert(mat.shader.code.contains("ROUGHNESS=.20") and not mat.shader.code.contains("age="))
	old.free();candidate.free()
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus");await physics_frame
	var before:=fingerprint(zone);var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size()
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	var controller=load("res://enhanced/trees/mushroom_trial.gd").new();world.add_child(controller);controller.override_manifest="res://.enhanced-session/hibernia_white_marble_20261023/manifest.json";assert(controller.attach(region));assert(controller.originals.size()==15 and controller.mushrooms.size()==82)
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.far=1000;camera.fov=55
	var at:=Vector3(1325.4,130,1236.3);camera.position=at+Vector3(-3.0,2.1,3.8);camera.look_at(at+Vector3.UP*1.9)
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,camera,"x4plus");sky.time_scale=0;sky.set_process(false)
	for hour in [14,23]:
		sky.set_hour(hour)
		for i in 30:await process_frame
		await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(out.path_join("marmol_%d.png"%hour))
	controller.restore();assert(fingerprint(zone)==before);assert(collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	var report:Dictionary={"geometry_and_emblem_identical":true,"surfaces":surfaces,"polished_white":true,"stock_restoration_exact":true,"collisions_unchanged":true,"day_and_night_rendered":true}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print("WHITE_MARBLE_CHECK_OK ",JSON.stringify(report))
	region.free();world.queue_free();await process_frame;await process_frame;quit()
