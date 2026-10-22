extends SceneTree
## Render and inspect one real Ardee fixture, with identical camera/light for A/B.
var args:Dictionary={}
var cam:Camera3D
var zone
var trial
var label:Label
var pivot:=Vector3(1395.2,130.0875,1302.4)
var angle:=0
var report:Dictionary={}
var views:=3

func _initialize() -> void:
	Engine.max_fps=60
	for arg in OS.get_cmdline_user_args():
		var pair:=arg.trim_prefix("--").split("=",true,1)
		if pair.size()==2:args[pair[0]]=pair[1]
		elif pair.size()==1:args[pair[0]]=true
	run.call_deferred()

func run() -> void:
	views=5 if args.has("repair-review") else 3
	root.size=Vector2i(1440,900)
	root.title="DAoC Enhanced - Un olmo en Ardee - Comparacion A/B"
	var world:=Node3D.new()
	root.add_child(world)
	zone=load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207","blend","x4plus")
	cam=Camera3D.new()
	cam.fov=60
	cam.far=1200
	world.add_child(cam)
	cam.make_current()
	place_camera(0)
	var sky=load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone,cam,"x4plus")
	sky.set_hour(14)
	sky.time_scale=0
	sky.storm_forced=0
	sky.set_process(false)
	await physics_frame
	await physics_frame
	var physics_before:=physics_signature()
	var originals_before:=fixture_signature()
	trial=load("res://enhanced/trees/elm_trial.gd").new()
	trial.override_manifest=String(args.get("manifest","res://.enhanced-session/elm_trial/bundles/user_20261021/manifest.json"))
	world.add_child(trial)
	if not trial.configure() or not trial.apply_zone(zone):
		push_error("The single elm replacement could not be verified")
		quit(3)
		return
	assert(trial.originals.size()==1)
	assert(physics_signature()==physics_before)
	assert(trial.replacement.transform.origin.distance_to(pivot)<0.001)
	trial.set_enabled(false)
	assert(fixture_signature()==originals_before)
	trial.set_enabled(true)
	if args.has("check"):
		var region=load("res://game/world/region_world.gd").new()
		region.zones[207]=zone
		trial.restore()
		trial.set_enabled(true)
		trial.attach(region)
		assert(is_instance_valid(trial.replacement))
		region.zone_removing.emit(zone)
		assert(fixture_signature()==originals_before)
		region.zone_added.emit(zone)
		assert(is_instance_valid(trial.replacement))
		assert(trial.enabled and trial.replacement.visible)
		assert(physics_signature()==physics_before)
		trial.restore()
		region.free()
		var out:=String(args.out)
		DirAccess.make_dir_recursive_absolute(out)
		var bad:Dictionary=trial.manifest.duplicate(true)
		bad.scene_sha256="0".repeat(64)
		var file:=FileAccess.open(out.path_join("invalid_manifest.json"),FileAccess.WRITE)
		file.store_string(JSON.stringify(bad))
		file.close()
		var invalid=load("res://enhanced/trees/elm_trial.gd").new()
		invalid.override_manifest=out.path_join("invalid_manifest.json")
		assert(not invalid.configure())
		invalid.free()
		file=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE)
		file.store_string(JSON.stringify({"single_original_slot":true,"fixture_placement_preserved":true,"collision_shapes_unchanged":true,"full_batch_restoration":true,"lab_region_attach":true,"zone_reload":true,"invalid_scene_hash_rejected":true},"  "))
		file.close()
		print("ELM_LAB_ATTACH_CHECK_OK")
		quit()
		return
	var clutter=load("res://enhanced/replant/replant_clutter.gd").new()
	var pointer:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/replant/latest.json"))
	clutter.override_bundle=String(pointer.bundle)
	zone.add_child(clutter)
	clutter.setup(zone,cam)
	var layer:=CanvasLayer.new()
	world.add_child(layer)
	label=Label.new()
	label.position=Vector2(20,18)
	label.add_theme_font_size_override("font_size",22)
	label.add_theme_color_override("font_shadow_color",Color.BLACK)
	label.add_theme_constant_override("shadow_outline_size",5)
	layer.add_child(label)
	var controls:=HBoxContainer.new()
	controls.position=Vector2(20,55)
	layer.add_child(controls)
	for entry in [["A - Original",func():toggle(false)],["B - Olmo nuevo",func():toggle(true)],["Otra vista",func():place_camera((angle+1)%views)],["Salir",func():quit()]]:
		var button:=Button.new()
		button.text=entry[0]
		button.custom_minimum_size=Vector2(160,38)
		button.pressed.connect(entry[1])
		controls.add_child(button)
	toggle(true)
	print("ELM_PREVIEW_READY fixture=207:1109 physics_unchanged=true original_restoration=true")
	if not args.has("capture"):return
	var out:=String(args.out)
	DirAccess.make_dir_recursive_absolute(out)
	report={"fixture":"207:1109","replacement_count":1,"original_triangles":266,"new_triangles":30162,"physics_unchanged":true,"original_restoration":true,"viewport":[root.size.x,root.size.y],"measurements":[],"note":"Standalone rendered zone, no server/NPCs. Timings may include another running game; not a forest performance benchmark."}
	for view in views:
		place_camera(view)
		for frame in 40:await process_frame
		var deadline:=Time.get_ticks_msec()+20000
		while not clutter.is_settled() and Time.get_ticks_msec()<deadline:await process_frame
		assert(clutter.is_settled())
		# Same plants and frozen sky for both images, even if the camera crossed a parcel boundary.
		clutter.set_process(false)
		for enabled in [false,true]:
			toggle(enabled)
			for frame in 20:await process_frame
			var start:=Time.get_ticks_usec()
			for frame in 40:await process_frame
			var seconds:float=(Time.get_ticks_usec()-start)/1000000.0
			await RenderingServer.frame_post_draw
			var path:=out.path_join("view%d_%s.png"%[view,"B"if enabled else"A"])
			assert(root.get_texture().get_image().save_png(path)==OK)
			report.measurements.append({"view":view,"new_tree":enabled,"camera":[cam.position.x,cam.position.y,cam.position.z],"fps":40/seconds,"render_primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),"render_draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"capture":path})
		clutter.set_process(true)
	trial.restore()
	assert(fixture_signature()==originals_before)
	assert(physics_signature()==physics_before)
	var file:=FileAccess.open(out.path_join("report.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	file.close()
	print("ELM_RENDER_CHECK_OK")
	quit()

func place_camera(view:int) -> void:
	angle=view
	var offset:Vector3=[Vector3(48,9,62),Vector3(-58,7,40),Vector3(17,2,22),Vector3(5,2.5,7),Vector3(3.5,3.5,4.8)][view]
	cam.position=pivot+offset
	cam.position.y=maxf(cam.position.y,zone.height_at(cam.position.x,cam.position.z)+2.5)
	cam.look_at(pivot+Vector3.UP*([16.0,16.0,22.0,0.8,3.5][view]))

func toggle(enabled:bool) -> void:
	trial.set_enabled(enabled)
	label.text=("B - OLMO NUEVO" if enabled else "A - OLMO ORIGINAL")+" | Ardee | Un arbol, misma posicion, misma luz"

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		if event.keycode==KEY_SPACE and trial!=null:toggle(not trial.enabled)
		if event.keycode==KEY_TAB and cam!=null:place_camera((angle+1)%views)

func fixture_signature() -> String:
	var context:=HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	for child in zone.get_children():
		if not child is MultiMeshInstance3D:continue
		context.update(String(child.name).to_utf8_buffer())
		for i in child.multimesh.instance_count:context.update(var_to_bytes(child.multimesh.get_instance_transform(i)))
	return context.finish().hex_encode()

func physics_signature() -> String:
	var values:=[]
	for shape in zone.find_children("*","CollisionShape3D",true,false):
		values.append([str(shape.get_path()),shape.transform,shape.shape.get_instance_id(),shape.disabled])
	return var_to_bytes(values).hex_encode().sha256_text()
