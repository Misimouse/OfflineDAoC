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
	var hit := get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(zone.to_global(p + Vector3.UP * 12), zone.to_global(p - Vector3.UP * 0.4)))
	return hit.is_empty() or zone.to_local(hit.position).y <= p.y + 0.12

func _process(delta: float) -> void:
	if plan.is_empty():
		super._process(delta)
		return
	clock += delta if options.get("wind", true) else 0.0
	plant_material.set_shader_parameter("wind_clock", clock)
	if viewer == null:
		return
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
		if not wanted.has(c) or bool(_chunks[c].get_meta("enhanced", false)) != should_plant(c):
			_chunks[c].queue_free()
			_chunks.erase(c)
			chunk_plants.erase(c)
			chunk_cells.erase(c)
	wanted.sort_custom(func(a, b):return Vector2(a - centre).length_squared() < Vector2(b - centre).length_squared())
	for c in wanted:
		if not _chunks.has(c):
			_chunks[c] = _build_chunk(c)
			break # One bounded chunk per frame, nearest first.
	_update_life(centre)

func should_plant(c: Vector2i) -> bool:
	if c.x < 0 or c.y < 0 or c.x * CHUNK_M >= float(zone.info.size_m) or c.y * CHUNK_M >= float(zone.info.size_m):
		return false
	var p := to_local(viewer.global_position)
	var centre := Vector2i(floori(p.x / CHUNK_M), floori(p.z / CHUNK_M))
	return enhanced_enabled and density_mult > 0 and radius_m > 0 and absi(c.x - centre.x) <= 1 and absi(c.y - centre.y) <= 1

func _build_chunk(c: Vector2i) -> MeshInstance3D:
	_building = c
	var patch: Node3D
	if not plan.is_empty() and should_plant(c):
		patch = _plant(c)
	var mi := super._build_chunk(c)
	mi.set_meta("enhanced", not plan.is_empty() and should_plant(c))
	if patch != null:
		mi.add_child(patch)
		chunk_plants[c] = patch
	return mi

func _plant(c: Vector2i) -> Node3D:
	var patch := Node3D.new()
	patch.set_script(load("res://enhanced/replant/patch_proxy.gd"))
	patch.controller = self
	var positions := {}
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(Vector3i(int(zone.info.id), c.x, c.y))
	var attempts := mini(40000, int(CHUNK_M * CHUNK_M * float(options.get("density", 24)) * density_mult))
	var limit := clampi(int(options.get("chunk_budget", 20000)), 500, 30000)
	var accepted := 0
	chunk_cells[c] = {}
	for i in attempts:
		if accepted >= limit:
			break
		var p := Vector2(c.x, c.y) * CHUNK_M + Vector2(rng.randf(), rng.randf()) * CHUNK_M
		var m := sample_mask(p)
		if m.r <= 0 or rng.randf() > m.r:
			continue
		var h: float = zone.height_at(p.x, p.y)
		if not surface_clear(Vector3(p.x, h, p.y)):
			continue
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
		chunk_cells[c][Vector2i(floori(p.x / 6.4), floori(p.y / 6.4))] = true
		accepted += 1
	for key in positions:
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = meshes[key]
		mm.instance_count = positions[key].size()
		for i in mm.instance_count:
			mm.set_instance_transform(i, positions[key][i])
			mm.set_instance_custom_data(i, Color(0.7, 0, 0, 1))
		var batch := MultiMeshInstance3D.new()
		batch.name = key
		batch.multimesh = mm
		batch.material_override = plant_material
		batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		batch.visibility_range_end = 50
		batch.extra_cull_margin = 0.2
		patch.add_child(batch)
	patch.set_meta("instances", accepted)
	return patch

func _add_tuft(st: SurfaceTool, item: Dictionary, pos: Vector3, rng: RandomNumberGenerator) -> void:
	var item_name := String(item.name).to_lower()
	var cell := Vector2i(floori(pos.x / 6.4), floori(pos.z / 6.4))
	var replaceable: bool = item_name in LOW or (options.get("remove_shrubs", true) and item_name in SHRUBS)
	if not plan.is_empty() and enhanced_enabled and replaceable and chunk_cells.get(_building, {}).has(cell) and sample_mask(Vector2(pos.x, pos.z)).r > 0 and surface_clear(pos):
		removed_counts[item.name] = int(removed_counts.get(item.name, 0)) + 1
		var discard := SurfaceTool.new()
		discard.begin(Mesh.PRIMITIVE_TRIANGLES)
		super._add_tuft(discard, item, pos, rng)
		st.set_color(Color.WHITE)
		st.set_uv(Vector2.ZERO)
		st.set_uv2(Vector2.ZERO)
		st.set_normal(Vector3.UP)
		for i in 3:
			st.add_vertex(pos)
		return
	super._add_tuft(st, item, pos, rng)

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

func set_enhanced(value: bool) -> void:
	enhanced_enabled = value
	apply_settings()

func apply_settings() -> void:
	super.apply_settings()
	chunk_plants.clear()
	chunk_cells.clear()
	removed_counts.clear()
	life_chunk = Vector2i(99999, 99999)

func _exit_tree() -> void:
	if is_instance_valid(palette):
		palette.free()
