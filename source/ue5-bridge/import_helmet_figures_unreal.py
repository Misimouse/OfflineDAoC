"""Import original helmet assemblies into a separate library; candidates only."""
import copy,hashlib,json,re,traceback
from pathlib import Path
import unreal

R=Path(__file__).resolve().parent;D=R/'Reports/helmets';D.mkdir(parents=True,exist_ok=True)
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
library='/DAoCVisualBridge/Helmets_v01'
report={'passed':False,'models':{},'errors':[],'active_catalog_changed':False}
def write():(D/'import.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    active=R/'equipment_catalog_v01.json';before=hashlib.sha256(active.read_bytes()).hexdigest()
    catalog=json.loads(active.read_text(encoding='utf-8-sig'));models=json.loads((R/'models.json').read_text(encoding='utf-8-sig'))
    helmets={};unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([library],True)
    normalize=lambda name:re.sub(r'[-_ ]','',str(name)).lower()
    for row in json.loads((R/'SourceHelmets/exported.json').read_text(encoding='utf-8-sig')):
        key=row['race']+'/'+str(row['model']);sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
        destination=library+'/'+row['race']+'_'+sha[:16]
        existing=assets.list_assets(destination,recursive=True,include_folder=False)
        if not existing:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=destination;task.automated=True;task.save=True;task.replace_existing=False
            tools.import_asset_tasks([task]);existing=assets.list_assets(destination,recursive=True,include_folder=False)
        meshes=[assets.load_asset(path) for path in existing if 'SkeletalMesh' in str(assets.find_asset_data(path).asset_class_path)]
        assert len(meshes)==1,(key,'expected one original skeleton assembly',len(meshes))
        mesh=meshes[0];assert isinstance(mesh,unreal.SkeletalMesh)
        body=unreal.load_asset(models[str(row['base_id'])]['asset'])
        source=unreal.SkeletonModifier();target=unreal.SkeletonModifier();assert source.set_skeletal_mesh(body) and target.set_skeletal_mesh(mesh)
        body_names={normalize(n):n for n in source.get_all_bone_names()}
        for name in target.get_all_bone_names():
            assert normalize(name) in body_names,(key,'missing leader bone',str(name))
            a=source.get_bone_transform(body_names[normalize(name)],True);b=target.get_bone_transform(name,True)
            assert a.translation.distance(b.translation)<.1,(key,'reference translation mismatch',str(name))
            dot=sum(getattr(a.rotation,axis)*getattr(b.rotation,axis) for axis in ('x','y','z','w'))
            assert abs(dot)>.99999,(key,'reference rotation mismatch',str(name))
        skeleton=mesh.get_editor_property('skeleton');skeleton.add_compatible_skeleton(body.get_editor_property('skeleton'));assets.save_loaded_asset(skeleton)
        sections=[]
        for index,material in enumerate(mesh.get_editor_property('materials')):
            descriptor=next((v for v in row['sections'] if v['material']==str(material.material_slot_name)),None)
            assert descriptor,(key,'material descriptor',str(material.material_slot_name))
            sections.append(dict(descriptor,index=index))
        entry={'asset':mesh.get_path_name(),'full':row['full'],'sections':sections,'hair_mode':row['hair_mode'],'source_sha256':sha}
        helmets.setdefault(str(row['base_id']),{})[str(row['model'])]=entry
        report['models'][key]=entry
        if len(report['models'])%20==0:
            write()
            unreal.SystemLibrary.collect_garbage()
    catalog['armour']['helmets']=helmets
    assert hashlib.sha256(active.read_bytes()).hexdigest()==before
    (R/'equipment_catalog_helmets_candidate.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    report['passed']=True
except Exception:report['errors'].append(traceback.format_exc())
write();assert report['passed'],report['errors']
