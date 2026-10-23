extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	Engine.max_fps=60;root.size=Vector2i(1440,1000);root.use_taa=true;root.msaa_3d=Viewport.MSAA_4X
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args.manifest))
	assert(FileAccess.get_sha256(manifest.scene)==manifest.scene_sha256)
	var spec:Dictionary={"grove":{"file":"models/holdgrove.gltf","fixture":146,"height":44.1452,"label":"GROVE | Conifera"},"dead":{"file":"models/hdeadtree.gltf","fixture":480,"height":20.2895,"label":"DEATH | Copa de invierno"},"bare":{"file":"models/hbareskny.gltf","fixture":1428,"height":23.1138,"label":"BARE | Seco retorcido"}}[String(manifest.variant)]
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone);zone.load_zone("res://content/zones/zone207","blend","x4plus")
	await physics_frame
	var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size()
	var fixture:Dictionary={}
	for f in zone.info.fixtures:
		if int(f.id)==int(spec.fixture):fixture=f;break
	assert(not fixture.is_empty() and zone.info.models[int(fixture.m)].file==spec.file)
	var model_name:String=zone.info.models[int(fixture.m)].name
	var original_at:=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]);var saved:Array=[]
	for child in zone.get_children():
		if not child is MultiMeshInstance3D or not String(child.name).begins_with(model_name+"_"):continue
		for index in child.multimesh.instance_count:
			var transform:Transform3D=child.multimesh.get_instance_transform(index)
			if transform.origin.distance_to(original_at)<0.001:saved.append({"node":child,"index":index,"transform":transform})
	assert(not saved.is_empty())
	var obstructions:Array=[]
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		var lower:=String(child.name).to_lower()
		if not ("tree" in lower or "birch" in lower or "elm" in lower):continue
		for index in child.multimesh.instance_count:
			var transform:Transform3D=child.multimesh.get_instance_transform(index)
			if transform.origin.distance_to(original_at)<0.001 or Vector2(transform.origin.x-original_at.x,transform.origin.z-original_at.z).length()>65:continue
			obstructions.append({"node":child,"index":index,"transform":transform})
			transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO);child.multimesh.set_instance_transform(index,transform)
	var holder:=Node3D.new();holder.transform=saved[0].transform
	var asset:Node3D=load(String(manifest.scene)).instantiate();holder.add_child(asset);zone.add_child(holder);await process_frame
	var roots:=asset.find_children("Broad_root_*","Node3D",true,false);assert(roots.size()==1)
	var at:Vector3=zone.to_local(roots[0].global_position);var gap:float=at.y-zone.height_at(at.x,at.z);assert(absf(gap+.045)<.002)
	var normal_count:=0;var visible_meshes:=0
	for mesh in asset.find_children("*","MeshInstance3D",true,false):
		if String(mesh.name).begins_with("CopaShadow"):
			assert(mesh.cast_shadow==GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY);continue
		visible_meshes+=1
		for surface in mesh.mesh.get_surface_count():
			var arrays:Array=mesh.mesh.surface_get_arrays(surface)
			for n in arrays[Mesh.ARRAY_NORMAL]:assert(n.is_finite() and absf(n.length()-1)<.025)
			normal_count+=arrays[Mesh.ARRAY_NORMAL].size()
			var material:ShaderMaterial=mesh.mesh.surface_get_material(surface)
			assert(material.shader.code.contains("SPECULAR=0.0") and material.shader.code.contains("ROUGHNESS=0.98"))
	assert(visible_meshes==(2 if manifest.variant=="grove" else 1))
	var cam:=Camera3D.new();world.add_child(cam);cam.make_current();cam.far=1500;cam.fov=55
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,cam,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	var layer:=CanvasLayer.new();world.add_child(layer);var label:=Label.new();layer.add_child(label);label.position=Vector2(20,20);label.add_theme_font_size_override("font_size",22)
	label.add_theme_color_override("font_shadow_color",Color.BLACK);label.add_theme_constant_override("shadow_outline_size",5)
	DirAccess.make_dir_recursive_absolute(args.out)
	var views:Array=[{"offset":Vector3(52,28,58) if manifest.variant=="grove" else Vector3(27,12,31),"look":Vector3.UP*float(spec.height)*.5},{"offset":Vector3(2.5,3,3),"look":Vector3(0,3,0)},{"offset":Vector3(10,14,8),"look":Vector3(4,14,1)}]
	for view_index in views.size():
		cam.position=at+views[view_index].offset;cam.position.y=maxf(cam.position.y,zone.height_at(cam.position.x,cam.position.z)+2);cam.look_at(at+views[view_index].look)
		for enabled in [false,true]:
			asset.visible=enabled
			for record in saved:
				var transform:Transform3D=record.transform
				if enabled:transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
				record.node.multimesh.set_instance_transform(record.index,transform)
			label.text=("B | Nuevo | " if enabled else "A | Original | ")+String(spec.label)+" | Luz 14:00"
			for frame in 25:await process_frame
			await RenderingServer.frame_post_draw;root.get_texture().get_image().save_png(String(args.out).path_join("vista%d_%s.png"%[view_index,"B" if enabled else "A"]))
	for record in saved:
		record.node.multimesh.set_instance_transform(record.index,record.transform)
		assert(record.node.multimesh.get_instance_transform(record.index).is_equal_approx(record.transform))
	for record in obstructions:record.node.multimesh.set_instance_transform(record.index,record.transform)
	assert(collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	var file:=FileAccess.open(String(args.out).path_join("checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"variant":manifest.variant,"root_gap":gap,"root_count":1,"normal_vertices":normal_count,"original_slots_restored":saved.size(),"collision_count_unchanged":true,"original_fixture_transform_retained":true,"matte_materials":true,"note":"Isolated real-zone rendering; no running game/server restarted."},"  "));file.close()
	print("FOREST_REVIEW_CHECK_OK");quit()
