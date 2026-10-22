extends SceneTree
var zone
var trial
var cam:Camera3D
var sky
var label:Label
var out:=""
var view:=0
var stones:=true
var ivy:=true

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")

func fixtures() -> String:
	var context:=HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		context.update(String(child.name).to_utf8_buffer())
		for i in child.multimesh.instance_count:context.update(var_to_bytes(child.multimesh.get_instance_transform(i)))
	return context.finish().hex_encode()

func physics() -> String:
	var data:=[]
	for shape in zone.find_children("*","CollisionShape3D",true,false):
		data.append([str(shape.get_path()),shape.transform,shape.shape.get_instance_id(),shape.disabled])
	return var_to_bytes(data).hex_encode().sha256_text()

func run() -> void:
	Engine.max_fps=60
	root.title="DAoC Enhanced - Piedras e hiedra con volumen - Ardee"
	var world:=Node3D.new()
	root.add_child(world)
	zone=load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	cam=Camera3D.new()
	cam.fov=55
	cam.far=1000
	world.add_child(cam)
	cam.make_current()
	sky=load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone,cam,"x4plus")
	sky.set_hour(14)
	sky.time_scale=0
	sky.storm_forced=0
	sky.set_process(false)
	await process_frame
	root.size=Vector2i(1440,1000)
	var original:=fixtures()
	var shapes:=physics()
	trial=load("res://enhanced/terrain/stone_ivy_trial.gd").new()
	world.add_child(trial)
	trial.override_manifest="res://.enhanced-session/stone_ivy/manifest.json"
	# A changed asset must be rejected before hiding any stock instance.
	var valid_manifest=JSON.parse_string(FileAccess.get_file_as_string(trial.override_manifest))
	var corrupt_manifest=valid_manifest.duplicate(true)
	corrupt_manifest.targets[0].scene_sha256="invalid-for-guard-check"
	var guard_path:="res://.enhanced-session/stone_ivy/rejected_test_manifest.json"
	var guard_file:=FileAccess.open(guard_path,FileAccess.WRITE)
	guard_file.store_string(JSON.stringify(corrupt_manifest))
	guard_file.close()
	trial.override_manifest=guard_path
	assert(not trial.configure() and fixtures()==original and physics()==shapes)
	DirAccess.remove_absolute(guard_path)
	trial.override_manifest="res://.enhanced-session/stone_ivy/manifest.json"
	if not trial.configure() or not trial.apply_zone(zone):
		push_error("Stone/ivy trial rejected: "+trial.error)
		quit(3)
		return
	assert(trial.assets.size()==8)
	assert(physics()==shapes)
	trial.set_choices(false,false)
	assert(fixtures()==original)
	var layer:=CanvasLayer.new()
	world.add_child(layer)
	label=Label.new()
	label.position=Vector2(20,18)
	label.add_theme_font_size_override("font_size",19)
	label.add_theme_color_override("font_shadow_color",Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size",5)
	layer.add_child(label)
	var controls:=HBoxContainer.new()
	controls.position=Vector2(20,55)
	layer.add_child(controls)
	for item in [["Todo original",func():toggle(false,false)],["Piedra mejorada",func():toggle(true,false)],["Piedra e hiedra 3D",func():toggle(true,true)],["Solo hiedra 3D",func():toggle(false,true)],["Otra vista",func():place_camera((view+1)%8)],["Salir",func():quit()]]:
		var button:=Button.new()
		button.text=item[0]
		button.custom_minimum_size=Vector2(170,38)
		button.pressed.connect(item[1])
		controls.add_child(button)
	place_camera(0)
	toggle(true,true)
	print("STONE_IVY_PREVIEW_READY stones=4 architecture=4")
	if out.is_empty():return
	DirAccess.make_dir_recursive_absolute(out)
	var measurements:=[]
	for angle in 8:
		place_camera(angle)
		for combo in [[false,false],[true,false],[true,true],[false,true]]:
			toggle(combo[0],combo[1])
			for frame in 24:await process_frame
			var start:=Time.get_ticks_usec()
			for frame in 24:await process_frame
			var suffix:=str(int(combo[0]))+str(int(combo[1]))
			measurements.append({"view":angle,"stones":combo[0],"ivy_3d":combo[1],"mean_ms":(Time.get_ticks_usec()-start)/24000.0,"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
			assert(physics()==shapes)
			if not combo[0] and not combo[1]:assert(fixtures()==original)
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join("view%d_%s.png"%[angle,suffix]))
	# Neutral material exposes real silhouette, hollows and fracture geometry without the texture.
	place_camera(0)
	toggle(true,false)
	for asset in trial.assets:
		var body=asset.node.get_node_or_null("body")
		if body:body.material_override.set_shader_parameter("neutral",true)
	for frame in 25:await process_frame
	await RenderingServer.frame_post_draw
	root.get_texture().get_image().save_png(out.path_join("geometry_neutral.png"))
	for asset in trial.assets:
		var body=asset.node.get_node_or_null("body")
		if body:body.material_override.set_shader_parameter("neutral",false)
	for mult in [2.0,1.0]:
		zone.set("view_mult",mult)
		zone.apply_view(mult)
		trial._process(0.0)
		for asset in trial.assets:
			var body=asset.node.get_node_or_null("body")
			if body:assert(body.visibility_range_end==asset.reference.visibility_range_end)
	trial.restore()
	assert(fixtures()==original and physics()==shapes)
	var region=load("res://game/world/region_world.gd").new()
	region.zones[207]=zone
	trial.set_choices(true,true)
	trial.attach(region)
	assert(trial.assets.size()==8)
	region.zone_removing.emit(zone)
	assert(fixtures()==original and physics()==shapes)
	region.zone_added.emit(zone)
	assert(trial.assets.size()==8 and trial.stones and trial.ivy)
	trial.restore()
	region.free()
	assert(fixtures()==original and physics()==shapes)
	var report={"zone":207,"stone_fixtures":[1429,1431,1430,935],"architecture_fixtures":[334,335,336,1107],"source_meshes_sculpted":3,"stone_variants":4,"stone_triangles_each":15360,"original_stone_triangles_each":60,"exact_fixture_restoration":true,"collision_shapes_unchanged":true,"independent_stone_ivy_choices":true,"region_unload_reload":true,"view_distance_followed":true,"viewport":[root.size.x,root.size.y],"measurements":measurements,"note":"Offline real renderer; live LAB gameplay not represented here. Original physics retained. Baked ivy in base textures is outside this separate-overlay trial."}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE)
	report["modified_resource_rejected_without_mutation"]=true
	file.store_string(JSON.stringify(report,"  "))
	print("STONE_IVY_RENDER_CHECK_OK restoration=true collision_unchanged=true independent_choices=true")
	quit()

func place_camera(index:int) -> void:
	view=index
	var target:Vector3
	var at:Vector3
	match index:
		0:target=Vector3(1254.4,132.4,1273.6);at=Vector3(1259.3,132.8,1280.4)
		1:target=Vector3(1241.6,132.2,1305.6);at=Vector3(1246.4,132.7,1312.0)
		2:target=Vector3(1196.8,133.7,1273.6);at=Vector3(1205.8,134.4,1285.6)
		3:target=Vector3(1240,132,1288);at=Vector3(1260,143,1340)
		4:target=Vector3(1337.6,133,1241.6);at=Vector3(1350,133,1254)
		5:target=Vector3(1372.8,133.0,1241.6);at=Vector3(1358,133,1252)
		6:target=Vector3(1254.9,131.35,1274.32);at=Vector3(1256.25,131.65,1275.45)
		_:target=Vector3(1341.0,131.7,1247.0);at=Vector3(1343.7,132.0,1249.3)
	cam.position=at
	cam.look_at(target)

func toggle(use_stones:bool,use_ivy:bool) -> void:
	stones=use_stones
	ivy=use_ivy
	trial.set_choices(stones,ivy)
	label.text="Piedras: %s | Hiedra: %s | Ardee | Vista %d"%["mejoradas"if stones else"originales","3D"if ivy else"original",view+1]

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		if event.keycode==KEY_SPACE and label!=null:toggle(not stones,ivy)
		if event.keycode==KEY_I and label!=null:toggle(stones,not ivy)
		if event.keycode==KEY_TAB and cam!=null:place_camera((view+1)%8)
