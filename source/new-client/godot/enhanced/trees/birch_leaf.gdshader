shader_type spatial;
render_mode cull_disabled;
void fragment() {
    float midrib=1.0-smoothstep(0.009,0.023,abs(UV.x-0.5));
    float secondary=1.0-smoothstep(0.025,0.07,abs(fract((UV.y+abs(UV.x-0.5)*0.65)*8.0)-0.5));
    vec3 green=COLOR.rgb*(FRONT_FACING?1.0:0.86);
    ALBEDO=green*(1.0-midrib*0.15-secondary*0.07);
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
