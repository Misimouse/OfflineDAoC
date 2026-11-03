extends "export_models.gd"
## Preserve each original clothing variant as a named material section.
## This exports new assets; it never edits the source figure or existing UE assets.
func run()->void:
	var base:String=get_script().resource_path.get_base_dir().path_join("../SourceArmour")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--output="):base=arg.trim_prefix("--output=")
	DirAccess.make_dir_recursive_absolute(base)
	var races:Array=["cel_m"]
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--races="):races=Array(arg.trim_prefix("--races=").split(","))
	var results:Array=[]
	if "--append" in OS.get_cmdline_user_args() and FileAccess.file_exists(base.path_join("exported.json")):
		var previous=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("exported.json")))
		if previous is Array:results=previous
	for race in races:
		export_folder=base.path_join(race);DirAccess.make_dir_recursive_absolute(export_folder)
		material_number=0
		var holder:=Node3D.new();root.add_child(holder);holder.name="Armor_"+race
		var factory=load("res://game/fig3_figure.gd")
		var f=factory.new();holder.add_child(f);assert(f.load_figure(race))
		var original_ids:Dictionary={"cel_m":"1984","cel_f":"310","elf_m":"382","elf_f":"388","fir_m":"352","fir_f":"1983","lur_m":"318","lur_f":"378","syl_m":"700","syl_f":"708"}
		f.apply(factory.npc_look("bridge-model-"+String(original_ids.get(race,race)),f.meta))
		var sections:Array=[]
		for mesh in holder.find_children("*","MeshInstance3D",true,false):
			var part:=String(mesh.name).get_slice("__",0)
			var slot:=part.get_slice("_v",0)
			var modular:bool=slot in ["body","lbody","legs","boots","arms","gloves"]
			if not modular and not mesh.is_visible_in_tree():mesh.free();continue
			if mesh.mesh==null:continue
			mesh.visible=true
			var variant:=int(part.get_slice("_v",1)) if part.contains("_v") else int(f.meta.get("clothes",{}).get(slot,{}).get("variant",1))
			for surface in mesh.mesh.get_surface_count():
				var material:Material=standard(mesh.get_active_material(surface)).duplicate()
				material.resource_name="Armor_"+part+"_"+str(sections.size())
				mesh.set_surface_override_material(surface,material)
				sections.append({"material":material.resource_name,"part":part,"slot":slot,"variant":variant,"modular":modular,"default_visible":not modular or variant==int(f.meta.get("clothes",{}).get(slot,{}).get("variant",1))})
			mesh.material_override=null
		merge_meshes(holder)
		for player in holder.find_children("*","AnimationPlayer",true,false):
			for name in player.get_animation_library_list():
				var library=player.get_animation_library(name).duplicate()
				for clip in library.get_animation_list():
					if String(clip) not in ["RESET","idle"]:library.remove_animation(clip)
				player.remove_animation_library(name);player.add_animation_library(name,library)
		var doc:=GLTFDocument.new();var state:=GLTFState.new()
		assert(doc.append_from_scene(holder,state)==OK)
		var path:=export_folder.path_join("armor_"+race+".glb")
		assert(doc.write_to_filesystem(state,path)==OK)
		var materials:Array=[]
		for material in state.get_materials():materials.append({"name":material.resource_name,"detail":material.get_meta("bridge_material",{})})
		results=results.filter(func(row):return String(row.get("race",""))!=String(race))
		results.append({"race":race,"file":path,"sections":sections,"materials":materials,"clothes":f.meta.get("clothes",{}),"variants":f.meta.get("variants",{})})
		holder.free();await process_frame
	var file:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);file.store_string(JSON.stringify(results,"  "));file.close()
	print("BRIDGE_MODULAR_ARMOR_PASS races=",results.size());quit()
