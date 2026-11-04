extends SceneTree
## Export only original ambient emitters and their source images, outside game content.
func _initialize()->void:run.call_deferred()
func run()->void:
    var output:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(not output.is_empty())
    var scene=load("res://game/nif_scene.gd").new();root.add_child(scene)
    assert(scene.load_scene("res://content/pregame/hib/scene.gltf"))
    var rows:Array=[]
    for emitter in scene.find_children("*","GPUParticles3D",true,false):
        var spec:Dictionary=emitter.get_meta("nif_spec",{}).duplicate(true)
        assert(spec.get("blend")=="add" and spec.get("texture")=="grnglow")
        assert(float(spec.get("lifetime_random",0))==0 and spec.get("quad")==null)
        for modifier in spec.get("modifiers",[]):assert(modifier.type=="growfade")
        var texture:Texture2D=scene.materials.texture(spec.texture)
        var image:Image=load("res://game/nif_materials.gd").source_image(texture)
        assert(image!=null)
        var file:=output.get_base_dir().path_join(spec.texture+".png")
        assert(image.save_png(file)==OK)
        spec["image"]=file
        spec["material"]="/DAoCVisualBridge/PregameParticles_v01/M_OriginalAmbient"
        rows.append(spec)
    assert(rows.size()==1)
    var f:=FileAccess.open(output,FileAccess.WRITE)
    f.store_string(JSON.stringify({"version":1,"emitters":rows}));f.close()
    print("PREGAME_PARTICLES_EXPORTED emitters=",rows.size());quit()
