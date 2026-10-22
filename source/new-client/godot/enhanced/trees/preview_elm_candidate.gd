extends "res://enhanced/trees/preview_elm.gd"
## Compare two private candidates at one unchanged fixture; never changes active.json.
var reference_anchor:Node3D

func place_camera(view:int) -> void:
	angle=view
	var offset:Vector3=[Vector3(34,11,32),Vector3(24,11,24),Vector3(18,10,20),Vector3(5,2.5,7),Vector3(3.5,3.5,4.8)][view]
	cam.position=pivot+offset
	cam.position.y=maxf(cam.position.y,zone.height_at(cam.position.x,cam.position.z)+2.5)
	cam.look_at(pivot+Vector3.UP*([13.0,13.0,18.0,0.8,3.5][view]))

func toggle(show_candidate:bool) -> void:
	if not is_instance_valid(reference_anchor):
		var path:=String(args.get("reference-manifest",""))
		var data=JSON.parse_string(FileAccess.get_file_as_string(path))
		assert(data is Dictionary and int(data.zone)==207 and int(data.fixture)==1109)
		assert(FileAccess.get_sha256(data.scene)==data.scene_sha256)
		reference_anchor=Node3D.new()
		reference_anchor.name="Reference_Elm_Private"
		reference_anchor.transform=trial.replacement.transform
		reference_anchor.add_child(load(String(data.scene)).instantiate())
		trial.get_parent().add_child(reference_anchor)
		root.title="Elm2 - Comparacion con el olmo actual"
	# Keep the stock slot hidden while switching between the two private trees.
	trial.set_enabled(true)
	trial.replacement.visible=show_candidate
	reference_anchor.visible=not show_candidate
	label.text=("B - ELM2 PROPUESTO" if show_candidate else "A - OLMO ACTUAL CORREGIDO")+" | Mismo lugar, escala y luz"
	for button in label.get_parent().get_children():
		if button is HBoxContainer:
			button.get_child(0).text="A - Olmo actual"
			button.get_child(1).text="B - Elm2 propuesto"

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode==KEY_ESCAPE:quit()
		if event.keycode==KEY_SPACE and trial!=null:toggle(not trial.replacement.visible)
		if event.keycode==KEY_TAB and cam!=null:place_camera((angle+1)%views)
