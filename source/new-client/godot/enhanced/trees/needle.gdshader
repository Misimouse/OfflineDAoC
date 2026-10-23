shader_type spatial;
render_mode cull_disabled;
void fragment() {
    ALBEDO=COLOR.rgb*(0.9+0.1*sin(UV.y*3.14159265));
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
