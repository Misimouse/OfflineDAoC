extends Node
## Reversible Connacht visual replacement. Original fixture data and physics stay intact.
const STATE:="res://.enhanced-session/forest_population/"
var override_manifest:=""
var manifest:Dictionary={}
var bound_zone
var anchor:Node3D
var originals:Array=[]
var planted:Array=[]
var enabled:=true
var last_view:=-1.0
var previous_taa:=false
var previous_msaa:int=0
var smoothing_changed:=false
var lod_clock:=0.0
func configure() -> bool:
	var path:=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(STATE+"active.json"):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(STATE+"active.json"))
		if pointer.get("disabled",true) or FileAccess.get_sha256(pointer.manifest)!=pointer.sha256:return false
		path=pointer.manifest
	manifest=JSON.parse_string(FileAccess.get_file_as_string(path))
	if manifest.get("zone",-1)!=207 or manifest.get("models",[]).size()!=11:return false
	if FileAccess.get_sha256("res://content/zones/zone207/zone.json")!=manifest.get("zone_sha256",""):return false
	for item in manifest.models:
		if FileAccess.get_sha256(item.scene)!=item.scene_sha256:return false
		if FileAccess.get_sha256("res://content/zones/zone207/"+String(item.file))!=item.stock_sha256:return false
	return true
func attach(region) -> bool:
	if region==null or not configure():return false
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():
		if int(zone.info.id)==207 and not apply_zone(zone):return false
	return true
func apply_zone(zone) -> bool:
	if int(zone.info.id)!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	var plans:Array=[];var slots:Array=[]
	for item in manifest.models:
		var model_index:=-1
		for index in zone.info.models.size():
			if zone.info.models[index].file==item.file:model_index=index;break
		if model_index<0:return false
		var model:Dictionary=zone.info.models[model_index]
		var expected:Dictionary={};var placed:Array=[]
		for fixture in zone.info.fixtures:
			if int(fixture.m)!=model_index:continue
			if fixture.has("basis"):return false
			var at:=Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2])
			if expected.has(at):return false
			expected[at]=true;placed.append(fixture)
		if placed.size()!=int(item.count):return false
		var seen:Dictionary={};var far:=900.0
		for child in zone.get_children():
			if not child is MultiMeshInstance3D or not String(child.name).begins_with(String(model.name)+"_"):continue
			far=float(child.get_meta("base_far",900.0))
			for index in child.multimesh.instance_count:
				var transform:Transform3D=child.multimesh.get_instance_transform(index)
				if not expected.has(transform.origin):return false
				seen[transform.origin]=true;slots.append({"node":child,"index":index,"transform":transform})
		if seen.size()!=placed.size():return false
		plans.append({"spec":item,"fixtures":placed,"far":far})
	# Build each root at its approved fixture transform before terrain seating runs.
	var pending:=Node3D.new();pending.name="Connacht_Approved_Forest"
	for plan in plans:
		var packed:PackedScene=load(String(plan.spec.scene))
		for fixture in plan.fixtures:
			var holder:=Node3D.new();holder.name="Fixture_%d"%int(fixture.id)
			holder.transform=Transform3D(Basis(Vector3.UP,deg_to_rad(float(fixture.yaw))).scaled(Vector3.ONE*float(fixture.scale)*float(plan.spec.art_scale)),Vector3(fixture.pos[0],fixture.pos[1],fixture.pos[2]))
			var asset:Node3D=packed.instantiate();holder.add_child(asset);pending.add_child(holder)
			var meshes:Array=[]
			for mesh in asset.find_children("*","MeshInstance3D",true,false):
				mesh.lod_bias=1.0
				mesh.visibility_range_fade_mode=GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
				meshes.append(mesh)
			planted.append({"id":int(fixture.id),"file":String(plan.spec.file),"holder":holder,"asset":asset,"meshes":meshes,"far":plan.far})
	if planted.size()!=int(manifest.total):pending.free();planted.clear();return false
	zone.add_child(pending);anchor=pending;originals=slots;bound_zone=zone
	previous_taa=get_viewport().use_taa;previous_msaa=get_viewport().msaa_3d
	get_viewport().use_taa=true;get_viewport().msaa_3d=maxi(previous_msaa,Viewport.MSAA_4X) as Viewport.MSAA;smoothing_changed=true
	last_view=-1;_process(0);set_enabled(enabled)
	print("FOREST_POPULATION_APPLIED total=",planted.size()," original_parts=",originals.size());return true
func update_lods(camera:Camera3D) -> void:
	if camera==null:return
	for tree in planted:
		var distance:float=Vector2(camera.global_position.x-tree.holder.global_position.x,camera.global_position.z-tree.holder.global_position.z).length()
		var bias:float=1.0 if distance<22 else (.40 if distance<65 else (.16 if distance<150 else (.07 if distance<300 else .025)))
		if tree.file in ["models/hdeadtree.gltf","models/hbareskny.gltf"]:bias=maxf(bias,.25)
		if tree.get("lod_bias",-1.0)==bias:continue
		tree["lod_bias"]=bias
		for mesh in tree.meshes:mesh.lod_bias=bias
func _process(delta:float) -> void:
	if not is_instance_valid(bound_zone):return
	lod_clock+=delta
	if lod_clock>=.20:
		lod_clock=0;update_lods(get_viewport().get_camera_3d())
	if last_view==ZoneLoader.view_mult:return
	last_view=ZoneLoader.view_mult
	for tree in planted:
		for mesh in tree.meshes:
			mesh.visibility_range_end=float(tree.far)*last_view
			if mesh.cast_shadow==GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY:mesh.visibility_range_end=minf(mesh.visibility_range_end,300.0*last_view)
func model_file_for(stock_file:String) -> String:
	if not enabled or not is_instance_valid(bound_zone):return ""
	for item in manifest.models:
		if item.file==stock_file:return String(item.source)
	return ""
func set_enabled(value:bool) -> void:
	enabled=value
	for record in originals:
		var transform:Transform3D=record.transform
		if value:transform.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
		record.node.multimesh.set_instance_transform(record.index,transform)
	if is_instance_valid(anchor):anchor.visible=value
func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.keycode==KEY_F9:
		set_enabled(not enabled);get_viewport().set_input_as_handled()
func restore() -> void:
	var choice:=enabled;set_enabled(false);enabled=choice
	originals.clear();planted.clear()
	if is_instance_valid(anchor):anchor.queue_free()
	anchor=null;bound_zone=null
	if smoothing_changed:
		get_viewport().use_taa=previous_taa;get_viewport().msaa_3d=previous_msaa as Viewport.MSAA;smoothing_changed=false
func _exit_tree() -> void:restore()
