extends Node
## Bounded, reversible art trial: four menhirs and separate ivy overlays on four Ardee structures.
const STATE:="res://.enhanced-session/stone_ivy/"
var override_manifest:=""
var manifest:Dictionary={}
var stones:=true
var ivy:=true
var records:Array=[]
var assets:Array=[]
var bound_zone
var anchor:Node3D
var label:Label
var error:=""
var last_view:=-1.0

func read_json(path:String) -> Dictionary:
	if not FileAccess.file_exists(path):return {}
	var value=JSON.parse_string(FileAccess.get_file_as_string(path))
	return value if value is Dictionary else {}

func configure() -> bool:
	var path:=override_manifest
	if path.is_empty():
		var pointer:=read_json(STATE+"active.json")
		if pointer.get("disabled",true):return false
		path=String(pointer.get("manifest",""))
		if FileAccess.get_sha256(path)!=pointer.get("sha256",""):return false
	manifest=read_json(path)
	if int(manifest.get("zone",-1))!=207 or manifest.get("targets",[]).size()!=8:return false
	var base:="res://content/zones/zone207/"
	if FileAccess.get_sha256(base+"zone.json")!=manifest.get("zone_sha256",""):return false
	var ids:Array=[]
	for entry in manifest.targets:
		ids.append(int(entry.fixture.id))
		if FileAccess.get_sha256(base+String(entry.model.file))!=entry.source_sha256:return false
		if FileAccess.get_sha256(String(entry.scene))!=entry.scene_sha256:return false
	ids.sort()
	if ids!=[334,335,336,935,1107,1429,1430,1431]:return false
	for map in manifest.maps:
		if FileAccess.get_sha256(String(map.path))!=map.sha256:return false
	for path_key in manifest.generated_resource_hashes:
		if FileAccess.get_sha256(String(path_key))!=manifest.generated_resource_hashes[path_key]:return false
	for name in manifest.mask_hashes:
		if FileAccess.get_sha256(base+"textures/x4plus/"+String(name))!=manifest.mask_hashes[name]:return false
	return true

func attach(region) -> void:
	if region==null or not configure():return
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():apply_zone(zone)
	if not records.is_empty():
		var layer:=CanvasLayer.new()
		add_child(layer)
		label=Label.new()
		label.position=Vector2(20,135)
		label.add_theme_font_size_override("font_size",16)
		label.add_theme_color_override("font_shadow_color",Color.BLACK)
		label.add_theme_constant_override("shadow_outline_size",4)
		layer.add_child(label)
		set_choices(stones,ivy)

func fixture_matches(actual:Dictionary,expected:Dictionary) -> bool:
	if actual.keys().size()!=expected.keys().size():return false
	for key in expected:
		if not actual.has(key):return false
		var a=actual[key]
		var b=expected[key]
		if a is Array and b is Array:
			if a.size()!=b.size():return false
			for i in a.size():
				if absf(float(a[i])-float(b[i]))>0.0002:return false
		elif (a is float or a is int) and (b is float or b is int):
			if absf(float(a)-float(b))>0.0002:return false
		elif a!=b:return false
	return true

func apply_zone(zone) -> bool:
	if int(zone.info.get("id",-1))!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	var planned:Array=[]
	# Validate all original slots and placements before loading the new art or hiding anything.
	for entry in manifest.targets:
		var fixture:Dictionary={}
		for f in zone.info.fixtures:
			if int(f.id)==int(entry.fixture.id):fixture=f;break
		if fixture.is_empty() or not fixture_matches(fixture,entry.fixture):
			error="Fixture changed: %s"%entry.fixture.id
			return false
		var model:Dictionary=zone.info.models[int(fixture.m)]
		if model.file!=entry.model.file:return false
		var at:=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2])
		var expected:=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)),at)
		var parts:Array=[]
		var is_stone:bool=entry.has("sculpt")
		var ivy_count:=0
		for node in zone.get_children():
			if not node is MultiMeshInstance3D or not String(node.name).begins_with(String(model.name)+"_"):continue
			var material=node.multimesh.mesh.surface_get_material(0)
			var spec:Dictionary=material.get_meta("spec",{}) if material else {}
			var dark:Dictionary=spec.get("slots",{}).get("dark",{})
			var is_ivy:bool=String(dark.get("tex","")) in ["hclimbvine","hbasevine"]
			if not is_stone and not is_ivy:continue
			for i in node.multimesh.instance_count:
				var transform:Transform3D=node.multimesh.get_instance_transform(i)
				if transform.origin.distance_to(at)>0.001:continue
				if not transform.is_equal_approx(expected):
					error="Uninspected model-part transform: %s"%node.name
					return false
				parts.append({"node":node,"index":i,"transform":transform,"ivy":is_ivy,"stone":is_stone,"material":material})
				if is_ivy:ivy_count+=1
		if (is_stone and parts.size()!=2) or ivy_count!=entry.old_ivy.clean_parts.size():
			error="Unexpected original parts fixture=%s parts=%d ivy=%d expected_ivy=%d"%[fixture.id,parts.size(),ivy_count,entry.old_ivy.clean_parts.size()]
			push_warning(error)
			return false
		planned.append({"entry":entry,"parts":parts,"transform":expected})
	var pending:=Node3D.new()
	pending.name="Enhanced_Stone_Ivy_Ardee"
	var all_records:Array=[]
	var all_assets:Array=[]
	for plan in planned:
		var packed=load(String(plan.entry.scene))
		if not packed is PackedScene:
			pending.free()
			return false
		var asset:Node3D=packed.instantiate()
		asset.transform=plan.transform
		pending.add_child(asset)
		all_assets.append({"node":asset,"stone":plan.entry.has("sculpt"),"reference":plan.parts[0].node,"fixture":int(plan.entry.fixture.id)})
		for part in plan.parts:
			if part.ivy:
				var clean:=MultiMeshInstance3D.new()
				var mm:=MultiMesh.new()
				mm.transform_format=MultiMesh.TRANSFORM_3D
				mm.mesh=part.node.multimesh.mesh
				mm.instance_count=1
				mm.set_instance_transform(0,part.transform)
				clean.multimesh=mm
				clean.material_override=part.material.duplicate()
				clean.material_override.set_shader_parameter("has_dark",false)
				clean.visibility_range_end=part.node.visibility_range_end
				clean.visibility_range_end_margin=part.node.visibility_range_end_margin
				clean.visibility_range_fade_mode=part.node.visibility_range_fade_mode
				pending.add_child(clean)
				part["clean"]=clean
			all_records.append(part)
	zone.add_child(pending)
	anchor=pending
	records=all_records
	assets=all_assets
	bound_zone=zone
	last_view=-1.0
	_process(0.0)
	set_choices(stones,ivy)
	print("STONE_IVY_APPLIED zone=207 stones=4 architecture=4 original_parts=",records.size()," physics_unchanged=true")
	return true

func set_choices(use_stones:bool,use_ivy:bool) -> void:
	stones=use_stones
	ivy=use_ivy
	for record in records:
		if not is_instance_valid(record.node):continue
		var hide:bool=(record.stone and stones) or (record.ivy and ivy)
		var transform:Transform3D=record.transform
		if hide:transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
		record.node.multimesh.set_instance_transform(int(record.index),transform)
		if record.has("clean"):record.clean.visible=ivy and (not record.stone or not stones)
	for asset in assets:
		for child in asset.node.get_children():
			if child.name=="body":
				child.visible=stones
				child.material_override.set_shader_parameter("flat_ivy",not ivy)
			elif String(child.name).begins_with("new_"):child.visible=asset.stone and stones and ivy
			elif String(child.name).begins_with("old_"):child.visible=ivy and (not asset.stone or not stones)
	if is_instance_valid(label):label.text="Piedras: %s (Alt+F7) | Hiedra: %s (Alt+F8)"%["mejoradas"if stones else"originales","3D"if ivy else"original"]

func _process(_delta:float) -> void:
	if last_view==ZoneLoader.view_mult:return
	last_view=ZoneLoader.view_mult
	for asset in assets:
		if not is_instance_valid(asset.node) or not is_instance_valid(asset.reference):continue
		for child in asset.node.get_children():
			if not child is GeometryInstance3D:continue
			child.visibility_range_end=asset.reference.visibility_range_end if child.name=="body" else minf(asset.reference.visibility_range_end,70.0*ZoneLoader.view_mult)
			child.visibility_range_end_margin=minf(asset.reference.visibility_range_end_margin,child.visibility_range_end*.1)
			child.visibility_range_fade_mode=GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	for record in records:
		if record.has("clean") and is_instance_valid(record.clean) and is_instance_valid(record.node):
			record.clean.visibility_range_end=record.node.visibility_range_end
			record.clean.visibility_range_end_margin=record.node.visibility_range_end_margin

func restore() -> void:
	var choices:=[stones,ivy]
	set_choices(false,false)
	records.clear()
	assets.clear()
	if is_instance_valid(anchor):anchor.queue_free()
	anchor=null
	bound_zone=null
	stones=choices[0]
	ivy=choices[1]

func _input(event:InputEvent) -> void:
	if not event is InputEventKey or not event.pressed or event.echo or not event.alt_pressed or records.is_empty():return
	if event.keycode==KEY_F7:set_choices(not stones,ivy)
	elif event.keycode==KEY_F8:set_choices(stones,not ivy)
	else:return
	get_viewport().set_input_as_handled()

func _exit_tree() -> void:
	restore()
