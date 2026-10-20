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

func build(zone: Node3D, _centre: Vector2, _radius: Vector2) -> void:
	noise.seed = 207348
	noise.frequency = 0.33
	noise.fractal_octaves = 3
	_build_mask()
	_bind_ground(zone)
	material = ShaderMaterial.new()
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode cull_disabled;
uniform float wind_clock = 0.0;
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
	vec3 vegetation = COLOR.rgb * mix(vec3(1.08, 0.91, 0.72), vec3(0.84, 1.04, 0.91), vigour);
	float leaf_weight = 1.0 - smoothstep(0.35, 0.55, min(COLOR.r, COLOR.g));
	ALBEDO = vegetation * mix(1.0, 0.78, leaf_weight);
	ROUGHNESS = 0.94;
	SPECULAR = 0.12;
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
}
"""
	material.shader = shader
	var meshes := {"hierba_fina": _grass_mesh(0), "hierba_ancha": _grass_mesh(1), "matas_secas": _grass_mesh(2), "treboles": _clover_mesh(), "rosetas": _rosette_mesh(), "margaritas": _flower_mesh(false), "flores_amarillas": _flower_mesh(true)}
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
		var scale_factor := rng.randf_range(0.70, 1.25)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * scale_factor)
		positions[species].append(Transform3D(basis, Vector3(p.x, h - 0.006, p.y)))
		colours[species].append(Color(m.g, 0, 0, 1))
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
uniform sampler2D landscape_grass : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D landscape_scrub : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec4 landscape_rect;
"""
	var finish := """
	vec2 lmuv = (world_pos.xz - landscape_rect.xy) / landscape_rect.zw;
	if (landscape_on && lmuv.x >= 0.0 && lmuv.y >= 0.0 && lmuv.x <= 1.0 && lmuv.y <= 1.0) {
		vec2 lm = texture(landscape_mask, lmuv).rg;
		vec3 green = texture(landscape_grass, world_pos.xz / 3.2).rgb;
		vec3 scrub = texture(landscape_scrub, world_pos.xz / 4.7).rgb;
		vec3 ground = mix(scrub, green, mix(0.28, 0.68, lm.g));
		ALBEDO = mix(ALBEDO, ground, lm.r * 0.82);
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
		own.set_shader_parameter("landscape_grass", zone.materials.texture("h_grass"))
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

func _grass_mesh(kind: int) -> ArrayMesh:
	var st := _start()
	var rng := RandomNumberGenerator.new()
	rng.seed = 507 + kind
	var colours := [Color(0.17, 0.29, 0.055), Color(0.20, 0.32, 0.075), Color(0.32, 0.29, 0.12)]
	for blade in (7 if kind == 0 else 5):
		var angle := rng.randf() * TAU
		var outward := Vector3(cos(angle), 0, sin(angle))
		var side := outward.cross(Vector3.UP)
		var height := rng.randf_range(0.12, 0.24) if kind == 0 else rng.randf_range(0.19, 0.36)
		var width := 0.014 if kind == 0 else 0.032
		if kind == 2:
			width = 0.012
		var origin := outward * rng.randf_range(0, 0.045)
		var bottom_a := origin - side * width * 0.5
		var bottom_b := origin + side * width * 0.5
		var mid := origin + Vector3.UP * height * 0.55 + outward * height * 0.12
		var tip := origin + Vector3.UP * height + outward * height * 0.5
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

func _clover_mesh() -> ArrayMesh:
	var st := _start()
	for sprig in 3:
		var angle := float(sprig) * TAU / 3
		var base := Vector3(cos(angle) * 0.04, 0.055 + sprig * 0.015, sin(angle) * 0.04)
		for leaflet in 3:
			var direction := Vector3(cos(angle + leaflet * TAU / 3), 0.14, sin(angle + leaflet * TAU / 3)).normalized()
			_leaf(st, base, direction, 0.065, 0.029, Color(0.14, 0.30, 0.06), true)
	return _finish(st)

func _rosette_mesh() -> ArrayMesh:
	var st := _start()
	for leaf in 6:
		var a := float(leaf) * TAU / 6
		_leaf(st, Vector3(0, 0.025, 0), Vector3(cos(a), 0.25, sin(a)).normalized(), 0.12, 0.026, Color(0.16, 0.27, 0.075))
	return _finish(st)

func _flower_mesh(yellow: bool) -> ArrayMesh:
	var st := _start()
	var height := 0.26 if yellow else 0.32
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
	var petals := 5 if yellow else 9
	for petal in petals:
		var a := float(petal) * TAU / petals
		var direction := Vector3(cos(a), 0.05, sin(a)).normalized()
		_leaf(st, top + direction * 0.009, direction, 0.047, 0.012, Color(0.65, 0.46, 0.045) if yellow else Color(0.83, 0.81, 0.65))
	for ring in 8:
		var a := float(ring) * TAU / 8
		var b := float(ring + 1) * TAU / 8
		_triangle(st, top + Vector3.UP * 0.016, top + Vector3(cos(a) * 0.015, 0.004, sin(a) * 0.015), top + Vector3(cos(b) * 0.015, 0.004, sin(b) * 0.015), Color(0.62, 0.39, 0.025))
	return _finish(st)
