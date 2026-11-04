"""Create inactive, versioned arm/hand textures and materials in the character lab."""
import hashlib,json,os,sys,traceback
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from appearance_material_unreal import build_appearance_material

root=Path(os.environ['DAOC_SKIN_DETAIL_LAB']).resolve()
assert Path(unreal.Paths.project_dir()).resolve()==root.parent/'Host'
content=(root.parent/'Host/Plugins/DAoCVisualBridge/Content').resolve();assert content.is_relative_to(root.parent)
meta=json.loads((root/'colour_calibration.json').read_text());assert meta['passed'] and not meta['generated_pixels_modified']
catalog=json.loads((root/'Baseline/appearance.json').read_text(encoding='utf-8-sig'))
bundle=hashlib.sha256(json.dumps(meta,sort_keys=True).encode()).hexdigest()[:12]
destination='/DAoCVisualBridge/ArmHandDetail_v01/'+bundle
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'passed':False,'installed':False,'bundle':destination,'textures':{},'errors':[]}
try:
    for key,row in meta['textures'].items():
        source=Path(row['source']);assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
        name='T_'+key+'_'+row['sha256'][:12];path=destination+'/Textures/'+name;texture=unreal.load_asset(path)
        if not texture:
            task=unreal.AssetImportTask();task.filename=str(source);task.destination_path=destination+'/Textures';task.destination_name=name;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);texture=unreal.load_asset(path)
        assert texture and texture.get_editor_property('srgb')
        # Resize during the engine's texture build, with no padding or UV shift.
        # This gives generated non-power-of-two PNGs a complete GPU mip chain.
        texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION)
        texture.set_editor_property('resize_during_build_x',row['build_dimensions'][0]);texture.set_editor_property('resize_during_build_y',row['build_dimensions'][1])
        texture.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP);assert assets.save_loaded_asset(texture)
        normal_texture=None;normal=row.get('normal')
        if normal:
            normal_source=Path(normal['source']);assert hashlib.sha256(normal_source.read_bytes()).hexdigest()==normal['sha256']
            normal_name='N_'+key+'_'+normal['sha256'][:12];normal_path=destination+'/Textures/'+normal_name;normal_texture=unreal.load_asset(normal_path)
            if not normal_texture:
                task=unreal.AssetImportTask();task.filename=str(normal_source);task.destination_path=destination+'/Textures';task.destination_name=normal_name;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);normal_texture=unreal.load_asset(normal_path)
            assert normal_texture
            normal_texture.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP);normal_texture.set_editor_property('srgb',False)
            normal_texture.set_editor_property('power_of_two_mode',unreal.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION);normal_texture.set_editor_property('resize_during_build_x',row['build_dimensions'][0]);normal_texture.set_editor_property('resize_during_build_y',row['build_dimensions'][1]);normal_texture.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP);assert assets.save_loaded_asset(normal_texture)
        material=build_appearance_material(destination+'/Materials','M_'+key,texture,False,original_colour_strength=0,skin_colour_scale=row['skin_colour_scale'],normal_texture=normal_texture,normal_strength=normal.get('strength',.5) if normal else .5)
        catalog['textures'][key]=texture.get_path_name();catalog.setdefault('surface_materials',{})[key]=material.get_path_name()
        report['textures'][key]={'texture':texture.get_path_name(),'normal_texture':normal_texture.get_path_name() if normal_texture else None,'material':material.get_path_name(),'skin_colour_scale':row['skin_colour_scale'],'build_dimensions':row['build_dimensions'],'original_mask_texture':catalog['original_color_textures'][key]}
    (root/'appearance_candidate.json').write_text(json.dumps(catalog,indent=2));report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(root/'import_report.json').write_text(json.dumps(report,indent=2));assert report['passed'],report['errors']
