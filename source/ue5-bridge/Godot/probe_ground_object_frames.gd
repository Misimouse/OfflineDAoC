extends SceneTree
## Measure the unchanged original make/make_world graphs; never alter installed catalogues.
var failures:Array=[]
var rows:Dictionary={}
func vec(v:Vector3)->Array:return [v.x,v.y,v.z]
func frame(t:Transform3D)->Array:return [t.basis.x.x,t.basis.x.y,t.basis.x.z,t.basis.y.x,t.basis.y.y,t.basis.y.z,t.basis.z.x,t.basis.z.y,t.basis.z.z,t.origin.x,t.origin.y,t.origin.z]
func from_frame(f:Array)->Transform3D:return Transform3D(Basis(Vector3(f[0],f[1],f[2]),Vector3(f[3],f[4],f[5]),Vector3(f[6],f[7],f[8])),Vector3(f[9],f[10],f[11]))
func positioned(mesh:MeshInstance3D,arrays:Array)->PackedVector3Array:
    var positions:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX].duplicate()
    if mesh.skin==null:return positions
    var sk:Skeleton3D=mesh.get_node_or_null(mesh.skeleton)
    if sk==null:failures.append("Missing original skin skeleton");return positions
    var bones:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS];var stride:int=bones.size()/positions.size();var matrices:Array=[]
    for b in mesh.skin.get_bind_count():
        var bi:int=mesh.skin.get_bind_bone(b)
        if bi<0:bi=sk.find_bone(mesh.skin.get_bind_name(b))
        if bi<0:failures.append("Missing original skin bone");return positions
        matrices.append(mesh.global_transform.affine_inverse()*sk.global_transform*sk.get_bone_global_pose(bi)*mesh.skin.get_bind_pose(b))
    for v in positions.size():
        var posed:=Vector3.ZERO
        for b in stride:
            if weights[v*stride+b]>0:posed+=(matrices[bones[v*stride+b]]*positions[v])*weights[v*stride+b]
        positions[v]=posed
    return positions
func _initialize()->void:run.call_deferred()
func run()->void:
    var args:=OS.get_cmdline_user_args()
    if args.size()!=2:push_error("Expected task and report paths");quit(1);return
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var factory:Script=load("res://game/weapon_models.gd")
    if not tasks is Array or factory==null:quit(1);return
    for task in tasks:
        var model:=int(task.model);var held:Node3D=factory.call("make",model,false,false);var world:Node3D=factory.call("make_world",model)
        if held==null or world==null:
            failures.append("Original scene missing for "+str(model));break
        root.add_child(held);root.add_child(world);held.transform=from_frame(task.canonical)
        await process_frame
        await process_frame
        var minimum:=Vector3(INF,INF,INF);var maximum:=-minimum;var world_min:=minimum;var world_max:=maximum;var vertices:=0;var error:=0.0;var transform:Transform3D;var have_transform:=false
        for hm in held.find_children("*","MeshInstance3D",true,false):
            if not hm.is_visible_in_tree() or hm.mesh==null:continue
            var wm:MeshInstance3D=world.get_node_or_null(held.get_path_to(hm))
            if wm==null or wm.mesh==null:failures.append("World scene mesh mismatch for "+str(model));break
            var candidate:Transform3D=wm.global_transform*hm.global_transform.affine_inverse()
            if not have_transform:transform=candidate;have_transform=true
            for surface in hm.mesh.get_surface_count():
                var hp:PackedVector3Array=positioned(hm,hm.mesh.surface_get_arrays(surface));var wp:PackedVector3Array=positioned(wm,wm.mesh.surface_get_arrays(surface))
                if hp.size()!=wp.size():failures.append("World vertex count mismatch");break
                for v in hp.size():
                    var a:Vector3=hm.global_transform*hp[v];var b:Vector3=wm.global_transform*wp[v];minimum=minimum.min(a);maximum=maximum.max(a);world_min=world_min.min(b);world_max=world_max.max(b);error=maxf(error,(transform*a).distance_to(b));vertices+=1
        var expected_min:=Vector3(task.canonical_bounds_m[0][0],task.canonical_bounds_m[0][1],task.canonical_bounds_m[0][2]);var expected_max:=Vector3(task.canonical_bounds_m[1][0],task.canonical_bounds_m[1][1],task.canonical_bounds_m[1][2])
        var bounds_error:=maxf(minimum.distance_to(expected_min),maximum.distance_to(expected_max))
        if not have_transform or vertices!=int(task.vertices) or error>.0001 or bounds_error>.001:failures.append("Original/canonical geometry mismatch for %d: vertices%d expected%d transform%.7f bounds%.7f"%[model,vertices,int(task.vertices),error,bounds_error])
        rows[str(task.export_id)]={"model":model,"asset":task.asset,"vertices":vertices,"canonical_to_world_godot":frame(transform),"world_bounds_m":[vec(world_min),vec(world_max)],"source_vertex_error_m":error,"canonical_bounds_error_m":bounds_error}
        held.free();world.free();factory._scenes.clear()
        if not failures.is_empty():break
        if rows.size()%25==0:print("GROUND_FRAME_PROGRESS ",rows.size(),"/",tasks.size())
    var result:={"passed":failures.is_empty() and rows.size()==tasks.size(),"models":rows,"checked_assets":rows.size(),"expected_assets":tasks.size(),"failures":failures,"original_make_world_executed":true,"normal_runtime_modified":false}
    var output:=FileAccess.open(args[1],FileAccess.WRITE);output.store_string(JSON.stringify(result));output.close();print(JSON.stringify({"passed":result.passed,"assets":rows.size(),"failures":failures}));quit(0 if result.passed else 1)
