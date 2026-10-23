extends Node
## Local material pilot: source distribution, terrain geometry and physics remain intact.
const STATE:="res://.enhanced-session/ground_patterns/"
var override_manifest:=""
var manifest:Dictionary={}
var bindings:Array=[]
var bound_zone
var legacy
var enabled:=true
var was_blend:=true
var label:Label
var resources:Dictionary={}
func configure() -> bool:
	var path:=override_manifest
	if path.is_empty():
		if not FileAccess.file_exists(STATE+"active.json"):return false
		var pointer=JSON.parse_string(FileAccess.get_file_as_string(STATE+"active.json"))
		if pointer.get("disabled",true) or FileAccess.get_sha256(pointer.manifest)!=pointer.sha256:return false
		path=pointer.manifest
	manifest=JSON.parse_string(FileAccess.get_file_as_string(path))
	if manifest.get("zone",-1)!=207 or manifest.get("patches",[]).size()!=4:return false
	if FileAccess.get_sha256("res://content/zones/zone207/zone.json")!=manifest.zone_sha256:return false
	if FileAccess.get_sha256("res://game/terrain.gdshader")!=manifest.original_shader_sha256:return false
	if FileAccess.get_sha256(manifest.paths_manifest)!=manifest.paths_manifest_sha256:return false
	if FileAccess.get_sha256("res://.enhanced-session/paths_pbr/active.json")!=manifest.paths_active_sha256:return false
	for item in manifest.files:
		if FileAccess.get_sha256(item.path)!=item.sha256:return false
	for file in manifest.weight_hashes:
		if FileAccess.get_sha256("res://content/zones/zone207/"+String(file))!=manifest.weight_hashes[file]:return false
	return true
func attach(region) -> bool:
	if region==null or not configure():return false
	legacy=load("res://enhanced/terrain/paths_pbr.gd").new();legacy.override_manifest=manifest.paths_manifest
	if not legacy.configure():legacy.free();legacy=null;return false
	add_child(legacy);legacy.set_process(false);legacy.set_process_input(false)
	region.zone_added.connect(apply_zone);region.zone_removing.connect(func(zone):
		if zone==bound_zone:restore())
	for zone in region.zones.values():
		if int(zone.info.id)==207 and not apply_zone(zone):return false
	var layer:=CanvasLayer.new();add_child(layer);label=Label.new();label.position=Vector2(20,110);label.add_theme_color_override("font_shadow_color",Color.BLACK);label.add_theme_constant_override("shadow_outline_size",4);layer.add_child(label);update_label();return true
func texture(path:String) -> ImageTexture:
	if resources.has(path):return resources[path]
	var image:=Image.load_from_file(path);assert(image!=null);image.generate_mipmaps();var result:=ImageTexture.create_from_image(image);resources[path]=result;return result
func atlas(path:String) -> ImageTexture:
	if resources.has(path):return resources[path]
	var image:=Image.create_from_data(manifest.atlas_size,manifest.atlas_size,false,Image.FORMAT_RGBAH if manifest.get("atlas_format","")=="rgba16f" else Image.FORMAT_RGBA8,FileAccess.get_file_as_bytes(path));assert(image!=null);image.generate_mipmaps();var result:=ImageTexture.create_from_image(image);resources[path]=result;return result
func apply_zone(zone) -> bool:
	if int(zone.info.id)!=207:return false
	if is_instance_valid(bound_zone):return bound_zone==zone
	if not legacy.apply_zone(zone):return false
	var shader=load(manifest.get("shader_path","res://enhanced/terrain/ground_patterns.gdshader"))
	for baseline in legacy.bindings:
		var mat:=ShaderMaterial.new();mat.shader=shader
		for key in ["tile_tex","base_tex","base_tiles","layer_tex","layer_tiles","layer_tileable","layer_count","weights0","weights1","patch_index","patches","far_fade_m","soil_index","gravel_index","soil_colour","soil_normal","soil_roughness","gravel_colour","gravel_normal","gravel_roughness","soil_tiles","gravel_tiles","normal_strength","normal_fade_m"]:mat.set_shader_parameter(key,baseline.replacement.get_shader_parameter(key))
		mat.set_shader_parameter("atlas0",atlas(manifest.atlas_paths[0]));mat.set_shader_parameter("atlas1",atlas(manifest.atlas_paths[1]))
		for name in ["grass","scrub","craggy"]:mat.set_shader_parameter(name+"_new",texture(manifest.texture_paths[name]))
		mat.set_shader_parameter("clover_tex",zone.materials.texture("clover_whiteflowers"));mat.set_shader_parameter("rock_tex",zone.materials.texture("rock4"));mat.set_shader_parameter("regional_tex",zone.materials.texture("connacht"))
		if manifest.has("regional_mean"):mat.set_shader_parameter("regional_mean",Vector3(manifest.regional_mean[0],manifest.regional_mean[1],manifest.regional_mean[2]))
		mat.set_shader_parameter("pilot_bounds",Vector4(manifest.pilot_bounds[0],manifest.pilot_bounds[1],manifest.pilot_bounds[2],manifest.pilot_bounds[3]));mat.set_shader_parameter("feather_metres",manifest.feather_metres)
		bindings.append({"mesh":baseline.mesh,"baseline":baseline.replacement,"replacement":mat})
	if bindings.size()!=4:restore();return false
	bound_zone=zone;was_blend=true;set_enabled(enabled);print("GROUND_PATTERNS_APPLIED patches=4 distribution=source geometry=unchanged");return true
func update_label() -> void:
	if is_instance_valid(label):label.text="Terreno: %s | Ctrl+F10: comparar"%["patrones Ardee y laderas" if enabled else "suelo anterior"]
func set_enabled(value:bool) -> void:
	enabled=value
	for binding in bindings:
		if is_instance_valid(binding.mesh):binding.mesh.material_override=(binding.replacement if value else binding.baseline) if was_blend else null
	update_label()
func _process(_delta:float) -> void:
	if not is_instance_valid(bound_zone):return
	var blend:bool=bound_zone.terrain_set=="blend"
	if blend!=was_blend:was_blend=blend;set_enabled(enabled)
func _input(event:InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.ctrl_pressed and event.keycode==KEY_F10 and not bindings.is_empty():set_enabled(not enabled);get_viewport().set_input_as_handled()
func image_files() -> Array:
	var result:Array=[]
	for name in ["grass","scrub","craggy"]:result.append(manifest.texture_paths[name])
	for item in legacy.manifest.maps:result.append(item.path)
	result.append_array(manifest.get("retained_color_paths",[]))
	return result
func restore() -> void:
	for binding in bindings:
		if is_instance_valid(binding.mesh):binding.mesh.material_override=binding.baseline
	bindings.clear()
	if is_instance_valid(legacy):legacy.restore()
	bound_zone=null;was_blend=true
func _exit_tree() -> void:restore()
