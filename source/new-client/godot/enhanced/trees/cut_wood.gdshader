shader_type spatial;
render_mode cull_disabled;
uniform sampler2D endgrain_albedo : source_color, filter_linear_mipmap_anisotropic;
void fragment() {
    ALBEDO=texture(endgrain_albedo,UV).rgb*.83;
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
