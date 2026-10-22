shader_type spatial;
render_mode cull_disabled;
uniform sampler2D bark_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D bark_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D bark_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float texture_scale = 0.32;
uniform float normal_strength = 0.35;
varying vec3 local_pos;
varying vec3 local_normal;
varying mat3 normal_to_view;

// Mix differently phased samples smoothly, keeping the bark grain upright.
// This breaks long bright bands without changing the supplied image pixels.
vec4 varied_sample(sampler2D tex, vec2 uv) {
    float a = 0.33 + 0.15 * sin(dot(uv, vec2(0.71, 0.93)));
    float b = 0.33 + 0.15 * sin(dot(uv, vec2(-0.83, 0.67)) + 1.7);
    return texture(tex, uv) * a
        + texture(tex, uv + vec2(0.371, 0.523)) * b
        + texture(tex, uv + vec2(0.733, 0.217)) * (1.0 - a - b);
}
void vertex() {
    local_pos = VERTEX;
    local_normal = NORMAL;
    normal_to_view = mat3(VIEW_MATRIX) * MODEL_NORMAL_MATRIX;
}
void fragment() {
    vec3 n = normalize(local_normal);
    if (!FRONT_FACING) { n = -n; }
    vec3 w = pow(abs(n), vec3(4.0));
    w /= max(w.x + w.y + w.z, 0.00001);
    // Source tree is Z-up. The two side projections both keep grain along Z.
    vec2 uvx = local_pos.yz * texture_scale;
    vec2 uvy = local_pos.xz * texture_scale;
    vec2 uvz = local_pos.xy * texture_scale;
    ALBEDO = varied_sample(bark_colour, uvx).rgb * w.x
        + varied_sample(bark_colour, uvy).rgb * w.y
        + varied_sample(bark_colour, uvz).rgb * w.z;
    vec3 nx = varied_sample(bark_normal, uvx).xyz * 2.0 - 1.0;
    vec3 ny = varied_sample(bark_normal, uvy).xyz * 2.0 - 1.0;
    vec3 nz = varied_sample(bark_normal, uvz).xyz * 2.0 - 1.0;
    vec3 detail = vec3(0.0, nx.x, nx.y) * w.x
        + vec3(ny.x, 0.0, ny.y) * w.y + vec3(nz.x, nz.y, 0.0) * w.z;
    NORMAL = normalize(normal_to_view * normalize(n + detail * normal_strength));
    ROUGHNESS = clamp(varied_sample(bark_roughness, uvx).r * w.x
        + varied_sample(bark_roughness, uvy).r * w.y
        + varied_sample(bark_roughness, uvz).r * w.z, 0.85, 1.0);
    SPECULAR = 0.12;
}
