extends SceneTree
func _initialize()->void:run.call_deferred()
func run()->void:
    var base:String=get_script().resource_path.get_base_dir().path_join("../SourceEquipmentAppearance_v01")
    var palette:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://content/rules/dye_tints.json"))
    var holder:=Node3D.new();root.add_child(holder);var instance:=MeshInstance3D.new();instance.mesh=BoxMesh.new();holder.add_child(instance)
    var material:=StandardMaterial3D.new();instance.material_override=material
    var results:Dictionary={}
    for key in palette:
        var c:Array=palette[key];material.albedo_color=Color(float(c[0]),float(c[1]),float(c[2]),1)
        var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
        var path:=base.path_join("dye_"+String(key)+".glb");assert(doc.write_to_filesystem(state,path)==OK)
        results[key]={"source_rgb":c,"file":path}
    var f:=FileAccess.open(base.path_join("exported.json"),FileAccess.WRITE);f.store_string(JSON.stringify(results));f.close();print("ORIGINAL_DYE_PALETTE_EXPORT_PASS ",results.size());quit()
