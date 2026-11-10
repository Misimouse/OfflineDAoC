"""Simulate the exact successor chain and reject damaged plans without runtime writes."""
import argparse
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch
import central_activation_receipts as core
import npc_effect_receipts as ghost
from prepare_combined_expansion_data import digest


def verify(workspace):
    root = workspace/'NpcEffectsLab'
    plan, receipt_path = root/'install_plan.json', root/'installed.json'
    planned = ghost.read(plan)
    assert not planned['installed'] and planned['phase'] == 'planned'
    rows = {Path(r['target']):r for r in planned['files']}
    before = {p:digest(p) if p.exists() else None for p in rows}
    assert all(before[p] == r['before_sha256'] for p,r in rows.items())
    assert not core.verify_files(workspace)['npc_effects_installed']
    modules = [m for name,m in list(sys.modules.items()) if name.endswith('_receipts') and hasattr(m,'digest')]
    exists, read_text = Path.exists, Path.read_text
    cache = {}

    def cached(path):
        key = str(path)
        if key not in cache:
            cache[key] = digest(path)
        return cache[key]

    def run(receipt):
        def sha(path):
            return rows[Path(path)]['after_sha256'] if Path(path) in rows else cached(path)
        def present(path):
            return True if path in rows or path == receipt_path else exists(path)
        def content(path,*args,**kwargs):
            return json.dumps(receipt) if path == receipt_path else read_text(path,*args,**kwargs)
        with ExitStack() as stack:
            for module in modules:
                stack.enter_context(patch.object(module,'digest',side_effect=sha))
            stack.enter_context(patch.object(Path,'exists',present))
            stack.enter_context(patch.object(Path,'read_text',content))
            return core.verify_files(workspace)

    good = copy.deepcopy(planned)
    good.update(installed=True,phase='complete')
    assert run(good)['npc_effects_installed']
    cases = []
    # Every code/catalogue row plus both ends of the immutable asset inventory.
    selected = list(range(len(good['files'])))
    for index in selected:
        for kind in ['missing','before','after']:
            bad = copy.deepcopy(good)
            if kind == 'missing':
                bad['files'].pop(index)
            else:
                bad['files'][index][kind+'_sha256'] = '0'*64
            cases.append(bad)
    for field,value in [('database_modified',True),('server_rules_modified',True),
                        ('map_geometry_modified',True),('teleport_enabled',True),('phase','planned'),
                        ('predecessor_receipt_sha256','0'*64),('native_before_sha256','0'*64),
                        ('native_after_sha256','0'*64)]:
        bad = copy.deepcopy(good)
        bad[field] = value
        cases.append(bad)
    bad = copy.deepcopy(good)
    bad['files'].append(bad['files'][0])
    cases.append(bad)
    for bad in cases:
        try:
            run(bad)
        except (AssertionError,KeyError):
            continue
        raise AssertionError('Damaged NPC successor accepted')
    assert all((digest(p) if p.exists() else None) == h for p,h in before.items())
    assert not core.verify_files(workspace)['npc_effects_installed']
    guards = ['central_activation_receipts.py','npc_ghost_receipts.py','npc_effect_receipts.py',
              'install_npc_effects.py','verify_npc_effects_install_simulation.py']
    result = dict(passed=True,simulated_only=True,normal_runtime_modified=False,
                  checks=1+len(cases),plan_sha256=digest(plan),
                  guard_sources={name:digest(Path(__file__).with_name(name)) for name in guards})
    (root/'install_simulation.json').write_text(json.dumps(result,indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    options = parser.parse_args()
    print(json.dumps(verify(options.workspace.resolve())))
