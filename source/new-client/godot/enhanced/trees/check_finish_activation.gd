extends SceneTree
func _initialize() -> void:call_deferred("run")
func run() -> void:
	var forest=load("res://enhanced/trees/forest_population.gd").new();assert(forest.configure());assert(forest.manifest.terrain_conform and not forest.manifest.terrain_extensions)
	var region=load("res://game/world/region_world.gd").new();var mushroom=load("res://enhanced/trees/mushroom_trial.gd").new();assert(mushroom.attach(region));assert(mushroom.manifest.has("bindstone_scene"))
	assert(FileAccess.get_sha256("res://.enhanced-session/water_trial/manifest.json")=="ba0e22e5b6da59fb6fd923ad82fd68b528b66b3217a2440bd1f2d50abf6a00a5")
	assert(load("res://enhanced/lab_session.gd").can_instantiate());assert(load("res://enhanced/godot_tools/inspector_bridge.gd").can_instantiate())
	mushroom.free();region.free();forest.free();print("FINISH_ACTIVE_POINTERS_OK");quit()
