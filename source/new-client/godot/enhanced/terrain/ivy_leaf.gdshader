shader_type spatial;
render_mode cull_disabled;
float strand(vec2 p,vec2 a,vec2 b) {
    vec2 d=b-a;
    float h=clamp(dot(p-a,d)/dot(d,d),0.0,1.0);
    return 1.0-smoothstep(0.003,0.012,length(p-a-d*h));
}
float noise2(vec2 p) {
    vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
    vec4 h=fract(sin(vec4(dot(i,vec2(127.1,311.7)),dot(i+vec2(1,0),vec2(127.1,311.7)),dot(i+vec2(0,1),vec2(127.1,311.7)),dot(i+vec2(1,1),vec2(127.1,311.7))))*43758.5453);
    return mix(mix(h.x,h.y,f.x),mix(h.z,h.w,f.x),f.y);
}
void fragment() {
    vec2 stem=vec2(0.0,-0.38);
    float vein=strand(UV,stem,vec2(0.0,0.59));
    for(int side=-1;side<=1;side+=2) {
        float s=float(side);
        vein=max(vein,strand(UV,stem,vec2(s*0.54,0.23))*0.8);
        vein=max(vein,strand(UV,stem,vec2(s*0.47,-0.25))*0.7);
        for(int row=0;row<4;row++) {
            float y=float(row)*0.16-0.20;
            vein=max(vein,strand(UV,vec2(0.0,y),vec2(s*(0.33-y*0.28),y+0.20))*0.45);
        }
    }
    float tissue=mix(0.72,1.12,noise2(UV*16.0))*mix(0.94,1.04,noise2(UV*91.0));
    vec3 base=COLOR.rgb*tissue;
    ALBEDO=mix(base,base*1.25+vec3(0.022,0.025,0.008),vein*0.72);
    ROUGHNESS=0.68+noise2(UV*12.0)*0.15;
    SPECULAR=0.3;
}
