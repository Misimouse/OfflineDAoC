extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("../SourceEmblems_v01/Patterns")
    DirAccess.make_dir_recursive_absolute(base)
    var original:Script=load("res://game/emblems.gd")
    var results:Dictionary={}
    for key in 513:
        var emblem:int=0 if key==512 else 512|key
        var texture:Texture2D=original.call("pattern_texture",emblem)
        var image:Image=texture.get_image();assert(image.get_width()==2 and image.get_height()==4)
        var path:String=base.path_join("pattern_%d.png"%key);assert(image.save_png(path)==OK)
        var pixels:Array=[]
        for y in 4:
            for x in 2:
                var c:Color=image.get_pixel(x,y);pixels.append([roundi(c.r*255),roundi(c.g*255),roundi(c.b*255)])
        results[str(key)]={"file":path,"pixels":pixels}
    var f:=FileAccess.open(base.path_join("../patterns.json"),FileAccess.WRITE);f.store_string(JSON.stringify(results));f.close();print("ORIGINAL_EMBLEM_PATTERNS_PASS ",results.size());quit()
