"""Read asset-registry dependencies without loading all character/equipment meshes."""
import json,os,traceback
from pathlib import Path
import unreal

inputs=Path(os.environ['DAOC_STEALTH_COVERAGE_INPUTS']).resolve()
output=Path(os.environ['DAOC_STEALTH_COVERAGE_OUTPUT']).resolve();output.parent.mkdir(parents=True,exist_ok=True)
report={'passed':False,'read_only':True,'meshes':0,'materials':[],'missing_meshes':[],'errors':[]}
try:
    data=json.loads(inputs.read_text(encoding='utf-8-sig'))
    registry=unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous(['/DAoCVisualBridge'],force_rescan=False)
    registry.wait_for_completion()
    options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=False)
    materials=set(data.get('materials',[]))
    for path in data['meshes']:
        package=path.split('.')[0]
        rows=registry.get_assets_by_package_name(package)
        if not rows:report['missing_meshes'].append(path);continue
        report['meshes']+=1
        for dependency in registry.get_dependencies(package,options) or []:
            for asset in registry.get_assets_by_package_name(dependency):
                if str(asset.asset_class_path.asset_name) in ['Material','MaterialInstanceConstant']:
                    materials.add(str(asset.package_name)+'.'+str(asset.asset_name))
    report['materials']=sorted(materials);report['passed']=bool(materials) and not report['missing_meshes']
except Exception:report['errors'].append(traceback.format_exc())
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['passed'],report['errors'] or report['missing_meshes']
