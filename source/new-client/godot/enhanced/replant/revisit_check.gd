extends SceneTree
## Render the production replacement shader through ready/unload/rebuild/return and A/B.
var args := {}
func _initialize() -> void:
	Engine.max_fps = 60
	for arg in OS.get_cmdline_user_args():
		var pair := arg.trim_prefix("--").split("=", true, 1)
		if pair.size() == 2: args[pair[0]] = pair[1]
	run.call_deferred()

func run() -> void:
	DirAccess.make_dir_recursive_absolute(String(args.out))
	root.size = Vector2i(640, 240)
	var world := Node3D.new()
	root.add_child(world)
	var zone = load("res://game/zone_loader.gd").new()
	world.add_child(zone)
	zone.load_zone("res://content/zones/zone207", "blend", "x4plus")
	var viewer := Node3D.new()
	zone.add_child(viewer)
	viewer.position = Vector3(1190, zone.height_at(1190, 1180) + 2, 1180)
	var clutter = load("res://enhanced/replant/replant_clutter.gd").new()
	clutter.override_bundle = args.bundle
	zone.add_child(clutter)
	if not clutter.setup(zone, viewer) or clutter.plan.is_empty():
		quit(3)
		return
	clutter.set_process(false)
	zone.visible = false
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.size = 6
	cam.position = Vector3(0, 0, 6)
	world.add_child(cam)
	cam.make_current()
	var material: ShaderMaterial = clutter._material.duplicate()
	var shader := Shader.new()
	# Only lighting is removed in this fixture. Production alpha, atlas, wind and metadata stay intact.
	shader.code = material.shader.code.replace("render_mode cull_disabled;", "render_mode cull_disabled, unshaded;")
	material.shader = shader
	var white := Image.create(2, 2, false, Image.FORMAT_RGBA8)
	white.fill(Color.WHITE)
	material.set_shader_parameter("atlas", ImageTexture.create_from_image(white))
	material.set_shader_parameter("replant_ready", clutter._ready_texture)
	material.set_shader_parameter("sway", 0.0)
	var mesh_node := MeshInstance3D.new()
	mesh_node.material_override = material
	world.add_child(mesh_node)
	var cell := Vector2i(185, 184)
	var chunk := Vector2i(37, 36)
	var stages := ["original", "first_visit", "ready", "unloaded_far", "return_rebuilt", "original_again"]
	var expected := [[true,true,true], [false,true,true], [false,false,true], [false,false,true], [false,false,true], [true,true,true]]
	var report := {"checks": [], "columns": ["unwanted_shrub", "replaced_low_grass", "retained_tall_plant"]}
	for stage in stages.size():
		if stage == 2:
			clutter.chunk_cells[chunk] = {cell: true}
			clutter._refresh_ready()
		if stage == 3:
			clutter.chunk_cells.erase(chunk)
			clutter._refresh_ready()
			assert(clutter._ready_image.get_pixel(cell.x, cell.y).r > 0.5, "Unloading resurrected old grass")
		cam.position.z = 40 if stage == 3 else 6
		material.set_shader_parameter("replant_on", 0.0 if stage in [0, 5] else 1.0)
		# Rebuild packed source cards, as happens when stock parcels stream back in.
		var surface := SurfaceTool.new()
		surface.begin(Mesh.PRIMITIVE_TRIANGLES)
		for column in 3:
			clutter._tag_cell = cell if column < 2 else Vector2i(-1, -1)
			clutter._tag_shrub = column == 0
			var x := float(column - 1) * 1.8
			clutter._quad(surface, Vector3(x-.5,-.5,0), Vector3(x+.5,-.5,0), Vector3(x+.5,.5,0), Vector3(x-.5,.5,0), 0, 1, 0, 1, Color.WHITE, true)
		mesh_node.mesh = surface.commit()
		for frame in 5: await process_frame
		await RenderingServer.frame_post_draw
		var frame_image := root.get_texture().get_image()
		var visible_cards := []
		for column in 3:
			var screen := cam.unproject_position(Vector3(float(column-1)*1.8, 0, 0))
			var color := frame_image.get_pixel(int(screen.x), int(screen.y))
			visible_cards.append(color.r > 0.5)
		assert(visible_cards == expected[stage], "Unexpected rendered vegetation: " + stages[stage] + str(visible_cards))
		assert(frame_image.save_png(String(args.out).path_join(stages[stage] + ".png")) == OK)
		report.checks.append({"stage": stages[stage], "visible": visible_cards, "passed": visible_cards == expected[stage]})
	clutter.set_enhanced(false)
	assert(clutter._ready_image.get_data().count(0) == 65536)
	report.disable_clears_coverage = true
	var file := FileAccess.open(String(args.out).path_join("revisit.json"), FileAccess.WRITE)
	assert(file != null)
	file.store_string(JSON.stringify(report, "  "))
	print("REVISIT_RENDER_CHECK_OK")
	quit()
