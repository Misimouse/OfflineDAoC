extends SceneTree
var args:Dictionary={}
var glyph:Image
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var p:=arg.trim_prefix("--").split("=",true,1)
		if p.size()==2:args[p[0]]=p[1]
	call_deferred("run")
func texture(path:String) -> ImageTexture:
	var image:=Image.load_from_file(path);assert(image!=null);image.generate_mipmaps();return ImageTexture.create_from_image(image)
func child_owners(node:Node,top:Node) -> void:
	for child in node.get_children():child.owner=top;child_owners(child,top)
func save_scene(scene:Node3D,path:String) -> void:
	child_owners(scene,scene);var packed:=PackedScene.new();assert(packed.pack(scene)==OK);assert(ResourceSaver.save(packed,path,ResourceSaver.FLAG_COMPRESS)==OK)
func carve(mesh:Mesh) -> ArrayMesh:
	var a:Array=mesh.surface_get_arrays(0);var positions:PackedVector3Array=a[Mesh.ARRAY_VERTEX];var normals:PackedVector3Array=a[Mesh.ARRAY_NORMAL];var uv:PackedVector2Array=a[Mesh.ARRAY_TEX_UV];var uv2:PackedVector2Array=a[Mesh.ARRAY_TEX_UV2];var f:PackedInt32Array=a[Mesh.ARRAY_INDEX];assert(uv2.size()==positions.size())
	var queue:Array=[]
	for t in range(0,f.size(),3):
		var triangle:Array=[]
		for k in 3:
			var i:int=f[t+k];triangle.append({"p":positions[i],"n":normals[i],"uv":uv[i],"uv2":uv2[i]})
		queue.append(triangle)
	var p:=PackedVector3Array();var n:=PackedVector3Array();var t0:=PackedVector2Array();var t1:=PackedVector2Array()
	while not queue.is_empty():
		var triangle:Array=queue.pop_back();var a0:Dictionary=triangle[0];var b:Dictionary=triangle[1];var c:Dictionary=triangle[2]
		if maxf(a0.p.distance_to(b.p),maxf(b.p.distance_to(c.p),c.p.distance_to(a0.p)))>.045:
			var ab:=midpoint(a0,b);var bc:=midpoint(b,c);var ca:=midpoint(c,a0)
			queue.append_array([[a0,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]);continue
		for v in triangle:
			var at:Vector2=v.uv2.clamp(Vector2.ZERO,Vector2.ONE);var color:=glyph.get_pixel(clampi(roundi(at.x*(glyph.get_width()-1)),0,glyph.get_width()-1),clampi(roundi(at.y*(glyph.get_height()-1)),0,glyph.get_height()-1))
			var ink:float=1.0-(color.r*.3+color.g*.59+color.b*.11)
			var h:float=smoothstep(.025,.12,ink)*.004-smoothstep(.25,.58,ink)*.009
			p.append(v.p+v.n.normalized()*h);n.append(v.n);t0.append(v.uv);t1.append(v.uv2)
	var arrays:Array=[];arrays.resize(Mesh.ARRAY_MAX);arrays[Mesh.ARRAY_VERTEX]=p;arrays[Mesh.ARRAY_NORMAL]=n;arrays[Mesh.ARRAY_TEX_UV]=t0;arrays[Mesh.ARRAY_TEX_UV2]=t1
	var output:=ArrayMesh.new();output.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,arrays)
	var surface:=SurfaceTool.new();surface.create_from(output,0);surface.generate_normals();surface.index();return surface.commit()
func midpoint(a:Dictionary,b:Dictionary) -> Dictionary:
	return {"p":a.p.lerp(b.p,.5),"n":a.n.lerp(b.n,.5).normalized(),"uv":a.uv.lerp(b.uv,.5),"uv2":a.uv2.lerp(b.uv2,.5)}
func run() -> void:
	DirAccess.make_dir_recursive_absolute(args.out)
	var mushroom:Node3D=load(String(args.mushroom)).instantiate()
	var cap:=ShaderMaterial.new();var shader:=Shader.new()
	shader.code="shader_type spatial; render_mode cull_disabled; uniform sampler2D cap_albedo:source_color,filter_linear_mipmap_anisotropic,repeat_enable; void fragment(){vec3 c=texture(cap_albedo,UV).rgb;float grey=dot(c,vec3(.3,.59,.11));ALBEDO=mix(c,vec3(grey),.23)*.48;ROUGHNESS=1.0;SPECULAR=0.0;METALLIC=0.0;}";cap.shader=shader;cap.set_shader_parameter("cap_albedo",texture(args.cap))
	for node in mushroom.find_children("cap","MeshInstance3D",true,false):
		for s in node.mesh.get_surface_count():node.set_surface_override_material(s,cap)
	save_scene(mushroom,String(args.out).path_join("mushroom.scn"));mushroom.free()
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file("res://content/zones/zone207/models/hbindstone.gltf",state)==OK)
	var imported:=doc.generate_scene(state);var stone:=Node3D.new();stone.name="Piedra_vinculacion_marmol"
	glyph=Image.load_from_file(args.glyph);var marble:=texture(args.marble);var carving:=texture(args.glyph);var triangles:=0
	for node in imported.find_children("*","MeshInstance3D",true,false):
		if not String(node.name) in ["bindstonering_0","bindstonering_1"]:continue
		var instance:=MeshInstance3D.new();instance.name=node.name;instance.transform=node.transform
		instance.mesh=carve(node.mesh) if String(node.name)=="bindstonering_1" else node.mesh
		var mat:=ShaderMaterial.new();var code:=Shader.new();code.code=FileAccess.get_file_as_string("res://enhanced/trees/bindstone_marble.gdshader");mat.shader=code;mat.set_shader_parameter("marble_albedo",marble);mat.set_shader_parameter("carving",carving);mat.set_shader_parameter("emblem",String(node.name)=="bindstonering_1");instance.material_override=mat
		stone.add_child(instance)
		for s in instance.mesh.get_surface_count():triangles+=(instance.mesh.surface_get_array_index_len(s) if instance.mesh.surface_get_array_index_len(s)>0 else instance.mesh.surface_get_array_len(s))/3
	save_scene(stone,String(args.out).path_join("bindstone.scn"));stone.free();imported.free();print("FINISH_SCENES_PREPARED stone_triangles=",triangles);quit()
