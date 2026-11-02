extends SceneTree
func _initialize()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("..")
    var catalog:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("models.json")))
    var definitions:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/weapons/weapons.json")).models
    var source:Script=load("res://game/weapon_models.gd")
    var m=load(base.path_join("Godot/combat_visual_state.gd")).new();m.configure(catalog,definitions,{},{})
    var checks:=0;var failures:Array=[];var seen:Dictionary={}
    for id in definitions:
        var raw:=int(definitions[id].get("stance",1))
        if seen.has(raw):continue
        seen[raw]=true;checks+=1
        if m.stance(int(id))!=String(source.call("stance",int(id))):failures.append("weapon stance "+str(id))
    var families:Array=[""];families.append_array(m.STANCES.values());families.append("unknown")
    for model in [0,123]:
        var player:=AnimationPlayer.new();var library:=AnimationLibrary.new()
        for clip in catalog[str(model)]:
            var path=catalog[str(model)][clip]
            if path is String and path.begins_with("/DAoCVisualBridge/") and clip!="asset":library.add_animation(clip,Animation.new())
        player.add_animation_library("",library)
        for family in families:
            for hand in ["","left","dual"]:
                seed(92817);var expected:String=source.call("attack_clip",player,family,hand)
                seed(92817);var actual:String=m.attack_clip(model,family,hand);checks+=1
                if expected!=actual:failures.append("attack "+str([model,family,hand,expected,actual]))
            for kind in ["parry","block","evade"]:
                seed(92817);var expected:String=source.call("defend_clip",player,family,kind)
                seed(92817);var actual:String=m.defend_clip(model,family,kind);checks+=1
                if expected!=actual:failures.append("defence "+str([model,family,kind,expected,actual]))
        player.free()
    var file:=FileAccess.open(base.path_join("Reports/combat_visual/reference_audit.json"),FileAccess.WRITE);file.store_string(JSON.stringify({"checks":checks,"passed":failures.is_empty(),"failures":failures,"reference":"unchanged installed WeaponModels methods, identical random seed","real_server":false},"  "));file.close();print("COMBAT_REFERENCE_AUDIT ",checks," failures=",failures);quit(0 if failures.is_empty() else 1)
