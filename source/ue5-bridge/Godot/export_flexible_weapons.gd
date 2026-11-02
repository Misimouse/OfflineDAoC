extends "export_pet_models.gd"
## Preserve the source weapon skeleton and its own animation library.
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("../SourceFlexibleWeapons_v01")
    export_folder=base
    var factory=load("res://game/fig3_figure.gd");var weapons=load("res://game/weapon_models.gd")
    var fig=factory.new();root.add_child(fig);assert(fig.load_figure("cel_m"))
    var skeleton:Skeleton3D=fig.find_children("*","Skeleton3D",true,false)[0]
    var results:Array=[]
    for task in JSON.parse_string(FileAccess.get_file_as_string(base.path_join("tasks.json"))):
        var bi:int=skeleton.find_bone(task.bone);assert(bi>=0)
        var holder:=Node3D.new();root.add_child(holder);holder.name="Flexible_"+str(task.model)
        holder.transform=skeleton.global_transform*skeleton.get_bone_global_rest(bi)
        var weapon:Node3D=weapons.call("make",task.model,false,task.left);assert(weapon!=null);holder.add_child(weapon)
        await process_frame
        var clips:Dictionary={}
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            ap.stop()
            for clip in ap.get_animation_list():clips[clip]=ap.get_animation(clip).length
            if ap.has_animation("idle"):ap.play("idle");ap.seek(0,true);ap.pause()
        assert(clips.has("idle") and clips.has("combat_idle") and clips.has("attack_high"))
        for mesh in holder.find_children("*","MeshInstance3D",true,false):
            if mesh.mesh==null:continue
            if not mesh.is_visible_in_tree():mesh.free();continue
            var converted:Array=[]
            for i in mesh.mesh.get_surface_count():converted.append(standard(mesh.get_active_material(i)))
            mesh.material_override=null
            for i in converted.size():mesh.set_surface_override_material(i,converted[i])
        merge_meshes(holder)
        var baseline:Array=[]
        var primary:Skeleton3D=weapon.find_children("*","Skeleton3D",true,false)[0]
        for bone in primary.get_bone_count():baseline.append([primary.get_bone_pose_position(bone),primary.get_bone_pose_rotation(bone),primary.get_bone_pose_scale(bone)])
        var idle_bounds:Array=measure_pose(holder)
        var attack_time:float=minf(.4,float(clips.attack_high)*.5)
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            if ap.has_animation("attack_high"):ap.play("attack_high");ap.seek(attack_time,true);ap.pause()
        var attack_bounds:Array=measure_pose(holder)
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            if ap.has_animation("idle"):ap.play("idle");ap.seek(0,true);ap.pause()
        reset_to_baseline(primary,baseline)
        var debug_before:Array=[]
        for skel in weapon.find_children("*","Skeleton3D",true,false):
            for bone in skel.get_bone_count():debug_before.append({"name":skel.get_bone_name(bone),"position":str(skel.get_bone_pose_position(bone)),"rotation":str(skel.get_bone_pose_rotation(bone)),"scale":str(skel.get_bone_pose_scale(bone)),"global":str(skel.global_transform)})
        var envelope:Array=[]
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            envelope=bake_complete_animation(ap,weapon,baseline)
        var baked_idle:Array=measure_pose(holder)
        var debug_after:Array=[]
        for skel in weapon.find_children("*","Skeleton3D",true,false):
            for bone in skel.get_bone_count():debug_after.append({"name":skel.get_bone_name(bone),"position":str(skel.get_bone_pose_position(bone)),"rotation":str(skel.get_bone_pose_rotation(bone)),"scale":str(skel.get_bone_pose_scale(bone)),"global":str(skel.global_transform)})
        var debug_file:=FileAccess.open(base.path_join("bake_debug.json"),FileAccess.WRITE);debug_file.store_string(JSON.stringify({"model":task.model,"before":debug_before,"after":debug_after,"idle_bounds":idle_bounds,"baked_idle":baked_idle},"  "));debug_file.close()
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            if ap.has_animation("attack_high"):ap.play("attack_high",0);ap.seek(attack_time,true);ap.pause()
        var baked_attack:Array=measure_pose(holder)
        for edge in 2:
            for axis in 3:
                assert(absf(float(baked_idle[edge][axis])-float(idle_bounds[edge][axis]))<.0001,"Complete bone tracks must preserve original idle")
                assert(absf(float(baked_attack[edge][axis])-float(attack_bounds[edge][axis]))<.0001,"Complete bone tracks must preserve original attack")
        for ap in weapon.find_children("*","AnimationPlayer",true,false):
            if ap.has_animation("idle"):ap.play("idle",0);ap.seek(0,true);ap.pause()
        var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_scene(holder,state)==OK)
        var path:=base.path_join("flex_"+str(task.model)+".glb");assert(document.write_to_filesystem(state,path)==OK)
        results.append({"model":task.model,"file":path,"animations":clips,"conservative_bounds_m":envelope,"complete_bone_tracks":true,"posed_idle_bounds_m":idle_bounds,"posed_attack_bounds_m":attack_bounds,"attack_sample_s":attack_time,"info":weapons.call("info",task.model)})
        holder.free()
    fig.free()
    var f:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);f.store_string(JSON.stringify(results,"  "));f.close()
    print("FLEXIBLE_WEAPONS_EXPORT_PASS ",results.size());quit()

func measure_pose(holder:Node3D)->Array:
    var minimum:=Vector3(INF,INF,INF);var maximum:=-minimum
    for mi in holder.find_children("*","MeshInstance3D",true,false):
        if mi.mesh==null:continue
        for surface in mi.mesh.get_surface_count():
            var arrays:Array=mi.mesh.surface_get_arrays(surface)
            var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX]
            var matrices:Array=[]
            if mi.skin!=null:
                var sk:Skeleton3D=mi.get_node_or_null(mi.skeleton)
                for k in mi.skin.get_bind_count():
                    var bone:int=mi.skin.get_bind_bone(k)
                    if bone<0:bone=sk.find_bone(mi.skin.get_bind_name(k))
                    matrices.append(mi.global_transform.affine_inverse()*sk.global_transform*sk.get_bone_global_pose(bone)*mi.skin.get_bind_pose(k))
            for v in vertices.size():
                var posed:Vector3=vertices[v]
                if mi.skin!=null:
                    posed=Vector3.ZERO
                    var bones:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS];var stride:int=bones.size()/vertices.size()
                    for k in stride:
                        if weights[v*stride+k]>0:posed+=(matrices[bones[v*stride+k]]*vertices[v])*weights[v*stride+k]
                posed=mi.global_transform*posed;minimum=minimum.min(posed);maximum=maximum.max(posed)
    return [[minimum.x,minimum.y,minimum.z],[maximum.x,maximum.y,maximum.z]]

func basis_scale_bound(basis:Basis)->float:
    var v:Vector3=basis.get_scale().abs()
    return maxf(v.x,maxf(v.y,v.z)) if basis.is_conformal() else sqrt(basis.x.length_squared()+basis.y.length_squared()+basis.z.length_squared())
func bone_radius(sk:Skeleton3D,bone:int,translations:Array,scales:Array,cache:Dictionary)->Vector2:
    if cache.has(bone):return cache[bone]
    var parent:int=sk.get_bone_parent(bone)
    var prior:Vector2=bone_radius(sk,parent,translations,scales,cache) if parent>=0 else Vector2(0,basis_scale_bound(sk.global_transform.basis))
    var value:=Vector2(prior.x+prior.y*float(translations[bone]),prior.y*float(scales[bone]));cache[bone]=value;return value
func reset_to_baseline(sk:Skeleton3D,baseline:Array)->void:
    for bone in sk.get_bone_count():
        sk.set_bone_pose_position(bone,baseline[bone][0]);sk.set_bone_pose_rotation(bone,baseline[bone][1]);sk.set_bone_pose_scale(bone,baseline[bone][2])
func bake_complete_animation(ap:AnimationPlayer,weapon:Node3D,baseline:Array)->Array:
    var skeletons:Array=weapon.find_children("*","Skeleton3D",true,false);assert(skeletons.size()==1)
    var sk:Skeleton3D=skeletons[0];var count:int=sk.get_bone_count()
    var translations:Array=[];var scales:Array=[];var radii:Array=[]
    for bone in count:translations.append(0.0);scales.append(0.0);radii.append(0.0)
    for mi in weapon.find_children("*","MeshInstance3D",true,false):
        if mi.mesh==null or mi.skin==null:continue
        for surface in mi.mesh.get_surface_count():
            var arrays:Array=mi.mesh.surface_get_arrays(surface);var vertices:PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var bones:PackedInt32Array=arrays[Mesh.ARRAY_BONES];var weights:PackedFloat32Array=arrays[Mesh.ARRAY_WEIGHTS];var stride:int=bones.size()/vertices.size()
            for v in vertices.size():
                var total:=0.0
                for k in stride:
                    var weight:float=weights[v*stride+k];total+=weight
                    if weight<=0:continue
                    var bind:int=bones[v*stride+k];var bi:int=mi.skin.get_bind_bone(bind)
                    if bi<0:bi=sk.find_bone(mi.skin.get_bind_name(bind))
                    radii[bi]=maxf(float(radii[bi]),(mi.skin.get_bind_pose(bind)*vertices[v]).length())
                assert(absf(total-1)<.0001,"Skinning envelope requires normalized original weights")
    var names:PackedStringArray=ap.get_animation_list();var library:=AnimationLibrary.new();var animation_root:Node=ap.get_node(ap.root_node);var path:String=String(animation_root.get_path_to(sk))
    for name in names:
        var original:Animation=ap.get_animation(name);var anim:=Animation.new();anim.length=original.length;anim.loop_mode=original.loop_mode
        for bone in count:
            var target:=NodePath(path+":"+sk.get_bone_name(bone))
            for kind in [Animation.TYPE_POSITION_3D,Animation.TYPE_ROTATION_3D,Animation.TYPE_SCALE_3D]:
                var track:int=anim.add_track(kind);anim.track_set_path(track,target);anim.track_set_interpolation_type(track,Animation.INTERPOLATION_LINEAR)
        reset_to_baseline(sk,baseline)
        ap.play("idle",0);ap.seek(0,true);ap.pause()
        var steps:int=maxi(1,ceili(anim.length*30))
        for sample in steps+1:
            var at:float=minf(float(sample)/30,anim.length)
            ap.play(name,0);ap.seek(at,true);ap.pause()
            for bone in count:
                anim.position_track_insert_key(bone*3,at,sk.get_bone_pose_position(bone))
                anim.rotation_track_insert_key(bone*3+1,at,sk.get_bone_pose_rotation(bone))
                anim.scale_track_insert_key(bone*3+2,at,sk.get_bone_pose_scale(bone))
                var parent:int=sk.get_bone_parent(bone);var local:Transform3D=sk.get_bone_global_pose(bone)
                if parent>=0:local=sk.get_bone_global_pose(parent).affine_inverse()*local
                translations[bone]=maxf(float(translations[bone]),local.origin.length());scales[bone]=maxf(float(scales[bone]),basis_scale_bound(local.basis))
        library.add_animation(name,anim)
    for name in ap.get_animation_library_list():ap.remove_animation_library(name)
    ap.add_animation_library("",library);ap.play("idle",0);ap.seek(0,true);ap.pause()
    var cache:Dictionary={};var radius:=0.0
    for bone in count:
        var value:Vector2=bone_radius(sk,bone,translations,scales,cache);radius=maxf(radius,value.x+value.y*float(radii[bone]))
    radius+=.02
    var minimum:Vector3=sk.global_position-Vector3.ONE*radius;var maximum:Vector3=sk.global_position+Vector3.ONE*radius
    return [[minimum.x,minimum.y,minimum.z],[maximum.x,maximum.y,maximum.z]]
