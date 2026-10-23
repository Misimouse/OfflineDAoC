shader_type spatial;
render_mode cull_disabled, alpha_to_coverage;
uniform sampler2D leaf_atlas : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D cellular_detail : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 detail_mean=vec3(0.10,0.20,0.03);
uniform vec4 atlas_tint : source_color=vec4(1.0);
uniform float original_cutoff=0.38;
void fragment() {
    vec4 original=texture(leaf_atlas,UV)*atlas_tint;
    vec3 micro=clamp(texture(cellular_detail,UV*3.0).rgb/max(detail_mean,vec3(0.001)),vec3(0.72),vec3(1.28));
    ALBEDO=original.rgb*mix(vec3(1.0),micro,0.55);
    ALPHA=original.a;
    ALPHA_SCISSOR_THRESHOLD=original_cutoff;
    ALPHA_ANTIALIASING_EDGE=0.25;
    ALPHA_TEXTURE_COORDINATE=UV*vec2(textureSize(leaf_atlas,0));
    if (!FRONT_FACING) { NORMAL=-NORMAL; }
    ROUGHNESS=0.98;SPECULAR=0.0;METALLIC=0.0;
}
