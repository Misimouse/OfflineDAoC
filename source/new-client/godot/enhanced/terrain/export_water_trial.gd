extends SceneTree
const STATE:="res://.enhanced-session/water_trial/"
func _initialize() -> void:call_deferred("run")
func run() -> void:
	var zone=load("res://game/zone_loader.gd").new()
	root.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	var bodies:=[]
	for node in zone.get_children():
		if not node is MeshInstance3D or not String(node.name).begins_with("Water_"):continue
		var verts:PackedVector3Array=node.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		assert(verts.size()%6==0)
		var raw:=PackedFloat32Array()
		for v in verts:raw.append_array([v.x,v.y,v.z])
		var path:=STATE+String(node.name)+".stock"
		var file:=FileAccess.open(path,FileAccess.WRITE)
		file.store_buffer(raw.to_byte_array());file.close()
		bodies.append({"name":String(node.name),"vertices":verts.size(),"file":ProjectSettings.globalize_path(path),"sha256":FileAccess.get_sha256(path),"height":verts[0].y})
	var hashes:Dictionary={}
	for rel in ["game/water.gdshader","game/zone_loader.gd","content/zones/zone207/zone.json","content/zones/zone207/water.png","content/zones/zone207/heights_2x.f32"]:
		hashes[rel]=FileAccess.get_sha256("res://"+rel)
	for rel in zone.info.get("water_maps",{}).values():
		var key:String="content/zones/zone207/"+String(rel)
		hashes[key]=FileAccess.get_sha256("res://"+key)
	var file:=FileAccess.open(STATE+"export.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"zone":207,"bodies":bodies,"source_hashes":hashes},"  "));file.close()
	print("WATER_STOCK_EXPORT_OK bodies=",bodies.size())
	zone.queue_free()
	await process_frame
	quit()
