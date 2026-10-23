extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	var pointer:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/stone_ivy/active.json"))
	assert(FileAccess.get_sha256(pointer.manifest)==pointer.sha256)
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(pointer.manifest))
	var image:=Image.load_from_file(args.texture);assert(image!=null);image.generate_mipmaps()
	var material:=ShaderMaterial.new();var shader:=Shader.new();shader.code=FileAccess.get_file_as_string("res://enhanced/terrain/textured_ivy.gdshader");material.shader=shader;material.set_shader_parameter("leaf_albedo",ImageTexture.create_from_image(image))
	DirAccess.make_dir_recursive_absolute(args.out)
	var changed:=0
	for entry in manifest.targets:
		assert(FileAccess.get_sha256(entry.scene)==entry.scene_sha256)
		var scene:Node3D=load(String(entry.scene)).instantiate()
		for node in scene.find_children("*leaves","MeshInstance3D",true,false):
			var arrays:Array=[]
			for s in node.mesh.get_surface_count():arrays.append(node.mesh.surface_get_arrays(s))
			node.material_override=material;changed+=1
			for s in node.mesh.get_surface_count():assert(arrays[s]==node.mesh.surface_get_arrays(s))
		var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
		var path:=String(args.out).path_join("fixture_%d.scn"%int(entry.fixture.id));assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
		entry.previous_scene_sha256=entry.scene_sha256;entry.scene=path;entry.scene_sha256=FileAccess.get_sha256(path);scene.free()
	assert(changed>0)
	manifest.leaf_detail={"geometry_unchanged":true,"leaf_parts":changed,"texture_sha256":FileAccess.get_sha256(args.texture),"matte":true}
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(manifest,"  "));file.close()
	print("IVY_DETAIL_PREPARED leaf_parts=",changed);quit()
