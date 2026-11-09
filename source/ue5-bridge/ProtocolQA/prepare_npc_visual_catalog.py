"""Annotate a private model catalogue from original NPC definitions, never from model names."""
import argparse
import json
from pathlib import Path
from prepare_combined_expansion_data import digest


def classification(info):
    if not isinstance(info, dict) or not info:
        return dict(known=False, race_figure=False, effect_only=False)
    race = info.get('race')
    figure = isinstance(race, str) and bool(race)
    effect_only = not figure and not info.get('gltf') and bool(info.get('effects'))
    return dict(known=True, race_figure=figure, effect_only=effect_only)


def prepare(workspace, install):
    lab = workspace/'NpcVisualFlagsLab'
    original = install/'new-client/godot/content/monsters/monsters.json'
    catalog = workspace/'models.json'
    samples = lab/'samples_imported.json'
    before = {str(p): digest(p) for p in [original, catalog, samples]}
    definitions = json.loads(original.read_text(encoding='utf-8-sig'))
    rows = json.loads(catalog.read_text(encoding='utf-8-sig'))
    additions = json.loads(samples.read_text())
    assert additions['passed'] and set(additions['models']) == {'110', '307'}
    assert all(key not in rows for key in additions['models']), 'Sample model must not replace an existing approved export'
    rows.update(additions['models'])
    for key, entry in rows.items():
        entry['ghost_render'] = classification(definitions.get(key))
    assert rows['110']['ghost_render'] == dict(known=True, race_figure=False, effect_only=False)
    assert rows['307']['ghost_render'] == dict(known=True, race_figure=True, effect_only=False)
    assert rows['966']['ghost_render']['effect_only'] and rows['966']['type'] == 'hidden'
    target = lab/'models_candidate.json'
    target.write_text(json.dumps(rows, indent=2))
    assert all(digest(Path(p)) == sha for p, sha in before.items())
    proof = dict(passed=True, installed=False, model_count=len(rows), added_original_models=sorted(additions['models']),
                 sources=before, catalog=str(target), sha256=digest(target), originals_unchanged=True,
                 known_models=sum(row['ghost_render']['known'] for row in rows.values()),
                 source_classification='original monsters.json race/effect metadata')
    (lab/'catalog_verified.json').write_text(json.dumps(proof, indent=2))
    return {key: value for key, value in proof.items() if key != 'sources'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(prepare(options.workspace.resolve(), options.install.resolve())))
