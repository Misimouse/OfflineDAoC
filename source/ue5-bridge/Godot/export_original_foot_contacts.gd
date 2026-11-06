extends SceneTree
## Read original Godot foot contacts without changing models, clips or content.
func _initialize()->void:run.call_deferred()
func run()->void:
    var tasks_path:="";var output:="";var helper_path:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--footstep-tasks="):tasks_path=arg.trim_prefix("--footstep-tasks=")
        if arg.begins_with("--footstep-output="):output=arg.trim_prefix("--footstep-output=")
        if arg.begins_with("--footstep-original-helper="):helper_path=arg.trim_prefix("--footstep-original-helper=")
    assert(not tasks_path.is_empty() and not output.is_empty() and not helper_path.is_empty())
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(tasks_path));var results:Dictionary={}
    for id in tasks:
        var task:Dictionary=tasks[id];var holder:Node3D;var model:Node3D;var anim:AnimationPlayer
        if not String(task.race).is_empty():
            holder=load("res://game/fig3_figure.gd").new();root.add_child(holder);assert(holder.load_figure(task.race))
            model=holder.model;anim=holder.anim
        else:
            var document:=GLTFDocument.new();var state:=GLTFState.new();assert(document.append_from_file(task.gltf,state)==OK)
            holder=document.generate_scene(state);root.add_child(holder);model=holder
            var players=holder.find_children("*","AnimationPlayer",true,false);assert(players.size()>0);anim=players[0]
        var helper=load(helper_path).new();root.add_child(helper)
        helper._anim=anim
        var skeletons=model.find_children("*","Skeleton3D",true,false);assert(skeletons.size()>0);helper._skel=skeletons[0]
        var clips:Dictionary={}
        for clip in ["walk","run","walk_back","strafe_left","strafe_right","swim"]:
            assert(anim.has_animation(clip));var contacts:Array=helper._find_contacts(clip,["Bip01 L Hand","Bip01 R Hand"] if clip=="swim" else ["Bip01 L Foot","Bip01 R Foot"])
            clips[clip]={"length":anim.get_animation(clip).length,"contacts":contacts}
        results[id]=clips;helper.free();holder.free();await process_frame
    var file:=FileAccess.open(output,FileAccess.WRITE);file.store_string(JSON.stringify({"passed":true,"models":results},"  "));file.close()
    print("ORIGINAL_FOOT_CONTACTS_PASS ",results.size());quit()
