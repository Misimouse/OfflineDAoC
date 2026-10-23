extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	var scene:Node3D
	var geometry_unchanged:=false
	var meshes:=0;var triangles:=0
	if args.variant=="grove":
		assert(FileAccess.get_sha256(args.retained)==args.sha256)
		scene=load(String(args.retained)).instantiate()
		var leaf:=ShaderMaterial.new();leaf.shader=shader("detailed_needle.gdshader");leaf.set_shader_parameter("needle_albedo",texture(args.needle))
		for node in scene.find_children("Hojas*","MeshInstance3D",true,false):
			node.mesh=node.mesh.duplicate()
			for surface in node.mesh.get_surface_count():
				var before:Array=node.mesh.surface_get_arrays(surface)
				node.mesh.surface_set_material(surface,leaf)
				assert(before==node.mesh.surface_get_arrays(surface))
		geometry_unchanged=true
	else:
		var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(args.source,state)==OK)
		var imported:=document.generate_scene(state)
		scene=Node3D.new();scene.name="Woody_"+String(args.variant);scene.set_script(load("res://enhanced/trees/broad_root_seating.gd"))
		var axes:=Node3D.new();axes.rotation.x=-PI/2;scene.add_child(axes);axes.add_child(imported)
		var wood:=ShaderMaterial.new();wood.shader=shader("organic_moss.gdshader" if args.has("organic") else "mossy_wood.gdshader");wood.set_shader_parameter("bark_albedo",texture(args.bark));wood.set_shader_parameter("moss_albedo",texture(args.moss))
		if not args.has("organic"):wood.set_shader_parameter("fallen",args.variant=="log")
		var torn:=ShaderMaterial.new();torn.shader=shader("torn_root.gdshader");torn.set_shader_parameter("bark_albedo",texture(args.bark))
		var cut:=ShaderMaterial.new();cut.shader=shader("cut_wood.gdshader");cut.set_shader_parameter("endgrain_albedo",texture(args.endgrain))
		for node in imported.find_children("*","MeshInstance3D",true,false):
			node.mesh=node.mesh.duplicate()
			for surface in node.mesh.get_surface_count():node.mesh.surface_set_material(surface,torn if String(node.name).begins_with("Cepa_desgarrada") else (cut if String(node.name).begins_with("Corte_anillos") else wood))
	for mesh in scene.find_children("*","MeshInstance3D",true,false):
		meshes+=1
		for surface in mesh.mesh.get_surface_count():triangles+=mesh.mesh.surface_get_array_index_len(surface)/3
	assign_owner(scene,scene);var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
	DirAccess.make_dir_recursive_absolute(args.out);var path:=String(args.out).path_join("forest.scn");assert(ResourceSaver.save(packed,path)==OK)
	var manifest:Dictionary={"schema":1,"variant":args.variant,"source_sha256":FileAccess.get_sha256(args.source),"scene":path,"scene_sha256":FileAccess.get_sha256(path),"meshes":meshes,"triangles":triangles,"geometry_unchanged":geometry_unchanged,"matte":true,"moss_not_ivy":args.variant!="grove"}
	if args.variant=="grove":manifest.retained_scene_sha256=args.sha256
	if args.has("organic"):manifest.root_plate=true
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(manifest,"  "));file.close()
	scene.free();print("WOODY_PREPARED ",JSON.stringify(manifest));quit()
func shader(name:String) -> Shader:
	var value:=Shader.new();value.code=FileAccess.get_file_as_string("res://enhanced/trees/"+name);return value
func texture(path:String) -> ImageTexture:
	var value:=Image.load_from_file(path);assert(value!=null and not value.is_empty());value.generate_mipmaps();return ImageTexture.create_from_image(value)
func assign_owner(node:Node,owner_root:Node) -> void:
	for child in node.get_children():child.owner=owner_root;assign_owner(child,owner_root)
