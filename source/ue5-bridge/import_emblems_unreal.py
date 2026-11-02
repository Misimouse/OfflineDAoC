import unreal,json,traceback
from pathlib import Path
R=Path(__file__).resolve().parent
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
    m=unreal.load_asset(root+'/M_OriginalShieldEmblem')
    if not m:
        m=tools.create_asset('M_OriginalShieldEmblem',root,unreal.Material,unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(m)
    m.set_editor_property('two_sided',False)
    def node(cls,x,y):return lib.create_material_expression(m,cls,x,y)
    samples=[]
    for i,(param,uvindex,default) in enumerate([('Surface',0,'Surface_sh_wood01'),('Pattern',3,'Pattern_512'),('Logo',1,'Logo_1')]):
        uv=node(unreal.MaterialExpressionTextureCoordinate,-1100,i*200);uv.set_editor_property('coordinate_index',uvindex)
        tex=node(unreal.MaterialExpressionTextureSampleParameter2D,-900,i*200);tex.set_editor_property('parameter_name',param);tex.set_editor_property('texture',unreal.load_asset(root+'/Textures/'+default));tex.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        lib.connect_material_expressions(uv,'',tex,'Coordinates');samples.append(tex)
    has=node(unreal.MaterialExpressionScalarParameter,-650,550);has.set_editor_property('parameter_name','HasLogo');has.set_editor_property('default_value',0)
    one=node(unreal.MaterialExpressionConstant,-650,430);one.set_editor_property('r',1)
    logo=node(unreal.MaterialExpressionLinearInterpolate,-400,400);lib.connect_material_expressions(one,'',logo,'A');lib.connect_material_expressions(samples[2],'R',logo,'B');lib.connect_material_expressions(has,'',logo,'Alpha')
    mul=node(unreal.MaterialExpressionMultiply,-400,0);lib.connect_material_expressions(samples[0],'RGB',mul,'A');lib.connect_material_expressions(samples[1],'RGB',mul,'B')
    double=node(unreal.MaterialExpressionMultiply,-200,0);double.set_editor_property('const_b',2);lib.connect_material_expressions(mul,'',double,'A')
    product=node(unreal.MaterialExpressionMultiply,0,0);lib.connect_material_expressions(double,'',product,'A');lib.connect_material_expressions(logo,'',product,'B')
    clamp=node(unreal.MaterialExpressionClamp,200,0);lib.connect_material_expressions(product,'',clamp,'Input')
    linear=node(unreal.MaterialExpressionPower,400,0);linear.set_editor_property('const_exponent',2.2);lib.connect_material_expressions(clamp,'',linear,'Base');lib.connect_material_property(linear,'',unreal.MaterialProperty.MP_BASE_COLOR)
    rough=node(unreal.MaterialExpressionConstant,400,200);rough.set_editor_property('r',.9);lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
    lib.recompile_material(m);assets.save_loaded_asset(m)
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
