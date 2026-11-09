extends "export_pet_models.gd"
## Original weapon models, kept separate from held-equipment and character libraries.
func run()->void:
    var base:String=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output-folder="):base=arg.trim_prefix("--output-folder=")
    assert(not base.is_empty());export_folder=base
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("tasks.json")))
    var results:Array=[]
    for task in tasks:
        var holder:=Node3D.new();root.add_child(holder);holder.name="Original_Siege_"+str(task.id)
        var weapons:Script=load("res://game/weapon_models.gd")
        var scene:Node3D=weapons.make_animated(int(task.id)) if task.animated else weapons.make_world(int(task.id))
        assert(scene!=null);holder.add_child(scene);await process_frame
        var vertices:int=0;var surfaces:int=0;var minimum:=Vector3.INF;var maximum:=-Vector3.INF
        for mesh in holder.find_children("*","MeshInstance3D",true,false):
            if not mesh.is_visible_in_tree():mesh.free();continue
            if mesh.mesh==null:continue
            for surface in mesh.mesh.get_surface_count():
                mesh.set_surface_override_material(surface,standard(mesh.get_active_material(surface)))
                surfaces+=1
                for v in mesh.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
                    var pos:Vector3=mesh.global_transform*v
                    minimum=minimum.min(pos);maximum=maximum.max(pos);vertices+=1
        assert(vertices>0 and minimum.is_finite() and maximum.is_finite())
        if task.animated:merge_meshes(holder)
        else:
            var merged:=ArrayMesh.new()
            for mesh in holder.find_children("*","MeshInstance3D",true,false):
                if mesh.mesh==null:continue
                for surface in mesh.mesh.get_surface_count():
                    var arrays:Array=mesh.mesh.surface_get_arrays(surface).duplicate(true)
                    var points:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
                    for i in points.size():points[i]=mesh.global_transform*points[i]
                    arrays[Mesh.ARRAY_VERTEX]=points
                    var normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
                    for i in normals.size():normals[i]=(mesh.global_basis.inverse().transposed()*normals[i]).normalized()
                    arrays[Mesh.ARRAY_NORMAL]=normals
                    var tangents:PackedFloat32Array=arrays[Mesh.ARRAY_TANGENT]
                    for i in range(0,tangents.size(),4):
                        var v:Vector3=(mesh.global_basis*Vector3(tangents[i],tangents[i+1],tangents[i+2])).normalized()
                        tangents[i]=v.x;tangents[i+1]=v.y;tangents[i+2]=v.z
                        if mesh.global_basis.determinant()<0:tangents[i+3]*=-1
                    arrays[Mesh.ARRAY_TANGENT]=tangents
                    var count:int=merged.get_surface_count()
                    merged.add_surface_from_arrays(mesh.mesh.surface_get_primitive_type(surface),arrays,[],{},mesh.mesh.surface_get_format(surface)&~(Mesh.ARRAY_FORMAT_BONES|Mesh.ARRAY_FORMAT_WEIGHTS))
                    assert(merged.get_surface_count()==count+1)
                    merged.surface_set_material(merged.get_surface_count()-1,mesh.get_active_material(surface))
                mesh.free()
            var body:=MeshInstance3D.new();body.name="Original_Siege_Body";body.mesh=merged;holder.add_child(body)
        var clips:Dictionary={}
        for player in holder.find_children("*","AnimationPlayer",true,false):
            for name in player.get_animation_list():
                if name!="RESET":clips[String(name)]=player.get_animation(name).length
            player.stop()
        if task.animated:assert(clips.has("idle") and clips.has("fire"))
        var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
        var path:String=base.path_join("model_"+str(task.id)+".glb");assert(doc.write_to_filesystem(state,path)==OK)
        results.append({"id":str(task.id),"file":path,"name":task.name,"animated":task.animated,"scale":1.0,"yaw_offset":-90,"vertices":vertices,"surfaces":surfaces,"clips":clips,"bounds_m":[[minimum.x,minimum.y,minimum.z],[maximum.x,maximum.y,maximum.z]]})
        print("SIEGE_MODEL_EXPORTED ",task.id," vertices=",vertices," clips=",clips.size())
        holder.free();await process_frame
    var out:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);out.store_string(JSON.stringify(results,"  "));out.close()
    print("SIEGE_MODELS_EXPORT_PASS ",results.size());quit()
