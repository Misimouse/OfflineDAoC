extends SceneTree
var out:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")
func run() -> void:
	DirAccess.make_dir_recursive_absolute(out)
	var pointer=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/forest_population/active.json"))
	var manifest=JSON.parse_string(FileAccess.get_file_as_string(pointer.manifest));var records:Array=[]
	for item in manifest.models:
		var scene:Node3D=load(String(item.scene)).instantiate()
		for mesh in scene.find_children("Tronco*","MeshInstance3D",true,false):
			var material:Material=mesh.get_active_material(0);var r:Dictionary={"variant":item.variant,"mesh":String(mesh.name),"material":material.get_class()}
			if material is ShaderMaterial:r["code"]=material.shader.code
			if material is BaseMaterial3D and item.variant=="elm1" and material.albedo_texture!=null:
				material.albedo_texture.get_image().save_png(out.path_join("elm1_bark.png"))
			records.append(r)
		scene.free()
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file("res://content/zones/zone207/models/hbindstone.gltf",state)==OK)
	var stone:=doc.generate_scene(state)
	for mesh in stone.find_children("*","MeshInstance3D",true,false):
		var mat:Material=mesh.get_active_material(0)
		if mat is BaseMaterial3D and mat.albedo_texture!=null:mat.albedo_texture.get_image().save_png(out.path_join(String(mesh.name).replace(":","_")+".png"))
		print("STONE_PART ",mesh.name," bounds=",mesh.mesh.get_aabb()," material=",mat)
	stone.free();var file:=FileAccess.open(out.path_join("materials.json"),FileAccess.WRITE);file.store_string(JSON.stringify(records,"  "));file.close();print("MATERIAL_PROBE_OK");quit()
