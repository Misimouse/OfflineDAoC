extends RefCounted
## Deform the original basal vertices; no extra collars, UV strips or overlapping faces.
var materials:Dictionary={}
var ground:ImageTexture
var grid:=Vector4.ZERO
var zone_y:=0.0
var bark:ImageTexture
var report:Dictionary={"meshes":0,"added_geometry":0,"canopy_displacement":0,"terrain_samples_exact":true}
const HEADER:="""
uniform sampler2D root_ground : filter_linear, repeat_disable;
uniform vec4 root_grid;
uniform float root_zone_y;
instance uniform vec2 root_band : instance_index(0);
vec3 seat_original_base(vec3 vertex,mat4 model) {
    vec3 world=(model*vec4(vertex,1.0)).xyz;
    float amount=1.0-smoothstep(root_band.x-root_band.y,root_band.x,world.y);
    if (amount>0.0) {
        vec2 cell=clamp((world.xz-root_grid.xy)/root_grid.z,vec2(0.0),vec2(root_grid.w-1.001));
        float soil=textureLod(root_ground,(cell+vec2(0.5))/root_grid.w,0.0).r+root_zone_y;
        world.y=mix(world.y,min(world.y,soil-0.24),amount);
        vertex=(inverse(model)*vec4(world,1.0)).xyz;
    }
    return vertex;
}
"""
func setup(zone:Node3D,bark_path:String) -> void:
	ground=ImageTexture.create_from_image(Image.create_from_data(zone.hsize,zone.hsize,false,Image.FORMAT_RF,zone.heights.to_byte_array()))
	report.terrain_samples_exact=ground.get_image().get_data()==zone.heights.to_byte_array();assert(report.terrain_samples_exact)
	grid=Vector4(zone.global_position.x,zone.global_position.z,zone.cell,zone.hsize);zone_y=zone.global_position.y
	var image:=Image.load_from_file(bark_path);assert(image!=null);image.generate_mipmaps();bark=ImageTexture.create_from_image(image)
func apply(asset:Node3D,file:String) -> void:
	for node in asset.find_children("Tronco*","MeshInstance3D",true,false):
		var stem:Node3D=asset;var parent:Node=node.get_parent()
		while parent!=asset:
			if String(parent.name).to_lower().contains("root_"):stem=parent;break
			parent=parent.get_parent()
		var scale_y:float=node.global_transform.basis.get_scale().x
		# The dense LOW shrub has branches near the soil; confine its correction to the foot.
		var top:float=.20 if file=="models/hlowtree.gltf" else 1.3
		var blend:float=.18 if file=="models/hlowtree.gltf" else 1.1
		node.set_instance_shader_parameter("root_band",Vector2(stem.global_position.y+top*scale_y,blend*scale_y))
		for s in node.mesh.get_surface_count():
			var original:ShaderMaterial=node.get_active_material(s);assert(original!=null)
			var key:String="%d:%s"%[original.get_instance_id(),file]
			if not materials.has(key):
				var material:ShaderMaterial=original.duplicate()
				var code:String=original.shader.code
				if file=="models/helm.gltf":
					code=FileAccess.get_file_as_string("res://enhanced/trees/oak_bark.gdshader")
					material=ShaderMaterial.new();material.set_shader_parameter("bark_albedo",bark)
				var vertex:int=code.find("void vertex()");assert(vertex>=0)
				var open:int=code.find("{",vertex);code=code.insert(open+1,"\n VERTEX=seat_original_base(VERTEX,MODEL_MATRIX);\n")
				code=code.replace("shader_type spatial;","shader_type spatial;\n"+HEADER)
				var shader:=Shader.new();shader.code=code;material.shader=shader
				# Set after assigning shader so Godot validates parameter names against the right shader.
				if file=="models/helm.gltf":material.set_shader_parameter("bark_albedo",bark)
				material.set_shader_parameter("root_ground",ground);material.set_shader_parameter("root_grid",grid);material.set_shader_parameter("root_zone_y",zone_y)
				materials[key]=material
			node.set_surface_override_material(s,materials[key])
		report.meshes+=1
