"""Stage a small private Shar outfit acceptance catalogue; never modify installed assets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil


def prepare(workspace, lab, package=None):
    workspace, lab = workspace.resolve(), lab.resolve()
    assert lab.is_relative_to(workspace) and lab != workspace
    package = package.resolve() if package else lab
    assert package.is_relative_to(lab)
    source = workspace / 'Client/Plugins/DAoCVisualBridge'
    destination = lab / 'NativeHost/Plugins/DAoCVisualBridge'
    assert (destination / 'Content').resolve().is_relative_to(lab)
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    native = read(package / 'native_outfit_import.json')
    assert native['passed'] and not native['installed']
    equipment = read(workspace / 'equipment_catalog_v01.json')
    armour = equipment['armour']
    selected = {str(k): armour['models'][str(k)] for k in [41, 34, 40, 32, 33, 57]}
    names = {part[1] for model in selected.values() for parts in model.values() for part in parts.values()}
    names |= {'cat_cloak', next(iter(armour['textures']))}
    definitions = read(package / 'outfit_definitions_candidate.json')
    private_textures = read(package / 'appearance_catalog_candidate.json')['textures'] if package != lab else {}
    for definition in definitions.values():
        names |= {r['tex'] for r in definition['clothes'].values()
                  if package != lab or r['tex'] in armour['textures']}
    textures = {}
    for key in sorted(names):
        value = armour['textures'].get(key) or private_textures.get(key.lower())
        assert value, ('Missing original outfit texture', key)
        textures[key] = value
    emblems = copy.deepcopy(armour['cloak_emblems'])
    emblems['patterns'] = {k: emblems['patterns'][k] for k in ['1', '512']}
    emblems['logos'] = {'1': emblems['logos']['1']}
    paths = set(textures.values()) | {armour['material'], armour['cloak_material']}
    paths |= set(emblems['patterns'].values()) | set(emblems['logos'].values())
    report = {'passed': False, 'installed': False, 'files': [], 'scope': 'Six original equipment models; no helmets or expansion activation. Not a full outfit content library.'}
    def stage(src, dst):
        assert dst.resolve().is_relative_to(lab)
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        if dst.exists():
            assert hashlib.sha256(dst.read_bytes()).hexdigest() == digest, ('Existing private asset differs', str(dst))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        report['files'].append({'target': str(dst), 'sha256': digest, 'bytes': src.stat().st_size})
    for path in sorted(paths):
        assert path.startswith('/DAoCVisualBridge/')
        relative = Path(path.removeprefix('/DAoCVisualBridge/').split('.')[0] + '.uasset')
        assert '..' not in relative.parts
        target = destination / 'Content' / relative
        origin = source / 'Content' / relative
        if not origin.exists():
            assert package != lab and target.exists(), ('Missing private dependency', str(target))
            origin = target
        stage(origin, target)
    equipment['armour'] = dict(armour, figures=definitions, models=selected, textures=textures, cloak_emblems=emblems, helmets={})
    (package / 'equipment_outfits_pilot.json').write_text(json.dumps(equipment, indent=2), encoding='utf-8')
    report['passed'] = True
    (package / 'outfit_pilot_prepared.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['workspace', 'lab']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--package', type=Path)
    args = parser.parse_args()
    report = prepare(args.workspace, args.lab, args.package)
    print(json.dumps({'passed': report['passed'], 'installed': False, 'dependencies': len(report['files']), 'bytes': sum(r['bytes'] for r in report['files'])}))
