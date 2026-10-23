shader_type spatial;
uniform sampler2D tile_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D base_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float base_tiles=256.0;
uniform sampler2D layer_tex[8] : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float layer_tiles[8];
uniform float layer_tileable[8];
uniform int layer_count=0;
uniform sampler2D weights0 : filter_linear, repeat_disable;
uniform sampler2D weights1 : filter_linear, repeat_disable;
uniform vec2 patch_index;
uniform float patches=8.0;
uniform float far_fade_m=260.0;
uniform int soil_index=-1;
uniform int gravel_index=-1;
uniform sampler2D soil_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D soil_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D soil_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float soil_tiles=1260.3077;
uniform float gravel_tiles=819.2;
uniform float normal_strength=.8;
uniform float normal_fade_m=70.0;
uniform sampler2D atlas0 : filter_linear_mipmap, repeat_disable;
uniform sampler2D atlas1 : filter_linear_mipmap, repeat_disable;
uniform sampler2D grass_new : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D scrub_new : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D craggy_new : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D clover_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D rock_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D regional_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec3 regional_mean=vec3(.15,.20,.10);
uniform vec4 pilot_bounds=vec4(1024.0,1024.0,1433.6,1433.6);
uniform float feather_metres=45.0;
varying vec3 world_pos;
void vertex(){world_pos=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;}
float hash2(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise2(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);return mix(mix(hash2(i),hash2(i+vec2(1,0)),f.x),mix(hash2(i+vec2(0,1)),hash2(i+vec2(1)),f.x),f.y);}
vec3 varied(sampler2D tex,vec2 p,vec2 dx,vec2 dy){
    mat2 rotate=mat2(vec2(.745,-.667),vec2(.667,.745));
    vec3 a=textureGrad(tex,p+vec2(.173,.619),dx,dy).rgb;
    vec3 b=textureGrad(tex,rotate*p*1.137+vec2(.731,.271),rotate*dx*1.137,rotate*dy*1.137).rgb;
    vec3 c=mix(a,b,.25+.5*noise2(p*.19))*(.94+.10*noise2(p*.067+vec2(7.3)));
    float grey=dot(c,vec3(.3,.59,.11));
    return mix(c,vec3(grey),.10)*vec3(.88,.94,1.02);
}
float local_weight(int i,vec2 puv){vec4 w=i<4?texture(weights0,puv):texture(weights1,puv);int k=i%4;return k==0?w.r:(k==1?w.g:(k==2?w.b:w.a));}
vec3 baseline(vec2 uv,vec2 dx,vec2 dy,float dist){
    vec3 c=textureGrad(base_tex,uv*base_tiles,dx*base_tiles,dy*base_tiles).rgb;
    vec2 puv=uv*patches-patch_index;
    for(int i=0;i<8;i++){
        if(i>=layer_count)break;float w=local_weight(i,puv);if(w<=.002)continue;
        float tiles=layer_tileable[i]>.5?layer_tiles[i]:1.0;
        vec3 v;
        if(i==soil_index)v=textureGrad(soil_colour,uv*soil_tiles,dx*soil_tiles,dy*soil_tiles).rgb;
        else if(i==gravel_index)v=textureGrad(gravel_colour,uv*gravel_tiles,dx*gravel_tiles,dy*gravel_tiles).rgb;
        else v=textureGrad(layer_tex[i],uv*tiles,dx*tiles,dy*tiles).rgb;
        c=mix(c,v,w);
    }
    return mix(c,texture(tile_tex,uv).rgb,smoothstep(far_fade_m*.6,far_fade_m,dist));
}
void fragment(){
    float dist=length(world_pos-CAMERA_POSITION_WORLD);vec2 dx=dFdx(UV),dy=dFdy(UV);
    vec4 a=texture(atlas0,UV),b=texture(atlas1,UV);
    float physical=max(dot(a,vec4(1.0))+b.x+b.y+b.w,.001);
    vec2 dpdx=dFdx(world_pos.xz),dpdy=dFdy(world_pos.xz);
    vec3 c=varied(grass_new,world_pos.xz/2.5,dpdx/2.5,dpdy/2.5)*a.x;
    c+=textureGrad(soil_colour,UV*soil_tiles,dx*soil_tiles,dy*soil_tiles).rgb*a.y;
    c+=textureGrad(gravel_colour,UV*gravel_tiles,dx*gravel_tiles,dy*gravel_tiles).rgb*a.z;
    c+=varied(scrub_new,world_pos.xz/3.0,dpdx/3.0,dpdy/3.0)*a.w;
    c+=varied(craggy_new,world_pos.xz/3.0,dpdx/3.0,dpdy/3.0)*b.x;
    c+=textureGrad(clover_tex,UV*256.0,dx*256.0,dy*256.0).rgb*b.y;
    c+=textureGrad(rock_tex,UV*256.0,dx*256.0,dy*256.0).rgb*b.w;
    c/=physical;
    vec3 macro=textureLod(regional_tex,UV,5.0).rgb;
    vec3 tint=clamp((macro+vec3(.035))/(regional_mean+vec3(.035)),vec3(.72),vec3(1.25));
    c=mix(c,c*tint,clamp(b.z,0.0,1.0));
    float edge=min(min(world_pos.x-pilot_bounds.x,world_pos.z-pilot_bounds.y),min(pilot_bounds.z-world_pos.x,pilot_bounds.w-world_pos.z));
    float strength=smoothstep(0.0,feather_metres,edge);
    if(strength<.999)c=mix(baseline(UV,dx,dy,dist),c,strength);
    ALBEDO=c;
    float near_strength=1.0-smoothstep(normal_fade_m*.5,normal_fade_m,dist);
    vec3 n=vec3(0,0,1);float rough=.98;
    if(near_strength>.001){
        vec3 ns=textureGrad(soil_normal,UV*soil_tiles,dx*soil_tiles,dy*soil_tiles).rgb*2.0-1.0;
        vec3 ng=textureGrad(gravel_normal,UV*gravel_tiles,dx*gravel_tiles,dy*gravel_tiles).rgb*2.0-1.0;
        n=normalize(vec3(0,0,1)*max(physical-a.y-a.z,0.0)+ns*a.y+ng*a.z);
        rough=(.98*max(physical-a.y-a.z,0.0)+textureGrad(soil_roughness,UV*soil_tiles,dx*soil_tiles,dy*soil_tiles).r*a.y+textureGrad(gravel_roughness,UV*gravel_tiles,dx*gravel_tiles,dy*gravel_tiles).r*a.z)/physical;
    }
    ROUGHNESS=clamp(rough,.65,1.0);SPECULAR=.10;
    vec3 pos=(VIEW_MATRIX*vec4(world_pos,1)).xyz;vec3 dp1=dFdx(pos),dp2=dFdy(pos);
    vec3 p2=cross(dp2,NORMAL),p1=cross(NORMAL,dp1);vec3 t=p2*dx.x+p1*dy.x;vec3 bt=p2*dx.y+p1*dy.y;
    float inverse_length=inversesqrt(max(max(dot(t,t),dot(bt,bt)),1e-30));
    n.xy*=normal_strength*near_strength;n=normalize(n);
    NORMAL=normalize(t*inverse_length*n.x-bt*inverse_length*n.y+NORMAL*n.z);
}
