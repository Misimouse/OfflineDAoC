extends Node
## Optional material overrides only. Never mutates source terrain mesh/material, collision, or masks.
const STATE:="res://.enhanced-session/paths_pbr/"
var override_manifest:=""
var manifest:Dictionary={}
var bindings:Array=[]
var mode:=2
var bound_zone
var label:Label
var textures:Dictionary={}
var error:=""
var was_blend:=true

func configure() -> bool:
	var path:=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(STATE+"active.json"):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(STATE+"active.json"))
		if not pointer is Dictionary or pointer.get("disabled",true):return false
		path=String(pointer.get("manifest",""))
		if FileAccess.get_sha256(path)!=pointer.get("sha256",""):return false
	if not FileAccess.file_exists(path):return false
	var parsed=JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:return false
	manifest=parsed
	if int(manifest.get("zone",-1))!=207:return false
	if FileAccess.get_sha256("res://game/terrain.gdshader")!=manifest.get("original_shader_sha256",""):return false
	var base:="res://content/zones/zone207/"
	if FileAccess.get_sha256(base+"zone.json")!=manifest.get("zone_sha256",""):return false
	if manifest.get("maps",[]).size()!=6:return false
	for spec in manifest.maps:
		if FileAccess.get_sha256(String(spec.path))!=spec.get("sha256",""):return false
	for file in manifest.installed_colour_hashes:
		if FileAccess.get_sha256(base+"textures/x4plus/"+file)!=manifest.installed_colour_hashes[file]:return false
	for file in manifest.weight_hashes:
		if FileAccess.get_sha256(base+file)!=manifest.weight_hashes[file]:return false
	return true

func attach(region) -> void:
	if region==null or not configure():return
	region.zone_added.connect(apply_zone)
	region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():apply_zone(zone)
	if not bindings.is_empty():
		var layer:=CanvasLayer.new()
		add_child(layer)
		label=Label.new()
		label.position=Vector2(20,110)
		label.add_theme_color_override("font_shadow_color",Color.BLACK)
		label.add_theme_constant_override("shadow_outline_size",4)
		layer.add_child(label)
		set_mode(mode)

func apply_zone(zone) -> bool:
	if int(zone.info.get("id",-1))!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	if zone.terrain_set!="blend":return false
	var targets:Array=[]
	for key in manifest.patches:
		var parts=String(key).split("_")
		var mesh=zone.get_node_or_null("Terrain_%s_%s"%[parts[0],parts[1]])
		if not mesh is MeshInstance3D or mesh.material_override!=null:return false
		var original:ShaderMaterial=mesh.mesh.surface_get_material(0)
		if not original.get_shader_parameter("use_splat"):return false
		var layers:Array=zone.info.ground_splat.patches[key].layers
		var soil_index:=-1
		var gravel_index:=-1
		for i in range(1,layers.size()):
			if layers[i].tex=="h_soil":soil_index=i-1
			if layers[i].tex=="h_tinypebbles":gravel_index=i-1
		if (soil_index<0 or gravel_index<0) and manifest.get("scope", "")!="whole-zone":return false
		targets.append({"mesh":mesh,"original":original,"soil":soil_index,"gravel":gravel_index})
	if targets.size()!=manifest.patches.size():return false
	if textures.is_empty():
		for spec in manifest.maps:
			var path=String(spec.path)
			if FileAccess.file_exists("res://.enhanced-session/godot_tools/active.json"):
				path=load("res://enhanced/godot_tools/forge_overrides.gd").new().resolve_file(path)
			var image:=Image.load_from_file(path)
			if image==null:return false
			image.generate_mipmaps()
			textures[String(spec.asset)+"/"+String(spec.kind)]=ImageTexture.create_from_image(image)
	var shader=load("res://enhanced/terrain/paths_pbr.gdshader")
	for target in targets:
		var mat:=ShaderMaterial.new()
		mat.shader=shader
		for param in ["tile_tex","base_tex","base_tiles","layer_tex","layer_tiles","layer_tileable","layer_count","weights0","weights1","patch_index","patches","far_fade_m"]:
			mat.set_shader_parameter(param,target.original.get_shader_parameter(param))
		mat.set_shader_parameter("soil_index",target.soil)
		mat.set_shader_parameter("gravel_index",target.gravel)
		mat.set_shader_parameter("normal_strength",float(manifest.normal_strength))
		mat.set_shader_parameter("normal_fade_m",float(manifest.normal_fade_m))
		for kind in ["soil","gravel"]:
			var spec:Dictionary=manifest.materials[kind]
			mat.set_shader_parameter(kind+"_tiles",float(zone.info.size_m)/float(spec.repeat_m))
			for pair in [["colour","Diffuse"],["normal","nor_gl"],["roughness","Rough"]]:
				mat.set_shader_parameter(kind+"_"+pair[0],textures[String(spec.asset)+"/"+pair[1]])
		target["replacement"]=mat
	bindings=targets
	bound_zone=zone
	set_mode(mode)
	print("PATHS_PBR_APPLIED zone=207 patches=",bindings.size()," material_overrides=",bindings.size()," mode=",mode," physics_unchanged=true")
	return true

func set_mode(value:int) -> void:
	mode=clampi(value,0,2)
	for binding in bindings:
		if not is_instance_valid(binding.mesh):continue
		binding.replacement.set_shader_parameter("trial_mode",mode)
		binding.mesh.material_override=null if mode==0 or not was_blend else binding.replacement
	if is_instance_valid(label):label.text="Caminos: %s | Ctrl+F10: comparar"%[["original","color nuevo","material completo"][mode]]

func restore() -> void:
	var choice:=mode
	set_mode(0)
	bindings.clear()
	bound_zone=null
	mode=choice

func _process(_delta:float) -> void:
	if not is_instance_valid(bound_zone):return
	var blend:bool=bound_zone.terrain_set=="blend"
	if blend!=was_blend:
		was_blend=blend
		set_mode(mode)

func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.keycode==KEY_F10 and not bindings.is_empty():
		set_mode((mode+1)%3)
		get_viewport().set_input_as_handled()

func _exit_tree() -> void:
	restore()
