shader_type spatial;
render_mode cull_disabled;
uniform float tree_seed=0.0;
uniform sampler2D bark_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 position_source;
varying float radius_source;
float hash3(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float noise3(vec3 p) {
    vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
    return mix(mix(mix(hash3(i),hash3(i+vec3(1,0,0)),f.x),mix(hash3(i+vec3(0,1,0)),hash3(i+vec3(1,1,0)),f.x),f.y),
        mix(mix(hash3(i+vec3(0,0,1)),hash3(i+vec3(1,0,1)),f.x),mix(hash3(i+vec3(0,1,1)),hash3(i+vec3(1,1,1)),f.x),f.y),f.z);
}
void vertex() { position_source=VERTEX; radius_source=UV2.x*0.5; }
void fragment() {
    vec3 p=position_source+vec3(tree_seed,tree_seed*0.371,0.0);
    float grain=noise3(p*vec3(27.0,27.0,6.0));
    vec2 uv=vec2(UV.x+tree_seed*0.17+0.13*sin(UV.y*0.4+tree_seed),UV.y*0.55+tree_seed);
    vec3 bark=texture(bark_albedo,uv).rgb*(0.86+grain*0.10);
    float young=smoothstep(0.018,0.095,radius_source);
    bark=mix(vec3(0.11,0.074,0.038)*(0.88+grain*0.3),bark,young);
    float root_age=(1.0-smoothstep(0.0,1.1,p.z))*smoothstep(0.38,0.65,noise3(p*7.0));
    ALBEDO=mix(bark,vec3(0.045,0.043,0.030),root_age*0.75);
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
