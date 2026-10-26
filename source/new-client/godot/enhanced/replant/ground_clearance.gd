extends RefCounted
## Ground vegetation clearance is private to the explicitly configured LAB session.
const FLAG := &"enhanced_lab_clear_ground_vegetation"
const POINTER := "res://.enhanced-session/ground_clearance/active.json"

static func configure_lab(root: Node, pointer_path: String = POINTER) -> bool:
	root.set_meta(FLAG, false)
	if not FileAccess.file_exists(pointer_path): return false
	var pointer = JSON.parse_string(FileAccess.get_file_as_string(pointer_path))
	if not pointer is Dictionary or pointer.get("disabled", true): return false
	var path := String(pointer.get("manifest", ""))
	if path.is_empty() or not FileAccess.file_exists(path): return false
	if FileAccess.get_sha256(path) != pointer.get("sha256", ""): return false
	var manifest = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not manifest is Dictionary: return false
	if manifest.get("schema") != 1 or manifest.get("mode") != "empty-ground": return false
	if manifest.get("scope") != "all-loaded-zones-in-lab": return false
	root.set_meta(FLAG, true)
	return true

static func is_enabled(root: Node) -> bool:
	return root != null and bool(root.get_meta(FLAG, false))

static func clear_existing(scene: Node) -> int:
	if not is_enabled(scene.get_tree().root): return 0
	var count := 0
	var clutters = scene.get("clutters")
	if not clutters is Dictionary: return 0
	for clutter in clutters.values():
		if not is_instance_valid(clutter): continue
		clutter.set_process(false)
		if clutter.has_method("set_enhanced"): clutter.set_enhanced(false)
		if clutter is Node3D: clutter.visible = false
		clutter.queue_free()
		count += 1
	clutters.clear()
	scene.set("clutter", null)
	return count
