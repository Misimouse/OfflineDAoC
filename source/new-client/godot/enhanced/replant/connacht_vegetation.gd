extends Node
## Connacht-wide deterministic near-field vegetation using the approved v4 model palette.
## Numeric terrain/road masks replace the old review ovals. Original clutter stays disabled.
const POINTER="res://.enhanced-session/connacht_vegetation/active.json"
const CELL=16.0
const ATTEMPTS=10000
var override_manifest:=""
var manifest:Dictionary={}
var mask:Image
var bound_zone
var viewer:Node3D
var cells:Dictionary={}
var meshes:Dictionary={}
var material:ShaderMaterial
var job:Dictionary={}
var clock:=0.0
var life_clock:=0.0
var built_groups:=0
var peak_job_us:=0
var cache:Dictionary={}
var lru:Array=[]
var workers:Array=[]
var generator
var visible_cells:Array=[]
var prefetch_cells:Array=[]
var velocity:=Vector2.ZERO
var last_position:=Vector2(INF,INF)
var plan_elapsed:=1.0
var worker_error:=false
var cache_hits:=0
var generation_us:=0
const CACHE_LIMIT=160
const WORKERS=2
var worker_limit:=2
var distance_cover
func configure() -> bool:
	var path=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(POINTER):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(POINTER))
		if not pointer is Dictionary or pointer.get("disabled",true):return false
		path=String(pointer.get("manifest",""))
		if path.is_empty() or FileAccess.get_sha256(path)!=pointer.get("sha256",""):return false
	var data=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not data is Dictionary or data.get("zone")!=207 or data.get("scope")!="whole-connacht":return false
	if FileAccess.get_sha256("res://content/zones/zone207/zone.json")!=data.get("source_sha256",""):return false
	for file in data.files:
		if FileAccess.get_sha256(file.path)!=file.sha256:return false
	manifest=data;worker_limit=clampi(int(data.get("worker_count",2)),1,2);mask=Image.load_from_file(manifest.mask)
	return mask!=null
func attach(region,follow:Node3D=null) -> bool:
	if region==null or not configure():return false
	viewer=follow
	_prepare_art()
	region.zone_added.connect(apply_zone);region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():
		if int(zone.info.id)==207 and not apply_zone(zone):return false
	if manifest.has("distance_manifest"):
		distance_cover=load(manifest.distance_controller).new();distance_cover.override_manifest=manifest.distance_manifest;add_child(distance_cover)
		if not distance_cover.attach(region,viewer):return false
	return true
func _prepare_art() -> void:
	var factory=load("res://enhanced/landscape_patch.gd").new();meshes=factory.make_catalog();material=factory.make_material(true)
	var shader=material.shader.duplicate();shader.code=shader.code.replace("uniform float wind_clock = 0.0;","uniform float wind_clock = 0.0; uniform vec3 vegetation_focus=vec3(0.0);");shader.code=shader.code.replace("float shrink = 1.0 - smoothstep(35.0, 50.0, distance(wp, CAMERA_POSITION_WORLD));", "float dist = distance(wp.xz,vegetation_focus.xz); float rank=INSTANCE_CUSTOM.g; float lod=mix(1.0,smoothstep(.60,.70,rank),smoothstep(16.0,28.0,dist)); float shrink=(1.0-smoothstep(26.0,36.0,dist))*lod;");material.shader=shader;factory.free()
	if is_instance_valid(viewer):material.set_shader_parameter("vegetation_focus",viewer.global_position)
func apply_zone(zone) -> bool:
	if int(zone.info.id)!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	bound_zone=zone
	generator=load(manifest.get("worker_path","res://enhanced/replant/vegetation_worker.gd")).new()
	var image=mask.duplicate();image.convert(Image.FORMAT_RGBA8);generator.pixels=image.get_data()
	generator.heights=zone.heights;generator.hsize=zone.hsize;generator.hcell=zone.cell
	generator.water_size=0;generator.levels={}
	if zone.water_mask!=null:
		var wm=zone.water_mask.duplicate();wm.convert(Image.FORMAT_R8);generator.water_size=wm.get_width();generator.water=wm.get_data()
		for body in zone.info.water:generator.levels[int(body.id)]=float(body.height)
	plan_elapsed=1.0;return true
func sample(p:Vector2) -> Color:
	if p.x<0 or p.y<0 or p.x>=1638.4 or p.y>=1638.4:return Color(0,0,0,1)
	return mask.get_pixel(clampi(int(p.x/1.6),0,1023),clampi(int(p.y/1.6),0,1023))
func _touch(c:Vector2i) -> void:
	lru.erase(c);lru.append(c)
func _cache_result(result:Dictionary) -> void:
	cache[result.cell]=result;generation_us=maxi(generation_us,int(result.generation_us));_touch(result.cell)
	while cache.size()>CACHE_LIMIT:
		var victim=lru.pop_front();cache.erase(victim)
func _upload(result:Dictionary) -> Node3D:
	var start=Time.get_ticks_usec();var node=load("res://enhanced/replant/continuous_patch.gd").new();node.name="Natural_%d_%d"%[result.cell.x,result.cell.y];node.mask=mask;bound_zone.add_child(node)
	for name in result.groups:
		var buffer:PackedFloat32Array=result.groups[name];var mm=MultiMesh.new();mm.transform_format=MultiMesh.TRANSFORM_3D;mm.use_custom_data=true;mm.mesh=meshes[name];mm.instance_count=buffer.size()/16;mm.buffer=buffer
		var batch=MultiMeshInstance3D.new();batch.name=name;batch.multimesh=mm;batch.material_override=material;batch.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF;batch.extra_cull_margin=.15;batch.visibility_range_end=65;node.add_child(batch)
	peak_job_us=maxi(peak_job_us,Time.get_ticks_usec()-start);built_groups+=int(result.count);return node
# Synchronous adapter for offline placement comparisons only; gameplay uses worker threads.
func _start(c:Vector2i) -> void:job={"cell":c,"result":generator.generate(c)}
func _advance(_budget_us:int=3500) -> void:
	if job.is_empty():return
	_cache_result(job.result);cells[job.cell]=_upload(job.result);job={}
func _score(c:Vector2i,p:Vector2,ahead:Vector2) -> float:
	var mid=Vector2((c.x+.5)*CELL,(c.y+.5)*CELL);var distance=mid.distance_to(p)
	return distance-10000.0 if distance<52 else minf(distance,mid.distance_to(ahead)+24)
func _plan(p:Vector2) -> void:
	var centre=Vector2i(floori(p.x/CELL),floori(p.y/CELL));var ahead=p+velocity.limit_length(18)*1.8
	visible_cells.clear();prefetch_cells.clear()
	for y in range(-7,8):
		for x in range(-7,8):
			var c=centre+Vector2i(x,y)
			if c.x<0 or c.y<0 or c.x>=103 or c.y>=103:continue
			var mid=Vector2((c.x+.5)*CELL,(c.y+.5)*CELL);var distance=mid.distance_to(p)
			if distance<52:visible_cells.append(c)
			if distance<88 or mid.distance_to(ahead)<80:prefetch_cells.append(c)
	visible_cells.sort_custom(func(a,b):return _score(a,p,ahead)<_score(b,p,ahead))
	prefetch_cells.sort_custom(func(a,b):return _score(a,p,ahead)<_score(b,p,ahead))
	for c in cells.keys():
		if Vector2((c.x+.5)*CELL,(c.y+.5)*CELL).distance_to(p)>72:cells[c].queue_free();cells.erase(c)
func _collect() -> void:
	for i in range(workers.size()-1,-1,-1):
		var thread:Thread=workers[i].thread
		if thread.is_alive():continue
		var result=thread.wait_to_finish();workers.remove_at(i)
		if result is Dictionary:_cache_result(result)
		else:worker_error=true;push_error("Connacht vegetation worker failed")
func _schedule() -> void:
	if worker_error:return
	for c in prefetch_cells:
		if workers.size()>=worker_limit:break
		if cache.has(c) or cells.has(c):continue
		var pending=false
		for work in workers:
			if work.cell==c:pending=true;break
		if pending:continue
		var thread=Thread.new();var result=thread.start(generator.generate.bind(c))
		if result==OK:workers.append({"cell":c,"thread":thread})
		else:worker_error=true;push_error("Connacht vegetation worker could not start");break
func _upload_ready() -> void:
	var start=Time.get_ticks_usec();var uploaded=0
	for c in visible_cells:
		if cells.has(c):continue
		if not cache.has(c):continue
		cache_hits+=1;_touch(c);cells[c]=_upload(cache[c]);uploaded+=1
		if uploaded>=2 or Time.get_ticks_usec()-start>=2500:break
func ready_fraction() -> float:
	if visible_cells.is_empty():return 0.0
	var ready=0
	for c in visible_cells:
		if cells.has(c):ready+=1
	return float(ready)/visible_cells.size()
func warm_up(loading=null) -> bool:
	if is_instance_valid(viewer) and is_instance_valid(bound_zone):
		var here:Vector3=bound_zone.to_local(viewer.global_position)
		_plan(Vector2(here.x,here.z));_collect();_upload_ready();_schedule()
	var start=Time.get_ticks_msec()
	while is_inside_tree() and is_instance_valid(bound_zone):
		if worker_error:return false
		if ready_fraction()>=1.0:
			return await distance_cover.warm_up(loading) if is_instance_valid(distance_cover) else true
		if loading!=null:loading.set_progress(.05+.9*ready_fraction())
		if Time.get_ticks_msec()-start>30000:return false
		await get_tree().process_frame
	return false
func _process(delta:float) -> void:
	if not is_instance_valid(bound_zone):return
	if not is_instance_valid(viewer):viewer=get_viewport().get_camera_3d()
	if not is_instance_valid(viewer):return
	clock+=delta;material.set_shader_parameter("wind_clock",clock);material.set_shader_parameter("vegetation_focus",viewer.global_position)
	var local:Vector3=bound_zone.to_local(viewer.global_position);var p=Vector2(local.x,local.z)
	if last_position.is_finite() and delta>.0001:
		var step=p-last_position
		if step.length()<32:velocity=velocity.lerp(step/delta,.2)
		else:velocity=Vector2.ZERO;plan_elapsed=1.0
	last_position=p;plan_elapsed+=delta
	if plan_elapsed>=.15:plan_elapsed=0;_plan(p)
	_collect();_upload_ready();_schedule()
	life_clock+=delta
	if life_clock>.6:life_clock=0;_update_life(p)
func _update_life(p:Vector2) -> void:
	var candidates=[]
	for c in cells:
		var mid=Vector2((c.x+.5)*CELL,(c.y+.5)*CELL)
		if mid.distance_to(p)>22:continue
		var has_flowers=false
		for batch in cells[c].get_children():
			if batch is MultiMeshInstance3D and (String(batch.name).begins_with("margaritas") or String(batch.name).begins_with("flores_")):has_flowers=true;break
		if has_flowers:candidates.append(c)
	candidates.sort_custom(func(a,b):return Vector2((a.x+.5)*CELL,(a.y+.5)*CELL).distance_squared_to(p)<Vector2((b.x+.5)*CELL,(b.y+.5)*CELL).distance_squared_to(p))
	if candidates.size()>3:candidates.resize(3)
	for c in cells:
		var patch=cells[c]
		if candidates.has(c) and not is_instance_valid(patch.life):
			patch.life=load("res://enhanced/flower_insects.gd").new();patch.add_child(patch.life);patch.life.setup(patch,absi(c.x*3209+c.y*131+207))
		elif not candidates.has(c) and is_instance_valid(patch.life):patch.life.queue_free();patch.life=null
func restore() -> void:
	if is_instance_valid(distance_cover):distance_cover.restore()
	for work in workers:
		if work.thread.is_started():work.thread.wait_to_finish()
	workers.clear();job={}
	for patch in cells.values():
		if is_instance_valid(patch):patch.queue_free()
	cells.clear();cache.clear();lru.clear();visible_cells.clear();prefetch_cells.clear();bound_zone=null;generator=null;last_position=Vector2(INF,INF);velocity=Vector2.ZERO
func _exit_tree() -> void:restore()
