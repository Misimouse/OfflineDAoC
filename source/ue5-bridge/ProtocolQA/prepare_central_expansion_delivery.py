"""Prepare additive expansion catalogs, preserving the current central visual calibration."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def prepare(workspace):
    workspace = workspace.resolve()
    lab = workspace/'ExpansionRaceLab'
    review = lab/'MinotaurOwnerReview'
    content = workspace/'Client/Plugins/DAoCVisualBridge/Content'
    union = lab/'SharLobbyHost/Plugins/DAoCVisualBridge/Content'
    output = lab/'CentralDelivery'
    output.mkdir(exist_ok=True)
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    seal_path = lab/'CombinedExpansionServerCandidate/verified_joint_creation.json'
    seal = read(seal_path)
    assert seal['passed'] and seal['joint_class_behavior_cases'] == 7
    assert seal['private_review_joint_server_and_data_installed'] and not seal['normal_database_modified']
    paths = {'models': workspace/'models.json', 'equipment': workspace/'equipment_catalog_v01.json',
             'appearance': content/'ClassicUI/Pregame/appearance_catalog.json',
             'tasks': workspace/'SourceModels/tasks.json', 'lore': content/'ClassicUI/Pregame/lore.json'}
    before = {name: read(path) for name, path in paths.items()}
    merged = copy.deepcopy(before)
    additions = {}

    def additive(target, source, label):
        added = []
        for key, value in source.items():
            if key in target:
                assert target[key] == value, ('Existing entry differs; do not overwrite', label, key)
            else:
                target[key] = copy.deepcopy(value)
                added.append(key)
        additions[label] = added

    models = read(review/'models.json')
    expansion_ids = ['1075', '1087', '1419']
    additive(merged['models'], {key: models[key] for key in expansion_ids}, 'models')
    equipment = read(review/'equipment_catalog.json')
    for key in ['figures', 'textures', 'helmets']:
        additive(merged['equipment']['armour'][key], equipment['armour'][key], 'armour.'+key)
    # All other equipment sections remain from the current central catalogue.
    appearance = read(review/'appearance_catalog.json')
    figures = {key: copy.deepcopy(appearance['figures'][key]) for key in expansion_ids}
    for figure in figures.values():
        figure['materials'] = copy.deepcopy(appearance['materials'])
    additive(merged['appearance']['figures'], figures, 'appearance.figures')
    for key in ['textures', 'original_color_textures']:
        additive(merged['appearance'].setdefault(key, {}), appearance[key], 'appearance.'+key)
    assert merged['appearance']['materials'] == before['appearance']['materials']
    assert merged['appearance']['surface_materials'] == before['appearance']['surface_materials']
    task_rows = read(lab/'OriginalTasks/tasks.json')
    task_ids = {str(row['id']): row for row in merged['tasks']}
    for ident in expansion_ids:
        row = next(row for row in task_rows if str(row['id']) == ident)
        assert ident not in task_ids or task_ids[ident] == row
        if ident not in task_ids:
            merged['tasks'].append(copy.deepcopy(row))
    lore = read(lab/'Delivery/lore.json')
    for key in lore:
        additive(merged['lore'].setdefault(key, {}), lore[key], 'lore.'+key)
    for name, value in merged.items():
        (output/(name+'.json')).write_text(json.dumps(value, indent=2), encoding='utf-8')
    # Include whole missing asset roots so material/texture references embedded
    # inside uassets are delivered together, rather than only direct JSON refs.
    packages = set()

    def references(value):
        if isinstance(value, dict):
            for key, item in value.items():
                references(key)
                references(item)
        elif isinstance(value, list):
            for item in value:
                references(item)
        elif isinstance(value, str) and value.startswith('/DAoCVisualBridge/'):
            packages.add(value.split('.')[0].removeprefix('/DAoCVisualBridge/')+'.uasset')

    for name in ['models', 'equipment', 'appearance']:
        references(merged[name])
    missing_roots = set()
    for relative in packages:
        target = content/relative
        assert target.resolve().is_relative_to(content.resolve())
        if not target.exists():
            assert (union/relative).is_file(), ('Missing delivery dependency', relative)
            missing_roots.add(Path(relative).parts[0])
    files = []
    for root in sorted(missing_roots):
        source_root = union/root
        for source in sorted(source_root.rglob('*')):
            if not source.is_file():
                continue
            assert source.resolve().is_relative_to(workspace.parent)
            relative = Path(root)/source.relative_to(source_root)
            target = content/relative
            assert target.resolve().is_relative_to(content.resolve())
            sha = digest(source)
            if target.exists():
                assert digest(target) == sha, ('Installed asset differs; preserve it', str(target))
            files.append({'source': str(source.resolve()), 'target': str(target), 'sha256': sha,
                          'bytes': source.stat().st_size, 'already_present': target.exists()})
    catalogs = {name: {'target': str(path), 'before_sha256': digest(path),
                      'candidate': str(output/(name+'.json')), 'after_sha256': digest(output/(name+'.json'))}
                for name, path in paths.items()}
    report = {'passed': True, 'installed': False, 'normal_database_modified': False,
              'source_seal': {'path': str(seal_path), 'sha256': digest(seal_path)},
              'catalogs': catalogs, 'additions': additions, 'assets': files,
              'preserved_global_materials': before['appearance']['materials'],
              'figure_material_overrides': {key: figures[key]['materials'] for key in expansion_ids},
              'existing_model_rows_preserved': len(before['models']),
              'asset_roots': sorted(missing_roots),
              'pending': ['Native acceptance of merged catalogs and per-figure materials',
                          'Reversible central deployment; no world population import or race activation here']}
    (output/'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'installed': False, 'catalogs': len(catalogs),
                      'assets': len(files), 'bytes_to_copy': sum(r['bytes'] for r in files if not r['already_present']),
                      'preserved_global_materials': report['preserved_global_materials']}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.workspace)
