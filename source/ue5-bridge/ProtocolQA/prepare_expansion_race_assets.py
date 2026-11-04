"""Prepare private original Shar/Minotaur export tasks without enabling races."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(game, server, workspace, output):
    game, server, workspace, output = (p.resolve() for p in (game, server, workspace, output))
    assert output.is_relative_to(workspace) and output != workspace
    assert not output.is_relative_to(game), 'Exports must not write into installed game content'
    content = game / 'content'
    manifest = content / 'monsters/monsters.json'
    source = json.loads(manifest.read_text(encoding='utf-8-sig'))
    models = source.get('models', source)
    enums = server / 'Enums/eLivingModel.cs'
    enum_text = re.sub(r'/\*.*?\*/|//[^\n]*', '', enums.read_text(encoding='utf-8-sig'), flags=re.S)
    definitions = dict(re.findall(r'(\w+)\s*=\s*(\d+)', enum_text))
    rows = [('SharMale', 'sha_m'), ('SharFemale', 'sha_f'), ('MinotaurMaleHib', None)]
    report = {'prepared': False, 'activated': False, 'source_hashes': {}, 'figures': {}, 'gaps': []}
    tasks = []
    for name, prefix in rows:
        ident = definitions[name]
        model = models[ident]
        required = {'idle', 'walk', 'run', 'death', 'cast_start', 'cast_mid', 'cast_end', 'sit_down', 'sit_idle'}
        row = {'model_id': int(ident), 'original_name': model['name'], 'figure': model['figure'], 'prefix': prefix}
        if prefix:
            assert model.get('race') == prefix, (name, ident, model.get('race'))
            folder = content / 'characters/races' / prefix
            metadata_file, geometry_file = folder / 'figure.json', folder / 'figure.gltf'
            metadata = json.loads(metadata_file.read_text(encoding='utf-8-sig'))
            geometry = json.loads(geometry_file.read_text(encoding='utf-8-sig'))
            assert metadata['prefix'] == prefix and metadata['race'] == 'Shar' and metadata['realm'] == 'hib'
            assert len(geometry['skins']) == 1
            clips = set(metadata['clip_seconds'])
            parts = {node['name']: geometry['meshes'][node['mesh']].get('extras', {}) for node in geometry['nodes'] if 'mesh' in node}
            assert 'head' in parts
            row.update(format='original_fig3_modular', original_clips=len(clips), missing_core_clips=sorted(required-clips),
                       appearance_options={key: len(metadata.get(key, [])) for key in ['faces', 'hair_styles', 'skin_tones', 'sliders']},
                       original_morph_parts={key: len(value.get('targetNames', [])) for key, value in parts.items() if value.get('targetNames')})
            for path in [metadata_file, geometry_file]:
                report['source_hashes'][str(path)] = digest(path)
        else:
            relative = model['gltf'].removeprefix('res://')
            geometry_file = (game / relative).resolve()
            assert geometry_file.is_relative_to(content) and geometry_file.is_file()
            geometry = json.loads(geometry_file.read_text(encoding='utf-8-sig'))
            clips = set(model.get('clip_seconds', {}))
            assert len(geometry['skins']) == 1
            aliases = {key: value for key, value in model.get('cast_clips', {}).items() if value in clips}
            row.update(format='original_monster_figure', original_clips=len(clips), missing_core_clips=sorted(required-clips-set(aliases)), original_cast_aliases=aliases,
                       modular_creation_metadata=False, geometry_file=str(geometry_file))
            report['source_hashes'][str(geometry_file)] = digest(geometry_file)
            report['gaps'].append('Minotaur original mesh is available, but no converted modular character-creation metadata is present; do not substitute another race.')
        if row['missing_core_clips']:
            report['gaps'].append(name + ' lacks converted core clips: ' + ', '.join(row['missing_core_clips']))
        report['figures'][name] = row
        info = dict(model)
        if prefix:
            info['clip_seconds'] = metadata['clip_seconds']
            info['cast_clips'] = metadata.get('cast_clips', model.get('cast_clips', {}))
        tasks.append({'id': ident, 'info': info, 'equipment': []})
    report['source_hashes'][str(manifest)] = digest(manifest)
    report['source_hashes'][str(enums)] = digest(enums)
    report['gaps'].extend(['Godot creation transport and bridge appearance allowlists omit Shar/Minotaur.',
                           'Native race assets, equipment compatibility and creation eligibility still require separate acceptance.'])
    output.mkdir(parents=True, exist_ok=True)
    (output / 'tasks.json').write_text(json.dumps(tasks, indent=2), encoding='utf-8')
    report['prepared'] = True
    (output / 'inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    assert all(digest(Path(path)) == sha for path, sha in report['source_hashes'].items())
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ['game', 'server-source', 'workspace', 'output']:
        parser.add_argument('--' + arg, type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.game, args.server_source, args.workspace, args.output)
    print(json.dumps({'prepared': result['prepared'], 'activated': False, 'figures': result['figures'], 'gaps': result['gaps']}))
