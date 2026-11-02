"""Import new modular figures; retain original meshes and skeleton assets untouched."""
import json, traceback, hashlib
from pathlib import Path
import unreal

ROOT=Path(__file__).resolve().parent
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'passed':False,'races':{},'errors':[]}
output=ROOT/'Reports/inventory/armor_import.json'
previous=json.loads(output.read_text(encoding='utf-8-sig')).get('races',{}) if output.exists() else {}
def write():output.write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    data=json.loads((ROOT/'SourceArmour/exported.json').read_text(encoding='utf-8-sig'))
    models=json.loads((ROOT/'models.json').read_text(encoding='utf-8-sig'))
    source=json.loads((ROOT/'SourceArmour/textures.json').read_text(encoding='utf-8-sig'))
    library='/DAoCVisualBridge/ModularArmor_v01'
    textures={};tasks=[]
    for name,row in source['textures'].items():
        path=library+'/Textures/'+name
        textures[name]=path+'.'+name
        if assets.does_asset_exist(path):continue
        task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=library+'/Textures';task.destination_name=name;task.automated=True;task.save=True;tasks.append(task)
    for start in range(0,len(tasks),24):
        tools.import_asset_tasks(tasks[start:start+24]);report['textures_imported']=start+len(tasks[start:start+24]);write()
    lib=unreal.MaterialEditingLibrary
    material=unreal.load_asset(library+'/M_OriginalArmor')
    if not material:
        material=tools.create_asset('M_OriginalArmor',library,unreal.Material,unreal.MaterialFactoryNew())
        material.set_editor_property('two_sided',True)
        tex=lib.create_material_expression(material,unreal.MaterialExpressionTextureSampleParameter2D,-700,0)
        tex.set_editor_property('parameter_name','ArmorTexture');tex.set_editor_property('texture',unreal.load_asset(next(iter(textures.values()))))
        # The original renderer multiplies dye in image colour space, then linearizes.
        gamma=lib.create_material_expression(material,unreal.MaterialExpressionPower,-500,0);gamma.set_editor_property('const_exponent',1/2.2);lib.connect_material_expressions(tex,'RGB',gamma,'Base')
        dye=lib.create_material_expression(material,unreal.MaterialExpressionVectorParameter,-500,200);dye.set_editor_property('parameter_name','ArmorDye');dye.set_editor_property('default_value',unreal.LinearColor(1,1,1,1))
        multiply=lib.create_material_expression(material,unreal.MaterialExpressionMultiply,-300,0);lib.connect_material_expressions(gamma,'',multiply,'A');lib.connect_material_expressions(dye,'RGB',multiply,'B')
        linear=lib.create_material_expression(material,unreal.MaterialExpressionPower,-100,0);linear.set_editor_property('const_exponent',2.2);lib.connect_material_expressions(multiply,'',linear,'Base');lib.connect_material_property(linear,'',unreal.MaterialProperty.MP_BASE_COLOR)
        rough=lib.create_material_expression(material,unreal.MaterialExpressionConstant,-100,200);rough.set_editor_property('r',.9);lib.connect_material_property(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
        lib.recompile_material(material);assets.save_loaded_asset(material)
    lib.set_material_usage(material,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    lib.recompile_material(material);assets.save_loaded_asset(material)
    for row in data:
        race=row['race'];destination='/DAoCVisualBridge/ModularArmor_v01/Figures_v02/'+race
        source_sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
        existing=assets.list_assets(destination,recursive=True,include_folder=False)
        if not existing or previous.get(race,{}).get('source_sha256')!=source_sha:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination
            task.automated=True;task.save=True;task.replace_existing=bool(existing)
            tools.import_asset_tasks([task]);existing=assets.list_assets(destination,recursive=True,include_folder=False)
        meshes=[assets.load_asset(p) for p in existing if 'SkeletalMesh' in str(assets.find_asset_data(p).asset_class_path)]
        meshes=[m for m in meshes if isinstance(m,unreal.SkeletalMesh)]
        assert len(meshes)==1,(race,len(meshes))
        mesh=meshes[0];skeleton=mesh.get_editor_property('skeleton')
        base_id={'cel_m':'1984','cel_f':'310','elf_m':'382','elf_f':'388','fir_m':'352','fir_f':'1983','lur_m':'318','lur_f':'378','syl_m':'700'}.get(race)
        if base_id:
            original=unreal.load_asset(models[base_id]['asset']).get_editor_property('skeleton')
            skeleton.add_compatible_skeleton(original);assets.save_loaded_asset(skeleton)
        sections=[]
        for index,slot_material in enumerate(mesh.get_editor_property('materials')):
            name=str(slot_material.material_slot_name)
            descriptor=next((s for s in row['sections'] if s['material']==name),None)
            assert descriptor,(race,index,name)
            sections.append(dict(descriptor,index=index))
        report['races'][race]={'asset':mesh.get_path_name(),'skeleton':skeleton.get_path_name(),'base_id':base_id,'original_asset':models[base_id]['asset'] if base_id else '', 'sections':sections,'clothes':row['clothes'],'variants':row['variants'],'source_sha256':source_sha}
        write()
    armour={'figures':{v['asset']:dict(v,gender='f' if k.endswith('_f') else 'm') for k,v in report['races'].items()},'models':source['models'],'textures':textures,'material':material.get_path_name(),'missing_textures':source['missing']}
    equipment=json.loads((ROOT/'equipment_catalog_v01.json').read_text(encoding='utf-8-sig'));armour['dyes']=equipment.get('dyes',{});equipment['armour']=armour
    (ROOT/'equipment_catalog_armour_candidate.json').write_text(json.dumps(equipment,indent=2),encoding='utf-8')
    # Point aliases at their new figure while retaining all original animation clips.
    substitutions={models[v['base_id']]['asset']:v['asset'] for v in report['races'].values() if v['base_id']}
    for entry in models.values():
        if entry.get('asset') in substitutions:entry['asset']=substitutions[entry['asset']]
    (ROOT/'models_armour_candidate.json').write_text(json.dumps(models,indent=2),encoding='utf-8')
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
write()
assert report['passed'],report['errors']
