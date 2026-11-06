extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
    var source:="";var output:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--riding-source="):source=arg.trim_prefix("--riding-source=")
        if arg.begins_with("--riding-contacts="):output=arg.trim_prefix("--riding-contacts=")
    assert(not source.is_empty() and not output.is_empty())
    var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(source,state)==OK)
    var holder:=document.generate_scene(state);root.add_child(holder)
    var players:=holder.find_children("*","AnimationPlayer",true,false);var skeletons:=holder.find_children("*","Skeleton3D",true,false)
    assert(players.size()==1 and skeletons.size()==1)
    var helper:Node3D=load("res://game/character_sounds.gd").new();root.add_child(helper);helper._anim=players[0];helper._skel=skeletons[0]
    var result:Dictionary={}
    for key in ["walk","run"]:
        assert(helper._anim.has_animation(key))
        result[key]={"length":helper._anim.get_animation(key).length,"contacts":helper._find_contacts(key,["Bip01 L Foot","Bip01 R Foot"])}
        assert(not result[key].contacts.is_empty())
    var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify({"passed":true,"model":448,"contacts":result},"  "));file.close()
    helper.free();holder.free();print("ORIGINAL_RIDING_CONTACTS_PASS");quit(0)
