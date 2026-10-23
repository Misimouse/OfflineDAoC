extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	assert(FileAccess.get_sha256(args.scene)==args.sha256)
	var model:Node3D=load(String(args.scene)).instantiate()
	var elm:bool=String(args.variant).begins_with("elm")
	var detail:=Image.load_from_file(args.texture);assert(detail!=null);detail.generate_mipmaps()
	var texture:=ImageTexture.create_from_image(detail)
	var mean:=Vector3.ZERO;var samples:=0
	for y in range(0,detail.get_height(),32):
		for x in range(0,detail.get_width(),32):
			var colour:=detail.get_pixel(x,y).srgb_to_linear();mean+=Vector3(colour.r,colour.g,colour.b);samples+=1
	mean/=float(samples)
	var leaves:=0;var meshes:=0;var vertices:=0;var geometry:Array=[]
	for mesh in model.find_children("*","MeshInstance3D",true,false):
		meshes+=1
		var is_leaf:bool=String(mesh.name).begins_with("Hojas") or String(mesh.name).begins_with("Follaje")
		if is_leaf:mesh.mesh=mesh.mesh.duplicate()
		for surface in mesh.mesh.get_surface_count():
			var arrays:Array=mesh.mesh.surface_get_arrays(surface);vertices+=arrays[Mesh.ARRAY_VERTEX].size()
			var before:Array=[hash(arrays[Mesh.ARRAY_VERTEX]),hash(arrays[Mesh.ARRAY_NORMAL]),hash(arrays[Mesh.ARRAY_INDEX]),hash(arrays[Mesh.ARRAY_TEX_UV])]
			if is_leaf:
				var material:=ShaderMaterial.new();var shader:=Shader.new()
				shader.code=FileAccess.get_file_as_string("res://enhanced/trees/"+("elm_leaf_detail.gdshader" if elm else "textured_leaf.gdshader"));material.shader=shader
				if elm:
					var old:BaseMaterial3D=mesh.get_active_material(surface);assert(old!=null and old.albedo_texture!=null)
					material.set_shader_parameter("leaf_atlas",old.albedo_texture)
					material.set_shader_parameter("cellular_detail",texture);material.set_shader_parameter("detail_mean",mean)
					material.set_shader_parameter("atlas_tint",old.albedo_color);material.set_shader_parameter("original_cutoff",old.alpha_scissor_threshold)
					assert(material.get_shader_parameter("leaf_atlas")==old.albedo_texture)
				else:
					material.set_shader_parameter("leaf_albedo",texture);material.set_shader_parameter("reference_green",Vector3(.055,.17,.028))
				mesh.mesh.surface_set_material(surface,material);mesh.set_surface_override_material(surface,null);leaves+=1
			var after:Array=mesh.mesh.surface_get_arrays(surface)
			assert(before==[hash(after[Mesh.ARRAY_VERTEX]),hash(after[Mesh.ARRAY_NORMAL]),hash(after[Mesh.ARRAY_INDEX]),hash(after[Mesh.ARRAY_TEX_UV])])
			geometry.append({"mesh":mesh.name,"surface":surface,"geometry_unchanged":true,"leaf_surface":is_leaf})
	assert(leaves>0)
	assign_owner(model,model);var packed:=PackedScene.new();assert(packed.pack(model)==OK)
	DirAccess.make_dir_recursive_absolute(args.out);var path:=String(args.out).path_join("forest.scn");assert(ResourceSaver.save(packed,path)==OK)
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"schema":1,"variant":args.variant,"scene":path,"scene_sha256":FileAccess.get_sha256(path),"retained_scene":args.scene,"retained_scene_sha256":args.sha256,"texture_sha256":FileAccess.get_sha256(args.texture),"geometry_unchanged":true,"bark_unchanged":true,"atlas_pixels_and_alpha_unchanged":elm,"leaf_surfaces":leaves,"meshes":meshes,"vertices":vertices,"geometry":geometry},"  "));file.close()
	model.free();print("RETAINED_LEAVES_PREPARED ",args.variant);quit()
func assign_owner(node:Node,owner_root:Node) -> void:
	for child in node.get_children():child.owner=owner_root;assign_owner(child,owner_root)
