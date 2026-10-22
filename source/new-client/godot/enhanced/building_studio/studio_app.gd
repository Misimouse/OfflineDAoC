extends Control
const Relief=preload("res://enhanced/building_studio/relief_mesh.gd")
const Regions=preload("res://enhanced/building_studio/texture_regions.gd")
const Materials=preload("res://game/nif_materials.gd")
const CATEGORIES=["Sin clasificar","Piedra","Madera","Tejado","Ventana","Puerta","Cristal","Vegetación","Mixto","Decoración"]
const MODELS=["helfshack","hlurikhut","hshop"]
var store_path="res://.enhanced-session/building_studio"
var catalog:Dictionary={}
var records:Array=[]
var groups:Array=[]
var selected=-1
var source_path=""
var source_sha=""
var edited=true
var clay=false
var mats
var model:Node3D
var world:Node3D
var camera:Camera3D
var viewport:SubViewport
var viewer:SubViewportContainer
var material_list:ItemList
var category:OptionButton
var region_category:OptionButton
var height_mode:OptionButton
var depth:SpinBox
var spacing:SpinBox
var invert:CheckBox
var preview:Control
var info:Label
var status:Label
var compare:Button
var asset_label:Label
var texture_dialog:FileDialog
var height_dialog:FileDialog
var model_dialog:FileDialog
var recipe_dialog:FileDialog
var center=Vector3.ZERO
var radius=15.0
var yaw=0.65
var pitch=0.25
var loading=false
var test_dir=""
func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--self-test="):test_dir=arg.trim_prefix("--self-test=");store_path=test_dir.path_join("state")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(store_path))
	var path=store_path.path_join("catalog.json")
	if FileAccess.file_exists(path) and test_dir.is_empty():
		var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
		if parsed is Dictionary:catalog=parsed
	build_ui()
	load_model("res://content/zones/zone207/models/helfshack.gltf")
	if not test_dir.is_empty():call_deferred("self_test")
func label(text:String,parent:Node) -> Label:
	var result=Label.new();result.text=text;parent.add_child(result);return result
func button(text:String,parent:Node,callback:Callable) -> Button:
	var result=Button.new();result.text=text;parent.add_child(result);result.pressed.connect(callback);return result
func option(items:Array,parent:Node) -> OptionButton:
	var result=OptionButton.new()
	for item in items:result.add_item(item)
	parent.add_child(result);return result
func build_ui() -> void:
	var background=ColorRect.new();background.color=Color("202731");background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);add_child(background)
	var margin=MarginContainer.new();margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left","right","top","bottom"]:margin.add_theme_constant_override("margin_"+edge,12)
	add_child(margin)
	var body=VBoxContainer.new();margin.add_child(body)
	var top=HBoxContainer.new();body.add_child(top)
	label("TALLER DE EDIFICIOS",top)
	var presets=option(["Casa del pozo · Ardee","Cabaña Lurikeen","Tienda"],top)
	presets.item_selected.connect(func(i):load_model("res://content/zones/zone207/models/"+MODELS[i]+".gltf"))
	button("Abrir modelo…",top,func():model_dialog.popup_centered_ratio(0.7))
	compare=button("Viendo: copia",top,toggle_compare)
	button("Guardar catálogo",top,save_catalog)
	button("Abrir receta…",top,func():recipe_dialog.popup_centered_ratio(0.7))
	button("Exportar copia 3D",top,export_copy)
	button("Abrir exportaciones",top,func():
		var path=ProjectSettings.globalize_path(store_path.path_join("exports"));DirAccess.make_dir_recursive_absolute(path);OS.shell_open(path))
	var columns=HBoxContainer.new();columns.size_flags_vertical=Control.SIZE_EXPAND_FILL;body.add_child(columns)
	var left=VBoxContainer.new();left.size_flags_horizontal=Control.SIZE_EXPAND_FILL;columns.add_child(left)
	label("Gira: arrastra con botón derecho · Rueda: acercar · Clic: elegir pieza",left)
	viewer=SubViewportContainer.new();viewer.stretch=true;viewer.size_flags_vertical=Control.SIZE_EXPAND_FILL;left.add_child(viewer)
	viewport=SubViewport.new();viewport.size=Vector2i(1000,800);viewport.own_world_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;viewer.add_child(viewport)
	world=Node3D.new();viewport.add_child(world)
	var environment=WorldEnvironment.new();var env=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color("293846");env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color("c4d0df");env.ambient_light_energy=0.7;environment.environment=env;world.add_child(environment)
	var sun=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-45,-35,0);sun.light_energy=1.5;sun.shadow_enabled=true;world.add_child(sun)
	camera=Camera3D.new();camera.fov=48;camera.near=0.05;camera.far=500;world.add_child(camera)
	info=label("",left);info.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	var scroll=ScrollContainer.new();scroll.custom_minimum_size.x=400;columns.add_child(scroll)
	var panel=VBoxContainer.new();panel.custom_minimum_size.x=380;panel.size_flags_horizontal=Control.SIZE_EXPAND_FILL;scroll.add_child(panel)
	label("1 · Elige un material",panel)
	material_list=ItemList.new();material_list.custom_minimum_size.y=165;panel.add_child(material_list);material_list.item_selected.connect(select_group)
	asset_label=label("",panel);asset_label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	category=option(CATEGORIES,panel);category.item_selected.connect(func(i):if not loading and selected>=0:rule()["category"]=CATEGORIES[i];material_list.set_item_text(selected,groups[selected].name+" · "+CATEGORIES[i]);save_catalog(false))
	button("Acercar al material elegido",panel,focus_selected)
	button("Cambiar imagen de color…",panel,func():texture_dialog.popup_centered_ratio(0.65))
	preview=Regions.new();panel.add_child(preview);preview.region_drawn.connect(add_region)
	label("Marca un rectángulo sobre la imagen y asígnale:",panel)
	region_category=option(CATEGORIES,panel);region_category.select(4)
	button("Borrar zonas marcadas",panel,func():if selected>=0:rule()["regions"]=[];refresh_preview();save_catalog(false))
	var clay_button=CheckBox.new();clay_button.text="Ver solo geometría, sin texturas";panel.add_child(clay_button);clay_button.toggled.connect(func(value):clay=value;refresh_comparison())
	label("2 · Relieve de geometría real",panel)
	height_mode=option(["Sin relieve","Brillo de imagen · borrador","Mapa de alturas propio"],panel)
	height_mode.item_selected.connect(func(i):if not loading and selected>=0:rule()["mode"]=i;save_catalog(false))
	button("Cargar mapa de alturas…",panel,func():height_dialog.popup_centered_ratio(0.65))
	var values=HBoxContainer.new();panel.add_child(values);label("Relieve (cm)",values);depth=SpinBox.new();depth.min_value=0;depth.max_value=6;depth.step=0.25;depth.value=2;values.add_child(depth)
	var quality=HBoxContainer.new();panel.add_child(quality);label("Detalle cada (m)",quality);spacing=SpinBox.new();spacing.min_value=0.12;spacing.max_value=0.6;spacing.step=0.02;spacing.value=0.3;quality.add_child(spacing)
	invert=CheckBox.new();invert.text="Invertir alturas";panel.add_child(invert)
	depth.value_changed.connect(func(v):if not loading and selected>=0:rule().depth_cm=v;save_catalog(false))
	spacing.value_changed.connect(func(v):if not loading and selected>=0:rule().spacing=v;save_catalog(false))
	invert.toggled.connect(func(v):if not loading and selected>=0:rule().invert=v;save_catalog(false))
	button("Generar relieve real",panel,generate_selected)
	button("Restaurar este material",panel,reset_selected)
	var note=label("El brillo solo da una aproximación. Ventanas, puertas y vidrio quedan protegidos. En materiales mixtos, marca primero las zonas de piedra.\n\nEsta versión exporta una copia estática para Godot. No instala cambios en el juego ni modifica sus colisiones.",panel);note.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;note.custom_minimum_size.x=360
	status=label("",body);status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART
	texture_dialog=make_dialog(["*.png,*.jpg,*.jpeg ; Imágenes"],func(p):set_image(p,false))
	height_dialog=make_dialog(["*.png,*.jpg,*.jpeg ; Alturas"],func(p):set_image(p,true))
	model_dialog=make_dialog(["*.gltf ; Edificio convertido DAoC"],load_model)
	recipe_dialog=make_dialog(["*.json ; Receta del taller"],load_recipe)
func make_dialog(filters:Array,callback:Callable) -> FileDialog:
	var dialog=FileDialog.new();dialog.access=FileDialog.ACCESS_FILESYSTEM;dialog.file_mode=FileDialog.FILE_MODE_OPEN_FILE;dialog.filters=PackedStringArray(filters);add_child(dialog);dialog.file_selected.connect(callback);return dialog
func suggested(name:String) -> String:
	if name in ["hstucwin2","hrockvine","hvinewalk"]:return "Mixto"
	if "window" in name:return "Ventana"
	if "door" in name:return "Puerta"
	if "glass" in name or "crystal" in name:return "Cristal"
	if "beam" in name:return "Madera"
	if "roof" in name or "straw" in name:return "Tejado"
	if "stone" in name or "rock" in name or "cobble" in name or "block" in name or "stonwal" in name:return "Piedra"
	return "Decoración"
func rule() -> Dictionary:return catalog[groups[selected].key]
func load_model(path:String) -> void:
	var document=GLTFDocument.new();var state=GLTFState.new()
	var result=document.append_from_file(path,state)
	if result!=OK:status.text="No se pudo abrir el modelo: "+error_string(result);return
	var specs:Array=state.json.get("extras",{}).get("nif_materials",[])
	if specs.is_empty():status.text="Usa un edificio convertido del cliente con sus materiales NIF.";return
	var imported=document.generate_scene(state)
	if imported==null:status.text="El modelo no contiene una escena utilizable.";return
	if model!=null:model.free()
	model=Node3D.new();model.name="Edificio";world.add_child(model)
	records.clear();groups.clear();material_list.clear();selected=-1
	source_path=path;source_sha=FileAccess.get_sha256(path)
	var zone=path.get_base_dir().get_base_dir();mats=Materials.new({"x4plus":zone.path_join("textures/x4plus"),"original":zone.path_join("textures/original")},"x4plus")
	var extras:Dictionary=state.json.get("extras",{})
	var bounds=AABB();var first=true
	for node in imported.find_children("*","MeshInstance3D",true,false):
		var lower=String(node.name).to_lower()
		if lower.begins_with("collision") or lower.begins_with("climb") or lower.begins_with("doorcol"):continue
		var transform=Transform3D.IDENTITY;var parent=node
		while parent!=imported and parent is Node3D:transform=parent.transform*transform;parent=parent.get_parent()
		if lower.begins_with("door"):
			for door in extras.get("nif_doors",[]):
				if lower.begins_with("door"+str(int(door.id))+"_"):
					var a:Array=door.closed;transform=Transform3D(Basis(Vector3(a[0],a[1],a[2]),Vector3(a[3],a[4],a[5]),Vector3(a[6],a[7],a[8])),Vector3(a[9],a[10],a[11]))
		for surface in node.mesh.get_surface_count():
			var old=node.mesh.surface_get_material(surface)
			if old==null or not old.resource_name.begins_with("nifmat:"):continue
			var spec:Dictionary=specs[int(old.resource_name.trim_prefix("nifmat:"))]
			var base:Dictionary=spec.get("slots",{}).get("base",{})
			var tex=String(base.get("tex","sin_textura"))
			var image=mats.image(tex)
			var digest=HashingContext.new();digest.start(HashingContext.HASH_SHA256)
			if image!=null:digest.update(image.get_data())
			var key=tex+":"+digest.finish().hex_encode()
			var group=-1
			for i in groups.size():
				if groups[i].key==key:group=i;break
			if group<0:
				group=groups.size();groups.append({"key":key,"name":tex,"image":image,"texture":mats.texture(tex)})
				if not catalog.has(key):catalog[key]={"category":suggested(tex),"regions":[],"mode":0,"depth_cm":2.0,"spacing":0.3,"invert":false,"color_path":"","height_path":""}
				material_list.add_item(tex+" · "+String(catalog[key].category))
			var mesh=ArrayMesh.new();mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,node.mesh.surface_get_arrays(surface))
			var material=mats.material(spec);mesh.surface_set_material(0,material)
			var piece=MeshInstance3D.new();piece.name=String(node.name)+"_"+str(surface);piece.mesh=mesh;piece.transform=transform;model.add_child(piece)
			records.append({"node":piece,"original":mesh,"edited":mesh,"material":material,"group":group,"uv":int(base.get("uv",0)),"report":{}})
			var box=transform*mesh.get_aabb();bounds=box if first else bounds.merge(box);first=false
	imported.free();center=bounds.get_center();radius=maxf(bounds.size.length()*1.2,3.0);yaw=0.65;pitch=0.2;update_camera();edited=true;compare.text="Viendo: copia"
	if not groups.is_empty():material_list.select(0);select_group(0)
	for i in groups.size():
		apply_color(i)
		if int(catalog[groups[i].key].get("mode",0))>0:select_group(i);generate_selected()
	if not groups.is_empty():material_list.select(0);select_group(0)
	status.text="Edificio completo cargado. Las categorías iniciales son sugerencias por nombre; puedes corregirlas.";update_stats()
func select_group(index:int) -> void:
	selected=index;material_list.ensure_current_is_visible();loading=true;var data=rule();category.select(maxi(CATEGORIES.find(data.category),0));height_mode.select(int(data.get("mode",0)));depth.value=float(data.get("depth_cm",2));spacing.value=float(data.get("spacing",0.3));invert.button_pressed=bool(data.get("invert",false));loading=false
	asset_label.text=groups[index].name+" · categoría recordada en el catálogo";refresh_preview()
func refresh_preview() -> void:
	preview.picture=groups[selected].texture
	var p=String(rule().get("color_path",""))
	if FileAccess.file_exists(p):preview.picture=ImageTexture.create_from_image(Image.load_from_file(p))
	preview.regions=rule().get("regions",[]);preview.selection=Rect2();preview.queue_redraw()
func add_region(rect:Rect2) -> void:
	if selected<0:return
	rule().regions.append({"rect":[rect.position.x,rect.position.y,rect.size.x,rect.size.y],"category":CATEGORIES[region_category.selected]});refresh_preview();save_catalog(false)
	status.text="Zona guardada: "+CATEGORIES[region_category.selected]+". Las zonas de ventana no reciben relieve."
func set_image(path:String,is_height:bool) -> void:
	if selected<0:return
	var image=Image.load_from_file(path)
	if image==null or image.is_empty():status.text="La imagen no se pudo leer.";return
	# Keep private copies so recipes survive moving the user's source images.
	var dir=store_path.path_join("images");DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var target=dir.path_join(FileAccess.get_sha256(path)+".png");image.save_png(target)
	rule()["height_path" if is_height else "color_path"]=ProjectSettings.globalize_path(target)
	if is_height:rule().mode=2;height_mode.select(2)
	else:apply_color(selected);refresh_preview()
	save_catalog(false);status.text="Imagen copiada al taller. El archivo original se conserva."
func apply_color(index:int) -> void:
	var data:Dictionary=catalog[groups[index].key];var path=String(data.get("color_path",""));var texture:Texture2D=null
	if FileAccess.file_exists(path):
		var color_image=Image.load_from_file(path)
		if color_image!=null:color_image.generate_mipmaps();texture=ImageTexture.create_from_image(color_image)
	for record in records:
		if record.group!=index:continue
		var material=record.material.duplicate()
		if texture!=null:material.set_shader_parameter("base_tex",texture)
		record["changed_material"]=material
		record.node.material_override=material if edited else record.material
func generate_selected() -> void:
	if selected<0:return
	var data=rule();data.depth_cm=depth.value;data.spacing=spacing.value;data.invert=invert.button_pressed;data.mode=height_mode.selected
	if data.mode==0:
		for record in records:
			if record.group==selected:record.edited=record.original;record.report={};record["applied_rule"]={}
		refresh_comparison();save_catalog(false);update_stats();status.text="Relieve retirado de este material; el color se conserva.";return
	if data.category not in ["Piedra","Madera","Tejado","Mixto"]:status.text="Este material está protegido. Solo se modifican piedra, madera, tejado o zonas marcadas de un material mixto.";return
	if data.category=="Mixto" and data.regions.is_empty():status.text="Marca primero las zonas que son piedra, madera o tejado.";return
	var image:Image=groups[selected].image
	if data.mode==2:
		image=Image.load_from_file(String(data.get("height_path","")))
	elif FileAccess.file_exists(String(data.get("color_path",""))):image=Image.load_from_file(data.color_path)
	if image==null:status.text="Falta una imagen utilizable para las alturas.";return
	var pending:Array=[];var total=0
	for record in records:
		if record.group!=selected:continue
		if record.uv!=0:status.text="Esta textura utiliza otro canal UV; se conserva para evitar un relieve mal colocado.";return
		var generator=Relief.new();var mesh=generator.generate(record.original,image,data)
		if mesh==null:status.text=generator.error;return
		total+=int(generator.report.triangles)
		if total>180000:status.text="Demasiado detalle para este material. Aumenta la separación.";return
		pending.append({"record":record,"mesh":mesh,"report":generator.report})
	for item in pending:item.record.edited=item.mesh;item.record.report=item.report;item.record["applied_rule"]=data.duplicate(true)
	edited=true;refresh_comparison();save_catalog(false);update_stats();status.text="Relieve real generado en "+str(pending.size())+" piezas. Compara con el original antes de exportar."
func reset_selected() -> void:
	if selected<0:return
	for record in records:
		if record.group==selected:record.edited=record.original;record.report={};record["applied_rule"]={}
	rule().color_path="";rule().height_path="";rule().mode=0;height_mode.select(0);apply_color(selected);refresh_preview();refresh_comparison();save_catalog(false);update_stats();status.text="Material restaurado. La clasificación y las zonas marcadas se conservan."
func toggle_compare() -> void:edited=not edited;refresh_comparison();update_stats()
func refresh_comparison() -> void:
	compare.text="Viendo: copia" if edited else "Viendo: original"
	for record in records:record.node.mesh=record.edited if edited else record.original;record.node.material_override=record.get("changed_material",record.material) if edited else record.material
	if clay:
		var plain=StandardMaterial3D.new();plain.albedo_color=Color("b6bdc1");plain.roughness=0.9
		for record in records:record.node.material_override=plain
func focus_selected() -> void:
	if selected<0:return
	var box=AABB();var first=true
	for record in records:
		if record.group==selected:
			var piece_box=record.node.transform*record.edited.get_aabb();box=piece_box if first else box.merge(piece_box);first=false
	center=box.get_center();radius=maxf(box.size.length()*0.9,1.2);update_camera()
func update_stats() -> void:
	var before=0;var after=0
	for record in records:before+=record.original.surface_get_array_index_len(0)/3;after+=record.edited.surface_get_array_index_len(0)/3
	info.text="%s · Original: %s triángulos · Copia: %s triángulos\nLos archivos del cliente se conservan intactos." %[source_path.get_file(),before,after]
func save_catalog(announce:bool=true) -> void:
	var path=store_path.path_join("catalog.json");var temp=path+".tmp";var file=FileAccess.open(temp,FileAccess.WRITE)
	if file==null:status.text="No se pudo guardar el catálogo.";return
	file.store_string(JSON.stringify(catalog,"\t"));file.close()
	var result=DirAccess.rename_absolute(ProjectSettings.globalize_path(temp),ProjectSettings.globalize_path(path))
	if announce:status.text="Catálogo guardado." if result==OK else "No se pudo sustituir el catálogo: "+error_string(result)
func load_recipe(path:String) -> void:
	var recipe=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not recipe is Dictionary or recipe.get("version",0)!=1 or not recipe.has("source") or not recipe.get("catalog",{}) is Dictionary:
		status.text="Este archivo no es una receta de este taller.";return
	var source=String(recipe.source)
	if not FileAccess.file_exists(source) or FileAccess.get_sha256(source)!=String(recipe.get("source_sha256","")):
		status.text="No se encuentra el mismo edificio original con el que se creó la receta.";return
	for key in recipe.catalog:
		catalog[key]=recipe.catalog[key].duplicate(true);catalog[key]["mode"]=0
	# Recreate the geometry that was actually exported, rather than pending UI settings.
	for piece in recipe.get("pieces",[]):
		var applied:Dictionary=piece.get("applied_rule",{})
		if catalog.has(piece.material) and not applied.is_empty():
			for key in ["mode","spacing","depth_cm","invert","regions","height_path"]:
				if applied.has(key):catalog[piece.material][key]=applied[key]
	load_model(source);save_catalog(false);status.text="Receta recuperada. Puedes seguir modificando la copia."
func export_copy() -> String:
	if FileAccess.get_sha256(source_path)!=source_sha:status.text="El modelo de origen cambió. Vuelve a abrirlo antes de exportar.";return ""
	var folder=store_path.path_join("exports").path_join(source_path.get_file().get_basename()+"_"+Time.get_datetime_string_from_system().replace(":","-")+"_"+str(Time.get_ticks_msec()))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(folder))
	var copy=Node3D.new();copy.name="Edificio_copia_estatica"
	for record in records:
		var part=MeshInstance3D.new();part.name=record.node.name;part.mesh=record.edited;part.material_override=record.get("changed_material",record.material);part.transform=record.node.transform;copy.add_child(part);part.owner=copy
	var packed=PackedScene.new();packed.pack(copy)
	var result=ResourceSaver.save(packed,folder.path_join("edificio.scn"),ResourceSaver.FLAG_COMPRESS|ResourceSaver.FLAG_BUNDLE_RESOURCES);copy.free()
	if result!=OK:status.text="No se pudo exportar: "+error_string(result);return ""
	var recipe={"version":1,"source":source_path,"source_sha256":source_sha,"static_copy":true,"gameplay_collisions_included":false,"catalog":{},"pieces":[]}
	for group in groups:recipe.catalog[group.key]=catalog[group.key]
	for record in records:recipe.pieces.append({"name":String(record.node.name),"material":groups[record.group].key,"relief":record.report,"applied_rule":record.get("applied_rule",{})})
	var file=FileAccess.open(folder.path_join("receta.json"),FileAccess.WRITE);file.store_string(JSON.stringify(recipe,"\t"));file.close();save_catalog(false)
	status.text="Copia exportada: "+folder.get_file()+" · Usa Abrir exportaciones para verla."
	return ProjectSettings.globalize_path(folder)
func update_camera() -> void:
	camera.position=center+Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*radius;camera.look_at(center)
func _input(event:InputEvent) -> void:
	if viewer==null or not viewer.get_global_rect().has_point(get_global_mouse_position()):return
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):yaw-=event.relative.x*0.008;pitch=clampf(pitch+event.relative.y*0.008,-0.6,1.35);update_camera()
	if event is InputEventMouseButton and event.pressed:
		if event.button_index==MOUSE_BUTTON_WHEEL_UP:radius=maxf(radius*0.88,0.5);update_camera()
		elif event.button_index==MOUSE_BUTTON_WHEEL_DOWN:radius=minf(radius*1.12,250);update_camera()
		elif event.button_index==MOUSE_BUTTON_LEFT:pick_piece(viewer.get_local_mouse_position())
func pick_piece(point:Vector2) -> void:
	var origin=camera.project_ray_origin(point);var direction=camera.project_ray_normal(point);var closest=INF;var group=-1
	for record in records:
		var transform:Transform3D=record.node.transform;var inverse=transform.affine_inverse();var local_origin=inverse*origin;var local_dir=(inverse.basis*direction).normalized()
		var arrays=record.original.surface_get_arrays(0);var points:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var indices:PackedInt32Array=arrays[Mesh.ARRAY_INDEX]
		for i in range(0,indices.size(),3):
			var hit=Geometry3D.ray_intersects_triangle(local_origin,local_dir,points[indices[i]],points[indices[i+1]],points[indices[i+2]])
			if hit!=null:
				var distance=origin.distance_squared_to(transform*hit)
				if distance<closest:closest=distance;group=record.group
	if group>=0:material_list.select(group);select_group(group)
func self_test() -> void:
	var checks:Array=[]
	for name in MODELS:
		load_model("res://content/zones/zone207/models/"+name+".gltf");checks.append({"model":name,"pieces":records.size(),"materials":groups.size(),"loaded":not records.is_empty()})
	load_model("res://content/zones/zone207/models/helfshack.gltf")
	for i in groups.size():
		if groups[i].name=="hlimestone":select_group(i);material_list.select(i);break
	height_mode.select(1);depth.value=3;spacing.value=0.3;generate_selected()
	var displaced=false;var grown=false
	for record in records:
		if record.group==selected and not record.report.is_empty():displaced=displaced or record.report.maximum_displacement_m>0;grown=grown or record.report.triangles>record.report.original_triangles
	checks.append({"real_displacement":displaced,"more_triangles":grown,"source_hash_unchanged":FileAccess.get_sha256(source_path)==source_sha})
	toggle_compare();var exact=true
	for record in records:exact=exact and record.node.mesh==record.original
	checks.append({"original_comparison_exact":exact});toggle_compare()
	add_region(Rect2(0.1,0.1,0.2,0.2));save_catalog(false)
	var saved=JSON.parse_string(FileAccess.get_file_as_string(store_path.path_join("catalog.json")));checks.append({"catalog_reloaded":saved is Dictionary and saved[groups[selected].key].regions.size()==1})
	var sample=Image.create(16,16,false,Image.FORMAT_RGBA8);sample.fill(Color(0.4,0.35,0.3,1))
	var sample_path=test_dir.path_join("color_prueba.png");sample.save_png(sample_path);set_image(sample_path,false)
	var color_changed=false;var originals_untouched=true
	for record in records:
		if record.group==selected:
			color_changed=color_changed or record.changed_material.get_shader_parameter("base_tex")!=record.material.get_shader_parameter("base_tex")
			originals_untouched=originals_untouched and record.original.surface_get_material(0)==record.material
	checks.append({"replacement_is_private":color_changed and originals_untouched})
	var folder=export_copy();var exported=load(folder.path_join("edificio.scn")) if not folder.is_empty() else null
	var persisted=false
	if exported is PackedScene:
		var restored=exported.instantiate()
		for child in restored.get_children():
			for record in records:
				if child.name==record.node.name and not record.report.is_empty():persisted=persisted or child.mesh.surface_get_array_len(0)==record.edited.surface_get_array_len(0)
		restored.free()
	checks.append({"export_reload_geometry":persisted,"export":folder})
	# A protected category must leave the currently generated mesh intact.
	var previous_category=rule().category;var before=[]
	for record in records:before.append(record.edited)
	rule().category="Ventana";generate_selected();var protected=true
	for i in records.size():protected=protected and records[i].edited==before[i]
	rule().category=previous_category;rule().regions=[];save_catalog(false)
	load_model(source_path)
	var recovered=false
	for record in records:recovered=recovered or not record.report.is_empty()
	checks.append({"protected_material_unchanged":protected,"saved_relief_recovered":recovered})
	load_recipe(folder.path_join("receta.json"))
	var recipe_ok=source_path.ends_with("helfshack.gltf")
	selected=-1;pick_piece(Vector2(viewport.size)*0.5)
	checks.append({"recipe_opens":recipe_ok,"click_selects_piece":selected>=0})
	await get_tree().process_frame;await get_tree().process_frame
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(test_dir.path_join("taller.png"))
	var report=FileAccess.open(test_dir.path_join("checks.json"),FileAccess.WRITE);report.store_string(JSON.stringify(checks,"\t"));report.close()
	print("STUDIO_CHECKS ",JSON.stringify(checks));var passed=true
	for check in checks:
		for key in check:
			if check[key] is bool and not check[key]:passed=false
	get_tree().quit(0 if passed else 1)
