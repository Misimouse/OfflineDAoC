extends "export_models.gd"
## Separate heads/hair retain original morph targets; active body libraries stay intact.
func run()->void:
    var base:=""
    var races:Array=["cel_m"]
    var factory_path:="res://game/fig3_figure.gd"
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):base=arg.trim_prefix("--output=")
        if arg.begins_with("--races="):races=Array(arg.trim_prefix("--races=").split(","))
        if arg.begins_with("--figure-factory="):factory_path=arg.trim_prefix("--figure-factory=")
    assert(not base.is_empty())
    DirAccess.make_dir_recursive_absolute(base.path_join("Textures"))
    var factory=load(factory_path)
    var ids:={"cel_m":"1984","cel_f":"310","elf_m":"382","elf_f":"388","fir_m":"352","fir_f":"1983","lur_m":"318","lur_f":"378","syl_m":"700","syl_f":"708","sha_m":"1075","sha_f":"1087","mino":"1419"}
    var report:Dictionary={"complete":false,"races":{},"textures":{},"missing_textures":[]}
    for race in races:
        assert(ids.has(race))
        var reader=factory.new();root.add_child(reader);assert(reader.load_figure(race))
        var meta:Dictionary=reader.meta.duplicate(true)
        # Original feature codes, not HM/FM indices, bind facial hair to the face.
        var original:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/characters/races/"+String(race)+"/figure.gltf"))
        var original_morphs:Dictionary={}
        for node in original.get("nodes",[]):
            if node.has("mesh"):original_morphs[String(node.get("name",""))]=original.meshes[int(node.mesh)].get("extras",{})
        var head_morphs:Dictionary=original_morphs.get("head",{})

        var names:Array=[]
        for item in meta.get("faces",[]):names.append(String(item.get("tex","")))
        for item in meta.get("tattoos",[]):names.append(String(item.get("tex","")))
        names.append_array(meta.get("eyes",[]))
        for style in meta.get("hair_styles",[]):
            for colour in style.get("colours",[]):names.append(String(colour.get("tex","")))
        for item in meta.get("clothes",{}).values():names.append(String(item.get("tex","")))
        for name in names:
            if String(name).is_empty() or report.textures.has(name):continue
            assert(String(name).is_valid_filename())
            var texture:Texture2D=reader._tex(String(name))
            if texture==null:report.missing_textures.append({"race":race,"texture":name});continue
            var source:Image=load("res://game/nif_materials.gd").source_image(texture)
            assert(source!=null)
            var path:=base.path_join("Textures/"+String(name)+".png");assert(source.save_png(path)==OK)
            report.textures[name]={"file":path,"width":source.get_width(),"height":source.get_height()}
        var pieces:Dictionary={"head":-1}
        for i in meta.get("hair_styles",[]).size():
            var style:Dictionary=meta.hair_styles[i]
            if style.get("node")!=null:pieces[String(style.node)]=i
        var result:Dictionary={"base_id":ids[race],"meta":meta,"parts":{}}
        reader.free()
        for part in pieces:
            export_folder=base.path_join(String(race)+"/"+String(part));DirAccess.make_dir_recursive_absolute(export_folder);material_number=0
            var holder:=Node3D.new();root.add_child(holder);holder.name="Appearance_"+String(race)+"_"+String(part)
            var figure=factory.new();holder.add_child(figure);assert(figure.load_figure(race))
            if int(pieces[part])>=0:figure.apply({"hair":int(pieces[part])})
            figure.anim.stop();figure.anim.play("RESET");figure.anim.advance(0)
            var selected:Array=[];var morphs:Array=[]
            for mesh in figure.find_children("*","MeshInstance3D",true,false):
                if String(mesh.name).get_slice("__",0)!=String(part):mesh.free();continue
                mesh.visible=true;selected.append(mesh)
                for i in mesh.mesh.get_blend_shape_count():
                    var name:=String(mesh.mesh.get_blend_shape_name(i))
                    if not name in morphs:morphs.append(name)
                for surface in mesh.mesh.get_surface_count():mesh.set_surface_override_material(surface,standard(mesh.get_active_material(surface)))
                mesh.material_override=null
            assert(not selected.is_empty(),"Missing original appearance part "+String(race)+"/"+String(part))
            # Keep each original morph array; merging all body parts would discard it.
            for player in holder.find_children("*","AnimationPlayer",true,false):player.free()
            var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
            var file:=export_folder.path_join("appearance.glb");assert(doc.write_to_filesystem(state,file)==OK)
            var bindings:Dictionary={};var part_morphs:Dictionary=original_morphs.get(String(part),{})
            var codes:Array=part_morphs.get("codes",[]);var target_names:Array=part_morphs.get("targetNames",[])
            for i in head_morphs.get("codes",[]).size():
                var code:=int(head_morphs.codes[i])
                if code>0 and code<21 and codes.has(code):bindings[String(head_morphs.targetNames[i])]=String(target_names[codes.find(code)])
            result.parts[part]={"file":file,"morphs":morphs,"hair_style":int(pieces[part]),"facial_morphs":bindings}
            holder.free();await process_frame
            print("BRIDGE_APPEARANCE_PART_EXPORTED ",race,"/",part)
        report.races[race]=result
        # This isolated export can release a completed race before loading the next.
        texture_cache.clear();image_cache.clear();factory._tex_cache.clear();factory._scenes.clear()
        await process_frame
    report.complete=true
    var out:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);out.store_string(JSON.stringify(report,"  "));out.close()
    print("BRIDGE_APPEARANCE_EXPORT_PASS races=",report.races.size()," textures=",report.textures.size());quit()
