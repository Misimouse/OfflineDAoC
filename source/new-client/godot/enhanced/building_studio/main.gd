extends SceneTree
func _initialize() -> void:
	root.size=Vector2i(1500,980)
	root.title="Taller de edificios · prueba local"
	root.add_child(load("res://enhanced/building_studio/studio_app.gd").new())
