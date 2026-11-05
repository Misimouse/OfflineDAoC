extends "export_models.gd"
## Separate original helmet assemblies. No active catalogue or source asset is changed.
## Hair uses the original helmet morph; full helmets retain their original head mesh.
func run()->void:
    var base:=""
    var races:Array=["cel_m"]
    var wanted:Array=[]
    var factory_path:="res://game/fig3_figure.gd"
    var catalogue_path:="res://content/helms/helms.json"
    var original_textures:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):base=arg.trim_prefix("--output=")
        if arg.begins_with("--races="):races=Array(arg.trim_prefix("--races=").split(","))
        if arg.begins_with("--models="):wanted=Array(arg.trim_prefix("--models=").split(","))
        if arg.begins_with("--figure-factory="):factory_path=arg.trim_prefix("--figure-factory=")
        if arg.begins_with("--helmet-catalogue="):catalogue_path=arg.trim_prefix("--helmet-catalogue=")
        if arg.begins_with("--original-helmet-textures="):original_textures=arg.trim_prefix("--original-helmet-textures=")
    assert(not base.is_empty())
    DirAccess.make_dir_recursive_absolute(base)
    var factory=load(factory_path)
    var library:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(catalogue_path)).models
    var ids:={"cel_m":"1984","cel_f":"310","elf_m":"382","elf_f":"388","fir_m":"352","fir_f":"1983","lur_m":"318","lur_f":"378","syl_m":"700","syl_f":"708","sha_m":"1075","sha_f":"1087","mino":"1419"}
    var results:Array=[]
    for race in races:
        assert(ids.has(race))
        for ident in library:
            if not wanted.is_empty() and not ident in wanted:continue
            var entry:Dictionary=library[ident]
            if not entry.has(race) and not entry.has("full"):continue
            export_folder=base.path_join(String(race)+"_"+ident);DirAccess.make_dir_recursive_absolute(export_folder);material_number=0
            var holder:=Node3D.new();root.add_child(holder);holder.name="Helmet_"+String(race)+"_"+ident
            var fig=factory.new();holder.add_child(fig);assert(fig.load_figure(race))
            fig.apply(factory.npc_look("bridge-model-"+ids[race],fig.meta))
            if not original_textures.is_empty() and entry.has("full") and entry.has("tex"):
                var key:=String(entry.tex).to_lower()
                var image:=Image.load_from_file(original_textures.path_join(key+".png"));assert(image!=null)
                var texture:=ImageTexture.create_from_image(image)
                fig._textures[key]=texture;factory._tex_cache[String(fig._texture_dir)+key]=texture
            fig.anim.stop();fig.anim.play("RESET");fig.anim.advance(0)
            fig.set_helm(int(ident))
            await process_frame
            var full:bool=entry.has("full") and int(entry.full) in (fig.meta.get("full_helms",[]) as Array).map(func(v):return int(v))
            var sk:Skeleton3D=fig.find_children("*","Skeleton3D",true,false)[0]
            var template:MeshInstance3D=fig._parts("head")[0]
            var selected:Array=[];var descriptors:Array=[]
            for mesh in fig.find_children("*","MeshInstance3D",true,false):
                if mesh.mesh==null or not mesh.is_visible_in_tree():continue
                var part:=String(mesh.name).get_slice("__",0)
                var helmet:bool=(fig._helm!=null and fig._helm.is_ancestor_of(mesh)) or (full and part=="fullhelm_"+str(int(entry.full)))
                var hair:bool=false
                for style in fig.meta.get("hair_styles",[]):
                    if style.get("node")!=null and part==String(style.node):hair=true
                if not helmet and not hair:continue
                # Bake active hair morphs before merging (merge_meshes does not carry morph targets).
                var materials:Array=[]
                for surface in mesh.mesh.get_surface_count():materials.append(mesh.get_active_material(surface))
                mesh.mesh=mesh.bake_mesh_from_current_blend_shape_mix()
                assert(mesh.mesh!=null)
                for surface in mesh.mesh.get_surface_count():
                    var material:Material=standard(materials[surface]).duplicate()
                    material.resource_name="Helmet_"+str(descriptors.size())
                    mesh.set_surface_override_material(surface,material)
                    descriptors.append({"material":material.resource_name,"helmet":helmet,"hair":hair,"part":part})
                mesh.material_override=null
                if mesh.skin==null:
                    # Bind the rigid original NIF to its original helmet bone, in the body's reference frame.
                    var skin:Skin=template.skin.duplicate()
                    var bone:int=-1
                    for bone_name in ["Bip01 Helmet","Bip01-Helmet","Bip01 Head","Bip01-Head"]:
                        bone=sk.find_bone(bone_name)
                        if bone>=0:break
                    assert(bone>=0)
                    var bind:=-1
                    for i in skin.get_bind_count():
                        if skin.get_bind_bone(i)==bone or skin.get_bind_name(i)==sk.get_bone_name(bone):bind=i;break
                    if bind<0:
                        bind=skin.get_bind_count()
                        skin.add_bind(bone,sk.get_bone_global_rest(bone).affine_inverse()*sk.global_transform.affine_inverse()*template.global_transform)
                    var t:Transform3D=template.global_transform.affine_inverse()*mesh.global_transform
                    var combined:=ArrayMesh.new()
                    for surface in mesh.mesh.get_surface_count():
                        var arrays:Array=mesh.mesh.surface_get_arrays(surface).duplicate(true)
                        var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
                        var bones:=PackedInt32Array();var weights:=PackedFloat32Array()
                        for i in positions.size():
                            positions[i]=t*positions[i]
                            bones.append_array(PackedInt32Array([bind,0,0,0]));weights.append_array(PackedFloat32Array([1,0,0,0]))
                        arrays[Mesh.ARRAY_VERTEX]=positions;arrays[Mesh.ARRAY_BONES]=bones;arrays[Mesh.ARRAY_WEIGHTS]=weights
                        if arrays[Mesh.ARRAY_NORMAL]!=null:
                            var normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
                            for i in normals.size():normals[i]=(t.basis.inverse().transposed()*normals[i]).normalized()
                            arrays[Mesh.ARRAY_NORMAL]=normals
                        if arrays[Mesh.ARRAY_TANGENT]!=null:
                            var tangents:PackedFloat32Array=arrays[Mesh.ARRAY_TANGENT]
                            for i in range(0,tangents.size(),4):
                                var v:Vector3=(t.basis*Vector3(tangents[i],tangents[i+1],tangents[i+2])).normalized()
                                tangents[i]=v.x;tangents[i+1]=v.y;tangents[i+2]=v.z
                            arrays[Mesh.ARRAY_TANGENT]=tangents
                        combined.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
                        combined.surface_set_material(surface,mesh.get_active_material(surface))
                    var rigid:=MeshInstance3D.new();rigid.name="Original_Helmet";rigid.mesh=combined;rigid.skin=skin
                    template.get_parent().add_child(rigid);rigid.skeleton=template.skeleton;rigid.transform=template.transform
                    selected.append(rigid)
                else:selected.append(mesh)
            assert(not selected.is_empty(),"Original helmet has no visible geometry: "+String(race)+"/"+ident)
            assert(descriptors.any(func(section):return section.helmet),"Export contains hair but no helmet: "+String(race)+"/"+ident)
            for mesh in fig.find_children("*","MeshInstance3D",true,false):
                if not mesh in selected:mesh.free()
            # The original rigid NIF's now-empty attachment/model nodes otherwise
            # become extra skeleton bones in GLTF/Interchange.
            if fig._helm!=null:fig._helm.free();fig._helm=null
            merge_meshes(holder)
            for player in holder.find_children("*","AnimationPlayer",true,false):player.free()
            var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
            var file:=export_folder.path_join("helmet.glb");assert(doc.write_to_filesystem(state,file)==OK)
            results.append({"race":race,"base_id":ids[race],"model":int(ident),"file":file,"full":full,"sections":descriptors,"hair_mode":entry.get(race,{}).get("hair",0)})
            print("BRIDGE_HELMET_EXPORTED ",race,"/",ident," full=",full)
            holder.free();await process_frame
    var out:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);out.store_string(JSON.stringify(results,"  "));out.close()
    print("BRIDGE_HELMET_EXPORT_PASS count=",results.size());quit()
