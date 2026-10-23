extends "res://enhanced/trees/prepare_forest.gd"
func run() -> void:
	var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(args.source,state)==OK)
	var imported:=document.generate_scene(state)
	var scene:Node3D
	if args.variant=="elm2":
		scene=load(String(args.retained)).instantiate()
		for old in scene.find_children("Tronco*","MeshInstance3D",true,false):
			if String(old.name).contains("brotes"):continue
			for fresh in imported.find_children("Tronco*","MeshInstance3D",true,false):
				if not String(fresh.name).contains("brotes"):old.mesh=fresh.mesh;break
	else:
		scene=Node3D.new();scene.name="Pino_copa_densa";scene.set_script(load("res://enhanced/trees/broad_root_seating.gd"))
		var axes:=Node3D.new();axes.rotation.x=-PI/2;scene.add_child(axes);axes.add_child(imported)
	var wood:=ShaderMaterial.new();wood.shader=shader("oak_bark.gdshader");wood.set_shader_parameter("bark_albedo",texture(args.bark))
	var leaf:=ShaderMaterial.new();leaf.shader=shader("detailed_needle.gdshader")
	if args.has("needle"):leaf.set_shader_parameter("needle_albedo",texture(args.needle))
	for node in scene.find_children("*","MeshInstance3D",true,false):
		if String(node.name).begins_with("Tronco"):
			node.mesh=node.mesh.duplicate()
			for s in node.mesh.get_surface_count():node.mesh.surface_set_material(s,wood);node.set_surface_override_material(s,null)
			node.material_override=null
		elif args.variant=="grove" and String(node.name).begins_with("Hojas"):
			node.mesh=node.mesh.duplicate()
			for s in node.mesh.get_surface_count():node.mesh.surface_set_material(s,leaf)
			load("res://enhanced/trees/foliage_shadow.gd").add_proxy(node,1600)
	assign_owner(scene,scene);var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
	DirAccess.make_dir_recursive_absolute(args.out);var path:=String(args.out).path_join("forest.scn");assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
	var file:=FileAccess.open(String(args.out).path_join("manifest.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"variant":args.variant,"scene":path,"scene_sha256":FileAccess.get_sha256(path),"source_sha256":FileAccess.get_sha256(args.source)},"  "));file.close()
	if args.variant=="elm2":imported.free()
	scene.free();print("CANOPY_PREPARED ",args.variant);quit()
