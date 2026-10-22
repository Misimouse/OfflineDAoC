extends SceneTree
## Offline Ardee soil material A/B. Original masks, geometry, scale and gravel are retained.
var zone
var cam:Camera3D
var label:Label
var bindings:Array=[]
var enabled:=false
var view:=0
var out:=""
var manifest:Dictionary={}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):out=arg.trim_prefix("--out=")
	call_deferred("run")

func run() -> void:
	manifest=JSON.parse_string(FileAccess.get_file_as_string("res://.enhanced-session/paths_trial/manifest.json"))
	var base:="res://content/zones/zone207/"
	assert(FileAccess.get_sha256(base+"zone.json")==manifest.zone_sha256)
	assert(FileAccess.get_sha256(String(manifest.remaster_png))==manifest.remaster_sha256)
	assert(FileAccess.get_sha256(base+"textures/x4plus/h_soil.png")==manifest.installed_png_sha256)
	for path in manifest.weight_hashes:assert(FileAccess.get_sha256(base+path)==manifest.weight_hashes[path])
	Engine.max_fps=60
	root.title="DAoC Enhanced - Tierra de Ardee - Comparacion A/B"
	var world:=Node3D.new()
	root.add_child(world)
	zone=load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone(base,"blend","x4plus")
	cam=Camera3D.new()
	cam.fov=65
	cam.far=1200
	world.add_child(cam)
	cam.make_current()
	var sky=load("res://game/sky_system.gd").new()
	world.add_child(sky)
	sky.setup(zone,cam,"x4plus")
	sky.set_hour(14)
	sky.time_scale=0
	sky.storm_forced=0
	sky.set_process(false)
	await process_frame
	root.size=Vector2i(1440,900)
	var image:=Image.load_from_file(String(manifest.remaster_png))
	image.generate_mipmaps()
	var replacement:=ImageTexture.create_from_image(image)
	for mat in zone.get("_terrain_mats"):
		var key:String=mat.get_meta("patch", "")
		if not manifest.patches.has(key):continue
		var layers:Array=zone.info.ground_splat.patches[key].layers
		assert(layers[0].tex!="h_soil")
		var index:=-1
		for i in range(1,layers.size()):
			if layers[i].tex=="h_soil":index=i-1;break
		assert(index>=0)
		var before:Array=mat.get_shader_parameter("layer_tex")
		var after:=before.duplicate()
		after[index]=replacement
		bindings.append({"mat":mat,"before":before,"after":after,"index":index,"patch":key,"weights0":mat.get_shader_parameter("weights0"),"weights1":mat.get_shader_parameter("weights1"),"tiles":mat.get_shader_parameter("layer_tiles")})
	assert(bindings.size()==4)
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
	for item in [["A - Tierra actual",func():toggle(false)],["B - Tierra Enhanced",func():toggle(true)],["Otra vista",func():place_camera((view+1)%2)],["Salir",func():quit()]]:
		var button:=Button.new()
		button.text=item[0]
		button.custom_minimum_size=Vector2(175,38)
		button.pressed.connect(item[1])
		controls.add_child(button)
	place_camera(0)
	toggle(false)
	print("PATHS_PREVIEW_READY four_patches=4 material=h_soil original_masks_and_scale=true")
	if out.is_empty():return
	DirAccess.make_dir_recursive_absolute(out)
	var timings:=[]
	for angle in 2:
		place_camera(angle)
		for use_new in [false,true]:
			toggle(use_new)
			for frame in 30:await process_frame
			var start:=Time.get_ticks_usec()
			for frame in 45:await process_frame
			timings.append({"view":angle,"enhanced":use_new,"mean_ms":(Time.get_ticks_usec()-start)/45000.0})
			await RenderingServer.frame_post_draw
			root.get_texture().get_image().save_png(out.path_join("view%d_%s.png"%[angle,"B"if use_new else"A"]))
	toggle(false)
	var report={"zone":207,"patches":manifest.patches,"changed_material":"h_soil","masks_unchanged":true,"tile_scale_unchanged":true,"gravel_unchanged":true,"exact_sampler_restoration":true,"viewport":[root.size.x,root.size.y],"timings":timings,"note":"Standalone comparison, not installed in LAB. Images use the same camera and frozen daylight. Soil also exists outside paths; original painting determines its extent."}
	var file:=FileAccess.open(out.path_join("checks.json"),FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "))
	print("PATHS_RENDER_CHECK_OK exact_restoration=true masks_and_scale_unchanged=true")
	quit()

func toggle(value:bool) -> void:
	enabled=value
	for binding in bindings:
		binding.mat.set_shader_parameter("layer_tex",binding.after if value else binding.before)
		var actual:Array=binding.mat.get_shader_parameter("layer_tex")
		for i in actual.size():
			assert(actual[i]==(binding.after[i]if value else binding.before[i]))
		assert(binding.mat.get_shader_parameter("weights0")==binding.weights0)
		assert(binding.mat.get_shader_parameter("weights1")==binding.weights1)
		assert(binding.mat.get_shader_parameter("layer_tiles")==binding.tiles)
	label.text=("B - Tierra Enhanced"if value else"A - Tierra actual")+" | Mismo trazado y escala | Grava sin cambios"

func place_camera(index:int) -> void:
	view=index
	var target:Vector3=[Vector3(1413.6,0,1250.4),Vector3(1312.8,0,1351.2)][index]
	target.y=zone.height_at(target.x,target.z)
	cam.position=target+Vector3(3,3.5,5)
	cam.look_at(target)

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		if event.keycode==KEY_SPACE and label!=null:toggle(not enabled)
		if event.keycode==KEY_TAB and cam!=null:place_camera((view+1)%2)
