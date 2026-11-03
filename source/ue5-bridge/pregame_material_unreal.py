"""Original pregame surface layers, UV sets and vertex lighting, in separate assets."""
import hashlib
from pathlib import Path
import unreal


def build(root, name, definition, folder):
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    lib = unreal.MaterialEditingLibrary
    material = assets.load_asset(root + '/' + name) if assets.does_asset_exist(root + '/' + name) else None
    if material is None:
        material = tools.create_asset(name, root, unreal.Material, unreal.MaterialFactoryNew())
    assert material, name
    lib.delete_all_material_expressions(material)
    spec = definition['spec']
    material.set_editor_property('two_sided', bool(spec.get('double_sided', False)))
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)

    def node(cls):
        return lib.create_material_expression(material, cls, -400, 0)

    def connect(a, pin, b, target):
        if isinstance(a, unreal.MaterialExpressionVertexColor) and pin == 'RGB':
            pin = ''
        if isinstance(b, unreal.MaterialExpressionClamp) and target == 'Input':
            target = ''
        assert lib.connect_material_expressions(a, pin, b, target), (pin, target)

    def constant(value):
        if isinstance(value, (list, tuple)):
            n = node(unreal.MaterialExpressionConstant3Vector)
            n.set_editor_property('constant', unreal.LinearColor(*value[:3], 1))
        else:
            n = node(unreal.MaterialExpressionConstant)
            n.set_editor_property('r', value)
        return n

    def operation(cls, a, b, ap='', bp=''):
        n = node(cls)
        connect(a, ap, n, 'A'); connect(b, bp, n, 'B')
        return n

    def multiply(a, b, ap='', bp=''):
        return operation(unreal.MaterialExpressionMultiply, a, b, ap, bp)

    def lerp(a, b, alpha, ap='', bp='', alphapin=''):
        n = operation(unreal.MaterialExpressionLinearInterpolate, a, b, ap, bp)
        connect(alpha, alphapin, n, 'Alpha')
        return n

    samples = {}
    for slot, layer in definition.get('layers', {}).items():
        source = Path(layer['file'])
        if not source.exists(): source = folder / source.name
        assert source.is_file(), source
        texname = 'T_' + hashlib.sha256(source.read_bytes()).hexdigest()[:20]
        texpath = root + '/' + texname
        if not assets.does_asset_exist(texpath):
            task = unreal.AssetImportTask(); task.filename = str(source)
            task.destination_path = root; task.destination_name = texname
            task.automated = True; task.save = True
            tools.import_asset_tasks([task])
        texture = assets.load_asset(texpath)
        assert isinstance(texture, unreal.Texture2D)
        sample = node(unreal.MaterialExpressionTextureSample)
        sample.set_editor_property('texture', texture)
        uv = node(unreal.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('coordinate_index', int(layer['uv']))
        if not spec.get('slots', {}).get(slot, {}).get('wrap', True):
            clamp = node(unreal.MaterialExpressionClamp)
            clamp.set_editor_property('min_default', 0)
            clamp.set_editor_property('max_default', 1)
            connect(uv, '', clamp, 'Input')
            uv = clamp
        connect(uv, '', sample, 'UVs')
        samples[slot] = sample

    one = constant(1)
    vertex = node(unreal.MaterialExpressionVertexColor)
    base = samples.get('base', one)
    colour = multiply(base, constant(spec.get('tint', [1, 1, 1])), 'RGB' if 'base' in samples else '')
    alpha = multiply(base, constant(spec.get('opacity', 1)), 'A' if 'base' in samples else '')
    if spec.get('blend2') and 'tex1' in samples and 'tex2' in samples:
        colour = lerp(samples['tex2'], samples['tex1'], vertex, 'RGB', 'RGB', 'A')
        colour = multiply(colour, constant(spec.get('tint', [1, 1, 1])))
        alpha = constant(spec.get('opacity', 1))
    for slot in ['dark', 'detail']:
        if slot not in samples: continue
        sample = samples[slot]
        factor = multiply(sample, constant(4.594 if slot == 'detail' and spec.get('detail_x2') else 1), 'RGB')
        if slot == 'dark' and spec.get('dark_plain'):
            alpha = multiply(alpha, sample, bp='A')
        else:
            factor = lerp(one, factor, sample, alphapin='A')
        colour = multiply(colour, factor)
    if 'decal' in samples:
        colour = lerp(colour, samples['decal'], samples['decal'], bp='RGB', alphapin='A')
    if spec.get('vertex_colors'):
        colour = multiply(colour, vertex, bp='RGB')
        if not spec.get('blend2'): alpha = multiply(alpha, vertex, bp='A')
    emissive = spec.get('emissive', [0, 0, 0])
    scale = min(1 if spec.get('vertex_colors') else spec.get('mat_light', 1), 1 - max(emissive))
    # The source realm uses a warm ambient fill; baked vertex/light maps retain
    # the original local shading instead of uniform base-texture emission.
    light = [min(1, emissive[i] + max(0, scale) * [1, .94, .8][i]) for i in range(3)]
    result = multiply(colour, constant(light))
    if 'glow' in samples:
        glow = multiply(samples['glow'], samples['glow'], 'RGB', 'A')
        result = operation(unreal.MaterialExpressionAdd, result, glow)
    mode = spec.get('alpha', 'opaque')
    if mode == 'mask':
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property('opacity_mask_clip_value', spec.get('cut', .5))
        assert lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    elif mode in ['blend', 'add']:
        material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE if mode == 'add' else unreal.BlendMode.BLEND_TRANSLUCENT)
        assert lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    else:
        assert mode == 'opaque', 'Unsupported original blend mode: ' + mode
    assert lib.connect_material_property(result, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(material)
    assets.save_loaded_asset(material)
    return material
