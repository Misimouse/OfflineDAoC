shader_type spatial;
render_mode cull_disabled;
uniform sampler2D bark_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 wood_position;
varying vec3 wood_normal;
void vertex() { wood_position=VERTEX; wood_normal=NORMAL; }
void fragment() {
    vec3 p=wood_position;
    vec3 weights=pow(abs(normalize(wood_normal)),vec3(5.0));
    weights/=max(dot(weights,vec3(1.0)),0.001);
    vec3 a=texture(bark_albedo,p.yz*0.48+vec2(0.17,0.31)).rgb;
    vec3 b=texture(bark_albedo,p.xz*0.48+vec2(0.53,0.13)).rgb;
    vec3 c=texture(bark_albedo,p.xy*0.48+vec2(0.27,0.61)).rgb;
    vec3 bark=a*weights.x+b*weights.y+c*weights.z;
    float variation=0.92+0.07*sin(p.x*0.51+p.y*0.41+p.z*0.37);
    ALBEDO=bark*variation;
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
