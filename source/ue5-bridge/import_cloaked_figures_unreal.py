"""Import separate cloak-capable figures and write candidate catalogues only."""
import json,traceback,hashlib,copy
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Reports/cosmetics';OUT.mkdir(parents=True,exist_ok=True)
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools();lib=unreal.MaterialEditingLibrary
report={'passed':False,'races':{},'errors':[],'active_catalogues_modified':False}
def write():(OUT/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    equipment=json.loads((ROOT/'equipment_catalog_v01.json').read_text(encoding='utf-8-sig'))
    models=json.loads((ROOT/'models.json').read_text(encoding='utf-8-sig'))
    catalogue=equipment['armour'];library='/DAoCVisualBridge/CloakedFigures_v01'
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([library],True)
    source=json.loads((ROOT/'SourceCosmetics/exported.json').read_text(encoding='utf-8-sig'))
    # This material uses the original cape's three UV sets, not shield UV indices.
    material=unreal.load_asset(library+'/M_OriginalCloak')
    if not material:
        material=tools.create_asset('M_OriginalCloak',library,unreal.Material,unreal.MaterialFactoryNew())
    if material:
        # Only this new candidate material is rebuilt; existing armour and shields stay untouched.
        lib.delete_all_material_expressions(material)
        def link(source,pin,destination,input_name):
            assert lib.connect_material_expressions(source,pin,destination,input_name),(source,pin,destination,input_name)
        def output(source,pin,property):
            assert lib.connect_material_property(source,pin,property),(source,pin,property)
        material.set_editor_property('two_sided',False)
        def node(cls,x,y):return lib.create_material_expression(material,cls,x,y)
        surface=node(unreal.MaterialExpressionTextureSampleParameter2D,-1200,0)
        surface.set_editor_property('parameter_name','ArmorTexture');surface.set_editor_property('texture',unreal.load_asset(catalogue['textures']['cat_cloak']))
        gamma=node(unreal.MaterialExpressionPower,-1000,0);gamma.set_editor_property('const_exponent',1/2.2);link(surface,'RGB',gamma,'Base')
        dye=node(unreal.MaterialExpressionVectorParameter,-1000,-220);dye.set_editor_property('parameter_name','ArmorDye');dye.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
        plain=node(unreal.MaterialExpressionMultiply,-700,-150);link(gamma,'',plain,'A');link(dye,'RGB',plain,'B')
        samples={}
        for i,(param,uv,default) in enumerate([('Pattern',1,equipment['emblems']['patterns']['512']),('Logo',2,equipment['emblems']['logos']['1'])]):
            coord=node(unreal.MaterialExpressionTextureCoordinate,-1200,240+i*200);coord.set_editor_property('coordinate_index',uv)
            sample=node(unreal.MaterialExpressionTextureSampleParameter2D,-1000,240+i*200);sample.set_editor_property('parameter_name',param);sample.set_editor_property('texture',unreal.load_asset(default));sample.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            link(coord,'',sample,'UVs');samples[param]=sample
        has_logo=node(unreal.MaterialExpressionScalarParameter,-800,650);has_logo.set_editor_property('parameter_name','HasLogo');has_logo.set_editor_property('default_value',0)
        one=node(unreal.MaterialExpressionConstant,-800,550);one.set_editor_property('r',1)
        logo=node(unreal.MaterialExpressionLinearInterpolate,-550,480);link(one,'',logo,'A');link(samples['Logo'],'R',logo,'B');link(has_logo,'',logo,'Alpha')
        pattern=node(unreal.MaterialExpressionMultiply,-700,150);link(gamma,'',pattern,'A');link(samples['Pattern'],'RGB',pattern,'B')
        double=node(unreal.MaterialExpressionMultiply,-500,150);double.set_editor_property('const_b',2);link(pattern,'',double,'A')
        product=node(unreal.MaterialExpressionMultiply,-300,150);link(double,'',product,'A');link(logo,'',product,'B')
        clamp=node(unreal.MaterialExpressionClamp,-100,150);link(product,'',clamp,'')
        has_emblem=node(unreal.MaterialExpressionScalarParameter,-300,-350);has_emblem.set_editor_property('parameter_name','HasEmblem');has_emblem.set_editor_property('default_value',0)
        choose=node(unreal.MaterialExpressionLinearInterpolate,120,0);link(plain,'',choose,'A');link(clamp,'',choose,'B');link(has_emblem,'',choose,'Alpha')
        linear=node(unreal.MaterialExpressionPower,340,0);linear.set_editor_property('const_exponent',2.2);link(choose,'',linear,'Base');output(linear,'',unreal.MaterialProperty.MP_BASE_COLOR)
        for property,value,y in [(unreal.MaterialProperty.MP_ROUGHNESS,.85,180),(unreal.MaterialProperty.MP_SPECULAR,.3,320)]:
            constant=node(unreal.MaterialExpressionConstant,340,y);constant.set_editor_property('r',value);output(constant,'',property)
        lib.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH);lib.recompile_material(material);assets.save_loaded_asset(material)
    catalogue['cloak_material']=material.get_path_name();catalogue['cloak_emblems']=copy.deepcopy(equipment['emblems'])
    for row in source:
        race=row['race'];ident=str(row['base_id']);old_asset=models[ident]['asset'];old=catalogue['figures'][old_asset]
        sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest();destination=library+'/Figures/'+race+'_'+sha[:12]
        existing=assets.list_assets(destination,recursive=True,include_folder=False)
        if not existing:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False
            tools.import_asset_tasks([task]);existing=assets.list_assets(destination,recursive=True,include_folder=False)
        meshes=[assets.load_asset(p) for p in existing if 'SkeletalMesh' in str(assets.find_asset_data(p).asset_class_path)]
        meshes=[m for m in meshes if isinstance(m,unreal.SkeletalMesh)];assert len(meshes)==1,(race,len(meshes))
        mesh=meshes[0];skeleton=mesh.get_editor_property('skeleton');original=unreal.load_asset(old['original_asset']).get_editor_property('skeleton')
        skeleton.add_compatible_skeleton(original);assets.save_loaded_asset(skeleton)
        sections=[]
        for index,mat in enumerate(mesh.get_editor_property('materials')):
            name=str(mat.material_slot_name);descriptor=next((s for s in row['sections'] if s['material']==name),None);assert descriptor,(race,index,name)
            sections.append(dict(descriptor,index=index))
        definition=dict(old,asset=mesh.get_path_name(),skeleton=skeleton.get_path_name(),sections=sections,clothes=row['clothes'],variants=row['variants'],cloaks=row['cloaks'],source_sha256=sha)
        del catalogue['figures'][old_asset];catalogue['figures'][mesh.get_path_name()]=definition
        for entry in models.values():
            if entry.get('asset')==old_asset:entry['asset']=mesh.get_path_name()
        report['races'][race]=definition;write()
    (ROOT/'equipment_catalog_cloaks_candidate.json').write_text(json.dumps(equipment,indent=2),encoding='utf-8')
    (ROOT/'models_cloaks_candidate.json').write_text(json.dumps(models,indent=2),encoding='utf-8')
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
write();assert report['passed'],report['errors']
