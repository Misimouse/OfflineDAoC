extends Node
## Two labelled review trees in LAB only. Never edits fixtures, stock content or physics.
var config_path:="res://.enhanced-session/elm_trial/review_stand.json"
var config:Dictionary={}
var bound_zone
var display:Node3D
var hidden:Array=[]
var hidden_positions:Dictionary={}
var rows:Array=[]
var tree_controller
var previous_taa:=false
var taa_changed:=false
var smoothing_layer:CanvasLayer
var smoothing_label:Label

func attach(region,trees) -> bool:
	config=JSON.parse_string(FileAccess.get_file_as_string(config_path))
	if config.get("disabled",true):return false
	for item in config.get("trees",[]):
		if FileAccess.get_sha256(String(item.scene))!=item.sha256:return false
	tree_controller=trees
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():apply_zone(zone)
	return true

func apply_zone(zone) -> void:
	if int(zone.info.id)!=207 or is_instance_valid(bound_zone):return
	if tree_controller.bound_zone!=zone:return
	var anchor:=Node3D.new()
	anchor.name="EnhancedElmReviewStand"
	var prepared:Array=[]
	for item in config.trees:
		var model:Node3D=load(String(item.scene)).instantiate()
		var at:=Vector3(float(item.x),0,float(item.z))
		at.y=zone.height_at(at.x,at.z)
		var holder:=Node3D.new()
		holder.name=String(item.id)
		holder.transform=Transform3D(Basis(Vector3.UP,deg_to_rad(float(item.yaw))).scaled(Vector3.ONE*float(item.scale)),at)
		holder.add_child(model)
		anchor.add_child(holder)
		var title:=Label3D.new()
		title.text=String(item.label)
		title.position=at+Vector3.UP*3.5
		title.billboard=BaseMaterial3D.BILLBOARD_ENABLED
		title.font_size=44
		title.outline_size=12
		title.pixel_size=0.012
		title.no_depth_test=true
		title.visibility_range_end=100.0
		title.modulate=Color(1.0,0.9,0.25)
		anchor.add_child(title)
		prepared.append({"id":"review:"+String(item.id),"name":String(item.label).replace("\n"," "),"position":[at.x,at.y,at.z],"model":String(item.id),"kind":"Árbol de prueba","zone":207,"model_file":String(item.get("model_file","")),"note":"Ejemplar de revisión LAB, sin cambiar colisiones. Modelo y materiales preparados; no usar atlas del árbol antiguo."})
	# Clear only the private elm visuals around the review pair, reversibly, in LAB.
	for record in tree_controller.originals:
		var at:Vector3=record.transform.origin
		var hide:=at.distance_to(Vector3(1395.2,130.0875,1302.4))<0.01
		for item in prepared:
			var center:=Vector2(float(item.position[0]),float(item.position[2]))
			if Vector2(at.x,at.z).distance_to(center)<float(config.get("clear_radius",0.0)):hide=true
		if not hide:continue
		hidden_positions[at]=true
		for link in tree_controller.batch_links:
			if link.reference!=record.node:continue
			var index:=int(record.index)
			var saved:Transform3D=link.batch.multimesh.get_instance_transform(index)
			hidden.append({"batch":link.batch,"index":index,"transform":saved})
			saved.basis=Basis(Vector3.ZERO,Vector3.ZERO,Vector3.ZERO)
			link.batch.multimesh.set_instance_transform(index,saved)
	zone.add_child(anchor)
	display=anchor;bound_zone=zone;rows=prepared
	if config.get("temporal_aa",false):
		previous_taa=get_viewport().use_taa
		get_viewport().use_taa=true
		taa_changed=true
		smoothing_layer=CanvasLayer.new()
		add_child(smoothing_layer)
		smoothing_label=Label.new()
		smoothing_label.position=Vector2(20,110)
		smoothing_label.add_theme_color_override("font_shadow_color",Color.BLACK)
		smoothing_label.add_theme_constant_override("shadow_outline_size",4)
		smoothing_layer.add_child(smoothing_label)
		update_smoothing_label()
	print("ELM_REVIEW_STAND_READY trees=",rows.size()," hidden_parts=",hidden.size())

func _process(_delta:float) -> void:
	if is_instance_valid(display) and is_instance_valid(tree_controller):
		display.visible=tree_controller.enabled

func restore() -> void:
	for record in hidden:
		if is_instance_valid(record.batch):record.batch.multimesh.set_instance_transform(int(record.index),record.transform)
	hidden.clear();hidden_positions.clear();rows.clear()
	if is_instance_valid(display):display.queue_free()
	display=null;bound_zone=null
	if taa_changed:
		get_viewport().use_taa=previous_taa
		taa_changed=false
	if is_instance_valid(smoothing_layer):smoothing_layer.queue_free()
	smoothing_layer=null;smoothing_label=null

func hides_fixture(zone,at:Vector3) -> bool:
	return bound_zone==zone and tree_controller.enabled and hidden_positions.has(at)

func toggle_leaf_smoothing() -> void:
	if not taa_changed:return
	get_viewport().use_taa=not get_viewport().use_taa
	update_smoothing_label()

func update_smoothing_label() -> void:
	if is_instance_valid(smoothing_label):
		smoothing_label.text="Suavizar hojas: %s · Ctrl+Mayús+F7 para comparar"%["SÍ" if get_viewport().use_taa else "NO"]

func _unhandled_input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.shift_pressed and event.keycode==KEY_F7 and taa_changed:
		toggle_leaf_smoothing()
		get_viewport().set_input_as_handled()

func _exit_tree() -> void:
	restore()
