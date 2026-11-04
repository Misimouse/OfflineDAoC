extends "export_pregame_scene.gd"
## Preserve the source morph controllers instead of freezing their first pose.
func vector_data(values, transform:Transform3D, normals:=false)->Array:
    var out:Array=[]
    if values==null:return out
    for v in values:
        var p:Vector3=(transform.basis.inverse().transposed()*v).normalized() if normals else transform*v
        out.append_array([p.x*(1 if normals else 100),p.z*(1 if normals else 100),p.y*(1 if normals else 100)])
    return out
func run()->void:
    var output:="";var materials_path:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
        if arg.begins_with("--materials="):materials_path=arg.trim_prefix("--materials=")
    assert(output!="" and materials_path!="")
    var definitions=JSON.parse_string(FileAccess.get_file_as_string(materials_path))
    var names:Dictionary={}
    for d in definitions:names[JSON.stringify(d.spec,"",true)]=d.name
    var scene=load("res://game/nif_scene.gd").new();root.add_child(scene)
    assert(scene.load_scene("res://content/pregame/hib/scene.gltf"))
    scene.set_process(false)
    var camera:=Camera3D.new();root.add_child(camera)
    camera.position=Vector3(-.727,-3.81,-4.28);camera.look_at(Vector3(-4.5,-3.865,-1));camera.make_current()
    scene.call("_step",0.0)
    var controllers:Dictionary={}
    for m in scene._morphs:
        var rows:Array=[]
        for r in m.rows:rows.append(Array(r))
        controllers[m.mi.get_instance_id()]={"times":Array(m.times),"weights":rows,"start":m.start,"stop":m.stop,"frequency":m.freq,"phase":m.phase,"cycle":m.cycle}
    var surfaces:Array=[];var triangles:=0;var moving:=0
    for node in scene.find_children("*","MeshInstance3D",true,false):
        var instance:MeshInstance3D=node
        if instance.mesh==null or not instance.is_visible_in_tree():continue
        for s in instance.mesh.get_surface_count():
            var original=instance.get_active_material(s)
            assert(original is ShaderMaterial)
            var spec:Dictionary=original.get_meta("spec",{}).duplicate(true)
            if spec.has("billboard"):spec["baked_billboard"]=spec.billboard;spec.erase("billboard")
            var key:=JSON.stringify(spec,"",true);assert(names.has(key),key)
            var transform:=surface_transform(instance,s,camera)
            var a:Array=instance.mesh.surface_get_arrays(s)
            var indices:Array=Array(a[Mesh.ARRAY_INDEX]) if a[Mesh.ARRAY_INDEX]!=null else []
            if indices.is_empty():for i in a[Mesh.ARRAY_VERTEX].size():indices.append(i)
            var uvs:Array=[[],[],[],[]];var colours:Array=[]
            for v in a[Mesh.ARRAY_VERTEX].size():
                for channel in 2:
                    var uv= a[Mesh.ARRAY_TEX_UV+channel]
                    uvs[channel].append_array([uv[v].x,uv[v].y] if uv!=null and uv.size()>v else [0,0])
                var custom=a[Mesh.ARRAY_CUSTOM0]
                # glTF uses RG_FLOAT for a third UV set and RGBA_FLOAT for four.
                # Assuming four floats skips every second vertex on RG surfaces.
                var stride:int=custom.size()/a[Mesh.ARRAY_VERTEX].size() if custom!=null else 0
                for channel in 2:uvs[2+channel].append_array([custom[v*stride+channel*2],custom[v*stride+channel*2+1]] if stride>=(channel+1)*2 else [0,0])
                var colors=a[Mesh.ARRAY_COLOR];var c:Color=colors[v] if colors!=null and colors.size()>v else Color.WHITE
                colours.append_array([c.r,c.g,c.b,c.a])
            var row:Dictionary={"name":str(instance.name),"material":names[key],"vertices":vector_data(a[Mesh.ARRAY_VERTEX],transform),"normals":vector_data(a[Mesh.ARRAY_NORMAL],transform,true),"indices":indices,"uvs":uvs,"colours":colours}
            if int(original.get_shader_parameter("billboard"))!=0:
                var origin:Vector3=instance.global_position
                var toward:Vector3=(camera.global_position-origin).normalized()
                row["billboard_origin"]=[origin.x*100,origin.z*100,origin.y*100]
                row["billboard_toward"]=[toward.x,toward.z,toward.y]
            if controllers.has(instance.get_instance_id()):
                assert(instance.mesh.blend_shape_mode==Mesh.BLEND_SHAPE_MODE_NORMALIZED)
                row["controller"]=controllers[instance.get_instance_id()];var shapes:Array=[]
                for shape in instance.mesh.surface_get_blend_shape_arrays(s):shapes.append(vector_data(shape[Mesh.ARRAY_VERTEX],transform))
                row["shapes"]=shapes;moving+=1
            surfaces.append(row);triangles+=indices.size()/3
    assert(triangles==62798 and moving==325)
    var file:=FileAccess.open(output,FileAccess.WRITE)
    file.store_string(JSON.stringify({"version":1,"material_root":"/DAoCVisualBridge/PregameMotion_v01","triangles":triangles,"moving_surfaces":moving,"surfaces":surfaces}));file.close()
    print("PREGAME_MOTION_EXPORTED triangles=",triangles," moving=",moving);quit()
