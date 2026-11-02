extends SceneTree
var texture_cache:Dictionary={}
var image_cache:Dictionary={}
var export_folder:String=""
var material_number:int=0
func _initialize()->void:run.call_deferred()
func merge_meshes(holder:Node3D)->void:
	var groups:Array=[]
	for mesh in holder.find_children("*","MeshInstance3D",true,false):
		if mesh.mesh==null or mesh.skin==null:continue
		var found:bool=false
		for group in groups:
			var first:MeshInstance3D=group[0]
			if mesh.get_node_or_null(mesh.skeleton)!=first.get_node_or_null(first.skeleton):continue
			if mesh.get_parent()!=first.get_parent() or not mesh.transform.is_equal_approx(first.transform):continue
			if mesh.skin.get_bind_count()!=first.skin.get_bind_count():continue
			var same:bool=true
			for bind in mesh.skin.get_bind_count():
				if mesh.skin.get_bind_bone(bind)!=first.skin.get_bind_bone(bind) or mesh.skin.get_bind_name(bind)!=first.skin.get_bind_name(bind) or not mesh.skin.get_bind_pose(bind).is_equal_approx(first.skin.get_bind_pose(bind)):same=false;break
			if same:group.append(mesh);found=true;break
		if not found:groups.append([mesh])
	for group in groups:
		if group.size()<2:continue
		var first:MeshInstance3D=group[0]
		var combined:=ArrayMesh.new()
		for mesh in group:
			for surface in mesh.mesh.get_surface_count():
				combined.add_surface_from_arrays(mesh.mesh.surface_get_primitive_type(surface),mesh.mesh.surface_get_arrays(surface))
				combined.surface_set_material(combined.get_surface_count()-1,mesh.get_active_material(surface))
		var result:=MeshInstance3D.new();result.name="Bridge_Merged_Character";result.mesh=combined
		result.skin=first.skin;result.skeleton=first.skeleton;result.transform=first.transform
		first.get_parent().add_child(result)
		for mesh in group:mesh.free()
func standard(original:Material)->Material:
	if not original is ShaderMaterial:return original
	var m:=StandardMaterial3D.new();m.roughness=.9
	var texture:Texture2D=original.get_shader_parameter("albedo_tex")
	if texture==null:texture=original.get_shader_parameter("base_tex")
	if texture!=null:
		var key:=texture.get_instance_id()
		if not texture_cache.has(key):
			var image:Image=load("res://game/nif_materials.gd").source_image(texture)
			if image!=null:texture_cache[key]=ImageTexture.create_from_image(image);image_cache[key]=image
		if texture_cache.has(key):m.albedo_texture=texture_cache[key]
	var tint=original.get_shader_parameter("tint")
	if tint is Color:m.albedo_color=tint
	m.cull_mode=BaseMaterial3D.CULL_DISABLED
	if "discard" in original.shader.code:m.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
	var detail:Dictionary={"color":[m.albedo_color.r,m.albedo_color.g,m.albedo_color.b,m.albedo_color.a]}
	if texture!=null and texture_cache.has(texture.get_instance_id()):
		var png:String=export_folder.path_join("texture_"+str(material_number)+".png")
		image_cache[texture.get_instance_id()].save_png(png)
		detail["texture"]=png
	material_number+=1
	m.set_meta("bridge_material",detail)
	return m
func run()->void:
	var base:String=get_script().resource_path.get_base_dir().path_join("../SourceConnachtModels_v01")
	export_folder=base
	var tasks=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("tasks.json")))
	var results:Array=[];var limit:int=tasks.size();var only_ids:PackedStringArray=[]
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--limit="):limit=int(arg.trim_prefix("--limit="))
		if arg.begins_with("--only-ids="):only_ids=arg.trim_prefix("--only-ids=").split(",")
	for task in tasks.slice(0,limit):
		if not only_ids.is_empty() and String(task.id) not in only_ids:continue
		print("BRIDGE_MODEL_START ",task.id)
		var holder:=Node3D.new();root.add_child(holder);holder.name="DAoC_Model_"+task.id
		var info:Dictionary=task.info;var figure:Node3D
		if info.get("race",null)!=null:
			var factory=load("res://game/fig3_figure.gd")
			var f=factory.new();holder.add_child(f);assert(f.load_figure(String(info.race)))
			f.apply(factory.npc_look("bridge-model-"+task.id,f.meta))
			var parts:Dictionary={};var tints:Dictionary={}
			for row in task.equipment:
				if int(row.slot) in [22,23,25,27,28]:
					var item:Dictionary=factory.armor_parts(int(row.model),String(info.race).ends_with("_f"));parts.merge(item,true)
					for name in item:tints[name]=factory.dye(int(row.get("color",0)))
			f.set_armor(parts,tints);figure=f
		else:
			var source=load("res://game/nif_scene.gd").new();holder.add_child(source);assert(source.load_scene(String(info.gltf)));figure=source
		for mesh in holder.find_children("*","MeshInstance3D",true,false):
			if not is_instance_valid(mesh):continue
			if not mesh.is_visible_in_tree():mesh.free();continue
			if mesh.mesh==null:continue
			var converted:Array=[]
			for surface in mesh.mesh.get_surface_count():converted.append(standard(mesh.get_active_material(surface)))
			mesh.material_override=null
			for surface in mesh.mesh.get_surface_count():mesh.set_surface_override_material(surface,converted[surface])
		merge_meshes(holder)
		for player in holder.find_children("*","AnimationPlayer",true,false):
			for library_name in player.get_animation_library_list():
				var library=player.get_animation_library(library_name).duplicate()
				for clip in library.get_animation_list():
					if false:library.remove_animation(clip)
				player.remove_animation_library(library_name);player.add_animation_library(library_name,library)
		var document:=GLTFDocument.new();var state:=GLTFState.new()
		assert(document.append_from_scene(holder,state)==OK)
		var path:=base.path_join("model_"+task.id+".glb")
		assert(document.write_to_filesystem(state,path)==OK)
		var materials:Array=[]
		for material in state.get_materials():materials.append(material.get_meta("bridge_material",{}))
		var sidecar:=FileAccess.open(path+".materials.json",FileAccess.WRITE);sidecar.store_string(JSON.stringify(materials));sidecar.close()
		results.append({"id":task.id,"file":path,"scale":1.0 if info.has("race") else float(info.get("scale",1.0)),"name":info.get("name","")})
		print("BRIDGE_MODEL_EXPORTED ",task.id)
		holder.free();await process_frame
	var file:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);file.store_string(JSON.stringify(results,"  "));file.close()
	print("BRIDGE_MODEL_EXPORT_PASS count=",results.size());quit()
