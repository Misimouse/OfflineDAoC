shader_type spatial;
render_mode cull_disabled;
uniform sampler2D needle_albedo : source_color, filter_linear_mipmap_anisotropic;
void fragment() {
    vec3 detail=texture(needle_albedo,vec2(UV.x*.09+.38,UV.y)).rgb;
    float level=dot(detail,vec3(.3,.59,.11));
    ALBEDO=COLOR.rgb*clamp(vec3(.90)+vec3(level-.065)*2.0,vec3(.73),vec3(1.16));
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
