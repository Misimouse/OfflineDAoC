extends Node3D
## Five client-only insects per flower patch. Routes stay inside flower clusters and the planting mask.
var flowers: Array[Vector3] = []
var actors: Array = []
var patch: Node3D
var clock := 0.0
var animate := true
var rng := RandomNumberGenerator.new()
var route_records: Array = []

func setup(owner_patch: Node3D, seed_value: int) -> void:
	patch = owner_patch
	rng.seed = seed_value
	for batch in patch.get_children():
		if not batch is MultiMeshInstance3D:
			continue
		var name_text := String(batch.name)
		if not name_text.begins_with("margaritas_") and not name_text.begins_with("flores_amarillas_"):
			continue
		var variant := int(name_text.get_slice("_", name_text.get_slice_count("_") - 1))
		var height := (0.22 if name_text.begins_with("flores_") else 0.27) * (0.80 + variant * 0.18)
		for i in batch.multimesh.instance_count:
			flowers.append(batch.multimesh.get_instance_transform(i) * Vector3(0, height + 0.02, 0))
	if flowers.is_empty():
		return
	for i in 5:
		var actor := Node3D.new()
		add_child(actor)
		var butterfly := i < 3
		var wings := _butterfly(actor, i) if butterfly else _bee(actor)
		var start := rng.randi_range(0, flowers.size() - 1)
		var state := {"node": actor, "wings": wings, "butterfly": butterfly, "from": start, "to": start, "elapsed": 0.0, "duration": 1.0, "pause": 0.0, "phase": rng.randf() * TAU}
		_new_route(state)
		state.elapsed = rng.randf() * float(state.duration)
		actors.append(state)
	_process(0)
	print("FLOWER_INSECTS=", actors.size(), " FLOWERS=", flowers.size())

func _new_route(state: Dictionary) -> void:
	var from_index := int(state.to)
	var a: Vector3 = flowers[from_index]
	var choices: Array[int] = []
	for i in flowers.size():
		var b: Vector3 = flowers[i]
		var distance := Vector2(a.x, a.z).distance_to(Vector2(b.x, b.z))
		if distance < 0.12 or distance > 2.6:
			continue
		var allowed := true
		for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
			var p: Vector3 = a.lerp(b, t)
			if patch.sample_mask(Vector2(p.x, p.z)).r < 0.20:
				allowed = false
		if allowed:
			choices.append(i)
	state.from = from_index
	state.to = choices[rng.randi_range(0, choices.size() - 1)] if not choices.is_empty() else from_index
	state.elapsed = 0.0
	state.duration = maxf(1.5, a.distance_to(flowers[state.to]) / (0.33 if state.butterfly else 0.52))
	state.pause = rng.randf_range(0.4, 1.5)
	route_records.append({"from": state.from, "to": state.to, "max_distance": 2.6})
	if route_records.size() > 256:
		route_records.pop_front()

func _process(delta: float) -> void:
	if not is_visible_in_tree():
		return
	if animate:
		clock += delta
	for state in actors:
		if animate:
			state.elapsed += delta
		if state.elapsed > state.duration + state.pause:
			_new_route(state)
		var t := clampf(float(state.elapsed) / float(state.duration), 0, 1)
		var a: Vector3 = flowers[state.from]
		var b: Vector3 = flowers[state.to]
		var p := a.lerp(b, smoothstep(0.0, 1.0, t))
		p.y += sin(t * PI) * (0.18 if state.butterfly else 0.10)
		p.y += 0.012 * sin(clock * 6.0 + state.phase)
		var node: Node3D = state.node
		node.position = p
		if a.distance_to(b) > 0.01:
			node.rotation.y = atan2(b.x - a.x, b.z - a.z)
		var flap := sin(clock * (23.0 if state.butterfly else 105.0) + state.phase)
		for side in 2:
			var wing: Node3D = state.wings[side]
			wing.rotation.z = (1 if side == 0 else -1) * (0.3 + flap * (0.85 if state.butterfly else 0.35))
		if get_viewport().get_camera_3d() != null:
			node.visible = node.global_position.distance_to(get_viewport().get_camera_3d().global_position) < 20.0

func snapshot() -> Dictionary:
	return {"count": actors.size(), "flower_count": flowers.size(), "flowers": flowers.map(func(p):return [p.x, p.y, p.z]), "routes": route_records, "positions": actors.map(func(s):return [s.node.position.x, s.node.position.y, s.node.position.z])}

func _material(colour: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = colour
	m.roughness = 0.9
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	return m

func _body(parent: Node3D, at: Vector3, size: Vector3, colour: Color) -> void:
	var mesh := SphereMesh.new()
	mesh.radius = 1.0
	mesh.height = 2.0
	mesh.radial_segments = 8
	mesh.rings = 4
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.material_override = _material(colour)
	node.scale = size
	node.position = at
	parent.add_child(node)

func _wing(parent: Node3D, sign_value: float, length: float, width: float, colour: Color, butterfly: bool) -> Node3D:
	var pivot := Node3D.new()
	parent.add_child(pivot)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var points := [Vector3(0, 0, -width * 0.3), Vector3(sign_value * length * 0.7, 0, -width), Vector3(sign_value * length, 0, -width * 0.35), Vector3(sign_value * length * 0.82, 0, width * 0.6), Vector3(sign_value * length * 0.4, 0, width), Vector3(0, 0, width * 0.25)]
	var centre := Vector3(sign_value * length * 0.42, 0, 0)
	for i in points.size():
		for p in [centre, points[i], points[(i + 1) % points.size()]]:
			st.add_vertex(p)
	st.generate_normals()
	var surface := MeshInstance3D.new()
	surface.mesh = st.commit()
	surface.material_override = _material(colour)
	pivot.add_child(surface)
	if butterfly:
		_body(pivot, Vector3(sign_value * length * 0.67, 0.0015, -width * 0.25), Vector3(0.009, 0.001, 0.009), Color(0.13, 0.08, 0.025))
	return pivot

func _butterfly(parent: Node3D, variant: int) -> Array:
	_body(parent, Vector3.ZERO, Vector3(0.004, 0.004, 0.024), Color(0.12, 0.08, 0.03))
	var colour: Color = [Color(0.75, 0.37, 0.08), Color(0.84, 0.73, 0.35), Color(0.70, 0.56, 0.29)][variant]
	return [_wing(parent, -1, 0.065, 0.04, colour, true), _wing(parent, 1, 0.065, 0.04, colour, true)]

func _bee(parent: Node3D) -> Array:
	for stripe in 3:
		_body(parent, Vector3(0, 0, (stripe - 1) * 0.009), Vector3(0.008, 0.007, 0.009), Color(0.15, 0.12, 0.035) if stripe % 2 == 0 else Color(0.70, 0.48, 0.06))
	return [_wing(parent, -1, 0.022, 0.012, Color(0.68, 0.68, 0.55), false), _wing(parent, 1, 0.022, 0.012, Color(0.68, 0.68, 0.55), false)]
