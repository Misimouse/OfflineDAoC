"""Run only from LiveRidingLab: import missing original taxi assets into its private namespace."""
import hashlib,json,traceback
from pathlib import Path
import unreal
root=Path(__file__).resolve().parent;assert root.name=='LiveRidingLab'
private=Path(unreal.Paths.project_plugins_dir()).resolve()/'DAoCVisualBridge/Content/LiveRiding_v01'
assert private.resolve().is_relative_to(root.resolve()) and not (getattr(private.lstat(),"st_file_attributes",0)&1024)
assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);tools=unreal.AssetToolsHelpers.get_asset_tools()
report={'passed':False,'models':{},'errors':[],'normal_content_modified':False};output=root/'asset_import.json'
try:
    central=root.parent/'models.json';catalog=json.loads(central.read_text(encoding='utf-8-sig'))
    for row in json.loads((root/'SourceModels/exported.json').read_text(encoding='utf-8-sig')):
        ident=row['id'];assert ident=='448' and ident not in catalog
        dest='/DAoCVisualBridge/LiveRiding_v01/Model_'+ident
        existing=assets.list_assets(dest,recursive=True,include_folder=False)
        if not existing:
            task=unreal.AssetImportTask();task.filename=row['file'];task.destination_path=dest;task.automated=True;task.save=True;task.replace_existing=False;tools.import_asset_tasks([task]);existing=assets.list_assets(dest,recursive=True,include_folder=False)
        meshes=[];animations={}
        for path in existing:
            obj=assets.load_asset(path)
            if isinstance(obj,unreal.SkeletalMesh):meshes.append(obj.get_path_name())
            elif isinstance(obj,unreal.AnimSequence):animations[obj.get_name()]=obj.get_path_name()
        assert len(meshes)==1,(meshes,existing)
        entry=dict(asset=meshes[0],type='skeletal',scale=row['scale'],yaw_offset=-90,name=row['name'])
        for name,path in animations.items():
            key=name.removeprefix('model_'+ident).removeprefix('_')
            if key:entry[key]=path
        assert all(key in entry for key in ['idle','walk','run']),entry
        catalog[ident]=entry;report['models'][ident]=entry
    (root/'models.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    report.update(passed=True,catalog_sha256=hashlib.sha256((root/'models.json').read_bytes()).hexdigest(),files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in private.rglob('*') if p.is_file()})
except Exception:report['errors'].append(traceback.format_exc());raise
finally:output.write_text(json.dumps(report,indent=2),encoding='utf-8')
