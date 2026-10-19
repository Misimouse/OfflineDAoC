extends Node3D
## Isolated geometry grass prototype. No textures, AI, terrain edits or shared resource mutations.
## Positions are supplied by the harness; this is not a global placement system.

var instances := 0
var triangles := 0
var batches: Array[MultiMeshInstance3D] = []
var material: ShaderMaterial
var clock := 0.0
var animate := true

func build(zone: Node3D, centre: Vector2, radius: Vector2) -> void:
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode cull_disabled;
uniform float wind_clock = 0.0;
uniform float fade_start = 35.0;
uniform float fade_end = 48.0;
varying vec3 tint;
void vertex() {
	vec3 wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float phase = wind_clock * 1.8 + wp.x * 0.7 + wp.z * 0.45;
	float tip = UV.y * UV.y;
	VERTEX.x += (sin(phase) + 0.35 * sin(phase * 1.7)) * 0.025 * tip;
	VERTEX.z += cos(phase * 0.8) * 0.014 * tip;
	float shrink = 1.0 - smoothstep(fade_start, fade_end, distance(wp, CAMERA_POSITION_WORLD));
	VERTEX *= shrink;
	tint = mix(vec3(0.10, 0.21, 0.035), vec3(0.25, 0.34, 0.085), INSTANCE_CUSTOM.r);
}
void fragment() {
	ALBEDO = tint * mix(0.65, 1.18, UV.y);
	ROUGHNESS = 0.94;
	SPECULAR = 0.12;
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
}
"""
	material = ShaderMaterial.new()
	material.shader = shader
	var mesh := _tuft_mesh()
	var rng := RandomNumberGenerator.new()
	rng.seed = 20720261020
	var positions: Array[Transform3D] = []
	var colours: Array[Color] = []
	# Irregular oval boundary rather than a rectangular carpet.
	for i in 4500:
		var local := Vector2(rng.randf_range(-radius.x, radius.x), rng.randf_range(-radius.y, radius.y))
		var oval := Vector2(local.x / radius.x, local.y / radius.y).length()
		var edge := oval + 0.09 * sin(local.x * 1.6) + 0.12 * sin(local.y * 1.4 + local.x * 0.6)
		var coverage := (1.0 - smoothstep(0.45, 1.05, edge)) * (0.8 + 0.2 * sin(local.x * 2.1 + local.y * 1.7))
		if oval > 1.1 or rng.randf() > coverage:
			continue
		var p := centre + local
		var h: float = zone.height_at(p.x, p.y)
		if h <= float(zone.water_level_at(p.x, p.y)) + 0.05:
			continue
		var scale_factor := rng.randf_range(0.7, 1.3)
		var basis := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * scale_factor)
		positions.append(Transform3D(basis, Vector3(p.x, h - 0.008, p.y)))
		colours.append(Color(rng.randf(), 0, 0, 1))
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = mesh
	mm.instance_count = positions.size()
	for i in positions.size():
		mm.set_instance_transform(i, positions[i])
		mm.set_instance_custom_data(i, colours[i])
	var batch := MultiMeshInstance3D.new()
	batch.multimesh = mm
	batch.material_override = material
	batch.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	batch.extra_cull_margin = 0.1
	batch.visibility_range_end = 50.0
	add_child(batch)
	batches.append(batch)
	instances = positions.size()
	triangles = instances * mesh.get_faces().size() / 3
	print("GRASS_INSTANCES=", instances, " TRIANGLES=", triangles, " CENTRE=", centre)

func _process(delta: float) -> void:
	if animate:
		clock += delta
	if material != null:
		material.set_shader_parameter("wind_clock", clock)

func _tuft_mesh() -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var rng := RandomNumberGenerator.new()
	rng.seed = 348207
	for blade in 7:
		var angle := float(blade) * TAU / 7.0 + rng.randf_range(-0.2, 0.2)
		var outward := Vector3(cos(angle), 0, sin(angle))
		var side := outward.cross(Vector3.UP)
		var height := rng.randf_range(0.17, 0.30)
		var width := rng.randf_range(0.014, 0.024)
		var lean := rng.randf_range(0.035, 0.11)
		var origin := outward * rng.randf_range(0.0, 0.035)
		for section in 2:
			var rows: Array = []
			for row in 2:
				var t := float(section + row) / 2.0
				var mid := origin + Vector3.UP * (height * t) + outward * (lean * t * t)
				var half_width := width * (1.0 - t) * 0.5
				rows.append([mid - side * half_width, mid + outward * half_width * 0.35, mid + side * half_width])
			for half in 2:
				var vertices := [[0, half], [1, half], [1, half + 1], [0, half], [1, half + 1], [0, half + 1]] if section == 0 else [[0, half], [1, 1], [0, half + 1]]
				for v in vertices:
					st.set_uv(Vector2(float(v[1]) * 0.5, float(section + v[0]) / 2.0))
					st.add_vertex(rows[v[0]][v[1]])
	st.generate_normals()
	return st.commit()
