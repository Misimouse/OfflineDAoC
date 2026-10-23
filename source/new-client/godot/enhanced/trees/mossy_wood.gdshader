shader_type spatial;
render_mode cull_disabled;
uniform sampler2D bark_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D moss_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool fallen=false;
varying vec3 wood_position;
varying vec3 wood_normal;
float hash3(vec3 p) { return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453); }
float noise3(vec3 p) {
    vec3 a=floor(p);vec3 b=fract(p);b=b*b*(3.0-2.0*b);
    return mix(mix(mix(hash3(a),hash3(a+vec3(1,0,0)),b.x),mix(hash3(a+vec3(0,1,0)),hash3(a+vec3(1,1,0)),b.x),b.y),mix(mix(hash3(a+vec3(0,0,1)),hash3(a+vec3(1,0,1)),b.x),mix(hash3(a+vec3(0,1,1)),hash3(a+vec3(1,1,1)),b.x),b.y),b.z);
}
float moss_mask(vec3 p,vec3 n) {
    float patch=noise3(p*1.7+vec3(7.3,2.1,4.9))*.70+noise3(p*5.5)*.30;
    float habitat=fallen ? smoothstep(-.25,.65,n.z) : (1.0-smoothstep(.35,1.85,p.z))*.80;
    habitat=max(habitat,fallen ? 0.0 : smoothstep(.2,.85,n.z)*.40);
    return smoothstep(.48,.67,patch)*habitat;
}
vec3 triplanar(sampler2D tex,vec3 p,vec3 w) {
    return texture(tex,p.yz).rgb*w.x+texture(tex,p.xz+vec2(.31,.67)).rgb*w.y+texture(tex,p.xy+vec2(.59,.13)).rgb*w.z;
}
void vertex() {
    wood_position=VERTEX;wood_normal=NORMAL;
    VERTEX+=NORMAL*(.015*moss_mask(VERTEX,NORMAL));
}
void fragment() {
    vec3 weights=pow(abs(normalize(wood_normal)),vec3(5.0));weights/=max(dot(weights,vec3(1)),.001);
    vec3 bark=triplanar(bark_albedo,wood_position*.48,weights);
    vec3 moss=triplanar(moss_albedo,wood_position*1.35,weights)*.88;
    float coverage=moss_mask(wood_position,normalize(wood_normal));
    ALBEDO=mix(bark,moss,coverage);
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
