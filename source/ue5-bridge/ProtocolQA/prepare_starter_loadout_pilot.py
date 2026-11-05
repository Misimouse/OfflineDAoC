"""Stage authoritative starter gear in a physically private expansion acceptance host."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(workspace, lab):
    workspace, lab = workspace.resolve(), lab.resolve()
    assert lab.is_relative_to(workspace) and lab != workspace
    source = workspace / 'Client/Plugins/DAoCVisualBridge/Content'
    target = lab / 'NativeHost/Plugins/DAoCVisualBridge/Content'
    assert target.resolve().is_relative_to(lab)
    read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
    protocol = read(workspace / 'Reports/shar_starter_creation/real_protocol.json')
    assert protocol['passed'] and len(protocol['cases']) == 10 and protocol['database_restored']
    loadouts = protocol['original_starter_loadouts']
    assert set(loadouts) == {f'{base}:{sex}' for base in [51, 52, 54] for sex in ['sha_m', 'sha_f']}
    full = read(workspace / 'equipment_catalog_v01.json')
    pilot = read(lab / 'equipment_helmets_full_candidate.json')
    dependencies = read(lab / 'starter_weapon_dependencies.json')
    assert dependencies['passed'] and not dependencies['installed']
    assert dependencies['models'] == {key: full['models'][key] for key in ['19', '59', '445', '454']}
    armour = full['armour']
    models = {str(item['model']) for row in loadouts.values() for item in row['items'] if item['slot'] in [22, 23, 25, 27, 28]}
    assert models == {str(model) for model in [378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 393, 394, 395, 396, 397]}
    names = set()
    for model in models:
        definition = armour['models'][model]
        pilot['armour']['models'][model] = definition
        names |= {part[1] for parts in definition.values() for part in parts.values()}
    pilot['armour']['textures'].update({name: armour['textures'][name] for name in names})
    pilot['models'] = dependencies['models']
    pilot['armour']['starter_loadouts'] = loadouts
    files = {row['relative']: row for row in dependencies['files']}
    for name in names:
        asset = armour['textures'][name]
        assert asset.startswith('/DAoCVisualBridge/')
        relative = asset.removeprefix('/DAoCVisualBridge/').split('.')[0] + '.uasset'
        path = source / relative
        files[relative] = {'source': str(path), 'relative': relative,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    staged = []
    for relative, row in sorted(files.items()):
        src, dst = Path(row['source']).resolve(), (target / relative).resolve()
        assert src.is_relative_to(source.resolve()) and dst.is_relative_to(target.resolve())
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        assert digest == row['sha256'], 'Source dependency changed'
        if dst.exists():
            assert hashlib.sha256(dst.read_bytes()).hexdigest() == digest, 'Private dependency differs'
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        staged.append({'relative': relative, 'sha256': digest, 'bytes': dst.stat().st_size})
    (lab / 'equipment_starter_candidate.json').write_text(json.dumps(pilot, indent=2), encoding='utf-8')
    report = {'passed': True, 'installed': False, 'loadouts': len(loadouts), 'files': staged}
    (lab / 'starter_pilot_prepared.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['workspace', 'lab']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.workspace, args.lab)
    print(json.dumps({'passed': report['passed'], 'files': len(report['files']), 'loadouts': report['loadouts']}))
