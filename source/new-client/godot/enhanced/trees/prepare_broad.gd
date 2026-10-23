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
	var scene:=Node3D.new();scene.name="Broad_Enhanced_"+String(args.variant)
	scene.set_script(load("res://enhanced/trees/broad_root_seating.gd"))
	var axes:=Node3D.new();axes.rotation.x=-PI/2;scene.add_child(axes);axes.add_child(imported)
	var wood_material:=ShaderMaterial.new();var leaf_material:=ShaderMaterial.new()
	for pair in [[wood_material,"oak_bark.gdshader"],[leaf_material,"birch_leaf.gdshader"]]:
		var shader:=Shader.new();shader.code=FileAccess.get_file_as_string("res://enhanced/trees/"+pair[1]);pair[0].shader=shader
	var image:=Image.load_from_file(args.bark);assert(image!=null and not image.is_empty())
	image.generate_mipmaps();wood_material.set_shader_parameter("bark_albedo",ImageTexture.create_from_image(image))
	var triangles:=0;var meshes:=0
	for mesh in imported.find_children("*","MeshInstance3D",true,false):
		mesh.mesh=mesh.mesh.duplicate()
		var bark_for_stem:ShaderMaterial=wood_material.duplicate()
		bark_for_stem.set_shader_parameter("tree_seed",float(String(mesh.name).get_slice("_",1).to_int())*19.7+(3.0 if args.variant=="single" else 41.0))
		for surface in mesh.mesh.get_surface_count():
			var arrays:Array=mesh.mesh.surface_get_arrays(surface)
			assert(arrays[Mesh.ARRAY_NORMAL].size()==arrays[Mesh.ARRAY_VERTEX].size())
			triangles+=arrays[Mesh.ARRAY_INDEX].size()/3
			mesh.mesh.surface_set_material(surface,leaf_material if String(mesh.name).begins_with("Hojas") else bark_for_stem)
		mesh.material_override=null;meshes+=1
	assign_owner(scene,scene)
	var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
	DirAccess.make_dir_recursive_absolute(args.out)
	var path:=String(args.out).path_join("broad.scn");assert(ResourceSaver.save(packed,path)==OK)
	var manifest:Dictionary={"schema":1,"variant":args.variant,"source_sha256":FileAccess.get_sha256(args.source),"scene":path,"scene_sha256":FileAccess.get_sha256(path),"meshes":meshes,"triangles":triangles,"source_up":"Z","roots":1,"materials":"Lit, fully rough, zero metallic/specular/emission; geometry leaves have no alpha cards"}
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE);file.store_string(JSON.stringify(manifest,"  "));file.close()
	scene.free();print("BROAD_PREPARED ",JSON.stringify(manifest));quit()
func assign_owner(node:Node,owner_root:Node) -> void:
	for child in node.get_children():child.owner=owner_root;assign_owner(child,owner_root)
