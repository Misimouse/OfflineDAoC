"""Extend the original lobby sky behind its finite panorama; never save a map."""
import hashlib
import json
import os
from pathlib import Path
import unreal

root = Path(os.environ['DAOC_BRIDGE_WORKSPACE'])
source = root / 'SourcePregame_v03'
definitions = json.loads((source / 'hibernia_lobby.glb.materials.json').read_text())
matches = [d for d in definitions if d.get('layers', {}).get('base', {}).get('source', '').endswith('/hib_clouds.png')]
assert len(matches) == 1
definition = matches[0]
texture_file = source / Path(definition['layers']['base']['file']).name
assert texture_file.is_file()
texture_path = '/DAoCVisualBridge/Pregame_v03/T_' + hashlib.sha256(texture_file.read_bytes()).hexdigest()[:20]
texture = unreal.load_asset(texture_path)
assert isinstance(texture, unreal.Texture2D)
folder = '/DAoCVisualBridge/PregameSky_v01'
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
material = unreal.load_asset(folder + '/M_OriginalClouds')
if not material:
    material = tools.create_asset('M_OriginalClouds', folder, unreal.Material, unreal.MaterialFactoryNew())
lib = unreal.MaterialEditingLibrary
lib.delete_all_material_expressions(material)
material.set_editor_property('two_sided', True)
material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
sample = lib.create_material_expression(material, unreal.MaterialExpressionTextureSample, -300, 0)
sample.set_editor_property('texture', texture)
assert lib.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.recompile_material(material)
assert assets.save_loaded_asset(material)
report = {'passed': True, 'material': material.get_path_name(), 'original_texture': texture_path,
          'source_sha256': hashlib.sha256(texture_file.read_bytes()).hexdigest(), 'map_saved': False}
output = root / 'Reports/appearance/pregame_sky_import.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
