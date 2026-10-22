extends RefCounted
## Godot Forge revision. Sources, RGB atlases, mesh and classic install remain private/unchanged.
const ACTIVE="res://.enhanced-session/godot_tools/active.json"
var bindings:Array=[]
var textures:Dictionary={}
func _init() -> void:
	if not FileAccess.file_exists(ACTIVE):return
	var pointer=JSON.parse_string(FileAccess.get_file_as_string(ACTIVE))
	if not pointer is Dictionary:return
	var path=String(pointer.get("manifest",""))
	var stage=ProjectSettings.globalize_path("res://.enhanced-session/godot_tools/").replace("\\","/")
	if not path.replace("\\","/").begins_with(stage) or FileAccess.get_sha256(path)!=pointer.get("sha256",""):return
	var value=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not value is Dictionary or int(value.get("schema",-1))!=1:return
	var pending:Array=[]
	for item in value.get("bindings",[]):
		if not item is Dictionary:return
		var image=String(item.get("path",""))
		if not image.replace("\\","/").begins_with(stage):return
		if FileAccess.get_sha256(image)!=item.get("sha256",""):return
		pending.append(item)
	bindings=pending

func canonical(path:String) -> String:
	return ProjectSettings.globalize_path(path).replace("\\","/").trim_suffix("/").to_lower()

func for_folders(folders:Dictionary) -> Dictionary:
	var original=String(folders.get("original",""))
	var result:Dictionary={}
	if original.is_empty():return result
	for item in bindings:
		var source=original.path_join(String(item.name)+".png")
		if canonical(source)!=canonical(String(item.original)):continue
		if FileAccess.get_sha256(source)!=item.original_sha256:continue
		result[String(item.name)]=String(item.path)
	return result

func resolve_file(path:String) -> String:
	var original=path.replace("/x4plus/","/original/").replace("\\x4plus\\","\\original\\")
	for item in bindings:
		if canonical(String(item.original))==canonical(original) and FileAccess.get_sha256(original)==item.original_sha256:
			return String(item.path)
	return path

func texture(path:String) -> Texture2D:
	if not textures.has(path):
		var image=Image.load_from_file(path)
		if image==null:return null
		image.generate_mipmaps();textures[path]=ImageTexture.create_from_image(image)
	return textures[path]

func apply_gltf(root:Node3D,path:String) -> int:
	if bindings.is_empty():return 0
	var document=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not document is Dictionary:return 0
	var by_material:Dictionary={}
	for material in document.get("materials",[]):
		var index=int(material.get("pbrMetallicRoughness",{}).get("baseColorTexture",{}).get("index",-1))
		if index<0:continue
		var source=int(document.textures[index].get("source",-1))
		if source<0:continue
		var uri=String(document.images[source].get("uri",""))
		if uri.begins_with("data:"):continue
		var source_path=path.get_base_dir().path_join(uri).simplify_path()
		var resolved=resolve_file(source_path)
		if canonical(source_path)!=canonical(resolved):by_material[String(material.get("name",""))]=resolved
	var count=0
	for mesh in root.find_children("*","MeshInstance3D",true,false):
		for surface in mesh.mesh.get_surface_count():
			var original=mesh.mesh.surface_get_material(surface)
			if not original is StandardMaterial3D or not by_material.has(original.resource_name):continue
			var replacement=original.duplicate()
			replacement.albedo_texture=texture(String(by_material[original.resource_name]))
			if replacement.albedo_texture==null:continue
			mesh.set_surface_override_material(surface,replacement);count+=1
	return count
