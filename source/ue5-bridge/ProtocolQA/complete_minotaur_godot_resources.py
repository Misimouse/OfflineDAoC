"""Inventory original external glTF resources for the prepared central Minotaur transport."""
import argparse
import json
from pathlib import Path
from urllib.parse import unquote

from prepare_combined_expansion_data import digest


def prepare(workspace, install):
    output = workspace/'ExpansionRaceLab/CentralDelivery/MinotaurActivation'
    plan_path = output/'plan.json'
    plan = json.loads(plan_path.read_text())
    assert plan['passed'] and not plan['installed']
    graph = next(row for row in plan['files'] if Path(row['source']).suffix == '.gltf')
    source_graph, target_graph = Path(graph['source']), Path(graph['target'])
    assert digest(source_graph) == graph['after_sha256']
    gltf = json.loads(source_graph.read_text())
    external = sorted({row['uri'] for key in ['buffers', 'images'] for row in gltf.get(key, [])
                       if row.get('uri') and not row['uri'].startswith('data:')})
    rows = []
    for uri in external:
        assert '://' not in uri
        source = (source_graph.parent/unquote(uri)).resolve()
        target = (target_graph.parent/unquote(uri)).resolve()
        assert source.is_relative_to(workspace/'ExpansionRaceLab/MinotaurModularCandidate/content')
        assert target.is_relative_to(install/'new-client/godot/content')
        sha = digest(source)
        if target.exists():
            assert digest(target) == sha, ('Existing original texture differs', str(target))
        rows.append({'source': str(source), 'target': str(target), 'after_sha256': sha,
                     'before_sha256': digest(target) if target.exists() else None})
    report = {'passed': True, 'plan_sha256': digest(plan_path), 'gltf_sha256': digest(source_graph),
              'files': rows, 'external_resources': len(external), 'installed': False,
              'normal_database_modified': False}
    (output/'godot_resources.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'external_resources': len(external),
                      'files_to_add': sum(row['before_sha256'] is None for row in rows)}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.workspace.resolve(), args.install.resolve())
