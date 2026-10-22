extends Control
signal region_drawn(rect:Rect2)
var picture:Texture2D
var regions:Array=[]
var selection:=Rect2()
var start:=Vector2.ZERO
var dragging:=false
func _ready() -> void:
	custom_minimum_size=Vector2(300,245)
	mouse_default_cursor_shape=Control.CURSOR_CROSS
func image_rect() -> Rect2:
	if picture==null:return Rect2(Vector2.ZERO,size)
	var scale:=minf(size.x/picture.get_width(),size.y/picture.get_height())
	var extent:=Vector2(picture.get_size())*scale
	return Rect2((size-extent)*0.5,extent)
func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO,size),Color(0.08,0.09,0.1))
	if picture==null:return
	var box:=image_rect();draw_texture_rect(picture,box,false)
	for item in regions:
		var r:Array=item.rect
		draw_rect(Rect2(box.position+Vector2(r[0],r[1])*box.size,Vector2(r[2],r[3])*box.size),Color(0.25,0.85,0.7),false,2)
	if selection.has_area():draw_rect(Rect2(box.position+selection.position*box.size,selection.size*box.size),Color(1,0.75,0.2),false,2)
func _gui_input(event:InputEvent) -> void:
	var box:=image_rect()
	if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
		if event.pressed:
			if not box.has_point(event.position):return
			start=((event.position-box.position)/box.size).clamp(Vector2.ZERO,Vector2.ONE);dragging=true
		else:
			if dragging and selection.size.x>0.005 and selection.size.y>0.005:region_drawn.emit(selection)
			dragging=false
		accept_event()
	elif event is InputEventMouseMotion and dragging:
		var end:Vector2=((event.position-box.position)/box.size).clamp(Vector2.ZERO,Vector2.ONE)
		selection=Rect2(start.min(end),(end-start).abs());queue_redraw();accept_event()
