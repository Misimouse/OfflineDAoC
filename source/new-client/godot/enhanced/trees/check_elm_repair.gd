extends SceneTree
func transform_to_root(node:Node) -> Transform3D:
	var result:=Transform3D.IDENTITY
	while node!=null:
		if node is Node3D:result=node.transform*result
		node=node.get_parent()
	return result
func geometry_signature(mesh:Mesh) -> String:
	var digest:=HashingContext.new()
	digest.start(HashingContext.HASH_SHA256)
	for i in mesh.get_surface_count():
		var arrays:=mesh.surface_get_arrays(i)
		var points:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
		var uv:PackedVector2Array=arrays[Mesh.ARRAY_TEX_UV]
		var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		var expanded:=PackedFloat32Array()
		for index in indices:
			expanded.append_array([points[index].x,points[index].y,points[index].z,uv[index].x,uv[index].y])
		digest.update(expanded.to_byte_array())
	return digest.finish().hex_encode()
func inspect(scene:Node3D,zone,fixture:Dictionary) -> Dictionary:
	var parts:Array=[]
	var root_gaps:Array[float]=[]
	var placement:=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)),Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]))
	for node in scene.find_children("*","MeshInstance3D",true,false):
		var normals:=0
		var vertices:=0
		for surface in node.mesh.get_surface_count():
			var arrays:Array=node.mesh.surface_get_arrays(surface)
			var points:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
			vertices+=points.size()
			if arrays[Mesh.ARRAY_NORMAL]!=null:
				normals+=arrays[Mesh.ARRAY_NORMAL].size()
				for normal in arrays[Mesh.ARRAY_NORMAL]:assert(absf(normal.length()-1.0)<0.02)
			var material:BaseMaterial3D=node.get_active_material(surface)
			assert(material!=null and material.albedo_texture!=null)
			var source_path:=str(get_meta("source"))+"/"+("Olmo_corteza.png" if String(node.name).begins_with("Tronco") else "Olmo_follaje.png")
			if bool(get_meta("final",false)) and String(node.name).begins_with("Tronco"):source_path=str(get_meta("bark"))+"/bark_colour.jpg"
			var source:=Image.load_from_file(source_path)
			var image:=material.albedo_texture.get_image()
			source.clear_mipmaps();source.convert(Image.FORMAT_RGBA8)
			image.clear_mipmaps();image.convert(Image.FORMAT_RGBA8)
			assert(source.get_data()==image.get_data(),"Original texture pixels changed")
			if String(node.name).begins_with("Tronco"):
				for point in points:
					var radial:=Vector2(point.x,point.y).length()
					if radial>1.4 and radial<1.8 and point.z<0.1:
						var world:Vector3=placement*transform_to_root(node)*point
						root_gaps.append(world.y-zone.height_at(world.x,world.z))
		parts.append({"name":node.name,"vertices":vertices,"normals":normals,"geometry_uv_signature":geometry_signature(node.mesh),"textures_pixel_identical":true})
	return {"parts":parts,"outer_root_samples":root_gaps.size(),"root_highest_gap_metres":root_gaps.max(),"root_lowest_gap_metres":root_gaps.min()}
func _initialize() -> void:
	await process_frame
	var args:Dictionary={}
	for argument in OS.get_cmdline_user_args():
		var pair:=argument.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	set_meta("source",args.source)
	set_meta("bark",args.get("bark",""))
	var zone=load("res://game/zone_loader.gd").new()
	zone.dir="res://content/zones/zone207"
	zone.info=JSON.parse_string(FileAccess.get_file_as_string(zone.dir+"/zone.json"))
	zone._load_heights()
	var fixture:Dictionary={}
	for f in zone.info.fixtures:
		if int(f.id)==1109:fixture=f;break
	var reports:Array=[]
	for bundle in ["user_20261021",String(args.get("bundle","ground_materials_20261022"))]:
		set_meta("final",bundle!="user_20261021" and args.has("bark"))
		var path:String="res://.enhanced-session/elm_trial/bundles/"+String(bundle)+"/manifest.json"
		var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(path))
		assert(FileAccess.get_sha256(manifest.scene)==manifest.scene_sha256)
		var scene:Node3D=load(manifest.scene).instantiate()
		reports.append(inspect(scene,zone,fixture));scene.free()
	assert(reports[1].root_highest_gap_metres<=0.03,"A root tip still floats above terrain")
	for i in 2:
		assert(reports[0].parts[i].geometry_uv_signature==reports[1].parts[i].geometry_uv_signature)
		assert(reports[1].parts[i].normals==reports[1].parts[i].vertices)
	var output:=FileAccess.open(args.out,FileAccess.WRITE)
	output.store_string(JSON.stringify({"before":reports[0],"corrected":reports[1],"same_geometry_uvs_and_texture_pixels":true,"normals_complete":true,"roots_contact_terrain":true},"  "));output.close()
	zone.free()
	print("ELM_REPAIR_CHECK_OK ",JSON.stringify(reports))
	quit()
