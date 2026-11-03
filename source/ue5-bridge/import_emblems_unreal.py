import unreal,json,traceback,sys
from pathlib import Path
R=Path(__file__).resolve().parent
if str(R) not in sys.path:sys.path.insert(0,str(R))
D=R/'Reports/training_staff_fx_pets'
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
lib=unreal.MaterialEditingLibrary
root='/DAoCVisualBridge/Emblems_v01'
report={'passed':False,'textures':0,'uv_models':0,'errors':[]}
try:
    textures=json.loads((R/'SourceEmblems_v01/textures.json').read_text())
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([root,'/DAoCVisualBridge/Equipment_All_v01'],True)
    tasks=[]
    for name,row in textures.items():
        if assets.does_asset_exist(root+'/Textures/'+name):continue
        t=unreal.AssetImportTask();t.filename=row['file'];t.destination_path=root+'/Textures';t.destination_name=name;t.automated=True;t.save=True;tasks.append(t)
    for i in range(0,len(tasks),32):tools.import_asset_tasks(tasks[i:i+32])
    for name,row in textures.items():
        tex=unreal.load_asset(root+'/Textures/'+name);assert tex,name
        # Original shader samples gamma-space images as data, then converts once at the end.
        tex.set_editor_property('srgb',False)
        tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
        if row.get('pattern'):
            tex.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            tex.set_editor_property('filter',unreal.TextureFilter.TF_BILINEAR)
        if row.get('clamp'):
            tex.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP);tex.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
        assets.save_loaded_asset(tex);report['textures']+=1
    from shield_emblem_material import build_shield_material
    m=build_shield_material(root)
    # Imported emblem meshes must retain the original pattern and logo UV sets.
    c=json.loads((R/'equipment_catalog_v01.json').read_text())['models']
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for ident,row in c.items():
        if not row.get('info',{}).get('emblem'):continue
        mesh=unreal.load_asset(row['asset']);assert isinstance(mesh,unreal.StaticMesh),ident
        if mesh_editor:assert mesh_editor.get_num_uv_channels(mesh,0)>=4,('missing original emblem UVs',ident)
        report['uv_models']+=1
    report['uv_native_verification_required']=mesh_editor is None
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
(D/'emblem_import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['passed'],report['errors']
