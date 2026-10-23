extends Node
## Reversible visual prototype; preserves bindstone geometry and all stock physics.
const STATE:="res://.enhanced-session/forest_revision_20261023/mushroom/"
var override_manifest:=""
var manifest:Dictionary={}
var bound_zone
var display:Node3D
var originals:Array=[]
var rows:Array=[]
var mushrooms:Array=[]
func attach(region) -> bool:
	var path:=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(STATE+"active.json"):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(STATE+"active.json"))
		if pointer.get("disabled",true) or FileAccess.get_sha256(pointer.manifest)!=pointer.sha256:return false
		path=pointer.manifest
	manifest=JSON.parse_string(FileAccess.get_file_as_string(path))
	if FileAccess.get_sha256(manifest.scene)!=manifest.sha256:return false
	for file in manifest.stock_hashes:
		if FileAccess.get_sha256("res://content/zones/zone207/models/"+String(file))!=manifest.stock_hashes[file]:return false
	region.zone_added.connect(apply_zone);region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():apply_zone(zone)
	return true
func apply_zone(zone) -> void:
	if int(zone.info.id)!=207 or is_instance_valid(bound_zone):return
	var pending:=Node3D.new();pending.name="Setas_magicas_prueba"
	var packed:PackedScene=load(String(manifest.scene))
	var plans:Array=[]
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		var name_string:=String(child.name)
		if not name_string.begins_with("Shroom Ring_") and not (name_string.begins_with("Bindstone_") and child.multimesh.mesh.get_aabb().size.y<1.0):continue
		for index in child.multimesh.instance_count:plans.append({"node":child,"index":index,"transform":child.multimesh.get_instance_transform(index)})
	if plans.size()!=9:pending.free();push_error("Expected nine mushroom rings; stock retained");return
	for fixture in zone.info.fixtures:
		var file:String=zone.info.models[int(fixture.m)].file.get_file()
		if not manifest.rings.has(file):continue
		var holder:=Node3D.new();holder.transform=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)),Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]));pending.add_child(holder)
		for component in manifest.rings[file]:
			var model:Node3D=packed.instantiate();var lo:Vector3=Vector3(component.minimum[0],component.minimum[1],component.minimum[2]);var hi:=Vector3(component.maximum[0],component.maximum[1],component.maximum[2]);var size:=hi-lo
			model.scale=Vector3(size.x/2.92,size.y/2.65,size.z/2.92);model.position=Vector3(component.center[0],0,component.center[2]);holder.add_child(model);mushrooms.append(model)
	var giant:Node3D=packed.instantiate();giant.name="Seta_gigante_prueba";giant.scale=Vector3.ONE*float(manifest.giant_scale);giant.position=Vector3(manifest.giant_x,0,manifest.giant_z);pending.add_child(giant);mushrooms.append(giant)
	zone.add_child(pending)
	for model in mushrooms:
		var at:Vector3=zone.to_local(model.global_position);at.y=zone.height_at(at.x,at.z)-.025;model.global_position=zone.to_global(at)
		for mesh in model.find_children("*","MeshInstance3D",true,false):mesh.visibility_range_end=600 if model==giant else 180
	var at:Vector3=giant.position
	var label:=Label3D.new();label.text="Seta gigante · prueba";label.billboard=BaseMaterial3D.BILLBOARD_ENABLED;label.font_size=42;label.outline_size=10;label.position=at+Vector3.UP*3;label.visibility_range_end=70;pending.add_child(label)
	rows=[{"id":"review:mushroom_giant","name":"Seta gigante · prueba","position":[at.x,at.y,at.z],"model":"Seta mágica","kind":"Prueba de seta","zone":207,"model_file":"","image_files":[manifest.texture],"note":"Prototipo LAB: sombrero redondeado, láminas y pie nuevo. Sin tenderos ni colisiones añadidas."}]
	originals=plans;display=pending;bound_zone=zone
	for record in originals:
		var transform:Transform3D=record.transform;transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO);record.node.multimesh.set_instance_transform(record.index,transform)
	print("MUSHROOM_TRIAL_READY small=",mushrooms.size()-1," giant=1")
func restore() -> void:
	for record in originals:
		if is_instance_valid(record.node):record.node.multimesh.set_instance_transform(record.index,record.transform)
	originals.clear();rows.clear();mushrooms.clear()
	if is_instance_valid(display):display.queue_free()
	display=null;bound_zone=null
func _exit_tree() -> void:restore()
