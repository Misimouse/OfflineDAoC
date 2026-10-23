extends SceneTree
## Isolated daylight A/B review at one original oak / LOW fixture. No server required.
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	Engine.max_fps=60;root.size=Vector2i(1440,1000);root.use_taa=true
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args.manifest))
	assert(FileAccess.get_sha256(manifest.scene)==manifest.scene_sha256)
	var single:bool=manifest.variant=="oak"
	var world:=Node3D.new();root.add_child(world)
	var zone=load("res://game/zone_loader.gd").new();world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	await physics_frame
	var collisions:int=zone.find_children("*","CollisionShape3D",true,false).size()
	var fixture:Dictionary={};var model_file:="models/hoaktree.gltf" if single else "models/hlowtree.gltf"
	for f in zone.info.fixtures:
		if int(f.id)==(359 if single else 1395):fixture=f;break
	assert(not fixture.is_empty() and zone.info.models[int(fixture.m)].file==model_file)
	var model_name:String=zone.info.models[int(fixture.m)].name
	var at:=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]);var saved:Array=[]
	for child in zone.get_children():
		if not child is MultiMeshInstance3D or not String(child.name).begins_with(model_name+"_"):continue
		for index in child.multimesh.instance_count:
			var transform:Transform3D=child.multimesh.get_instance_transform(index)
			if transform.origin.distance_to(at)<0.001:saved.append({"node":child,"index":index,"transform":transform})
	assert(saved.size()==1)
	# Clear only obstructing tree visuals in this isolated renderer. Restore at exit.
	var obstructions:Array=[]
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		var name_lower:=String(child.name).to_lower()
		if not ("tree" in name_lower or "birch" in name_lower or "elm" in name_lower):continue
		for index in child.multimesh.instance_count:
			var transform:Transform3D=child.multimesh.get_instance_transform(index)
			if transform.origin.distance_to(at)<0.001 or Vector2(transform.origin.x-at.x,transform.origin.z-at.z).length()>55.0:continue
			obstructions.append({"node":child,"index":index,"transform":transform})
			transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO);child.multimesh.set_instance_transform(index,transform)
	var holder:=Node3D.new();holder.transform=saved[0].transform
	var asset:Node3D=load(String(manifest.scene)).instantiate();holder.add_child(asset);zone.add_child(holder)
	await process_frame
	var roots:=asset.find_children("Broad_root_*","Node3D",true,false)
	assert(roots.size()==1)
	var root_gaps:Array=[]
	for stem in roots:
		var local:Vector3=zone.to_local(stem.global_position)
		var gap:float=local.y-zone.height_at(local.x,local.z)
		assert(absf(gap+0.045)<0.002);root_gaps.append(gap)
	var normal_vertices:=0
	for mesh in asset.find_children("*","MeshInstance3D",true,false):
		for surface in mesh.mesh.get_surface_count():
			var arrays:Array=mesh.mesh.surface_get_arrays(surface)
			assert(arrays[Mesh.ARRAY_VERTEX].size()==arrays[Mesh.ARRAY_NORMAL].size())
			for n in arrays[Mesh.ARRAY_NORMAL]:assert(n.is_finite() and absf(n.length()-1.0)<0.025)
			normal_vertices+=arrays[Mesh.ARRAY_NORMAL].size()
			var material:ShaderMaterial=mesh.mesh.surface_get_material(surface)
			assert(material.shader.code.contains("SPECULAR=0.0") and material.shader.code.contains("ROUGHNESS=0.98"))
	var camera:=Camera3D.new();world.add_child(camera);camera.make_current();camera.far=1200;camera.fov=55
	var sky=load("res://game/sky_system.gd").new();world.add_child(sky)
	sky.setup(zone,camera,"x4plus");sky.set_hour(14);sky.time_scale=0;sky.set_process(false)
	var layer:=CanvasLayer.new();world.add_child(layer);var label:=Label.new();layer.add_child(label)
	label.position=Vector2(20,20);label.add_theme_font_size_override("font_size",22);label.add_theme_color_override("font_shadow_color",Color.BLACK);label.add_theme_constant_override("shadow_outline_size",5)
	DirAccess.make_dir_recursive_absolute(args.out)
	var views=[{"offset":Vector3(25,10,30),"look":Vector3(0,12,0)}, {"offset":Vector3(8,11,9),"look":Vector3(2,14,2)}, {"offset":Vector3(1.8,3.2,2.2),"look":Vector3(0,3,0)}, {"offset":Vector3(9,18,7),"look":Vector3(6,19,4)}]
	views[0].offset=Vector3(-29,12,-34) if single else Vector3(-22,8,26)
	if not single:
		views[0].look=Vector3(0,3,0)
		views[1]={"offset":Vector3(3,2,4),"look":Vector3(1,3,1)}
		views[3]={"offset":Vector3(5,5,4),"look":Vector3(2,4,1)}
	for index in views.size():
		camera.position=at+views[index].offset
		camera.position.y=maxf(camera.position.y,zone.height_at(camera.position.x,camera.position.z)+2.0)
		camera.look_at(at+views[index].look)
		for enabled in [false,true]:
			asset.visible=enabled
			var transform:Transform3D=saved[0].transform
			if enabled:transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
			saved[0].node.multimesh.set_instance_transform(saved[0].index,transform)
			label.text=("B | Nuevo | " if enabled else "A | Original | ")+("ROBLE" if single else "LOW | Arbusto denso")+" | Luz 14:00"
			for frame in 35:await process_frame
			await RenderingServer.frame_post_draw
			assert(root.get_texture().get_image().save_png(String(args.out).path_join("vista%d_%s.png"%[index,"B" if enabled else "A"]))==OK)
		if index==0:
			asset.visible=true
			var transform:Transform3D=saved[0].transform;transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO);saved[0].node.multimesh.set_instance_transform(saved[0].index,transform)
			for mesh in asset.find_children("Hojas_*","MeshInstance3D",true,false):mesh.visible=false
			label.text="Estructura | Ramas conectadas antes de las hojas"
			for frame in 30:await process_frame
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(String(args.out).path_join("estructura.png"))
			for mesh in asset.find_children("Hojas_*","MeshInstance3D",true,false):mesh.visible=true
	assert(collisions==zone.find_children("*","CollisionShape3D",true,false).size())
	saved[0].node.multimesh.set_instance_transform(saved[0].index,saved[0].transform);holder.queue_free()
	for record in obstructions:record.node.multimesh.set_instance_transform(record.index,record.transform)
	var report:Dictionary={"variant":manifest.variant,"root_count":roots.size(),"root_gaps":root_gaps,"normal_vertices":normal_vertices,"matte_lit_materials":true,"original_fixture_transform_retained":true,"original_slot_restored":true,"collision_count_unchanged":true,"source_original_model":model_file,"triangles":manifest.triangles,"note":"Isolated renderer at 14:00. No server or user game restarted."}
	var file:=FileAccess.open(String(args.out).path_join("checks.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("BROAD_REVIEW_CHECK_OK");quit()
