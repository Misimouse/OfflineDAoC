shader_type spatial;
render_mode cull_disabled;
uniform sampler2D leaf_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec3 reference_green=vec3(1.0);
void fragment() {
    vec3 detail=texture(leaf_albedo,UV).rgb;
    vec3 variation=clamp(COLOR.rgb/reference_green,vec3(0.65),vec3(1.35));
    ALBEDO=detail*variation*1.15*(FRONT_FACING?1.0:0.94);
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
