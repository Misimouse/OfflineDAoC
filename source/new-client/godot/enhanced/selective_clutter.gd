extends "res://game/clutter.gd"
## Preserve tall seed grasses. Filter only named undergrowth, locally and reversibly.
var cleanup_enabled := false
var cleanup_centre := Vector2.ZERO
var removed_counts := {}
const UNDERGROWTH := ["thorny undergrowth", "leafy branch", "large green leaves (bush)", "vivid green leaf", "narrow green leaf", "leafy"]

func set_cleanup(value: bool, centre: Vector2) -> void:
	if cleanup_enabled == value and cleanup_centre == centre:
		return
	cleanup_enabled = value
	cleanup_centre = centre
	removed_counts.clear()
	if _material != null:
		apply_settings()

func _add_tuft(st: SurfaceTool, item: Dictionary, pos: Vector3, rng: RandomNumberGenerator) -> void:
	if cleanup_enabled and int(item.group) == 6 and String(item.name) in UNDERGROWTH and Vector2(pos.x, pos.z).distance_to(cleanup_centre) < 26.0:
		removed_counts[item.name] = int(removed_counts.get(item.name, 0)) + 1
		# Consume the original placement random stream so following seed grasses do not move.
		var discard := SurfaceTool.new()
		discard.begin(Mesh.PRIMITIVE_TRIANGLES)
		super._add_tuft(discard, item, pos, rng)
		# The original chunk builder counts every tuft; a zero-area placeholder keeps all-filtered chunks valid.
		st.set_color(Color.WHITE)
		st.set_uv(Vector2.ZERO)
		st.set_uv2(Vector2.ZERO)
		st.set_normal(Vector3.UP)
		for i in 3:
			st.add_vertex(pos)
		return
	super._add_tuft(st, item, pos, rng)
