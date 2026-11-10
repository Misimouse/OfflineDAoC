"""Enable only already-exported original effect-only NPC identities in a private catalogue."""
import argparse
import copy
import json
from pathlib import Path
from prepare_combined_expansion_data import digest


def prepare(workspace):
    lab = workspace/'NpcEffectsLab'
    normal = workspace/'models.json'
    before = digest(normal)
    rows = json.loads(normal.read_text())
    original = copy.deepcopy(rows)
    catalog = json.loads((lab/'Resources/catalog.json').read_text())
    changed = []
    for model, info in catalog['models'].items():
        if model not in rows or not info['effect_only']:
            continue
        assert rows[model]['type'] == 'hidden' and rows[model]['ghost_render']['effect_only']
        rows[model]['type'] = 'effect_body'
        changed.append(model)
    assert set(changed) == {'966','2020'}
    assert all(row == original[model] for model,row in rows.items() if model not in changed)
    assert digest(normal) == before
    output = lab/'models_candidate.json'
    output.write_text(json.dumps(rows,indent=2))
    proof = dict(passed=True,installed=False,changed_models=changed,models=len(rows),
                 before_catalogue_sha256=before,candidate=str(output),sha256=digest(output),
                 original_effect_catalogue_sha256=digest(lab/'Resources/catalog.json'),
                 normal_runtime_modified=False)
    (lab/'catalog_verified.json').write_text(json.dumps(proof,indent=2))
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    options = parser.parse_args()
    print(json.dumps(prepare(options.workspace.resolve())))
