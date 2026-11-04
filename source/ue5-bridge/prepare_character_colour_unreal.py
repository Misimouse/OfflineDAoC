"""Create an inactive colour/detail library in an isolated host. Never save a map."""
import hashlib,json,os,sys,traceback
from pathlib import Path
import unreal
R=Path(os.environ['DAOC_CHARACTER_LAB']);sys.path.insert(0,str(Path(__file__).resolve().parent))
from appearance_material_unreal import build_appearance_material
A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools()
C=json.loads((R/'appearance_catalog_prepared.json').read_text(encoding='utf-8-sig'));root='/DAoCVisualBridge/AppearanceColour_v02'
report={'passed':False,'installed':False,'textures':{},'errors':[]}
try:
    for name,source in C['original_color_sources'].items():
        file=Path(source);sha=hashlib.sha256(file.read_bytes()).hexdigest();asset_name='T_Original_'+sha[:20];path=root+'/Textures/'+asset_name;texture=unreal.load_asset(path)
        if not texture:
            task=unreal.AssetImportTask();task.filename=str(file);task.destination_path=root+'/Textures';task.destination_name=asset_name;task.automated=True;task.save=True;task.replace_existing=False;T.import_asset_tasks([task]);texture=unreal.load_asset(path)
        assert texture and texture.get_editor_property('srgb'),name
        report['textures'][name]={'asset':texture.get_path_name(),'sha256':sha,'source':str(file)}
    default=unreal.load_asset(C['textures']['cel_m_head01']);material=build_appearance_material(root+'/Materials','M_OriginalColourDetailSkin',default,False)
    C['materials']['skin']=material.get_path_name();C['original_color_textures']={name:row['asset'] for name,row in report['textures'].items()}
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(['/Engine/EditorMaterials/AssetViewer'],True)
    cube=unreal.load_asset(root+'/T_CharacterAmbient')
    if not cube:cube=A.duplicate_asset('/Engine/EditorMaterials/AssetViewer/T_GreyAmbient',root+'/T_CharacterAmbient')
    assert isinstance(cube,unreal.TextureCube);assert A.save_loaded_asset(cube)
    report['ambient']=cube.get_path_name();C.pop('original_color_sources')
    (R/'appearance_catalog_colour_candidate.json').write_text(json.dumps(C,indent=2),encoding='utf-8');report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(R/'character_colour_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8');assert report['passed'],report['errors']
