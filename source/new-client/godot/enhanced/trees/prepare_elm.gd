extends SceneTree
## Import the supplied GLB as a private Godot scene. Never rewrites the supplied model or zone.
var args := {}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair := arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	run.call_deferred()

func run() -> void:
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	if document.append_from_file(String(args.source),state)!=OK:
		quit(3)
		return
	var imported := document.generate_scene(state)
	var scene := Node3D.new()
	scene.name="Olmo_Enhanced_Prueba"
	var axes := Node3D.new()
	axes.name="Adaptacion_eje_Z_a_Y"
	axes.rotation.x=-PI/2
	scene.add_child(axes)
	axes.add_child(imported)
	var bounds:=AABB()
	var first:=true
	var triangles:=0
	for node in imported.find_children("*","MeshInstance3D",true,false):
		var transform:=Transform3D.IDENTITY
		var parent:Node=node
		while parent!=scene:
			if parent is Node3D:transform=parent.transform*transform
			parent=parent.get_parent()
		var box:AABB=transform*node.mesh.get_aabb()
		bounds=box if first else bounds.merge(box)
		first=false
		for surface in node.mesh.get_surface_count():
			var arrays:Array=node.mesh.surface_get_arrays(surface)
			triangles+=(arrays[Mesh.ARRAY_INDEX].size() if arrays[Mesh.ARRAY_INDEX]!=null else arrays[Mesh.ARRAY_VERTEX].size())/3
			var material:BaseMaterial3D=node.mesh.surface_get_material(surface)
			if material!=null and material.albedo_texture!=null:
				var image:=material.albedo_texture.get_image()
				if not image.has_mipmaps():image.generate_mipmaps()
				material.albedo_texture=ImageTexture.create_from_image(image)
				material.texture_filter=BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	if first or bounds.size.y<=0:
		quit(4)
		return
	# Match the old elm's above-ground height with uniform scaling; never stretch the crown.
	var old_json:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/zones/zone207/models/helm.gltf"))
	var old_top:=0.0
	for mesh in old_json.meshes:
		for primitive in mesh.primitives:
			var accessor:Dictionary=old_json.accessors[int(primitive.attributes.POSITION)]
			old_top=maxf(old_top,float(accessor.max[1]))
	var scale_factor:=old_top/bounds.size.y
	scene.scale=Vector3.ONE*scale_factor
	axes.position.y=-bounds.position.y
	assign_owner(scene,scene)
	var packed:=PackedScene.new()
	assert(packed.pack(scene)==OK)
	var out:=String(args.out)
	DirAccess.make_dir_recursive_absolute(out)
	var path:=out.path_join("elm.scn")
	assert(ResourceSaver.save(packed,path)==OK)
	var manifest:Dictionary={"schema":1,"zone":207,"fixture":1109,"model":"models/helm.gltf","source_sha256":FileAccess.get_sha256(String(args.source)),"zone_sha256":FileAccess.get_sha256("res://content/zones/zone207/zone.json"),"stock_sha256":FileAccess.get_sha256("res://content/zones/zone207/models/helm.gltf"),"scene":path,"scene_sha256":FileAccess.get_sha256(path),"triangles":triangles,"stock_triangles":266,"uniform_scale":scale_factor,"height_metres_before_fixture_scale":old_top,"source_bounds_y_up":{"position":[bounds.position.x,bounds.position.y,bounds.position.z],"size":[bounds.size.x,bounds.size.y,bounds.size.z]},"note":"One visual replacement only. Original fixture placement, collision and source art remain untouched. Prototype has no dedicated distance LODs."}
	var file:=FileAccess.open(out.path_join("manifest.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest,"  "))
	file.close()
	scene.free()
	print("ELM_PREPARED ",JSON.stringify(manifest))
	quit()

func assign_owner(node:Node,owner_root:Node) -> void:
	for child in node.get_children():
		child.owner=owner_root
		assign_owner(child,owner_root)
