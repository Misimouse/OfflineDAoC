extends SceneTree
var state:="res://.enhanced-session/water_trial/"
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--state="):state=arg.trim_prefix("--state=")
	assert(state.begins_with("res://.enhanced-session/water_trial/") and not ".." in state)
	call_deferred("run")
func run() -> void:
	var data:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(state+"geometry.json"))
	for entry in data.chunks:
		for kind in ["near","far"]:
			var spec:Dictionary=entry[kind]
			assert(FileAccess.get_sha256(state+String(spec.vertex_file))==spec.vertex_sha256)
			assert(FileAccess.get_sha256(state+String(spec.index_file))==spec.index_sha256)
			var raw:=FileAccess.get_file_as_bytes(state+String(spec.vertex_file)).to_float32_array()
			var vertices:=PackedVector3Array()
			var normals:=PackedVector3Array()
			var colours:=PackedColorArray()
			for i in int(spec.vertices):
				vertices.append(Vector3(raw[i*4],raw[i*4+1],raw[i*4+2]))
				normals.append(Vector3.UP)
				colours.append(Color(raw[i*4+3],0,0,1))
			var indices:=FileAccess.get_file_as_bytes(state+String(spec.index_file)).to_int32_array()
			var arrays:=[]
			arrays.resize(Mesh.ARRAY_MAX)
			arrays[Mesh.ARRAY_VERTEX]=vertices
			arrays[Mesh.ARRAY_NORMAL]=normals
			arrays[Mesh.ARRAY_COLOR]=colours
			arrays[Mesh.ARRAY_INDEX]=indices
			var mesh:=ArrayMesh.new()
			mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
			var path:String=state+String(entry.name)+"_"+kind+".res"
			assert(ResourceSaver.save(mesh,path,ResourceSaver.FLAG_COMPRESS)==OK)
			spec.resource=ProjectSettings.globalize_path(path)
			spec.resource_sha256=FileAccess.get_sha256(path)
	var file:=FileAccess.open(state+"manifest.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(data,"  "));file.close()
	print("WATER_PREPARE_OK chunks=",data.chunks.size())
	quit()
