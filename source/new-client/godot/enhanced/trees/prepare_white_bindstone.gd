extends SceneTree
var args:Dictionary={}
func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var p:=arg.trim_prefix("--").split("=",true,1)
		if p.size()==2:args[p[0]]=p[1]
	call_deferred("run")
func run() -> void:
	var stone:Node3D=load(String(args.source)).instantiate()
	var image:=Image.load_from_file(args.texture);assert(image!=null);image.generate_mipmaps();var marble:=ImageTexture.create_from_image(image)
	for mesh in stone.find_children("*","MeshInstance3D",true,false):
		var old:ShaderMaterial=mesh.get_active_material(0)
		var mat:=ShaderMaterial.new();var shader:=Shader.new();shader.code=FileAccess.get_file_as_string("res://enhanced/trees/bindstone_white_marble.gdshader");mat.shader=shader
		mat.set_shader_parameter("marble_albedo",marble);mat.set_shader_parameter("carving",old.get_shader_parameter("carving"));mat.set_shader_parameter("emblem",old.get_shader_parameter("emblem"));mesh.material_override=mat
	var packed:=PackedScene.new();assert(packed.pack(stone)==OK);assert(ResourceSaver.save(packed,args.out,ResourceSaver.FLAG_COMPRESS)==OK)
	stone.free();print("WHITE_BINDSTONE_PREPARED");quit()
