extends Node
## Isolated Connacht art override. Original water nodes, levels and physics stay intact.
const STATE:="res://.enhanced-session/water_trial/"
var override_manifest:=""
var manifest:Dictionary={}
var bound_zone
var bindings:Array=[]
var pieces:Array=[]
var anchor:Node3D
var mode:=2
var label:Label
var error:=""

func configure() -> bool:
	var path:=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(STATE+"active.json"):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(STATE+"active.json"))
		if not pointer is Dictionary or pointer.get("disabled",true):return false
		path=String(pointer.get("manifest",""))
		if FileAccess.get_sha256(path)!=pointer.get("sha256",""):return false
	var value=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not value is Dictionary:return false
	manifest=value
	if int(manifest.get("zone",-1))!=207 or manifest.get("bodies",[]).size()!=1 or manifest.bodies[0].name!="Water_River":return false
	for rel in manifest.source_hashes:
		if FileAccess.get_sha256("res://"+String(rel))!=manifest.source_hashes[rel]:return false
	if manifest.chunks.size()!=161:return false
	for chunk in manifest.chunks:
		for kind in ["near","far"]:
			if FileAccess.get_sha256(String(chunk[kind].resource))!=chunk[kind].resource_sha256:return false
	return true

func attach(region) -> void:
	if region==null or not configure():return
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	var layer:=CanvasLayer.new()
	add_child(layer)
	label=Label.new()
	label.position=Vector2(20,160)
	label.add_theme_color_override("font_shadow_color",Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size",4)
	layer.add_child(label)
	for zone in region.zones.values():
		if int(zone.info.get("id",-1))==207 and not apply_zone(zone):push_warning("Water trial: "+error)
	set_mode(mode)

func apply_zone(zone) -> bool:
	if int(zone.info.get("id",-1))!=207:return false
	if is_instance_valid(bound_zone):return zone==bound_zone
	var planned:Array=[]
	for body in manifest.bodies:
		var node=zone.get_node_or_null(String(body.name))
		if not node is MeshInstance3D or not node.material_override is ShaderMaterial:
			error="Original water node missing";return false
		if not node.transform.is_equal_approx(Transform3D.IDENTITY):return false
		var vertices:PackedVector3Array=node.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		var raw:=PackedFloat32Array()
		for v in vertices:raw.append_array([v.x,v.y,v.z])
		var hash:=HashingContext.new()
		hash.start(HashingContext.HASH_SHA256);hash.update(raw.to_byte_array())
		if hash.finish().hex_encode()!=body.sha256:
			error="Original water footprint changed";return false
		var mat:=ShaderMaterial.new()
		mat.shader=load("res://enhanced/terrain/water_trial.gdshader")
		planned.append({"node":node,"visible":node.visible,"original_mesh":node.mesh,"original_material":node.material_override,"material":mat,"name":body.name})
	var pending:=Node3D.new()
	pending.name="Enhanced_Water_Connacht"
	var staged:Array=[]
	for chunk in manifest.chunks:
		var binding:Dictionary={}
		for item in planned:
			if item.name==chunk.body:binding=item;break
		if binding.is_empty():pending.free();return false
		for kind in ["near","far"]:
			var mesh=load(String(chunk[kind].resource))
			if not mesh is ArrayMesh:pending.free();return false
			var node:=MeshInstance3D.new()
			node.name=String(chunk.name)+"_"+kind
			node.mesh=mesh
			node.material_override=binding.material
			node.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			node.extra_cull_margin=0.06
			pending.add_child(node)
			staged.append({"node":node,"near":kind=="near"})
	zone.add_child(pending)
	anchor=pending;bound_zone=zone;bindings=planned;pieces=staged
	_process(0.0)
	set_mode(mode)
	print("WATER_TRIAL_APPLIED zone=207 chunks=",manifest.chunks.size()," waves_max_cm=4.0 nominal_level_unchanged=true")
	return true

func set_mode(value:int) -> void:
	mode=clampi(value,0,2)
	for binding in bindings:
		binding.node.visible=binding.visible if mode==0 else false
		binding.material.set_shader_parameter("waves",mode==2)
	for piece in pieces:
		piece.node.visible=mode>0 and (mode==2 or not piece.near)
		piece.node.visibility_range_begin=140.0 if mode==2 and not piece.near else 0.0
		piece.node.visibility_range_end=140.0 if mode==2 and piece.near else 0.0
	if is_instance_valid(label):label.text="Agua: %s | Ctrl+Alt+U: comparar"%[["original","material nuevo","material y ondas 3D"][mode]]

func _process(_delta:float) -> void:
	for binding in bindings:
		if not is_instance_valid(binding.node):continue
		for param in ["bump_tex","env_tex","sky_color","sun_dir","sun_color","drift"]:
			var value=binding.original_material.get_shader_parameter(param)
			if value!=null and binding.material.get_shader_parameter(param)!=value:binding.material.set_shader_parameter(param,value)

func restore() -> void:
	var choice:=mode
	set_mode(0)
	bindings.clear();pieces.clear()
	if is_instance_valid(anchor):anchor.queue_free()
	anchor=null;bound_zone=null;mode=choice

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.alt_pressed and event.keycode==KEY_U and not bindings.is_empty():
		set_mode((mode+1)%3)
		get_viewport().set_input_as_handled()

func _exit_tree() -> void:restore()
