shader_type spatial;
uniform sampler2D marble_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D carving : filter_linear_mipmap_anisotropic, repeat_disable;
uniform bool emblem=false;
varying vec3 stone_position;
varying vec3 stone_normal;
void vertex(){stone_position=VERTEX;stone_normal=NORMAL;}
void fragment(){
    vec3 p=stone_position;
    vec3 w=pow(abs(normalize(stone_normal)),vec3(5.0));w/=max(dot(w,vec3(1.0)),.001);
    vec3 marble=texture(marble_albedo,p.yz*.65+vec2(.17,.31)).rgb*w.x+texture(marble_albedo,p.xz*.65+vec2(.23,.57)).rgb*w.y+texture(marble_albedo,p.xy*.65+vec2(.51,.11)).rgb*w.z;
    float mask=0.0;float ink=0.0;
    if(emblem){vec3 glyph=texture(carving,UV2).rgb;ink=1.0-dot(glyph,vec3(.3,.59,.11));mask=smoothstep(.025,.12,ink);}
    vec3 engraved=mix(marble*1.10,marble*.58,smoothstep(.25,.58,ink));
    float age=(1.0-smoothstep(-.1,.75,p.y))*(.45+.25*sin(p.x*3.7+p.z*4.3));
    ALBEDO=mix(mix(marble,engraved,mask),marble*vec3(.72,.77,.64),age*.4)*.78;
    ROUGHNESS=.98;METALLIC=0.0;SPECULAR=0.0;
}
