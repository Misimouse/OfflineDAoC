"""Read AssetRegistry dependencies; set DAOC_BRIDGE_WORKSPACE and DAOC_BRIDGE_PRIVATE_LAB.

Run as an Unreal Python commandlet in a project that mounts the installed bridge
content. No assets or maps are loaded for editing or saved by this script.
"""
import hashlib
import json
import os
from pathlib import Path

import unreal

workspace = Path(os.environ['DAOC_BRIDGE_WORKSPACE']).resolve()
lab = Path(os.environ['DAOC_BRIDGE_PRIVATE_LAB']).resolve()
assert lab.is_relative_to(workspace) and lab != workspace
content = workspace / 'Client/Plugins/DAoCVisualBridge/Content'
catalog = json.loads((workspace / 'equipment_catalog_v01.json').read_text(encoding='utf-8-sig'))
selected = {ident: catalog['models'][ident] for ident in ['19', '59', '445', '454']}
registry = unreal.AssetRegistryHelpers.get_asset_registry()
registry.scan_paths_synchronous(['/DAoCVisualBridge/Equipment_All_v01'], True)
options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,
    include_soft_package_references=True, include_searchable_names=False,
    include_hard_management_references=False, include_soft_management_references=False)
queue = [row['asset'].split('.')[0] for row in selected.values()]
seen, external = set(), set()
while queue:
    package = queue.pop()
    if package in seen:
        continue
    seen.add(package)
    for value in registry.get_dependencies(unreal.Name(package), options):
        name = str(value)
        if name.startswith('/DAoCVisualBridge/'):
            if name not in seen:
                queue.append(name)
        else:
            external.add(name)
files = []
for package in sorted(seen):
    relative = package.removeprefix('/DAoCVisualBridge/')
    path = content / (relative + '.uasset')
    assert path.resolve().is_relative_to(content.resolve()) and path.exists(), str(path)
    for suffix in ['.uasset', '.uexp', '.ubulk']:
        candidate = path.with_suffix(suffix)
        if candidate.exists():
            files.append({'source': str(candidate), 'relative': candidate.relative_to(content).as_posix(),
                'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(), 'bytes': candidate.stat().st_size})
report = {'passed': True, 'installed': False, 'source_assets_modified': False,
    'models': selected, 'files': files, 'engine_dependencies': sorted(external)}
(lab / 'starter_weapon_dependencies.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('SHAR_STARTER_DEPENDENCIES_PASS files=' + str(len(files)))
