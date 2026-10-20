extends SceneTree
## Native local control panel. All paths are supplied by a local ignored configuration.
const STATE := "res://.enhanced-session/replant"
var config := {}
var catalog := {}
var manifest := {}
var bundle := ""
var zones: ItemList
var status: Label
var detail: Label
var active_label: Label
var map
var density: SpinBox
var budget: SpinBox
var radius: SpinBox
var slope: SpinBox
var shrubs: CheckBox
var insects: CheckBox
var wind: CheckBox
var pid := -1
var working := false
var poll := 0.0
var selected := 207
var preview_point := Vector2(1190, 1180)
var exclusions := {}
var controls: Array[Button] = []
var auto_capture := ""
func read_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null: return {}
	var data = JSON.parse_string(f.get_as_text())
	return data if data is Dictionary else {}
func write_json(path: String, data: Dictionary) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify(data, "  "))
func _initialize() -> void:
	config = read_json(STATE.path_join("config.json"))
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--capture="): auto_capture = a.trim_prefix("--capture=")
	run.call_deferred()
func run() -> void:
	root.title = "DAoC Enhanced - Replantar Hibernia"
	root.size = Vector2i(1360, 1020)
	Engine.max_fps = 30
	var bg := ColorRect.new()
	bg.color = Color("16231e")
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(bg)
	var outer := VBoxContainer.new()
	outer.position = Vector2(24, 18)
	outer.size = Vector2(1312, 980)
	outer.add_theme_constant_override("separation", 12)
	root.add_child(outer)
	var title := Label.new()
	title.text = "REPLANTAR HIBERNIA"
	title.add_theme_font_size_override("font_size", 27)
	outer.add_child(title)
	var subtitle := Label.new()
	subtitle.text = "Clasico + Shrouded Isles  |  ToA excluido  |  Cambios reversibles en el cliente de desarrollo"
	outer.add_child(subtitle)
	active_label = Label.new()
	outer.add_child(active_label)
	var body := HBoxContainer.new()
	body.add_theme_constant_override("separation", 20)
	outer.add_child(body)
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(325, 640)
	body.add_child(left)
	var zone_title := Label.new()
	zone_title.text = "Zonas exteriores disponibles"
	left.add_child(zone_title)
	zones = ItemList.new()
	zones.custom_minimum_size = Vector2(325, 450)
	zones.item_selected.connect(select_zone)
	left.add_child(zones)
	button(left, "Actualizar inventario", func():job(["--scan"]))
	button(left, "Preparar mapa de esta zona", func():prepare(false))
	button(left, "Preparar mapas de Hibernia", func():prepare(true))
	button(left, "Preparar plantas de Ardee", prepare_resources)
	var middle := VBoxContainer.new()
	middle.custom_minimum_size = Vector2(580, 640)
	body.add_child(middle)
	map = load("res://enhanced/replant/map.gd").new()
	map.custom_minimum_size = Vector2(570, 570)
	map.picked.connect(pick)
	middle.add_child(map)
	var legend := Label.new()
	legend.text = "Verde: pradera  Ã‚Â·  Ocre: seco  Ã‚Â·  Turquesa: sotobosque\nOscuro: conservar original  Ã‚Â·  Rojo: exclusion manual\nClic: punto de vista  Ã‚Â·  Clic derecho: excluir circulo"
	middle.add_child(legend)
	var right := VBoxContainer.new()
	right.custom_minimum_size = Vector2(365, 640)
	body.add_child(right)
	density = spin(right, "Densidad de vegetacion", 4, 32, 24)
	budget = spin(right, "Plantas por parcela (32 m)", 1000, 30000, 20000, 1000)
	slope = spin(right, "Pendiente maxima (grados)", 10, 40, 32)
	radius = spin(right, "Radio de exclusion manual (m)", 5, 80, 15)
	shrubs = check(right, "Retirar arbustos bajos originales", true)
	insects = check(right, "Mariposas y abejas entre flores", true)
	wind = check(right, "Movimiento con viento", true)
	var preserve := Label.new()
	preserve.text = "Siempre: conservar plantas altas y suelo original.\nEl juego carga plantas ya preparadas. El limite de plantas afecta al rendimiento.\nAgua, roca y nieve conservan su vegetacion."
	preserve.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right.add_child(preserve)
	button(right, "Borrar exclusiones de esta zona", clear_exclusions)
	button(right, "Vista previa 3D / A-B", preview)
	button(right, "Verificar paquete y originales", func():job(["--action", "verify"]))
	button(right, "Activar en desarrollo", func():job(["--action", "activate"]))
	button(right, "Volver al estado anterior", func():job(["--action", "rollback"]))
	button(right, "Restaurar vegetacion original", func():job(["--action", "disable"]))
	detail = Label.new()
	detail.custom_minimum_size = Vector2(1280, 65)
	detail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	outer.add_child(detail)
	status = Label.new()
	status.custom_minimum_size = Vector2(1280, 50)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	outer.add_child(status)
	status.text = "Preparar crea un paquete nuevo. Activar afecta solo a futuras cargas en desarrollo; no modifica la instalacion ni el servidor."
	reload_data()
	if config.is_empty(): status.text = "Falta configuracion local: abrir con el acceso preparado en outputs."
	print("REPLANT_PANEL_READY eligible=", zones.item_count)
	if not auto_capture.is_empty():
		for f in 10: await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(auto_capture)
		quit()
func button(parent: Node, text: String, action: Callable) -> void:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size.y = 36
	b.pressed.connect(action)
	parent.add_child(b)
	controls.append(b)
func spin(parent: Node, text: String, lo: float, hi: float, value: float, step: float = 1) -> SpinBox:
	var label := Label.new()
	label.text = text
	parent.add_child(label)
	var box := SpinBox.new()
	box.min_value = lo
	box.max_value = hi
	box.step = step
	box.value = value
	parent.add_child(box)
	return box
func check(parent: Node, text: String, value: bool) -> CheckBox:
	var box := CheckBox.new()
	box.text = text
	box.button_pressed = value
	parent.add_child(box)
	return box
func reload_data() -> void:
	catalog = read_json(STATE.path_join("catalog.json"))
	var latest := read_json(STATE.path_join("latest.json"))
	bundle = String(latest.get("bundle", ""))
	manifest = read_json(bundle.path_join("manifest.json")) if not bundle.is_empty() else {}
	zones.clear()
	for zone in catalog.get("zones", []):
		if not zone.eligible: continue
		var i := zones.add_item("%d  %s  [%s]" % [zone.id, zone.name, "SI" if int(zone.region) == 181 else "Classic"])
		zones.set_item_metadata(i, zone)
		if int(zone.id) == selected: zones.select(i)
	var options: Dictionary = manifest.get("options", {})
	exclusions = options.get("exclusions", {})
	density.value = float(options.get("density", density.value))
	budget.value = float(options.get("chunk_budget", budget.value))
	slope.value = float(options.get("max_slope", slope.value))
	shrubs.button_pressed = options.get("remove_shrubs", true)
	insects.button_pressed = options.get("insects", true)
	wind.button_pressed = options.get("wind", true)
	var active := read_json(STATE.path_join("active.json"))
	active_label.text = ("Estado: ORIGINAL" if active.is_empty() or active.get("disabled", false) else "Estado: PAQUETE ACTIVO EN DESARROLLO - " + String(active.bundle).get_file()) + "  |  Ultimo paquete: %d zonas" % manifest.get("zones", []).size()
	for i in zones.item_count:
		if int(zones.get_item_metadata(i).id) == selected:
			select_zone(i)
			return
	if zones.item_count > 0:
		zones.select(0)
		select_zone(0)
func select_zone(i: int) -> void:
	var row: Dictionary = zones.get_item_metadata(i)
	selected = int(row.id)
	var plan := read_json(bundle.path_join("zone%03d/plan.json" % selected))
	map.overlay = null
	map.metres = float(row.size_m)
	if not plan.is_empty():
		var image := Image.load_from_file(bundle.path_join("zone%03d/overlay.png" % selected))
		if image != null: map.overlay = ImageTexture.create_from_image(image)
		if not plan.preview_points.is_empty():
			preview_point = Vector2(plan.preview_points[0].x, plan.preview_points[0].z)
		map.point = preview_point / map.metres
		var s: Dictionary = plan.summary
		detail.text = "%s | %s | %.2f km2 de cobertura candidata | Suelo y plantas altas originales conservados\nEl mapa usa los grupos originales de vegetacion. Cada zona requiere revision visual antes de darla por terminada." % [row.name, row.edition, float(s.plantable_m2) / 1000000]
	else:
		detail.text = row.name + ": no hay plan en el ultimo paquete. Preparar esta zona o toda Hibernia."
	map.exclusions = exclusions.get(str(selected), [])
	map.queue_redraw()
func pick(p: Vector2, exclude: bool) -> void:
	preview_point = p
	if exclude:
		var key := str(selected)
		if not exclusions.has(key): exclusions[key] = []
		exclusions[key].append({"x": p.x, "z": p.y, "radius": radius.value})
		map.exclusions = exclusions[key]
		status.text = "Exclusion anadida. Preparar de nuevo para incorporarla al paquete."
	else:
		status.text = "Vista previa en coordenadas locales (m): %.1f / %.1f" % [p.x, p.y]
func clear_exclusions() -> void:
	exclusions.erase(str(selected))
	map.exclusions = []
	map.queue_redraw()
	status.text = "Exclusiones manuales borradas. Preparar de nuevo para guardar."
func prepare(all_zones: bool) -> void:
	write_json(STATE.path_join("options.json"), {"density": density.value, "chunk_budget": budget.value, "max_slope": slope.value, "remove_shrubs": shrubs.button_pressed, "insects": insects.button_pressed, "wind": wind.button_pressed, "exclusions": exclusions})
	var extra := ["--options", ProjectSettings.globalize_path(STATE.path_join("options.json"))]
	if not all_zones: extra.append_array(["--zones", str(selected)])
	job(extra)
func job(extra: Array) -> void:
	if working or config.is_empty(): return
	DirAccess.remove_absolute(ProjectSettings.globalize_path(STATE.path_join("job.json")))
	var args := [ProjectSettings.globalize_path("res://enhanced/replant/planner.py"), "--source", config.source, "--state", ProjectSettings.globalize_path(STATE), "--libs", config.libs]
	args.append_array(extra)
	pid = OS.create_process(config.python, PackedStringArray(args))
	if pid < 0:
		status.text = "No se pudo iniciar el preparador. Revisar configuracion local."
		return
	working = true
	for b in controls: b.disabled = true
	status.text = "Procesando... Los originales se leen sin modificarlos."
func _process(delta: float) -> bool:
	if not working: return false
	poll += delta
	if poll < 0.25: return false
	poll = 0
	var progress := read_json(STATE.path_join("job.json"))
	if not progress.is_empty(): status.text = progress.get("message", "Procesando...")
	if progress.get("status") in ["done", "error"] or not OS.is_process_running(pid):
		working = false
		for b in controls: b.disabled = false
		if progress.is_empty() or progress.get("status") == "working": status.text = "El preparador termino sin resultado. Revisar job.json."
		reload_data()
	return false
func preview() -> void:
	var path := bundle.path_join("zone%03d/plan.json" % selected)
	if not FileAccess.file_exists(path):
		status.text = "Preparar primero esta zona."
		return
	var args := ["--path", ProjectSettings.globalize_path("res://"), "--audio-driver", "Dummy", "--script", "res://enhanced/replant/preview.gd", "--", "--bundle=" + bundle, "--zone=" + str(selected), "--x=" + str(preview_point.x), "--z=" + str(preview_point.y)]
	OS.create_process(OS.get_executable_path(), PackedStringArray(args))
	status.text = "Vista 3D abierta. A/B mantiene la misma camara y luz; espacio alterna. La instalacion original no cambia."

func prepare_resources() -> void:
	if working or bundle.is_empty(): return
	if selected != 207:
		status.text = "Preparacion de plantas: piloto en Ardee. Las demas zonas conservan sus plantas originales."
		return
	var progress:=ProjectSettings.globalize_path(STATE.path_join("job.json"))
	write_json(progress,{"status":"working","message":"Preparando plantas de Ardee fuera del juego..."})
	var result:=ProjectSettings.globalize_path(STATE.path_join("prepared_ardee.json"))
	var args:=["--headless","--render-thread","safe","--path",ProjectSettings.globalize_path("res://"),"--script","res://enhanced/replant/bake_check.gd","--","--bundle="+bundle,"--out="+result,"--status="+progress]
	pid=OS.create_process(OS.get_executable_path(),PackedStringArray(args))
	if pid<0:
		status.text="No se pudo abrir el preparador de plantas."
		return
	working=true
	for b in controls:b.disabled=true
	status.text="Preparando plantas de Ardee. No hace falta abrir el juego."
