extends SceneTree
func _initialize()->void:run.call_deferred()
func norm(s:String)->String:return s.replace("-", "").replace(" ", "").to_lower()
func unpack(a:Array)->Transform3D:return Transform3D(Basis(Vector3(a[0],a[1],a[2]),Vector3(a[3],a[4],a[5]),Vector3(a[6],a[7],a[8])),Vector3(a[9],a[10],a[11]))
func ue(v:Vector3)->Array:return [v.x,v.z,v.y]
func packed(t:Transform3D)->Dictionary:return {"basis":[ue(t.basis.x),ue(t.basis.z),ue(t.basis.y)],"translation_cm":ue(t.origin*100)}
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("..")
    var catalog:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("equipment_catalog_v01.json")))
    var exported:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("SourceWeapons_All_v01/exported.json")))
    var canonical:Dictionary={}
    for row in exported.models:
        if row.has("canonical_godot_frame"):canonical[norm(row.canonical_bone)]=unpack(row.canonical_godot_frame)
    var weapons:Script=load("res://game/weapon_models.gd")
    var count:int=0;var measured:int=0
    for key in catalog.models:
        var row:Dictionary=catalog.models[key]
        if not row.has("reference"):continue
        var info:Dictionary=row.get("info",{})
        for side in 2:
            if side==1 and not row.has("left_variant"):continue
            var definition:Dictionary=row if side==0 else row.left_variant
            var original:Transform3D=canonical[norm(definition.canonical_bone)]
            var grip:Transform3D=unpack(info.held2) if side==1 and info.has("held2") else unpack(info.held) if info.has("held") else Transform3D.IDENTITY
            var result:Transform3D=original*grip*weapons.TO_NIF
            definition.effect_frame=packed(result);count+=1
            if (int(key) in [19,59,445,857,3287] or info.has("held2")) and measured<50:
                var parent:=Node3D.new();root.add_child(parent);parent.transform=original
                var holder:Node3D=weapons.call("make",int(key),false,side==1)
                if holder:
                    parent.add_child(holder);await process_frame
                    assert((holder.get_child(0) as Node3D).global_transform.is_equal_approx(result),"Effect frame must match original weapon holder")
                    measured+=1
                parent.free();weapons._scenes.clear()
    var file:=FileAccess.open(base.path_join("equipment_catalog_weapon_fx_candidate.json"),FileAccess.WRITE);file.store_string(JSON.stringify(catalog));file.close()
    var proof:={"passed":true,"frames":count,"measured_original_holders":measured}
    file=FileAccess.open(base.path_join("Reports/training_staff_fx_pets/weapon_fx_frames.json"),FileAccess.WRITE);file.store_string(JSON.stringify(proof));file.close();print("WEAPON_FX_FRAMES_PASS ",proof);quit()
