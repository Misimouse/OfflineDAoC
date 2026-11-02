extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("..")
    var tasks=JSON.parse_string(FileAccess.get_file_as_string(base.path_join("SourceModels/tasks.json")))
    var report:Dictionary={"models":{},"errors":[]}
    for task in tasks:
        var info:Dictionary=task.info
        var figure:Node3D
        if info.has("race"):
            figure=load("res://game/fig3_figure.gd").new();root.add_child(figure)
            if not figure.load_figure(String(info.race)):report.errors.append(task.id);figure.free();continue
        else:
            figure=load("res://game/nif_scene.gd").new();root.add_child(figure)
            if not figure.load_scene(String(info.gltf)):report.errors.append(task.id);figure.free();continue
        var clips:Dictionary={}
        for player in figure.find_children("*","AnimationPlayer",true,false):
            for clip in player.get_animation_list():
                var anim:Animation=player.get_animation(clip)
                clips[String(clip)]={"seconds":anim.length,"loop":anim.loop_mode,"tracks":anim.get_track_count()}
        report.models[String(task.id)]={"name":String(info.get("name","")),"race":String(info.get("race","")),"clips":clips}
        figure.free();await process_frame
    var file:=FileAccess.open(base.path_join("Reports/player_state/animation_audit.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
    print("ANIMATION_AUDIT models=",report.models.size()," errors=",report.errors);quit(0 if report.errors.is_empty() else 1)
