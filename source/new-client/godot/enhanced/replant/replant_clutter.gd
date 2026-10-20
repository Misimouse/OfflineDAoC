extends "res://game/clutter.gd"
## Versioned, opt-in Hibernia overlays. No plan means the upstream clutter path.
var plan := {}
var options := {}
var density_map: Image
var habitat_map: Image
var meshes := {}
var palette: Node3D
var plant_material: ShaderMaterial
var enhanced_enabled := true
var clock := 0.0
var chunk_plants := {}
var chunk_cells := {}
var removed_counts := {}
var life
var life_chunk := Vector2i(99999, 99999)
var override_bundle := ""
var force_original := false
var _building := Vector2i.ZERO
var _job := {}
var _tags_by_chunk := {}
var _tag_cell := Vector2i(-1, -1)
var _tag_shrub := false
var _ready_image: Image
var _ready_texture: ImageTexture
const WORK_BUDGET_US := 6000
const STATE := "res://.enhanced-session/replant"
const LOW := ["grass clump 1", "grass clump 2", "small plant", "brown small plant", "brown grass clump 2", "grass clump new", "grass clump", "scrubby grass", "brown small leafy weed 1"]
const SHRUBS := ["thorny undergrowth", "leafy branch", "large green leaves (bush)", "vivid green leaf", "narrow green leaf", "leafy", "bush 1", "bush 2", "large bush"]

func read_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var data = JSON.parse_string(file.get_as_text())
	return data if data is Dictionary else {}

func setup(z: ZoneLoader, follow: Node3D) -> bool:
	if not super.setup(z, follow):
		return false
	if force_original:
		return true
	var pointer := read_json(STATE.path_join("active.json"))
	if not override_bundle.is_empty():
		pointer = {"bundle": override_bundle, "sha256": FileAccess.get_sha256(override_bundle.path_join("manifest.json"))}
	if pointer.get("disabled", false) or not pointer.has("bundle"):
		return true
	var bundle := String(pointer.bundle)
	if FileAccess.get_sha256(bundle.path_join("manifest.json")) != pointer.get("sha256", ""):
		push_warning("Enhanced: invalid manifest; preserving original vegetation")
		return true
	var manifest := read_json(bundle.path_join("manifest.json"))
	if manifest.get("realm") != "hib" or manifest.get("exclude_toa") != true:
		return true
	var index := read_json(z.dir.get_base_dir().path_join("zones_index.json"))
	var region := int(index.get(str(int(z.info.id)), {}).get("region", -1))
	if region not in [181, 200] or String(_info.get("atlas", "")) not in ["grass_hib", "grass_hibexp"]:
		return true
	for entry in manifest.get("zones", []):
		if int(entry.id) != int(z.info.id):
			continue
		var file := bundle.path_join(String(entry.path))
		if not file.simplify_path().begins_with(bundle.simplify_path() + "/") and not file.replace("\\", "/").begins_with(bundle.replace("\\", "/") + "/"):
			return true
		if FileAccess.get_sha256(file) != entry.sha256:
			return true
		var candidate := read_json(file)
		if int(candidate.get("region", -1)) != region or candidate.get("realm") != "hib":
			return true
		for input in candidate.get("inputs", {}):
			if FileAccess.get_sha256(z.dir.path_join(input)) != candidate.inputs[input]:
				push_warning("Enhanced: source changed; original vegetation kept: " + input)
				return true
		for output in candidate.get("outputs", {}):
			if FileAccess.get_sha256(file.get_base_dir().path_join(output)) != candidate.outputs[output]:
				return true
		plan = candidate
		density_map = Image.load_from_file(file.get_base_dir().path_join("density.png"))
		habitat_map = Image.load_from_file(file.get_base_dir().path_join("habitat.png"))
		if density_map == null or habitat_map == null:
			plan.clear()
			return true
		options = plan.get("options", {})
		palette = load("res://enhanced/landscape_patch.gd").new()
		meshes = palette.make_catalog()
		plant_material = palette.make_material(true)
		if not _setup_replacement_shader():
			plan.clear()
		return true
	return true

func sample_mask(p: Vector2) -> Color:
	if plan.is_empty() or p.x < 0 or p.y < 0 or p.x >= zone.info.size_m or p.y >= zone.info.size_m:
		return Color(0, 0, 0)
	var x := clampi(int(p.x / float(zone.info.size_m) * 256), 0, 255)
	var z := clampi(int(p.y / float(zone.info.size_m) * 256), 0, 255)
	return Color(density_map.get_pixel(x, z).r, habitat_map.get_pixel(x, z).r * 255.0, 0)

func surface_clear(p: Vector3) -> bool:
	if p.y < zone.water_level_at(p.x, p.z) + 0.05:
		return false
	var dx: float = (zone.height_at(p.x + 0.2, p.z) - zone.height_at(p.x - 0.2, p.z)) / 0.4
	var dz: float = (zone.height_at(p.x, p.z + 0.2) - zone.height_at(p.x, p.z - 0.2)) / 0.4
	if rad_to_deg(atan(Vector2(dx, dz).length())) > float(options.get("max_slope", 32)):
		return false
	# NPC click volumes use another layer and must not change a seeded landscape when actors move.
	var mask := ZoneLoader.LAYER_WALL | ZoneLoader.LAYER_FLOOR | ZoneLoader.LAYER_SCENERY
	var hit := get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(zone.to_global(p + Vector3.UP * 12), zone.to_global(p - Vector3.UP * 0.4), mask))
	return hit.is_empty() or zone.to_local(hit.position).y <= p.y + 0.12

func _process(delta: float) -> void:
	if plan.is_empty():
		super._process(delta)
		return
	if viewer == null or not is_visible_in_tree():
		return
	clock += delta if options.get("wind", true) else 0.0
	plant_material.set_shader_parameter("wind_clock", clock)
	var p := to_local(viewer.global_position)
	var centre := Vector2i(floori(p.x / CHUNK_M), floori(p.z / CHUNK_M))
	var reach := ceili(radius_m / CHUNK_M)
	var wanted: Array[Vector2i] = []
	for dz in range(-reach, reach + 1):
		for dx in range(-reach, reach + 1):
			var c := centre + Vector2i(dx, dz)
			if Vector2((c.x + 0.5) * CHUNK_M, (c.y + 0.5) * CHUNK_M).distance_to(Vector2(p.x, p.z)) < radius_m + CHUNK_M * 0.71:
				wanted.append(c)
	for c in _chunks.keys():
		if not wanted.has(c):
			_chunks[c].queue_free()
			_chunks.erase(c)
			_tags_by_chunk.erase(c)
	wanted.sort_custom(func(a, b):return Vector2(a - centre).length_squared() < Vector2(b - centre).length_squared())
	for c in wanted:
		if not _chunks.has(c):
			_chunks[c] = _build_chunk(c)
			break
	var changed := false
	for c in chunk_plants.keys():
		if not should_plant(c):
			chunk_plants[c].queue_free()
			chunk_plants.erase(c)
			chunk_cells.erase(c)
			changed = true
	if changed: _refresh_ready()
	if not _job.is_empty() and not should_plant(_job.c): _cancel_job()
	if _job.is_empty():
		for c in wanted:
			if should_plant(c) and not chunk_plants.has(c):
				_start_job(c)
				break
	_advance_job()
	_update_life(centre)

func should_plant(c: Vector2i) -> bool:
	if c.x < 0 or c.y < 0 or c.x * CHUNK_M >= float(zone.info.size_m) or c.y * CHUNK_M >= float(zone.info.size_m):
		return false
	var p := to_local(viewer.global_position)
	var centre := Vector2i(floori(p.x / CHUNK_M), floori(p.z / CHUNK_M))
	return enhanced_enabled and density_mult > 0 and radius_m > 0 and absi(c.x - centre.x) <= 1 and absi(c.y - centre.y) <= 1

func is_settled() -> bool:
	if plan.is_empty() or viewer == null: return true
	var p := to_local(viewer.global_position)
	var centre := Vector2i(floori(p.x / CHUNK_M), floori(p.z / CHUNK_M))
	var expected := 0
	for dz in range(-1, 2):
		for dx in range(-1, 2):
			var c := centre + Vector2i(dx, dz)
			var mid := Vector2((c.x + 0.5) * CHUNK_M, (c.y + 0.5) * CHUNK_M)
			if should_plant(c) and mid.distance_to(Vector2(p.x, p.z)) < radius_m + CHUNK_M * 0.71: expected += 1
	return _job.is_empty() and chunk_plants.size() == expected

func _build_chunk(c: Vector2i) -> MeshInstance3D:
	_building = c
	_tags_by_chunk[c] = {}
	var mi := super._build_chunk(c)
	if not plan.is_empty(): _recount_removed()
	return mi

func _start_job(c: Vector2i) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(int(zone.info.id), c.x, c.y))
	var patch := Node3D.new()
	patch.set_script(load("res://enhanced/replant/patch_proxy.gd"))
	patch.controller = self
	patch.visible = false
	add_child(patch)
	_job = {"c": c, "rng": rng, "patch": patch, "positions": {}, "cells": {}, "accepted": 0, "i": 0,
		"attempts": mini(40000, int(CHUNK_M * CHUNK_M * float(options.get("density", 24)) * density_mult)),
		"limit": clampi(int(options.get("chunk_budget", 20000)), 500, 30000), "stage": 0,
		"species": [], "group": 0, "upload": 0, "mm": null}

func _generate_candidate(job: Dictionary) -> void:
	var rng: RandomNumberGenerator = job.rng
	var c: Vector2i = job.c
	var positions: Dictionary = job.positions
	var cells: Dictionary = job.cells
	var p := Vector2(c.x, c.y) * CHUNK_M + Vector2(rng.randf(), rng.randf()) * CHUNK_M
	var m := sample_mask(p)
	if m.r <= 0 or rng.randf() > m.r:
		return
	var h: float = zone.height_at(p.x, p.y)
	if not surface_clear(Vector3(p.x, h, p.y)):
		return
	var kind := roundi(m.g)
	var pick := rng.randf()
	var species := "tapiz_bajo"
	if pick > 0.45:
		if kind == 2:
			species = "matas_secas" if pick < 0.82 else "hierba_fina"
		elif kind == 3:
			species = "helechos" if pick < 0.70 else ("treboles" if pick < 0.86 else "hojas_largas")
		else:
			species = "hierba_fina" if pick < 0.68 else ("hierba_ancha" if pick < 0.83 else ("treboles" if pick < 0.94 else ("margaritas" if pick < 0.97 else "flores_amarillas")))
	var variants := 2 if species in ["tapiz_bajo", "helechos", "hojas_largas"] else 3
	var key := species + "_%d" % rng.randi_range(0, variants - 1)
	if not positions.has(key):
		positions[key] = []
	var dx: float = (zone.height_at(p.x + 0.2, p.y) - zone.height_at(p.x - 0.2, p.y)) / 0.4
	var dz: float = (zone.height_at(p.x, p.y + 0.2) - zone.height_at(p.x, p.y - 0.2)) / 0.4
	var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * rng.randf_range(0.75, 1.2))
	if species == "tapiz_bajo":
		basis = Basis(Quaternion(Vector3.UP, Vector3(-dx, 1, -dz).normalized())) * basis
	positions[key].append(Transform3D(basis, Vector3(p.x, h - 0.005, p.y)))
	cells[Vector2i(floori(p.x / 6.4), floori(p.y / 6.4))] = true
	job.accepted += 1

func _advance_job() -> void:
	if _job.is_empty(): return
	var deadline := Time.get_ticks_usec() + WORK_BUDGET_US
	if int(_job.stage) == 0:
		while int(_job.i) < int(_job.attempts) and int(_job.accepted) < int(_job.limit):
			_generate_candidate(_job)
			_job.i += 1
			if Time.get_ticks_usec() >= deadline: return
		_job.stage = 1
		_job.species = _job.positions.keys()
	while int(_job.group) < _job.species.size():
		var key: String = _job.species[int(_job.group)]
		if _job.mm == null:
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.mesh = meshes[key]
			mm.instance_count = _job.positions[key].size()
			_job.mm = mm
		while int(_job.upload) < int(_job.mm.instance_count):
			_job.mm.set_instance_transform(int(_job.upload), _job.positions[key][int(_job.upload)])
			_job.mm.set_instance_custom_data(int(_job.upload), Color(0.7, 0, 0, 1))
			_job.upload += 1
			if Time.get_ticks_usec() >= deadline: return
		var batch := MultiMeshInstance3D.new()
		batch.name = key
		batch.multimesh = _job.mm
		batch.material_override = plant_material
		batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		batch.visibility_range_end = 50
		batch.extra_cull_margin = 0.2
		_job.patch.add_child(batch)
		_job.mm = null
		_job.upload = 0
		_job.group += 1
		if Time.get_ticks_usec() >= deadline: return
	var c: Vector2i = _job.c
	_job.patch.set_meta("instances", int(_job.accepted))
	chunk_plants[c] = _job.patch
	chunk_cells[c] = _job.cells
	_job.patch.visible = true
	_job.clear()
	_refresh_ready()

func _cancel_job() -> void:
	if not _job.is_empty() and is_instance_valid(_job.patch): _job.patch.queue_free()
	_job.clear()

func _setup_replacement_shader() -> bool:
	if not SHADER.contains("varying float fade;") or not SHADER.contains("ALPHA = c.a * fade;"):
		push_warning("Enhanced: upstream clutter shader changed; original vegetation retained")
		return false
	_ready_image = Image.create(256, 256, false, Image.FORMAT_L8)
	_ready_image.fill(Color.BLACK)
	_ready_texture = ImageTexture.create_from_image(_ready_image)
	# UV2 is the stock sprite's wind metadata, not its atlas UV0. Pack cell coordinates in values exactly
	# representable even as half floats; floor(UV2.x) recovers the unchanged top/bottom wind weight.
	var code := SHADER.replace("UV2.x", "floor(UV2.x)")
	code = code.replace("varying float fade;", "varying float fade;\nvarying vec2 replant_cell;\nvarying float replant_shrub;\nuniform sampler2D replant_ready : filter_nearest, repeat_disable;\nuniform float replant_on = 1.0;")
	code = code.replace("void vertex() {", "void vertex() {\n replant_shrub = step(512.0, UV2.y);\n replant_cell = vec2(fract(UV2.x) * 2.0, (UV2.y - replant_shrub * 512.0 - 0.5) / 256.0);")
	code = code.replace("ALPHA = c.a * fade;", "ALPHA = c.a * fade * (1.0 - step(0.5, UV2.y) * mix(texture(replant_ready, replant_cell).r, 1.0, replant_shrub) * replant_on);")
	var shader := Shader.new()
	shader.code = code
	_material.shader = shader
	_material.set_shader_parameter("replant_ready", _ready_texture)
	_set_fade()
	refresh_textures()
	return true

func _refresh_ready() -> void:
	if _ready_image == null: return
	# Remember replaced cells for this overlay session, even after their parcels unload.
	for cells in chunk_cells.values():
		for cell in cells: _ready_image.set_pixel(cell.x, cell.y, Color.WHITE)
	_ready_texture.update(_ready_image)
	_recount_removed()

func _recount_removed() -> void:
	removed_counts.clear()
	if not enhanced_enabled: return
	for c in _tags_by_chunk:
		var tags: Dictionary = _tags_by_chunk[c]
		for cell in tags:
			for item_name in tags[cell]:
				# Unwanted shrubs stay hidden throughout the stock draw range, including unloaded
				# replacement parcels. Low grass remains a fallback until its cell is ready.
				if String(item_name).to_lower() in SHRUBS or (_ready_image != null and _ready_image.get_pixel(cell.x, cell.y).r > 0.5):
					removed_counts[item_name] = int(removed_counts.get(item_name, 0)) + int(tags[cell][item_name])

func _add_tuft(st: SurfaceTool, item: Dictionary, pos: Vector3, rng: RandomNumberGenerator) -> void:
	_tag_cell = Vector2i(-1, -1)
	_tag_shrub = false
	var item_name := String(item.name).to_lower()
	var replaceable: bool = item_name in LOW or (options.get("remove_shrubs", true) and item_name in SHRUBS)
	if not plan.is_empty() and replaceable and sample_mask(Vector2(pos.x, pos.z)).r > 0:
		_tag_cell = Vector2i(clampi(int(pos.x / float(zone.info.size_m) * 256), 0, 255), clampi(int(pos.z / float(zone.info.size_m) * 256), 0, 255))
		_tag_shrub = item_name in SHRUBS
		if not _tags_by_chunk[_building].has(_tag_cell): _tags_by_chunk[_building][_tag_cell] = {}
		var tags: Dictionary = _tags_by_chunk[_building][_tag_cell]
		tags[item.name] = int(tags.get(item.name, 0)) + 1
	super._add_tuft(st, item, pos, rng)

func _quad(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, d: Vector3, u0: float, u1: float, vb: float, vt: float, tint: Color, upright: bool) -> void:
	if plan.is_empty():
		super._quad(st, a, b, c, d, u0, u1, vb, vt, tint, upright)
		return
	var verts := [a, b, c, a, c, d]
	var uvs := [Vector2(u0, vb), Vector2(u1, vb), Vector2(u1, vt), Vector2(u0, vb), Vector2(u1, vt), Vector2(u0, vt)]
	var tops := [0.0, 0.0, 1.0, 0.0, 1.0, 1.0]
	var cell_x := (float(_tag_cell.x) + 0.5) / 512.0 if _tag_cell.x >= 0 else 0.0
	var cell_z := float(_tag_cell.y + 1) if _tag_cell.y >= 0 else 0.0
	# Integers 513..768 are exact in half floats; bit 512 marks only eligible unwanted shrubs.
	if _tag_shrub: cell_z += 512.0
	for i in 6:
		st.set_color(tint)
		st.set_uv(uvs[i])
		st.set_uv2(Vector2((float(tops[i]) if upright else 0.0) + cell_x, cell_z))
		st.set_normal(Vector3.UP)
		st.add_vertex(verts[i])

func _update_life(centre: Vector2i) -> void:
	if not options.get("insects", true) or not enhanced_enabled:
		if is_instance_valid(life):
			life.queue_free()
		return
	if life_chunk == centre and is_instance_valid(life):
		return
	if not chunk_plants.has(centre) or not is_instance_valid(chunk_plants[centre]):
		return
	if is_instance_valid(life):
		life.queue_free()
	life = load("res://enhanced/flower_insects.gd").new()
	chunk_plants[centre].add_child(life)
	life.setup(chunk_plants[centre], hash(centre))
	life_chunk = centre # Five insects maximum per loaded zone; only actual meadow flowers.

func _clear_new() -> void:
	_cancel_job()
	for patch in chunk_plants.values():
		if is_instance_valid(patch): patch.queue_free()
	chunk_plants.clear()
	chunk_cells.clear()
	removed_counts.clear()
	life_chunk = Vector2i(99999, 99999)
	if _ready_image != null: _ready_image.fill(Color.BLACK)
	_refresh_ready()

func set_enhanced(value: bool) -> void:
	enhanced_enabled = value
	_clear_new()
	if not plan.is_empty(): _material.set_shader_parameter("replant_on", 1.0 if value else 0.0)

func apply_settings() -> void:
	super.apply_settings()
	_tags_by_chunk.clear()
	_clear_new()

func _exit_tree() -> void:
	if is_instance_valid(palette):
		palette.free()
