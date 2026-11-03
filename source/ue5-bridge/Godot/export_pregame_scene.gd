extends SceneTree
## Original Hibernian lobby geometry. No map, NIF or source texture is modified.
var images:Dictionary={}
var export_materials:Array=[]
var saved_layers:Dictionary={}
var export_folder:=""
func _initialize()->void:run.call_deferred()
func standard(original:Material)->Material:
    if not original is ShaderMaterial:return original
    var m:=StandardMaterial3D.new();m.roughness=.9;m.cull_mode=BaseMaterial3D.CULL_DISABLED
    var tex:Texture2D=original.get_shader_parameter("albedo_tex")
    if tex==null:tex=original.get_shader_parameter("base_tex")
    if tex!=null:
        var key:=tex.get_instance_id()
        if not images.has(key):
            var image:Image=load("res://game/nif_materials.gd").source_image(tex)
            if image!=null:images[key]=ImageTexture.create_from_image(image)
        if images.has(key):m.albedo_texture=images[key]
    var tint=original.get_shader_parameter("tint")
    if tint is Color:m.albedo_color=tint
    if "ALPHA_SCISSOR_THRESHOLD =" in original.shader.code:
        m.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
        var cutoff=original.get_shader_parameter("alpha_cut")
        if cutoff is float:m.alpha_scissor_threshold=cutoff
    elif "ALPHA = c.a * opacity;" in original.shader.code:m.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA
    elif "blend_add" in original.shader.code:
        m.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA;m.blend_mode=BaseMaterial3D.BLEND_MODE_ADD
    m.set_meta("source_spec",original.get_meta("spec",{}))
    var slots:Dictionary={}
    for slot in ["base","dark","detail","decal","glow","tex1","tex2"]:
        if not bool(original.get_shader_parameter("has_"+slot)):continue
        var source:Texture2D=original.get_shader_parameter(slot+"_tex")
        if source==null:continue
        var image:Image=load("res://game/nif_materials.gd").source_image(source)
        if image==null:continue
        var png:=export_folder.path_join("layer_"+str(source.get_instance_id())+".png")
        if not saved_layers.has(png):image.save_png(png);saved_layers[png]=true
        slots[slot]={"file":png,"uv":int(original.get_shader_parameter(slot+"_uv")),"source":source.get_meta("daoc_source_path","")}
    m.set_meta("source_layers",slots)
    return m
func run()->void:
    var output:=""
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--output="):output=arg.trim_prefix("--output=")
    assert(not output.is_empty());export_folder=output.get_base_dir()
    var scene=load("res://game/nif_scene.gd").new();root.add_child(scene)
    assert(scene.load_scene("res://content/pregame/hib/scene.gltf"))
    var combined:=ArrayMesh.new();var surfaces:=0;var groups:Dictionary={}
    for node in scene.find_children("*","MeshInstance3D",true,false):
        var instance:MeshInstance3D=node
        if instance.mesh==null or not instance.is_visible_in_tree():continue
        for surface in instance.mesh.get_surface_count():
            var material:Material=standard(instance.get_active_material(surface))
            var key:=str(material.get_instance_id())
            if material is StandardMaterial3D:
                key=str(material.albedo_texture.get_instance_id() if material.albedo_texture else 0)+str(material.albedo_color)+str(material.transparency)
            if not groups.has(key):
                material.resource_name="PGM%03d" % groups.size()
                export_materials.append({"name":material.resource_name,"spec":material.get_meta("source_spec",{}),"layers":material.get_meta("source_layers",{})})
                var builder:=SurfaceTool.new();builder.begin(Mesh.PRIMITIVE_TRIANGLES);builder.set_material(material);groups[key]=builder
            groups[key].append_from(instance.mesh,surface,instance.global_transform)
    assert(groups.size()<=256)
    for builder in groups.values():builder.commit(combined);surfaces+=1
    var holder:=Node3D.new();root.add_child(holder);holder.name="Original_Hibernia_Lobby"
    var mesh:=MeshInstance3D.new();mesh.mesh=combined;holder.add_child(mesh)
    var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_scene(holder,state)==OK)
    assert(doc.write_to_filesystem(state,output)==OK)
    var sidecar:=FileAccess.open(output+".materials.json",FileAccess.WRITE);sidecar.store_string(JSON.stringify(export_materials,"  "));sidecar.close()
    print("ORIGINAL_HIBERNIA_LOBBY_EXPORTED surfaces=",surfaces);quit()
