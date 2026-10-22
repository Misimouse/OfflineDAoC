shader_type spatial;
uniform sampler2D stone_colour : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D stone_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D original_ivy : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform bool flat_ivy = false;
uniform bool neutral = false;
uniform float repeat_m = 1.5;
uniform float normal_strength = 0.55;
varying vec3 local_pos;
varying vec3 local_normal;
varying mat3 normal_to_view;
void vertex() {
    local_pos = VERTEX;
    local_normal = NORMAL;
    normal_to_view = mat3(VIEW_MATRIX) * MODEL_NORMAL_MATRIX;
}
void fragment() {
    vec3 n = normalize(local_normal);
    vec3 w = pow(abs(n), vec3(5.0));
    w /= max(w.x+w.y+w.z, 0.00001);
    vec2 uvx = local_pos.zy / repeat_m;
    vec2 uvy = local_pos.xz / repeat_m;
    vec2 uvz = local_pos.xy / repeat_m;
    vec3 c = texture(stone_colour,uvx).rgb*w.x + texture(stone_colour,uvy).rgb*w.y + texture(stone_colour,uvz).rgb*w.z;
    vec3 nx = texture(stone_normal,uvx).rgb*2.0-1.0;
    vec3 ny = texture(stone_normal,uvy).rgb*2.0-1.0;
    vec3 nz = texture(stone_normal,uvz).rgb*2.0-1.0;
    vec3 detail = vec3(0.0,nx.y,nx.x)*w.x + vec3(ny.x,0.0,-ny.y)*w.y + vec3(nz.x,nz.y,0.0)*w.z;
    NORMAL = normalize(normal_to_view * normalize(n+detail*normal_strength));
    float rough = texture(stone_roughness,uvx).r*w.x+texture(stone_roughness,uvy).r*w.y+texture(stone_roughness,uvz).r*w.z;
    if (neutral) { c=vec3(0.45,0.47,0.49); NORMAL=normalize(normal_to_view*n); rough=0.9; }
    if (flat_ivy && COLOR.a>0.5) {
        vec4 ivy=texture(original_ivy,UV2);
        c=mix(c,c*ivy.rgb,ivy.a);
    }
    ALBEDO = c * COLOR.r;
    ROUGHNESS = clamp(rough,0.72,1.0);
    SPECULAR = 0.25;
}
