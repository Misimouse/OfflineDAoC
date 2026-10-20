extends Node3D
## A bounded landscape experiment. Resources are cloned in memory, never saved over DAoC content.
var instances := 0
var triangles := 0
var clock := 0.0
var animate := true
var material: ShaderMaterial
var counts := {}
var ground_materials: Array[ShaderMaterial] = []
var coverage: Image
var mask_texture: ImageTexture
var bounds := Rect2(1357, 1252, 14, 22)
var centre := Vector2(1364, 1263)
var noise := FastNoiseLite.new()
var plant_positions := {}
var green_profile := false
var low_cover_instances := 0

func build(zone: Node3D, _centre: Vector2, _radius: Vector2) -> void:
	noise.seed = 207348
	noise.frequency = 0.33
	noise.fractal_octaves = 3
	_build_mask()
	if not green_profile:
		_bind_ground(zone)
	material = make_material(green_profile)
	var meshes := make_catalog()
	var positions := {}
	var colours := {}
	for species in meshes:
		positions[species] = []
		colours[species] = []
	var rng := RandomNumberGenerator.new()
	rng.seed = 20720261021
	for i in 11500:
		var p := bounds.position + Vector2(rng.randf(), rng.randf()) * bounds.size
		var m := sample_mask(p)
		if rng.randf() > m.r * 0.72:
			continue
		var h: float = zone.height_at(p.x, p.y)
		if h < float(zone.water_level_at(p.x, p.y)) + 0.05:
			continue
		# Physics rejects roofs, fixture floors and colliding objects; ground must remain the first surface.
		var query := PhysicsRayQueryParameters3D.create(Vector3(p.x, h + 12.0, p.y), Vector3(p.x, h - 0.4, p.y))
		var hit: Dictionary = zone.get_world_3d().direct_space_state.intersect_ray(query)
		if not hit.is_empty() and float(hit.position.y) > h + 0.12:
			continue
		var clump := noise.get_noise_2d(p.x * 1.7 + 100, p.y * 1.7 - 30)
		var choice := rng.randf()
		var species := "hierba_fina"
		if choice < 0.025 and clump > 0.04:
			species = "margaritas"
		elif choice < 0.045 and clump < -0.08:
			species = "flores_amarillas"
		elif choice < 0.22 and clump > -0.05:
			species = "treboles"
		elif choice < 0.30 and clump < 0.05:
			species = "rosetas"
		elif m.g < 0.40 and choice < 0.6:
			species = "matas_secas"
		elif choice > 0.66:
			species = "hierba_ancha"
		# Replace a fraction of the existing plants instead of increasing total density.
		if species == "rosetas" and i % 4 == 0:
			species = "helechos"
		elif species == "treboles" and i % 4 == 0:
			species = "hojas_largas"
		var variant_count := 2 if species in ["helechos", "hojas_largas"] else 3
		var variant := absi(i * 17 + int(p.x * 13.0) + int(p.y * 19.0)) % variant_count
		species += "_%d" % variant
		var scale_factor := rng.randf_range(0.70, 1.25)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * scale_factor)
		positions[species].append(Transform3D(basis, Vector3(p.x, h - 0.006, p.y)))
		colours[species].append(Color(m.g, 0, 0, 1))
	# Infill has its own RNG so established tall plants and flowers keep their positions.
	var low_rng := RandomNumberGenerator.new()
	low_rng.seed = 2078731
	for i in 19000:
		var p := bounds.position + Vector2(low_rng.randf(), low_rng.randf()) * bounds.size
		var m := sample_mask(p)
		if low_rng.randf() > m.r * 0.85:
			continue
		var h: float = zone.height_at(p.x, p.y)
		if h < float(zone.water_level_at(p.x, p.y)) + 0.05:
			continue
		var query := PhysicsRayQueryParameters3D.create(Vector3(p.x, h + 12, p.y), Vector3(p.x, h - 0.4, p.y))
		var hit: Dictionary = zone.get_world_3d().direct_space_state.intersect_ray(query)
		if not hit.is_empty() and float(hit.position.y) > h + 0.12:
			continue
		var species := "tapiz_bajo_%d" % (i % 2)
		# Follow the slope using the same height field as the rendered terrain.
		var dx: float = (zone.height_at(p.x + 0.2, p.y) - zone.height_at(p.x - 0.2, p.y)) / 0.4
		var dz: float = (zone.height_at(p.x, p.y + 0.2) - zone.height_at(p.x, p.y - 0.2)) / 0.4
		var normal := Vector3(-dx, 1, -dz).normalized()
		var aligned := Basis(Quaternion(Vector3.UP, normal)) * Basis(Vector3.UP, low_rng.randf() * TAU)
		aligned = aligned.scaled(Vector3.ONE * low_rng.randf_range(0.8, 1.25))
		positions[species].append(Transform3D(aligned, Vector3(p.x, h - 0.005, p.y)))
		colours[species].append(Color(m.g, 0, 0, 1))
		low_cover_instances += 1
	for species in meshes:
		var mesh: ArrayMesh = meshes[species]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_custom_data = true
		mm.mesh = mesh
		mm.instance_count = positions[species].size()
		for i in mm.instance_count:
			mm.set_instance_transform(i, positions[species][i])
			mm.set_instance_custom_data(i, colours[species][i])
		var batch := MultiMeshInstance3D.new()
		batch.name = species
		batch.multimesh = mm
		batch.material_override = material
		batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		batch.extra_cull_margin = 0.12
		batch.visibility_range_end = 52.0
		add_child(batch)
		counts[species] = mm.instance_count
		instances += mm.instance_count
		triangles += mm.instance_count * mesh.get_faces().size() / 3
		plant_positions[species] = positions[species].map(func(t):return [t.origin.x, t.origin.y, t.origin.z])
	print("LANDSCAPE_COUNTS=", JSON.stringify(counts), " TRIANGLES=", triangles)

func _build_mask() -> void:
	coverage = Image.create(256, 256, false, Image.FORMAT_RGBA8)
	for z in 256:
		for x in 256:
			var p := bounds.position + Vector2(float(x) / 255.0, float(z) / 255.0) * bounds.size
			var q := p - centre
			var oval := Vector2(q.x / 6.2, q.y / 9.7).length()
			var edge := oval + noise.get_noise_2d(p.x, p.y) * 0.24
			var fill := 1.0 - smoothstep(0.60, 1.04, edge)
			# A small footpath connects the well to the open eastern side. Both soil and plants use this same mask.
			var path_z := 1260.8 - (p.x - 1353.6) * 0.102
			fill *= smoothstep(0.70, 1.65, absf(p.y - path_z))
			fill *= smoothstep(3.5, 4.8, p.distance_to(Vector2(1353.6, 1260.8)))
			var vigour := clampf(0.53 + noise.get_noise_2d(p.x * 0.45 + 150, p.y * 0.45) * 0.75, 0.18, 0.85)
			if green_profile:
				vigour = maxf(vigour, 0.65)
			coverage.set_pixel(x, z, Color(fill, vigour, 0, 1))
	mask_texture = ImageTexture.create_from_image(coverage)

func sample_mask(p: Vector2) -> Color:
	var uv := (p - bounds.position) / bounds.size
	if uv.x < 0 or uv.y < 0 or uv.x > 1 or uv.y > 1:
		return Color(0, 0, 0, 1)
	return coverage.get_pixel(clampi(roundi(uv.x * 255), 0, 255), clampi(roundi(uv.y * 255), 0, 255))

func _bind_ground(zone: Node3D) -> void:
	var base_shader: Shader = load("res://game/terrain.gdshader")
	var extra := """
uniform bool landscape_on = true;
uniform sampler2D landscape_mask : filter_linear, repeat_disable;
uniform sampler2D landscape_soil : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D landscape_scrub : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec4 landscape_rect;
"""
	var finish := """
	vec2 lmuv = (world_pos.xz - landscape_rect.xy) / landscape_rect.zw;
	if (landscape_on && lmuv.x >= 0.0 && lmuv.y >= 0.0 && lmuv.x <= 1.0 && lmuv.y <= 1.0) {
		vec2 lm = texture(landscape_mask, lmuv).rg;
		// Fine mineral/organic ground, rather than a large photograph of grass under real blades.
		vec2 soil_uv = world_pos.xz / 1.15;
		vec3 soil = texture(landscape_soil, soil_uv).rgb;
		soil = mix(soil, texture(landscape_soil, vec2(-soil_uv.y, soil_uv.x) * 0.71 + vec2(0.37, 0.61)).rgb, 0.35);
		vec3 scrub = texture(landscape_scrub, world_pos.xz / 0.80).rgb;
		vec3 ground = mix(soil, scrub, mix(0.40, 0.62, lm.g));
		float lum = dot(ground, vec3(0.299, 0.587, 0.114));
		ground = mix(ground, vec3(lum) * vec3(0.92, 1.03, 0.72), 0.38);
		ALBEDO = mix(ALBEDO, ground, lm.r * 0.94);
	}
"""
	var code := base_shader.code.replace("varying vec3 world_pos;", extra + "\nvarying vec3 world_pos;")
	code = code.replace("\tROUGHNESS = 0.95;", finish + "\n\tROUGHNESS = 0.95;")
	assert(code != base_shader.code)
	var shader := Shader.new()
	shader.code = code
	for child in zone.get_children():
		if not child is MeshInstance3D or not String(child.name).begins_with("Terrain_"):
			continue
		var mesh: Mesh = child.mesh
		var old := mesh.surface_get_material(0) as ShaderMaterial
		if old == null or String(old.get_meta("patch", "")) != "6_6":
			continue
		var own := old.duplicate() as ShaderMaterial
		own.shader = shader
		own.set_shader_parameter("landscape_mask", mask_texture)
		own.set_shader_parameter("landscape_soil", zone.materials.texture("h_soil"))
		own.set_shader_parameter("landscape_scrub", zone.materials.texture("h_ground_scrub"))
		own.set_shader_parameter("landscape_rect", Vector4(bounds.position.x, bounds.position.y, bounds.size.x, bounds.size.y))
		child.material_override = own
		ground_materials.append(own)
	assert(ground_materials.size() == 1, "Unexpected ground patch scope")

func set_active(value: bool) -> void:
	visible = value
	for mat in ground_materials:
		mat.set_shader_parameter("landscape_on", value)

func _process(delta: float) -> void:
	if animate:
		clock += delta
	if material:
		material.set_shader_parameter("wind_clock", clock)

func _triangle(st: SurfaceTool, a: Vector3, b: Vector3, c: Vector3, colour: Color) -> void:
	for p in [a, b, c]:
		st.set_color(colour)
		st.add_vertex(p)

func _start() -> SurfaceTool:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	return st

func _finish(st: SurfaceTool) -> ArrayMesh:
	st.generate_normals()
	return st.commit()

func _grass_mesh(kind: int, variant: int = 0) -> ArrayMesh:
	var st := _start()
	var rng := RandomNumberGenerator.new()
	rng.seed = 507 + kind + variant * 911
	var colours := [Color(0.17, 0.29, 0.055), Color(0.20, 0.32, 0.075), Color(0.32, 0.29, 0.12)]
	for blade in ((6 + variant) if kind == 0 else (4 + variant)):
		var angle := rng.randf() * TAU
		var outward := Vector3(cos(angle), 0, sin(angle))
		var side := outward.cross(Vector3.UP)
		var height := rng.randf_range(0.10, 0.22) if kind == 0 else rng.randf_range(0.16, 0.30)
		height *= 0.85 + variant * 0.13
		var width := (0.011 if kind == 0 else 0.024) * (0.85 + variant * 0.15)
		if kind == 2:
			width = 0.012
		var origin := outward * rng.randf_range(0, 0.045)
		var bottom_a := origin - side * width * 0.5
		var bottom_b := origin + side * width * 0.5
		var mid := origin + Vector3.UP * height * 0.55 + outward * height * 0.12
		var tip := origin + Vector3.UP * height + outward * height * (0.32 + variant * 0.17)
		var col: Color = colours[kind]
		_triangle(st, bottom_a, mid - side * width * 0.35, mid, col * 0.83)
		_triangle(st, bottom_a, mid, bottom_b, col * 0.83)
		_triangle(st, bottom_b, mid, mid + side * width * 0.35, col)
		_triangle(st, mid - side * width * 0.35, tip, mid, col)
		_triangle(st, mid, tip, mid + side * width * 0.35, col * 1.12)
	return _finish(st)

func _leaf(st: SurfaceTool, base: Vector3, direction: Vector3, length: float, width: float, colour: Color, heart: bool = false) -> void:
	var side := direction.cross(Vector3.UP).normalized()
	var outline: Array
	if heart:
		outline = [Vector2(0, 0), Vector2(-0.8, 0.35), Vector2(-1, 0.72), Vector2(-0.5, 1), Vector2(0, 0.83), Vector2(0.5, 1), Vector2(1, 0.72), Vector2(0.8, 0.35)]
	else:
		outline = [Vector2(0, 0), Vector2(-0.75, 0.25), Vector2(-1, 0.55), Vector2(-0.65, 0.8), Vector2(0, 1), Vector2(0.65, 0.8), Vector2(1, 0.55), Vector2(0.75, 0.25)]
	var mid := base + direction * length * 0.52 + Vector3.UP * 0.009
	for i in outline.size():
		var a: Vector2 = outline[i]
		var b: Vector2 = outline[(i + 1) % outline.size()]
		_triangle(st, mid, base + direction * a.y * length + side * a.x * width, base + direction * b.y * length + side * b.x * width, colour * (0.87 if i < 4 else 1.06))

func _clover_mesh(variant: int = 0) -> ArrayMesh:
	var st := _start()
	for sprig in (2 + variant):
		var angle := float(sprig) * 2.39 + variant * 0.7
		var base := Vector3(cos(angle) * 0.04, 0.04 + sprig * 0.012, sin(angle) * 0.04)
		for leaflet in 3:
			var direction := Vector3(cos(angle + leaflet * TAU / 3), 0.14, sin(angle + leaflet * TAU / 3)).normalized()
			_leaf(st, base, direction, 0.048 + variant * 0.008, 0.022 + variant * 0.003, Color(0.14, 0.30, 0.06), true)
	return _finish(st)

func _rosette_mesh(variant: int = 0) -> ArrayMesh:
	var st := _start()
	for leaf in (4 + variant):
		var a := float(leaf) * 2.39
		_leaf(st, Vector3(0, 0.02, 0), Vector3(cos(a), 0.16 + variant * 0.10, sin(a)).normalized(), 0.085 + variant * 0.018, 0.018 + variant * 0.004, Color(0.16, 0.27, 0.075))
	return _finish(st)

func _flower_mesh(yellow: bool, variant: int = 0) -> ArrayMesh:
	var st := _start()
	var height := (0.22 if yellow else 0.27) * (0.80 + variant * 0.18)
	for side in 3:
		var a := float(side) * TAU / 3
		var b := float(side + 1) * TAU / 3
		var pa := Vector3(cos(a), 0, sin(a)) * 0.003
		var pb := Vector3(cos(b), 0, sin(b)) * 0.003
		_triangle(st, pa, pa + Vector3.UP * height, pb + Vector3.UP * height, Color(0.17, 0.26, 0.05))
		_triangle(st, pa, pb + Vector3.UP * height, pb, Color(0.17, 0.26, 0.05))
	for leaf in 2:
		_leaf(st, Vector3(0, 0.08 + leaf * 0.05, 0), Vector3(1 - leaf * 2, 0.3, 0).normalized(), 0.07, 0.015, Color(0.15, 0.28, 0.06))
	var top := Vector3(0, height, 0)
	var petals := (5 + variant % 2) if yellow else (7 + variant)
	for petal in petals:
		var a := float(petal) * TAU / petals
		var direction := Vector3(cos(a), 0.05, sin(a)).normalized()
		_leaf(st, top + direction * 0.009, direction, 0.047, 0.012, Color(0.65, 0.46, 0.045) if yellow else Color(0.83, 0.81, 0.65))
	for ring in 8:
		var a := float(ring) * TAU / 8
		var b := float(ring + 1) * TAU / 8
		_triangle(st, top + Vector3.UP * 0.016, top + Vector3(cos(a) * 0.015, 0.004, sin(a) * 0.015), top + Vector3(cos(b) * 0.015, 0.004, sin(b) * 0.015), Color(0.62, 0.39, 0.025))
	return _finish(st)

func _herb_mesh(variant: int) -> ArrayMesh:
	var st := _start()
	for level in 3:
		var a := float(level) * 1.75 + variant
		for side in [-1, 1]:
			var direction := Vector3(cos(a) * side, 0.4 + level * 0.13, sin(a) * side).normalized()
			_leaf(st, Vector3(0, 0.018 + level * 0.025, 0), direction, 0.09 - level * 0.012 + variant * 0.018, 0.012, Color(0.12, 0.24, 0.055))
	return _finish(st)

func _fern_mesh(variant: int) -> ArrayMesh:
	var st := _start()
	for frond in 3:
		var a := float(frond) * 2.39 + variant * 0.8
		var direction := Vector3(cos(a), 0.35 + variant * 0.15, sin(a)).normalized()
		var side := direction.cross(Vector3.UP).normalized()
		for pair in 4:
			var t := float(pair + 1) / 5.0
			var base := Vector3.UP * 0.025 + direction * (0.15 + variant * 0.025) * t
			for sign_value in [-1, 1]:
				var leaflet: Vector3 = (side * float(sign_value) + direction * 0.5).normalized()
				_leaf(st, base, leaflet, 0.045 * (1.0 - t * 0.65), 0.008, Color(0.11, 0.23, 0.05))
	return _finish(st)

func _low_cover_mesh(variant: int) -> ArrayMesh:
	var st := _start()
	# Seven broad, short, curved blades: 14 triangles per tuft, no alpha texture.
	for blade in 7:
		var a := float(blade) * 2.399 + variant * 0.7
		var outward := Vector3(cos(a), 0, sin(a))
		var side := outward.cross(Vector3.UP)
		var base := outward * (0.015 + (blade % 3) * 0.02)
		var height := 0.045 + (blade % 4) * 0.015 + variant * 0.015
		var tip := base + Vector3.UP * height + outward * (0.07 + variant * 0.025)
		var middle := (base + tip) * 0.5 + Vector3.UP * 0.018
		var col := Color(0.115, 0.215, 0.052)
		_triangle(st, base - side * 0.012, middle - side * 0.014, tip, col)
		_triangle(st, base + side * 0.012, tip, middle + side * 0.014, col * 1.08)
	return _finish(st)

func make_material(green: bool = true) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode cull_disabled;
uniform float wind_clock = 0.0;
uniform float green_profile = 0.0;
varying float vigour;
void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float phase = wind_clock * 1.65 + wp.x * 0.65 + wp.z * 0.38;
	float weight = clamp(VERTEX.y / 0.4, 0.0, 1.0);
	VERTEX.x += sin(phase) * 0.026 * weight * weight;
	VERTEX.z += cos(phase * 0.8) * 0.016 * weight * weight;
	float shrink = 1.0 - smoothstep(35.0, 50.0, distance(wp, CAMERA_POSITION_WORLD));
	VERTEX *= shrink;
	vigour = INSTANCE_CUSTOM.r;
}
void fragment() {
	// Keep living foliage in a shared olive palette; preserve flower petal colours.
	float foliage = step(COLOR.r * 1.06, COLOR.g);
	vec3 olive = mix(vec3(0.105, 0.135, 0.043), vec3(0.095, 0.165, 0.052), vigour);
	olive = mix(olive, vec3(0.10, 0.215, 0.065), green_profile);
	vec3 vegetation = mix(COLOR.rgb * 0.72, olive, 0.62);
	ALBEDO = mix(COLOR.rgb, vegetation, foliage);
	float straw = (1.0 - step(0.40, COLOR.r)) * step(COLOR.g, COLOR.r) * step(COLOR.b * 1.4, COLOR.g);
	ALBEDO *= mix(1.0, 0.65, straw);
	ROUGHNESS = 0.94;
	SPECULAR = 0.12;
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
}
"""
	material.shader = shader
	material.set_shader_parameter("green_profile", 1.0 if green else 0.0)
	return material

func make_catalog() -> Dictionary:
	var meshes := {}
	for variant in 3:
		meshes["hierba_fina_%d" % variant] = _grass_mesh(0, variant)
		meshes["hierba_ancha_%d" % variant] = _grass_mesh(1, variant)
		meshes["matas_secas_%d" % variant] = _grass_mesh(2, variant)
		meshes["treboles_%d" % variant] = _clover_mesh(variant)
		meshes["rosetas_%d" % variant] = _rosette_mesh(variant)
		meshes["margaritas_%d" % variant] = _flower_mesh(false, variant)
		meshes["flores_amarillas_%d" % variant] = _flower_mesh(true, variant)
	for variant in 2:
		meshes["hojas_largas_%d" % variant] = _herb_mesh(variant)
		meshes["helechos_%d" % variant] = _fern_mesh(variant)
		meshes["tapiz_bajo_%d" % variant] = _low_cover_mesh(variant)
	return meshes
