extends "export_models.gd"
## Bake original held geometry in the same reference frame as the exported body.
## Runtime attachment will use the inverse canonical bone frame, never guessed offsets.
func frame(t:Transform3D)->Array:
    return [t.basis.x.x,t.basis.x.y,t.basis.x.z,t.basis.y.x,t.basis.y.y,t.basis.y.z,t.basis.z.x,t.basis.z.y,t.basis.z.z,t.origin.x,t.origin.y,t.origin.z]
func point(v:Vector3)->Array:return [v.x,v.y,v.z]
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("../SourceWeapons_All_v01")
    DirAccess.make_dir_recursive_absolute(base);export_folder=base
    var factory:Script=load("res://game/fig3_figure.gd");var weapons:Script=load("res://game/weapon_models.gd")
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("../SourceModels/tasks.json")))
    var body:Dictionary=tasks.filter(func(t):return String(t.id)=="1984")[0]
    var fig=factory.new();root.add_child(fig);assert(fig.load_figure(String(body.info.race)));fig.apply(factory.npc_look("bridge-model-1984",fig.meta))
    var skeleton:Skeleton3D=fig.find_children("*","Skeleton3D",true,false)[0]
    var results:Array=[];var done:Dictionary={};material_number=10000
    if FileAccess.file_exists(base.path_join("exported.json")):
        results=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("exported.json"))).get("models",[])
        for row in results:done[String(row.export_id)]=true
    for task in JSON.parse_string(FileAccess.get_file_as_string(base.path_join("tasks.json"))):
        if done.has(String(task.export_id)):continue
        var bone:=skeleton.find_bone(task.bone);assert(bone>=0)
        var canonical:Transform3D=skeleton.global_transform*skeleton.get_bone_global_rest(bone)
        var parent:=Node3D.new();root.add_child(parent);parent.transform=canonical
        var weapon:Node3D=weapons.call("make",task.model,false,task.left);assert(weapon!=null);parent.add_child(weapon)
        await process_frame # original make() queues removal of collision-only nodes
        var combined:=ArrayMesh.new();var minimum:=Vector3(INF,INF,INF);var maximum:=-minimum;var vertices:=0
        for mesh in weapon.find_children("*","MeshInstance3D",true,false):
            if not mesh.is_visible_in_tree() or mesh.mesh==null:continue
            var source_mesh:Mesh=mesh.mesh
            var t:Transform3D=mesh.global_transform;var normal_basis:Basis=t.basis.inverse().transposed()
            for surface in source_mesh.get_surface_count():
                var arrays:Array=source_mesh.surface_get_arrays(surface).duplicate(true)
                var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
                if mesh.skin!=null:
                    var sk:Skeleton3D=mesh.get_node_or_null(mesh.skeleton);assert(sk!=null)
                    var bones:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS];var stride:int=bones.size()/positions.size()
                    var matrices:Array=[]
                    for b in mesh.skin.get_bind_count():
                        var bi:int=mesh.skin.get_bind_bone(b)
                        if bi<0:bi=sk.find_bone(mesh.skin.get_bind_name(b))
                        assert(bi>=0);matrices.append(mesh.global_transform.affine_inverse()*sk.global_transform*sk.get_bone_global_pose(bi)*mesh.skin.get_bind_pose(b))
                    for v in positions.size():
                        var posed:=Vector3.ZERO
                        for w in stride:
                            if weights[v*stride+w]>0:posed+=(matrices[bones[v*stride+w]]*positions[v])*weights[v*stride+w]
                        positions[v]=posed
                    arrays[Mesh.ARRAY_BONES]=null;arrays[Mesh.ARRAY_WEIGHTS]=null
                for i in positions.size():positions[i]=t*positions[i];minimum=minimum.min(positions[i]);maximum=maximum.max(positions[i])
                vertices+=positions.size();arrays[Mesh.ARRAY_VERTEX]=positions
                if arrays[Mesh.ARRAY_NORMAL]!=null:
                    var normals:PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
                    for i in normals.size():normals[i]=(normal_basis*normals[i]).normalized()
                    arrays[Mesh.ARRAY_NORMAL]=normals
                if arrays[Mesh.ARRAY_TANGENT]!=null:
                    var tangents:PackedFloat32Array=arrays[Mesh.ARRAY_TANGENT]
                    for i in range(0,tangents.size(),4):
                        var v:Vector3=(t.basis*Vector3(tangents[i],tangents[i+1],tangents[i+2])).normalized();tangents[i]=v.x;tangents[i+1]=v.y;tangents[i+2]=v.z
                    arrays[Mesh.ARRAY_TANGENT]=tangents
                var count:=combined.get_surface_count()
                combined.add_surface_from_arrays(source_mesh.surface_get_primitive_type(surface),arrays,[],{},source_mesh.surface_get_format(surface)&~(Mesh.ARRAY_FORMAT_BONES|Mesh.ARRAY_FORMAT_WEIGHTS))
                assert(combined.get_surface_count()==count+1,"Original vertex formats must survive baking")
                combined.surface_set_material(combined.get_surface_count()-1,standard(mesh.get_active_material(surface)))
        if vertices==0:
            results.append({"model":task.model,"export_id":String(task.export_id),"hidden":true,"info":weapons.call("info",task.model),"source_geometry_empty":true})
            print("WEAPON_ORIGINAL_EMPTY ",task.model)
            parent.free();weapons._scenes.clear()
            var progress:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);progress.store_string(JSON.stringify({"complete":false,"models":results}));progress.close()
            continue
        assert(vertices>0 and combined.get_surface_count()>0 and minimum.is_finite() and maximum.is_finite())
        var holder:=Node3D.new();holder.name="Weapon_"+str(task.model);root.add_child(holder)
        var instance:=MeshInstance3D.new();instance.name="Original_Rigid_Item";instance.mesh=combined;holder.add_child(instance)
        var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_scene(holder,state)==OK)
        var path:=base.path_join("weapon_"+String(task.export_id)+".glb");assert(document.write_to_filesystem(state,path)==OK)
        results.append({"model":task.model,"export_id":String(task.export_id),"left":task.left,"file":path,"canonical_bone":task.bone,"canonical_godot_frame":frame(canonical),"bounds_m":[point(minimum),point(maximum)],"vertices":vertices,"info":weapons.call("info",task.model),"geometry_frame":"body reference in Godot metres; all node transforms baked"})
        print("WEAPON_EXPORTED ",task.model," vertices=",vertices)
        holder.free();parent.free();weapons._scenes.clear();await process_frame
        var progress:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);progress.store_string(JSON.stringify({"complete":false,"models":results}));progress.close()
    fig.free();var file:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"complete":true,"models":results},"  "));file.close();print("STARTER_WEAPONS_PASS");quit()
