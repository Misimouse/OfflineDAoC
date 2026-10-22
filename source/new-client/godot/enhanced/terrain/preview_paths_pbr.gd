extends SceneTree
## Three-way material comparison on the real unchanged Ardee ground, no server/DB.
var zone
var trial
var cam:Camera3D
var sky
var label:Label
var out:=""
var view:=0
var mode:=2
var hour:=14

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")

func signature() -> String:
	var data:=[]
	for node in zone.get_children():
		if node is MeshInstance3D and String(node.name).begins_with("Terrain_"):
			data.append([String(node.name),node.mesh.get_instance_id(),node.transform,node.mesh.surface_get_material(0).get_instance_id()])
	for shape in zone.find_children("*","CollisionShape3D",true,false):
		data.append([str(shape.get_path()),shape.transform,shape.shape.get_instance_id(),shape.disabled])
	return var_to_bytes(data).hex_encode().sha256_text()

func run() -> void:
	Engine.max_fps=60
	root.title="DAoC Enhanced - Caminos con relieve - Ardee"
	var world:=Node3D.new()
	root.add_child(world)
	zone=load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	cam=Camera3D.new()
	cam.fov=65
	cam.far=1200
	world.add_child(cam)
	cam.make_current()
	sky=load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone,cam,"x4plus")
	sky.set_hour(hour)
	sky.time_scale=0
	sky.storm_forced=0
	sky.set_process(false)
	await process_frame
	root.size=Vector2i(1440,900)
	var original:=signature()
	trial=load("res://enhanced/terrain/paths_pbr.gd").new()
	world.add_child(trial)
	trial.override_manifest="res://.enhanced-session/paths_pbr/manifest.json"
	assert(trial.configure())
	assert(trial.apply_zone(zone))
	assert(trial.bindings.size()==4)
	assert(signature()==original)
	var mask_checks:=0
	for binding in trial.bindings:
		for param in ["weights0","weights1","layer_tiles","layer_tileable","patch_index","layer_count","tile_tex"]:
			assert(binding.replacement.get_shader_parameter(param)==binding.original.get_shader_parameter(param))
			mask_checks+=1
	var trees=load("res://enhanced/trees/elm_trial.gd").new()
	world.add_child(trees)
	if trees.configure():trees.apply_zone(zone)
	place_camera(0)
	var clutter=load("res://enhanced/replant/replant_clutter.gd").new()
	var pointer=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/replant/latest.json"))
	clutter.override_bundle=String(pointer.bundle)
	zone.add_child(clutter)
	clutter.setup(zone,cam)
	var layer:=CanvasLayer.new()
	world.add_child(layer)
	label=Label.new()
	label.position=Vector2(20,18)
	label.add_theme_font_size_override("font_size",20)
	label.add_theme_color_override("font_shadow_color",Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size",5)
	layer.add_child(label)
	var controls:=HBoxContainer.new()
	controls.position=Vector2(20,53)
	layer.add_child(controls)
	for item in [["A - Actual",func():toggle(0)],["B - Solo color nuevo",func():toggle(1)],["C - Material completo",func():toggle(2)],["Otra vista",func():place_camera((view+1)%3)],["Cambiar luz",func():set_hour(17 if hour==14 else 14)],["Salir",func():quit()]]:
		var button:=Button.new()
		button.text=item[0]
		button.custom_minimum_size=Vector2(160,38)
		button.pressed.connect(item[1])
		controls.add_child(button)
	toggle(2)
	print("PATHS_PBR_PREVIEW_READY patches=4 modes=3 maps=6")
	if out.is_empty():return
	DirAccess.make_dir_recursive_absolute(out)
	var measurements:=[]
	for angle in 3:
		place_camera(angle)
		var deadline:=Time.get_ticks_msec()+12000
		while not clutter.is_settled() and Time.get_ticks_msec()<deadline:await process_frame
		assert(clutter.is_settled())
		clutter.set_process(false)
		for use_mode in 3:
			toggle(use_mode)
			for frame in 45:await process_frame
			var at:=Time.get_ticks_usec()
			for frame in 45:await process_frame
			measurements.append({"view":angle,"mode":use_mode,"mean_ms":(Time.get_ticks_usec()-at)/45000.0,"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join("view%d_%s.png"%[angle,["A","B","C"][use_mode]]))
		clutter.set_process(true)
	# Same camera at a second sun angle: the normal-only comparison should react to lighting.
	place_camera(1)
	set_hour(17)
	for use_mode in [1,2]:
		toggle(use_mode)
		for frame in 30:await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(out.path_join("late_%s.png"%[["A","B","C"][use_mode]]))
	toggle(0)
	for binding in trial.bindings:
		assert(binding.mesh.material_override==null)
		assert(binding.mesh.mesh.surface_get_material(0)==binding.original)
	assert(signature()==original)
	var region=load("res://game/world/region_world.gd").new()
	region.zones[207]=zone
	trial.restore()
	trial.set_mode(2)
	trial.attach(region)
	assert(trial.bindings.size()==4)
	region.zone_removing.emit(zone)
	assert(trial.bindings.is_empty() and signature()==original)
	region.zone_added.emit(zone)
	assert(trial.bindings.size()==4 and trial.mode==2)
	trial.restore()
	assert(signature()==original)
	region.free()
	var report={"zone":207,"patches":4,"modes":["original","new_colour_only","new_colour_normal_roughness"],"maps":6,"checks_preserved_parameters":mask_checks,"geometry_and_collision_unchanged":true,"exact_original_material_restoration":true,"region_unload_reload":true,"viewport":[root.size.x,root.size.y],"normal_fade_m":70,"measurements":measurements,"note":"Offline rendered Ardee with existing tree/plant trials. Same camera/light for A/B/C. Not a full live LAB performance result. No displacement or extra stone meshes."}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print("PATHS_PBR_RENDER_CHECK_OK restoration=true geometry_and_collision_unchanged=true")
	quit()

func place_camera(index:int) -> void:
	view=index
	var target:Vector3=[Vector3(1413.6,0,1250.4),Vector3(1312.8,0,1351.2),Vector3(1312.8,0,1351.2)][index]
	target.y=zone.height_at(target.x,target.z)
	cam.position=target+([Vector3(3,2.0,5),Vector3(3,1.7,5),Vector3(12,9,42)][index] as Vector3)
	cam.look_at(target)

func set_hour(value:int) -> void:
	hour=value
	sky.set_hour(hour)
	toggle(mode)

func toggle(value:int) -> void:
	mode=value
	trial.set_mode(mode)
	label.text=["A - Suelo actual","B - Solo color nuevo","C - Color, relieve y rugosidad"][mode]+" | Ardee | Luz %d h"%hour

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		if event.keycode==KEY_SPACE and label!=null:toggle((mode+1)%3)
		if event.keycode==KEY_TAB and cam!=null:place_camera((view+1)%3)
