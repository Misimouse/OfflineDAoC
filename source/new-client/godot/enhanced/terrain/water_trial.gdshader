shader_type spatial;
render_mode cull_disabled, depth_draw_never, blend_mix, specular_schlick_ggx;
uniform sampler2D bump_tex : filter_linear_mipmap, repeat_enable;
uniform sampler2D env_tex : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform vec3 sky_color : source_color=vec3(0.55,0.68,0.78);
uniform vec3 sun_dir=vec3(0.4,0.7,0.5);
uniform vec3 sun_color : source_color=vec3(1.0,0.95,0.86);
uniform vec2 drift=vec2(-0.0185,-0.0074);
uniform vec3 river_colour : source_color=vec3(0.12,0.23,0.19);
uniform bool waves=true;
uniform bool neutral=false;
uniform float time_override=-1.0;
uniform float micro_strength=1.0;
uniform float geometry_scale=1.0;
varying vec3 world_pos;
varying float bank_depth;
varying float wave_attenuation;

vec3 wave_field(vec2 p,float t) {
    // One prevailing current with slowly curved, nonuniform crests: no perpendicular wave lattice.
    vec2 direction=normalize(vec2(1.0,0.35));
    vec2 across=vec2(-direction.y,direction.x);
    float u=dot(p,direction);
    float v=dot(p,across);
    vec3 fu=vec3(0.17,0.12,0.22);
    vec3 fv=vec3(0.23,-0.19,0.13);
    vec3 bend=fu*u+fv*v+vec3(-0.12,0.09,0.07)*t;
    vec3 strength=vec3(0.50,0.65,0.40);
    // Broader spacing (9, 6.5 and 4.8 metres), with short irregular crest groups across the current.
    vec3 k=vec3(0.698132,0.966644,1.308997);
    vec3 phase=k*u+strength*sin(bend)+vec3(0.0,2.3,0.5)-vec3(0.90,1.20,1.60)*t;
    vec3 a=vec3(0.022,0.012,0.006);
    vec3 eu=vec3(0.13,-0.09,0.17);
    vec3 ev=vec3(0.45,0.31,-0.52);
    vec3 envelope_phase=eu*u+ev*v+vec3(0.09,-0.07,0.05)*t;
    vec3 group=0.5+0.5*sin(envelope_phase);
    vec3 envelope=0.18+0.82*group*group;
    vec3 envelope_derivative=0.82*group*cos(envelope_phase);
    vec3 cs=cos(phase)*a*envelope;
    vec3 edge=sin(phase)*a*envelope_derivative;
    vec2 gradient=direction*(dot(cs,k+strength*cos(bend)*fu)+dot(edge,eu))+across*(dot(cs,strength*cos(bend)*fv)+dot(edge,ev));
    return vec3(dot(sin(phase),a*envelope),gradient);
}
// Restore irregular texture-based detail; crossed high-frequency sine waves made a visible micro grid.
vec2 fine_ripples(vec2 p,float t) {
    vec2 a=texture(bump_tex,p/3.5+drift*t*1.4,1.0).rg*2.0-1.0;
    vec2 b=texture(bump_tex,p.yx/1.7-drift.yx*t*0.7,1.0).rg*2.0-1.0;
    return a*0.040+b*0.018;
}
void vertex() {
    float t=time_override>=0.0 ? time_override:TIME;
    world_pos=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    bank_depth=COLOR.r*4.0;
    vec3 eye=INV_VIEW_MATRIX[3].xyz;
    wave_attenuation=smoothstep(0.035,0.65,bank_depth)*(1.0-smoothstep(45.0,85.0,distance(eye,world_pos)));
    if(waves) {
        VERTEX.y+=wave_field(world_pos.xz,t).x*wave_attenuation*geometry_scale;
        world_pos=(MODEL_MATRIX*vec4(VERTEX,1.0)).xyz;
    }
}
void fragment() {
    float t=time_override>=0.0 ? time_override:TIME;
    vec2 p=world_pos.xz;
    vec3 field=wave_field(p,t);
    vec2 ripples=fine_ripples(p,t);
    float eye_distance=distance(INV_VIEW_MATRIX[3].xyz,world_pos);
    float ripple_fade=1.0-smoothstep(45.0,180.0,eye_distance);
    float normal_attenuation=smoothstep(0.035,0.65,bank_depth)*(1.0-smoothstep(25.0,130.0,eye_distance));
    vec2 slope=(waves ? field.yz*normal_attenuation:vec2(0.0))+ripples*ripple_fade*micro_strength;
    vec3 n=normalize(vec3(-slope.x,1.0,-slope.y));
    vec3 eye=normalize(INV_VIEW_MATRIX[3].xyz-world_pos);
    if(eye.y<0.0)n=-n;
    NORMAL=normalize(mat3(VIEW_MATRIX)*n);
    float raw=texture(depth_tex,SCREEN_UV).r;
    #if CURRENT_RENDERER == RENDERER_COMPATIBILITY
    vec3 ndc=vec3(SCREEN_UV,raw)*2.0-1.0;
    #else
    vec3 ndc=vec3(SCREEN_UV*2.0-1.0,raw);
    #endif
    vec4 bed=INV_PROJECTION_MATRIX*vec4(ndc,1.0);
    bed.xyz/=bed.w;
    float thickness=max(0.0,-bed.z+VERTEX.z);
    float absorption=1.0-exp(-thickness*0.30);
    float fresnel=0.025+0.975*pow(1.0-clamp(dot(n,eye),0.0,1.0),5.0);
    vec3 reflection=reflect(-eye,n);
    vec2 env_uv=reflection.xz/(abs(reflection.y)+0.28)*0.35+vec2(t*0.003,0.0);
    vec3 clouds=texture(env_tex,env_uv).rgb;
    vec3 reflected_sky=sky_color*mix(vec3(0.62),clouds*1.35,0.55);
    ALBEDO=river_colour*mix(0.55,1.0,exp(-thickness*0.12));
    EMISSION=reflected_sky*fresnel*0.85;
    ROUGHNESS=0.20+length(ripples)*0.35;
    SPECULAR=0.52;
    METALLIC=0.0;
    float edge=smoothstep(0.01,0.18,thickness);
    ALPHA=clamp((0.04+absorption*0.88)*(1.0-fresnel)+fresnel,0.0,0.97)*edge;
    if(neutral) { ALBEDO=vec3(0.36); EMISSION=vec3(0.0); ALPHA=1.0; ROUGHNESS=0.75; }
}
