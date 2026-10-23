extends SceneTree
var args:Dictionary={}
func foliage_lods(arrays:Array,group:int,needle:bool) -> Dictionary:
	var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
	var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
	assert(positions.size()%group==0)
	var groups:int=positions.size()/group
	var block:int=indices.size()/groups
	assert(block*groups==indices.size())
	var result:Dictionary={};var added:=0
	var strides:Array=[2,6,16,32] if needle and args.has("dense") else [2,8,32,128]
	for stride in strides:added+=ceili(float(groups)/stride)*group
	for channel in [Mesh.ARRAY_VERTEX,Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_COLOR]:
		if arrays[channel]!=null:arrays[channel]=arrays[channel].duplicate();arrays[channel].resize(positions.size()+added)
	if arrays[Mesh.ARRAY_TANGENT]!=null:
		arrays[Mesh.ARRAY_TANGENT]=arrays[Mesh.ARRAY_TANGENT].duplicate();arrays[Mesh.ARRAY_TANGENT].resize((positions.size()+added)*4)
	var offset:=positions.size()
	var errors:=[.025,.09,.30,.80]
	for level in 4:
		var stride:int=strides[level]
		var target:=PackedInt32Array();target.resize(ceili(float(groups)/stride)*block)
		var cursor:=0
		for leaf in range(0,groups,stride):
			var start:=leaf*group;var center:=Vector3.ZERO
			for k in group:center+=positions[start+k]
			center/=group
			var axis:=Vector3.ZERO
			if needle:axis=(positions[start+2]-positions[start]).normalized()
			var scale:float=minf(sqrt(float(stride))*.90,4.0)
			for k in group:
				var delta:Vector3=positions[start+k]-center
				if needle:
					var along:=axis*delta.dot(axis)
					delta=along*(minf(sqrt(float(stride))*.75,3.0) if args.has("dense") else (1.0+.055*level))+(delta-along)*sqrt(float(stride))
				else:delta*=scale
				arrays[Mesh.ARRAY_VERTEX][offset+k]=center+delta
				for channel in [Mesh.ARRAY_NORMAL,Mesh.ARRAY_TEX_UV,Mesh.ARRAY_TEX_UV2,Mesh.ARRAY_COLOR]:
					if arrays[channel]!=null:arrays[channel][offset+k]=arrays[channel][start+k]
				if arrays[Mesh.ARRAY_TANGENT]!=null:
					for c in 4:arrays[Mesh.ARRAY_TANGENT][(offset+k)*4+c]=arrays[Mesh.ARRAY_TANGENT][(start+k)*4+c]
			for k in block:
				var local:int=indices[leaf*block+k]-start;assert(local>=0 and local<group)
				target[cursor]=offset+local;cursor+=1
			offset+=group
		result[errors[level]]=target
	assert(offset==arrays[Mesh.ARRAY_VERTEX].size())
	return result
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
	call_deferred("run")
func run() -> void:
	var spec:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args.spec))
	assert(FileAccess.get_sha256(spec.scene)==spec.sha256)
	var scene:Node3D=load(String(spec.scene)).instantiate()
	var report:Array=[]
	for node in scene.find_children("*","MeshInstance3D",true,false):
		var source:Mesh=node.mesh
		var importer:=ImporterMesh.new()
		var leaf_group:=0
		if String(node.name).begins_with("Hojas"):
			leaf_group=4 if spec.id=="forest_grove" else (26 if spec.id=="broad_oak" else (12 if spec.id=="broad_low" else (21 if String(spec.id).begins_with("forest_birch") else 0)))
		for s in source.get_surface_count():
			var arrays:Array=source.surface_get_arrays(s)
			var lods:Dictionary=foliage_lods(arrays,leaf_group,spec.id=="forest_grove") if leaf_group>0 else {}
			importer.add_surface(Mesh.PRIMITIVE_TRIANGLES,arrays,[],lods,source.surface_get_material(s),source.surface_get_name(s))
		if leaf_group==0:importer.generate_lods(25.0,60.0,[])
		var surfaces:Array=[]
		for s in source.get_surface_count():
			var levels:Array=[]
			for level in importer.get_surface_lod_count(s):levels.append({"error":importer.get_surface_lod_size(s,level),"triangles":importer.get_surface_lod_indices(s,level).size()/3})
			surfaces.append({"base_triangles":source.surface_get_array_index_len(s)/3,"lods":levels})
		node.mesh=importer.get_mesh()
		for s in source.get_surface_count():
			var before:Array=source.surface_get_arrays(s);var after:Array=node.mesh.surface_get_arrays(s)
			assert(before[Mesh.ARRAY_INDEX]==after[Mesh.ARRAY_INDEX])
			assert(before[Mesh.ARRAY_VERTEX]==after[Mesh.ARRAY_VERTEX].slice(0,before[Mesh.ARRAY_VERTEX].size()))
		report.append({"mesh":String(node.name),"surfaces":surfaces})
	var packed:=PackedScene.new();assert(packed.pack(scene)==OK)
	DirAccess.make_dir_recursive_absolute(args.out)
	var path:=String(args.out).path_join("forest.scn");assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
	var file:=FileAccess.open(String(args.out).path_join("lod_checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify({"id":spec.id,"source_scene_sha256":spec.sha256,"scene":path,"scene_sha256":FileAccess.get_sha256(path),"meshes":report},"  "));file.close()
	scene.free();print("POPULATION_LODS_PREPARED ",spec.id);quit()
