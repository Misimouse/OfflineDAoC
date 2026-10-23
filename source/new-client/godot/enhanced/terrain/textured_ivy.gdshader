shader_type spatial;
render_mode cull_disabled;
uniform sampler2D leaf_albedo : source_color, filter_linear_mipmap_anisotropic;
void fragment() {
    vec2 atlas=vec2(UV.x*.86+.50,.57-UV.y*.82);
    vec3 leaf=texture(leaf_albedo,atlas).rgb;
    float variation=clamp(dot(COLOR.rgb,vec3(.3,.59,.11))/.12,.72,1.22);
    ALBEDO=leaf*variation*.92;
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
