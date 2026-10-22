extends "res://enhanced/trees/check_elm_repair.gd"
## Verify the candidate against its own supplied GLB, not against the previous tree.
func _initialize() -> void:
	await process_frame
	var args:Dictionary={}
	for argument in OS.get_cmdline_user_args():
		var pair:=argument.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args.manifest))
	assert(FileAccess.get_sha256(args.source)==manifest.source_sha256)
	assert(FileAccess.get_sha256(manifest.scene)==manifest.scene_sha256)
	var document:=GLTFDocument.new()
	var state:=GLTFState.new()
	assert(document.append_from_file(args.source,state)==OK)
	var original:=document.generate_scene(state)
	var candidate:Node3D=load(String(manifest.scene)).instantiate()
	var source_parts:=original.find_children("*","MeshInstance3D",true,false)
	var fixed_parts:=candidate.find_children("*","MeshInstance3D",true,false)
	assert(source_parts.size()>=2 and fixed_parts.size()==source_parts.size())
	var results:Array=[]
	for index in source_parts.size():
		var src:MeshInstance3D=source_parts[index]
		var dst:MeshInstance3D=fixed_parts[index]
		assert(geometry_signature(src.mesh)==geometry_signature(dst.mesh))
		var vertices:=0
		var normals:=0
		for surface in dst.mesh.get_surface_count():
			var arrays:=dst.mesh.surface_get_arrays(surface)
			vertices+=arrays[Mesh.ARRAY_VERTEX].size()
			normals+=arrays[Mesh.ARRAY_NORMAL].size()
			for normal in arrays[Mesh.ARRAY_NORMAL]:assert(absf(normal.length()-1.0)<0.02)
			assert(arrays[Mesh.ARRAY_TANGENT].size()==arrays[Mesh.ARRAY_VERTEX].size()*4)
			var before:BaseMaterial3D=src.get_active_material(surface)
			var after:Material=dst.get_active_material(surface)
			var a:=before.albedo_texture.get_image()
			if args.has("bark") and String(src.name).begins_with("Tronco"):
				a=Image.load_from_file(String(args.bark).path_join("bark_colour.jpg"))
			var expected_texture:Texture2D
			if after is ShaderMaterial:
				assert(String(src.name).begins_with("Tronco") and args.has("bark"))
				expected_texture=after.get_shader_parameter("bark_colour")
			else:expected_texture=after.albedo_texture
			var b:=expected_texture.get_image()
			a.clear_mipmaps();b.clear_mipmaps()
			a.convert(Image.FORMAT_RGBA8);b.convert(Image.FORMAT_RGBA8)
			assert(a.get_data()==b.get_data())
		assert(normals==vertices)
		results.append({"part":dst.name,"vertices":vertices,"normals":normals,"same_geometry_and_uv":true,"expected_texture_pixels_preserved":true,"original_texture_pixels_preserved":not(args.has("bark") and String(src.name).begins_with("Tronco"))})
	var zone=load("res://game/zone_loader.gd").new()
	zone.dir="res://content/zones/zone207"
	zone.info=JSON.parse_string(FileAccess.get_file_as_string(zone.dir+"/zone.json"))
	zone._load_heights()
	var fixture:Dictionary={}
	for f in zone.info.fixtures:
		if int(f.id)==1109:fixture=f;break
	var placement:=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)),Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]))
	var gaps:Array[float]=[]
	var trunk:MeshInstance3D=fixed_parts[0]
	for point in trunk.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]:
		if point.z < -0.09:
			var world:Vector3=placement*transform_to_root(trunk)*point
			gaps.append(world.y-zone.height_at(world.x,world.z))
	assert(gaps.size()>=8 and gaps.max()<0.03)
	var file:=FileAccess.open(args.out,FileAccess.WRITE)
	file.store_string(JSON.stringify({"parts":results,"base_samples":gaps.size(),"base_highest_gap_metres":gaps.max(),"base_lowest_gap_metres":gaps.min(),"triangles":manifest.triangles,"note":"Elm2 at the existing well fixture as an isolated comparison. No activation."},"  "))
	file.close()
	original.free();candidate.free();zone.free()
	print("ELM_CANDIDATE_CHECK_OK")
	quit()
