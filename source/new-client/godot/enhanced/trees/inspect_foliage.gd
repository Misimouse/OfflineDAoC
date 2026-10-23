extends SceneTree
func _initialize() -> void:
	var config:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/elm_trial/review_stand.json"))
	for item in config.trees:
		var scene:Node3D=load(String(item.scene)).instantiate()
		for node in scene.find_children("*","MeshInstance3D",true,false):
			if not (String(node.name).begins_with("Hojas") or String(node.name).begins_with("Follaje")):continue
			for s in node.mesh.get_surface_count():
				var a:Array=node.mesh.surface_get_arrays(s)
				print(item.id," ",node.name," vertices=",a[Mesh.ARRAY_VERTEX].size()," indices=",a[Mesh.ARRAY_INDEX].size()," first=",a[Mesh.ARRAY_INDEX].slice(0,60))
		scene.free()
	quit()
