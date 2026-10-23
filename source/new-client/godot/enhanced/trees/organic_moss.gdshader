shader_type spatial;
render_mode cull_disabled;
uniform sampler2D bark_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D moss_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
varying vec3 wood_position;
varying vec3 wood_normal;
float field(vec3 p) {
    vec3 q=p+vec3(sin(p.y*1.33+p.z),sin(p.z*1.51-p.x),cos(p.x*1.17+p.y))*.52;
    return .50+.17*sin(q.x*2.37+q.y*.83)+.15*cos(q.y*1.69+q.z*1.21)+.12*sin(q.z*3.11-q.x*1.07)+.035*sin(q.x*13.7+q.y*11.3+q.z*15.9);
}
float moss_mask(vec3 p,vec3 n) {
    float habitat=smoothstep(-.18,.56,n.z);
    return smoothstep(.52,.72,field(p*1.05+vec3(2.7,5.1,1.3)))*habitat;
}
vec3 triplanar(sampler2D tex,vec3 p,vec3 w) {
    return texture(tex,p.yz).rgb*w.x+texture(tex,p.xz+vec2(.31,.67)).rgb*w.y+texture(tex,p.xy+vec2(.59,.13)).rgb*w.z;
}
void vertex() {
    wood_position=VERTEX;wood_normal=NORMAL;
    VERTEX+=NORMAL*(.012*moss_mask(VERTEX,NORMAL));
}
void fragment() {
    vec3 weights=pow(abs(normalize(wood_normal)),vec3(5));weights/=max(dot(weights,vec3(1)),.001);
    vec3 bark=triplanar(bark_albedo,wood_position*.48,weights);
    vec3 moss=triplanar(moss_albedo,wood_position*1.35,weights)*.82;
    ALBEDO=mix(bark,moss,moss_mask(wood_position,normalize(wood_normal)));
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
