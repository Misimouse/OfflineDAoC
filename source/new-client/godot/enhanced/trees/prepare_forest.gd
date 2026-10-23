extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	var document:=GLTFDocument.new();var state:=GLTFState.new()
	assert(document.append_from_file(args.source,state)==OK)
	var imported:=document.generate_scene(state)
	var scene:=Node3D.new();scene.name="Forest_Enhanced_"+String(args.variant)
	scene.set_script(load("res://enhanced/trees/broad_root_seating.gd"))
	var axes:=Node3D.new();axes.rotation.x=-PI/2;scene.add_child(axes);axes.add_child(imported)
	var wood:=ShaderMaterial.new();wood.shader=shader("oak_bark.gdshader")
	wood.set_shader_parameter("bark_albedo",texture(args.bark))
	wood.set_shader_parameter("weathering",0.72 if args.variant=="bare" else (0.45 if args.variant=="dead" else 0.0))
	var leaf:=ShaderMaterial.new()
	if args.variant=="grove":leaf.shader=shader("needle.gdshader")
	elif args.has("leaf"):
		leaf.shader=shader("textured_leaf.gdshader");leaf.set_shader_parameter("leaf_albedo",texture(args.leaf))
	var triangles:=0;var meshes:=0;var shadow_triangles:=0
	for mesh in imported.find_children("*","MeshInstance3D",true,false):
		mesh.mesh=mesh.mesh.duplicate()
		for surface in mesh.mesh.get_surface_count():
			var arrays:Array=mesh.mesh.surface_get_arrays(surface)
			assert(arrays[Mesh.ARRAY_NORMAL].size()==arrays[Mesh.ARRAY_VERTEX].size())
			triangles+=arrays[Mesh.ARRAY_INDEX].size()/3
			mesh.mesh.surface_set_material(surface,leaf if String(mesh.name).begins_with("Hojas") else wood)
		mesh.material_override=null;meshes+=1
		if String(mesh.name).begins_with("Hojas") and args.get("shadow_profile","stable")=="stable":
			var count:=1664 if args.variant=="oak" else (672 if args.variant=="low" else 1280)
			shadow_triangles+=load("res://enhanced/trees/foliage_shadow.gd").add_proxy(mesh,count)
	assign_owner(scene,scene)
	var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
	DirAccess.make_dir_recursive_absolute(args.out)
	var path:=String(args.out).path_join("forest.scn");assert(ResourceSaver.save(packed,path)==OK)
	var manifest:Dictionary={"schema":1,"variant":args.variant,"source_sha256":FileAccess.get_sha256(args.source),"scene":path,"scene_sha256":FileAccess.get_sha256(path),"meshes":meshes,"triangles":triangles,"source_up":"Z","roots":1,"shadow_profile":args.get("shadow_profile","stable"),"shadow_proxy_triangles":shadow_triangles,"materials":"Matte lit materials; mipmapped leaf detail; specular 0"}
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(manifest,"  "));file.close()
	scene.free();print("FOREST_PREPARED ",JSON.stringify(manifest));quit()
func shader(name:String) -> Shader:
	var value:=Shader.new();value.code=FileAccess.get_file_as_string("res://enhanced/trees/"+name);return value
func texture(path:String) -> ImageTexture:
	var value:=Image.load_from_file(path);assert(value!=null and not value.is_empty());value.generate_mipmaps();return ImageTexture.create_from_image(value)
func assign_owner(node:Node,owner_root:Node) -> void:
	for child in node.get_children():child.owner=owner_root;assign_owner(child,owner_root)
