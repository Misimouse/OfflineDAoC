extends Control
signal picked(point: Vector2, exclude: bool)
var overlay: Texture2D
var point := Vector2(0.5, 0.5)
var exclusions: Array = []
var metres := 1638.4
func _draw() -> void:
	var rect := Rect2(Vector2.ZERO, size)
	draw_rect(rect, Color(0.08, 0.12, 0.10))
	if overlay != null: draw_texture_rect(overlay, rect, false)
	for i in range(1, 8):
		draw_line(Vector2(size.x * i / 8.0, 0), Vector2(size.x * i / 8.0, size.y), Color(1, 1, 1, 0.12))
		draw_line(Vector2(0, size.y * i / 8.0), Vector2(size.x, size.y * i / 8.0), Color(1, 1, 1, 0.12))
	for area in exclusions:
		draw_circle(Vector2(area.x, area.z) / metres * size, float(area.radius) / metres * size.x, Color(0.9, 0.15, 0.12, 0.8), false, 2)
	draw_circle(point * size, 5, Color.WHITE)
	draw_line(point * size - Vector2(12, 0), point * size + Vector2(12, 0), Color.WHITE, 1)
	draw_line(point * size - Vector2(0, 12), point * size + Vector2(0, 12), Color.WHITE, 1)
func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed:
		point = event.position / size
		picked.emit(point * metres, event.button_index == MOUSE_BUTTON_RIGHT)
		queue_redraw()
