shader_type spatial;
render_mode cull_disabled;
uniform sampler2D bark_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 local_position;
void vertex() { local_position=VERTEX; }
void fragment() {
    vec2 p=local_position.xz;float a=atan(p.y-1.05,p.x);
    float fibre=.97+.03*sin(a*17.0+length(p-vec2(0,1.05))*8.0);
    vec3 grain=texture(bark_albedo,p*.8).rgb;
    ALBEDO=mix(grain*vec3(.80,.68,.52),vec3(.065,.043,.020),.45)*fibre;
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
