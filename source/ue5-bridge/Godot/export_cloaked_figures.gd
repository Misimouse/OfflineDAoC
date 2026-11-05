extends "export_models.gd"
## Export separate candidate figures, preserving all original cloak/hood sections.
## Stock figures and the active modular-armour library are never overwritten.
func run()->void:
    var base:=""
    var races:Array=["cel_m"]
    var factory_path:="res://game/fig3_figure.gd"
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):base=arg.trim_prefix("--output=")
        if arg.begins_with("--races="):races=Array(arg.trim_prefix("--races=").split(","))
        if arg.begins_with("--figure-factory="):factory_path=arg.trim_prefix("--figure-factory=")
    assert(not base.is_empty() and not base.trim_suffix("/").ends_with("SourceArmour"))
    DirAccess.make_dir_recursive_absolute(base)
    var ids:={"cel_m":"1984","cel_f":"310","elf_m":"382","elf_f":"388","fir_m":"352","fir_f":"1983","lur_m":"318","lur_f":"378","syl_m":"700","syl_f":"708","sha_m":"1075","sha_f":"1087","mino":"1419"}
    var results:Array=[]
    for race in races:
        assert(ids.has(race))
        export_folder=base.path_join(race);DirAccess.make_dir_recursive_absolute(export_folder);material_number=0
        var holder:=Node3D.new();holder.name="Cloaked_"+race;root.add_child(holder)
        var factory=load(factory_path);var figure=factory.new();holder.add_child(figure);assert(figure.load_figure(race))
        figure.apply(factory.npc_look("bridge-model-"+String(ids[race]),figure.meta))
        var cloak_material:ShaderMaterial=figure._material(false,true)
        cloak_material.set_shader_parameter("albedo_tex",figure._tex("cat_cloak"))
        var hair_nodes:Array=[]
        for style in figure.meta.get("hair_styles",[]):
            if style.get("node")!=null:hair_nodes.append(String(style.node))
        var sections:Array=[];var cloak_channels:Array=[]
        for mesh in holder.find_children("*","MeshInstance3D",true,false):
            var part:=String(mesh.name).get_slice("__",0);var slot:=part.get_slice("_v",0)
            var modular:bool=slot in ["body","lbody","legs","boots","arms","gloves"]
            var cloak:bool=part.begins_with("cloak_")
            if not modular and not cloak and not mesh.is_visible_in_tree():mesh.free();continue
            if mesh.mesh==null:continue
            mesh.visible=true
            if cloak:mesh.material_override=cloak_material
            var variant:=int(part.trim_prefix("cloak_")) if cloak else (int(part.get_slice("_v",1)) if part.contains("_v") else int(figure.meta.get("clothes",{}).get(slot,{}).get("variant",1)))
            for surface in mesh.mesh.get_surface_count():
                var material:BaseMaterial3D=standard(mesh.get_active_material(surface)).duplicate()
                material.resource_name="Cloaked_"+part+"_"+str(sections.size())
                if cloak:
                    material.cull_mode=BaseMaterial3D.CULL_BACK
                    var arrays:Array=mesh.mesh.surface_get_arrays(surface)
                    cloak_channels.append({"part":part,"surface":surface,"vertices":arrays[Mesh.ARRAY_VERTEX].size(),"uv":arrays[Mesh.ARRAY_TEX_UV].size(),"uv2":arrays[Mesh.ARRAY_TEX_UV2].size(),"custom0_values":arrays[Mesh.ARRAY_CUSTOM0].size() if arrays[Mesh.ARRAY_CUSTOM0]!=null else 0,"format":mesh.mesh.surface_get_format(surface)})
                mesh.set_surface_override_material(surface,material)
                sections.append({"material":material.resource_name,"part":part,"slot":"cloak" if cloak else slot,"variant":variant,"modular":modular,"cosmetic":cloak,"hood_hair":part in hair_nodes,"default_visible":false if cloak else (not modular or variant==int(figure.meta.get("clothes",{}).get(slot,{}).get("variant",1)))})
            mesh.material_override=null
        merge_meshes(holder)
        for player in holder.find_children("*","AnimationPlayer",true,false):
            for name in player.get_animation_library_list():
                var library=player.get_animation_library(name).duplicate()
                for clip in library.get_animation_list():
                    if String(clip) not in ["RESET","idle"]:library.remove_animation(clip)
                player.remove_animation_library(name);player.add_animation_library(name,library)
        var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
        var path:=export_folder.path_join("cloaked_"+race+".glb");assert(doc.write_to_filesystem(state,path)==OK)
        results.append({"race":race,"base_id":ids[race],"file":path,"sections":sections,"clothes":figure.meta.get("clothes",{}),"variants":figure.meta.get("variants",{}),"cloaks":figure.meta.get("cloaks",[]),"cloak_channels":cloak_channels})
        holder.free();await process_frame
    var out:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);out.store_string(JSON.stringify(results,"  "));out.close();print("BRIDGE_CLOAK_EXPORT_PASS races=",results.size());quit()
