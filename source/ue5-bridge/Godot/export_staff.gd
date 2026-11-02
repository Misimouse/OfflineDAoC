extends "export_models.gd"
## Bake original held geometry in the same reference frame as the exported body.
## Runtime attachment will use the inverse canonical bone frame, never guessed offsets.
func frame(t:Transform3D)->Array:
    return [t.basis.x.x,t.basis.x.y,t.basis.x.z,t.basis.y.x,t.basis.y.y,t.basis.y.z,t.basis.z.x,t.basis.z.y,t.basis.z.z,t.origin.x,t.origin.y,t.origin.z]
func point(v:Vector3)->Array:return [v.x,v.y,v.z]
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("../SourceWeapons_v02")
    DirAccess.make_dir_recursive_absolute(base);export_folder=base
    var factory:Script=load("res://game/fig3_figure.gd");var weapons:Script=load("res://game/weapon_models.gd")
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("../SourceModels/tasks.json")))
    var body:Dictionary=tasks.filter(func(t):return String(t.id)=="1984")[0]
    var fig=factory.new();root.add_child(fig);assert(fig.load_figure(String(body.info.race)));fig.apply(factory.npc_look("bridge-model-1984",fig.meta))
    var skeleton:Skeleton3D=fig.find_children("*","Skeleton3D",true,false)[0]
    var results:Array=[]
    for task in [{"model":19,"bone":"Bip01 R Held","left":false}]:
        var bone:=skeleton.find_bone(task.bone);assert(bone>=0)
        var canonical:Transform3D=skeleton.global_transform*skeleton.get_bone_global_rest(bone)
        var parent:=Node3D.new();root.add_child(parent);parent.transform=canonical
        var weapon:Node3D=weapons.call("make",task.model,false,task.left);assert(weapon!=null);parent.add_child(weapon)
        await process_frame # original make() queues removal of collision-only nodes
        var combined:=ArrayMesh.new();var minimum:=Vector3(INF,INF,INF);var maximum:=-minimum;var vertices:=0
        for mesh in weapon.find_children("*","MeshInstance3D",true,false):
            if not mesh.is_visible_in_tree() or mesh.mesh==null:continue
            assert(mesh.skin==null,"Starter rigid item unexpectedly has skin")
            var t:Transform3D=mesh.global_transform;var normal_basis:Basis=t.basis.inverse().transposed()
            for surface in mesh.mesh.get_surface_count():
                var arrays:Array=mesh.mesh.surface_get_arrays(surface).duplicate(true)
                var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
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
                combined.add_surface_from_arrays(mesh.mesh.surface_get_primitive_type(surface),arrays,[],{},mesh.mesh.surface_get_format(surface))
                assert(combined.get_surface_count()==count+1,"Original vertex formats must survive baking")
                combined.surface_set_material(combined.get_surface_count()-1,standard(mesh.get_active_material(surface)))
        assert(vertices>0 and combined.get_surface_count()>0 and minimum.is_finite() and maximum.is_finite())
        var holder:=Node3D.new();holder.name="Weapon_"+str(task.model);root.add_child(holder)
        var instance:=MeshInstance3D.new();instance.name="Original_Rigid_Item";instance.mesh=combined;holder.add_child(instance)
        var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_scene(holder,state)==OK)
        var path:=base.path_join("weapon_"+str(task.model)+".glb");assert(document.write_to_filesystem(state,path)==OK)
        results.append({"model":task.model,"file":path,"canonical_bone":task.bone,"canonical_godot_frame":frame(canonical),"bounds_m":[point(minimum),point(maximum)],"vertices":vertices,"info":weapons.call("info",task.model),"geometry_frame":"body reference in Godot metres; all node transforms baked"})
        print("WEAPON_EXPORTED ",task.model," vertices=",vertices)
        holder.free();parent.free();await process_frame
    fig.free();var file:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"complete":true,"models":results},"  "));file.close();print("STARTER_WEAPONS_PASS");quit()
