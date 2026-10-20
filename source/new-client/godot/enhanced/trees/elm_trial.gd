extends Node
## One reversible visual replacement in the existing fixture batches. No physics or DB changes.
const STATE:="res://.enhanced-session/elm_trial"
var override_manifest:=""
var manifest:Dictionary={}
var enabled:=true
var originals:Array=[]
var replacement:Node3D
var bound_zone:ZoneLoader
var error:=""
var status_label:Label

func read_json(path:String) -> Dictionary:
	var f:=FileAccess.open(path,FileAccess.READ)
	if f==null:return {}
	var data=JSON.parse_string(f.get_as_text())
	return data if data is Dictionary else {}

func configure() -> bool:
	var pointer:=read_json(STATE.path_join("active.json"))
	var path:=override_manifest
	if path.is_empty():
		if pointer.get("disabled",true):return false
		path=String(pointer.get("manifest",""))
		if FileAccess.get_sha256(path)!=pointer.get("sha256",""):return false
	manifest=read_json(path)
	if int(manifest.get("zone",-1))!=207 or int(manifest.get("fixture",-1))!=1109:return false
	if FileAccess.get_sha256(String(manifest.get("scene","")))!=manifest.get("scene_sha256",""):return false
	if FileAccess.get_sha256("res://content/zones/zone207/zone.json")!=manifest.get("zone_sha256",""):return false
	if FileAccess.get_sha256("res://content/zones/zone207/models/helm.gltf")!=manifest.get("stock_sha256",""):return false
	return true

func attach(region:RegionWorld) -> void:
	if region==null or not configure():return
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore(true))
	for zone in region.zones.values():apply_zone(zone)
	if is_instance_valid(replacement):
		var layer:=CanvasLayer.new()
		add_child(layer)
		status_label=Label.new()
		status_label.position=Vector2(20,85)
		status_label.add_theme_font_size_override("font_size",16)
		status_label.add_theme_color_override("font_shadow_color",Color.BLACK)
		status_label.add_theme_constant_override("shadow_outline_size",4)
		layer.add_child(status_label)
		set_enabled(enabled)

func apply_zone(zone:ZoneLoader) -> bool:
	if int(zone.info.get("id",-1))!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	var fixture:Dictionary={}
	for f in zone.info.fixtures:
		if int(f.get("id",-1))==int(manifest.fixture):fixture=f;break
	if fixture.is_empty():return false
	var model:Dictionary=zone.info.models[int(fixture.m)]
	if model.file!=manifest.model:return false
	var at:=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2])
	var matches:Array=[]
	# The inspected stock elm has one identity-transform mesh. Require exactly one matching slot.
	for child in zone.get_children():
		if not child is MultiMeshInstance3D or not String(child.name).begins_with(String(model.name)+"_"):continue
		for i in child.multimesh.instance_count:
			var transform:Transform3D=child.multimesh.get_instance_transform(i)
			if transform.origin.distance_to(at)<0.001:
				matches.append({"node":child,"index":i,"transform":transform})
	if matches.size()!=1:
		error="Expected one original elm slot, found %d"%matches.size()
		push_warning(error)
		return false
	var packed=load(String(manifest.scene))
	if not packed is PackedScene:return false
	var asset:Node3D=packed.instantiate()
	var anchor:=Node3D.new()
	anchor.name="Enhanced_Elm_fixture_1109"
	anchor.add_child(asset)
	anchor.transform=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)),at)
	# Use the same static MultiMesh rendering and draw distance as the original tree.
	var reference:MultiMeshInstance3D=matches[0].node
	for node in asset.find_children("*","MeshInstance3D",true,false):
		var relative:=Transform3D.IDENTITY
		var parent:Node=node
		while parent!=anchor:
			if parent is Node3D:relative=parent.transform*relative
			parent=parent.get_parent()
		var mm:=MultiMesh.new()
		mm.transform_format=MultiMesh.TRANSFORM_3D
		mm.mesh=node.mesh
		mm.instance_count=1
		mm.set_instance_transform(0,relative)
		var batch:=MultiMeshInstance3D.new()
		batch.name=String(node.name)+"_batch"
		batch.multimesh=mm
		batch.visibility_range_end=reference.visibility_range_end
		batch.visibility_range_end_margin=reference.visibility_range_end_margin
		batch.visibility_range_fade_mode=reference.visibility_range_fade_mode
		batch.set_meta("base_far",reference.get_meta("base_far",900.0))
		anchor.add_child(batch)
	anchor.remove_child(asset)
	asset.free()
	zone.add_child(anchor)
	originals=matches
	replacement=anchor
	bound_zone=zone
	set_enabled(enabled)
	print("ELM_TRIAL_APPLIED fixture=207:1109 originals=1 new_tree=1 triangles=",manifest.triangles)
	return true

func set_enabled(value:bool) -> void:
	enabled=value
	for original in originals:
		if not is_instance_valid(original.node):continue
		var transform:Transform3D=original.transform
		if value:transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
		original.node.multimesh.set_instance_transform(int(original.index),transform)
	if is_instance_valid(replacement):replacement.visible=value
	if is_instance_valid(status_label):status_label.text="Olmo: %s | Ctrl+F9: comparar"%("nuevo"if value else"original")

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.keycode==KEY_F9 and is_instance_valid(replacement):
		set_enabled(not enabled)
		get_viewport().set_input_as_handled()

func restore(keep_choice:bool=false) -> void:
	var choice:=enabled
	set_enabled(false)
	originals.clear()
	if is_instance_valid(replacement):replacement.queue_free()
	replacement=null
	bound_zone=null
	if keep_choice:enabled=choice

func _exit_tree() -> void:
	restore()
