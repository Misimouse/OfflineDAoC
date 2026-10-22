shader_type spatial;
// Private four-patch experiment. The original terrain shader is never modified.
uniform sampler2D tile_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D base_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float base_tiles = 256.0;
uniform sampler2D layer_tex[8] : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float layer_tiles[8];
uniform float layer_tileable[8];
uniform int layer_count = 0;
uniform sampler2D weights0 : filter_linear, repeat_disable;
uniform sampler2D weights1 : filter_linear, repeat_disable;
uniform vec2 patch_index;
uniform float patches = 8.0;
uniform float far_fade_m = 260.0;
uniform int soil_index = -1;
uniform int gravel_index = -1;
uniform int trial_mode = 2; // 1 colour only, 2 colour + normal + roughness
uniform sampler2D soil_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D soil_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D soil_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D gravel_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float soil_tiles = 1260.3077; // 1638.4m zone / 1.3m photographed material
uniform float gravel_tiles = 819.2;  // 1638.4m zone / 2m photographed material
uniform float normal_strength = 0.8;
uniform float normal_fade_m = 70.0;
varying vec3 world_pos;

void vertex() {
    world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float layer_weight(int i, vec2 puv) {
    vec4 w = i < 4 ? texture(weights0, puv) : texture(weights1, puv);
    int k = i % 4;
    return k == 0 ? w.r : (k == 1 ? w.g : (k == 2 ? w.b : w.a));
}

void fragment() {
    float dist = length(world_pos - CAMERA_POSITION_WORLD);
    vec3 painted = texture(tile_tex, UV).rgb;
    vec2 puv = UV * patches - patch_index;
    vec2 dx = dFdx(UV);
    vec2 dy = dFdy(UV);
    vec3 c = textureGrad(base_tex, UV * base_tiles, dx * base_tiles, dy * base_tiles).rgb;
    vec3 n = vec3(0.0, 0.0, 1.0);
    float r = 0.95;
    float near_strength = 1.0 - smoothstep(normal_fade_m * 0.5, normal_fade_m, dist);
    for (int i = 0; i < 8; i++) {
        if (i >= layer_count) break;
        float w = layer_weight(i, puv);
        if (w <= 0.002) continue;
        float tiles = layer_tileable[i] > 0.5 ? layer_tiles[i] : 1.0;
        vec3 colour;
        vec3 layer_n = vec3(0.0, 0.0, 1.0);
        float layer_r = 0.95;
        if (i == soil_index) {
            colour = textureGrad(soil_colour, UV * soil_tiles, dx * soil_tiles, dy * soil_tiles).rgb;
            if (trial_mode == 2 && near_strength > 0.001) {
                layer_n = textureGrad(soil_normal, UV * soil_tiles, dx * soil_tiles, dy * soil_tiles).rgb * 2.0 - 1.0;
                layer_r = textureGrad(soil_roughness, UV * soil_tiles, dx * soil_tiles, dy * soil_tiles).r;
            }
        } else if (i == gravel_index) {
            colour = textureGrad(gravel_colour, UV * gravel_tiles, dx * gravel_tiles, dy * gravel_tiles).rgb;
            if (trial_mode == 2 && near_strength > 0.001) {
                layer_n = textureGrad(gravel_normal, UV * gravel_tiles, dx * gravel_tiles, dy * gravel_tiles).rgb * 2.0 - 1.0;
                layer_r = textureGrad(gravel_roughness, UV * gravel_tiles, dx * gravel_tiles, dy * gravel_tiles).r;
            }
        } else {
            colour = textureGrad(layer_tex[i], UV * tiles, dx * tiles, dy * tiles).rgb;
        }
        // Each later overlay attenuates the preceding colour AND its surface detail with the same weight.
        c = mix(c, colour, w);
        n = mix(n, layer_n, w);
        r = mix(r, layer_r, w);
    }
    float far_mix = smoothstep(far_fade_m * 0.6, far_fade_m, dist);
    ALBEDO = mix(c, painted, far_mix);
    ROUGHNESS = clamp(mix(0.95, r, near_strength), 0.55, 1.0);
    SPECULAR = 0.25;
    // Converted ground meshes have no tangent attribute. Derive a frame from their unchanged UVs/positions.
    vec3 pos = (VIEW_MATRIX * vec4(world_pos, 1.0)).xyz;
    vec3 dp1 = dFdx(pos);
    vec3 dp2 = dFdy(pos);
    vec3 dp2perp = cross(dp2, NORMAL);
    vec3 dp1perp = cross(NORMAL, dp1);
    vec3 t = dp2perp * dx.x + dp1perp * dy.x;
    vec3 b = dp2perp * dx.y + dp1perp * dy.y;
    // Whole-zone UVs are tiny per pixel; a world-scale epsilon would erase the close-up normal detail.
    float invlen = inversesqrt(max(max(dot(t, t), dot(b, b)), 1e-30));
    n.xy *= normal_strength * near_strength * (1.0 - far_mix);
    n = normalize(n);
    // OpenGL normal maps: +Y points up the texture, opposite this terrain's increasing V.
    NORMAL = normalize(t * invlen * n.x - b * invlen * n.y + NORMAL * n.z);
}
