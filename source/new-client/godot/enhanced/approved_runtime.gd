extends RefCounted
## The installer's marker enables the approved snapshot in the normal source build.
const MARKER = "res://enhanced/approved_assets.json"

static func enabled() -> bool:
	if not FileAccess.file_exists(MARKER): return false
	var value = JSON.parse_string(FileAccess.get_file_as_string(MARKER))
	return value is Dictionary and value.get("enabled", false)

static func private_lab(scene: Node) -> bool:
	var server = scene.get_node_or_null("/root/Server")
	return server != null and server.get("protocol_profile") == "lab" and server.get("server_port") == 10310

static func clears_ground(scene: Node, zone_id: int) -> bool:
	return enabled() and not private_lab(scene) and zone_id in [207, 209]

static func attach(scene: Node, loading = null) -> void:
	if not enabled() or private_lab(scene) or scene.get("region") == null: return
	if scene.get_meta("approved_hibernia_bound", false): return
	scene.set_meta("approved_hibernia_bound", true)
	# Workers inspect native model families and retain native geometry for restoration.
	var profiles = [
		"res://.enhanced-session/ligen_20261025/forest.gd",
		"res://enhanced/trees/mushroom_trial.gd",
		"res://.enhanced-session/plaza_wallstone_20261024/controller.gd",
		"res://.enhanced-session/parthanan_canvas_fence_20261025/stones.gd",
		"res://.enhanced-session/parthanan_canvas_fence_20261025/manager.gd",
		"res://enhanced/terrain/water_trial.gd",
		"res://enhanced/replant/connacht_vegetation.gd"
	]
	for path in profiles:
		var script = load(path)
		if script == null:
			push_error("Approved art controller missing: " + path)
			continue
		var worker = script.new()
		scene.add_child(worker)
		if path.ends_with("connacht_vegetation.gd"):
			if worker.attach(scene.get("region"), scene.get("player")):
				await worker.warm_up(loading)
		else:
			worker.attach(scene.get("region"))
