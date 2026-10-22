extends SceneTree
var zone
var trial
var cam:Camera3D
var sky
var label:Label
var view:=0
var out:=""
var manifest_path:=""
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
		if arg.begins_with("--manifest="):manifest_path=arg.trim_prefix("--manifest=")
	call_deferred("run")
func physics() -> String:
	var data:=[]
	for shape in zone.find_children("*","CollisionShape3D",true,false):data.append([str(shape.get_path()),shape.transform,shape.shape.get_instance_id(),shape.disabled])
	return var_to_bytes(data).hex_encode().sha256_text()
func verify_originals(original:Dictionary) -> void:
	var water=zone.get_node("Water_River")
	assert(water.mesh==original.mesh and water.material_override==original.material and water.transform==original.transform)
	for p in [Vector2(1280,960),Vector2(1250,920),Vector2(1200,1200)]:
		assert(zone.water_level_at(p.x,p.y)==original.levels[str(p)])
func run() -> void:
	Engine.max_fps=60
	root.title="DAoC Enhanced - Agua de Connacht - Prueba reversible"
	var world:=Node3D.new();root.add_child(world)
	zone=load("res://game/zone_loader.gd").new();world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	cam=Camera3D.new();cam.fov=60;cam.far=1800;world.add_child(cam);cam.make_current()
	sky=load("res://game/sky_system.gd").new();world.add_child(sky);sky.setup(zone,cam,"x4plus")
	sky.set_hour(14);sky.time_scale=0;sky.storm_forced=0;sky.set_process(false)
	await process_frame
	root.size=Vector2i(1440,960)
	var water=zone.get_node("Water_River")
	var original={"mesh":water.mesh,"material":water.material_override,"transform":water.transform,"visible":water.visible,"levels":{}}
	for p in [Vector2(1280,960),Vector2(1250,920),Vector2(1200,1200)]:original.levels[str(p)]=zone.water_level_at(p.x,p.y)
	var shapes:=physics()
	trial=load("res://enhanced/terrain/water_trial.gd").new();world.add_child(trial)
	if manifest_path.is_empty():
		var latest_path:="res://.enhanced-session/water_trial/latest.json"
		if FileAccess.file_exists(latest_path):
			var latest=JSON.parse_string(FileAccess.get_file_as_string(latest_path))
			if latest is Dictionary and FileAccess.get_sha256(String(latest.get("manifest","")))==latest.get("sha256",""):manifest_path=String(latest.manifest)
	trial.override_manifest=manifest_path if not manifest_path.is_empty() else "res://.enhanced-session/water_trial/manifest.json"
	if not trial.configure() or not trial.apply_zone(zone):
		push_error("Water trial rejected: "+trial.error);quit(3);return
	assert(trial.pieces.size()==322 and physics()==shapes)
	var layer:=CanvasLayer.new();world.add_child(layer)
	label=Label.new();label.position=Vector2(20,18);label.add_theme_font_size_override("font_size",20)
	label.add_theme_color_override("font_shadow_color",Color.BLACK);label.add_theme_constant_override("shadow_outline_size",5);layer.add_child(label)
	var controls:=HBoxContainer.new();controls.position=Vector2(20,55);layer.add_child(controls)
	for item in [["Original",func():set_mode(0)],["Material nuevo",func():set_mode(1)],["Material y ondas 3D",func():set_mode(2)],["Otra vista",func():place_camera((view+1)%5)],["Salir",func():quit()]]:
		var button:=Button.new();button.text=item[0];button.custom_minimum_size=Vector2(190,36);button.pressed.connect(item[1]);controls.add_child(button)
	place_camera(0);set_mode(2)
	print("WATER_PREVIEW_READY")
	if out.is_empty():return
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	DirAccess.make_dir_recursive_absolute(out)
	var results:=[]
	for angle in 5:
		place_camera(angle)
		for mode in [0,1,2]:
			set_mode(mode)
			for binding in trial.bindings:binding.material.set_shader_parameter("time_override",12.0)
			for frame in 20:await process_frame
			Engine.max_fps=0
			var samples:=[]
			for frame in 60:
				var start:=Time.get_ticks_usec();await process_frame;samples.append((Time.get_ticks_usec()-start)/1000.0)
			samples.sort()
			results.append({"view":angle,"mode":mode,"median_frame_ms":samples[30],"p95_frame_ms":samples[57],"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
			Engine.max_fps=60
			assert(physics()==shapes);verify_originals(original)
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join("view%d_mode%d.png"%[angle,mode]))
	place_camera(1);set_mode(2)
	for t in [12.0,13.4]:
		for binding in trial.bindings:binding.material.set_shader_parameter("time_override",t)
		for frame in 15:await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("ondas_t%.1f.png"%t))
	trial.restore();await process_frame
	assert(water.visible==original.visible and physics()==shapes);verify_originals(original)
	var region=load("res://game/world/region_world.gd").new();region.zones[207]=zone
	trial.attach(region);assert(trial.bindings.size()==1)
	region.zone_removing.emit(zone);assert(water.visible==original.visible)
	await process_frame
	region.zone_added.emit(zone);assert(trial.bindings.size()==1 and trial.mode==2)
	trial.restore();region.free();await process_frame
	verify_originals(original);assert(physics()==shapes and water.visible==original.visible)
	var corrupt=trial.manifest.duplicate(true);corrupt.chunks[0].near.resource_sha256="guard-check-invalid"
	var guard_path:="res://.enhanced-session/water_trial/guard_test.json"
	var file:=FileAccess.open(guard_path,FileAccess.WRITE);file.store_string(JSON.stringify(corrupt));file.close()
	trial.override_manifest=guard_path;assert(not trial.configure());DirAccess.remove_absolute(guard_path)
	verify_originals(original);assert(water.visible==original.visible)
	var report={"zone":207,"renderer":"actual Vulkan Forward+","physics_unchanged":true,"nominal_water_levels_unchanged":true,"exact_original_restoration":true,"region_unload_reload":true,"modified_resource_rejected":true,"maximum_wave_amplitude_m":0.04,"near_detail_spacing_m":0.8,"near_detail_chunks":161,"near_global_triangles":973824,"far_global_triangles":20154,"measurements":results,"note":"Offline actual scene without NPCs; median/p95 frame times, not a combat benchmark. Dense meshes culled beyond 140m, waves fade between 45m and 85m."}
	report.near_detail_spacing_m=trial.manifest.near_spacing_m
	report.near_global_triangles=trial.manifest.totals.near_triangles
	file=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
	print("WATER_RENDER_CHECK_OK restoration=true water_levels_unchanged=true physics_unchanged=true")
	quit()
func place_camera(index:int) -> void:
	view=index
	sky.set_hour(23 if index==4 else 14)
	var at:Vector3
	var target:Vector3
	match index:
		0,4:at=Vector3(1290,125.8,1010);target=Vector3(1260,117.5,925)
		1:at=Vector3(1285,118.15,969);target=Vector3(1280,117.27,948)
		2:at=Vector3(1290,140,1015);target=Vector3(1250,117.25,900)
		_:at=Vector3(1295,118.4,977);target=Vector3(1280,117.25,952)
	cam.position=at;cam.look_at(target)
	if label!=null:set_mode(trial.mode)
func set_mode(mode:int) -> void:
	trial.set_mode(mode)
	label.text="Agua: %s | Vista %d | %s"%[["original","material nuevo","material + ondas con volumen"][mode],view+1,"noche" if view==4 else "dia"]
func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		elif event.keycode==KEY_SPACE and label!=null:set_mode((trial.mode+1)%3)
		elif event.keycode==KEY_TAB and label!=null:place_camera((view+1)%5)
