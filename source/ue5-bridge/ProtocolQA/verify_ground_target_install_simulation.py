"""Simulate the complete delivery chain and reject damaged ground-target receipts."""
import argparse,copy,json
from pathlib import Path
from unittest.mock import patch
import central_activation_receipts as core
import inventory_quantity_receipts as quantity
import realm_war_receipts as realm_war
import siege_receipts as siege
import ground_target_receipts as ground_target
from prepare_combined_expansion_data import digest

def verify(workspace):
    root=workspace/'GroundTargetLab';plan=root/'install_plan.json';receipt_path=root/'installed.json'
    planned=json.loads(plan.read_text());assert not planned['installed'] and planned['phase']=='planned'
    rows={Path(r['target']):r for r in planned['files']};before={p:digest(p) if p.exists() else None for p in rows}
    assert all(before[p]==r['before_sha256'] for p,r in rows.items())
    exists=Path.exists;read=Path.read_text
    def run(receipt):
        def sha(p):return rows[Path(p)]['after_sha256'] if Path(p) in rows else digest(p)
        def present(p):return True if p in rows or p==receipt_path else exists(p)
        def content(p,*a,**kw):return json.dumps(receipt) if p==receipt_path else read(p,*a,**kw)
        with patch.object(core,'digest',side_effect=sha),patch.object(quantity,'digest',side_effect=sha),patch.object(realm_war,'digest',side_effect=sha),patch.object(siege,'digest',side_effect=sha),patch.object(ground_target,'digest',side_effect=sha),patch.object(Path,'exists',present),patch.object(Path,'read_text',content):return core.verify_files(workspace)
    good=copy.deepcopy(planned);good.update(installed=True,phase='complete');assert run(good)['ground_target_installed']
    cases=[]
    for i in range(len(good['files'])):
        for kind in ['missing','before','after']:
            bad=copy.deepcopy(good)
            if kind=='missing':bad['files'].pop(i)
            else:bad['files'][i][kind+'_sha256']='0'*64
            cases.append(bad)
    for field,value in [('database_modified',True),('server_rules_modified',True),('map_geometry_modified',True),('teleport_enabled',True),('phase','planned'),('predecessor_receipt_sha256','0'*64),('native_before_sha256','0'*64),('native_after_sha256','0'*64)]:
        bad=copy.deepcopy(good);bad[field]=value;cases.append(bad)
    bad=copy.deepcopy(good);bad['files'].append(bad['files'][0]);cases.append(bad)
    for bad in cases:
        try:run(bad)
        except (AssertionError,KeyError):continue
        raise AssertionError('Damaged receipt unexpectedly accepted')
    assert all((digest(p) if p.exists() else None)==h for p,h in before.items())
    assert not core.verify_files(workspace)['ground_target_installed']
    report=dict(passed=True,simulated_only=True,normal_runtime_modified=False,checks=1+len(cases),plan_sha256=digest(plan),core_source_sha256=digest(Path(core.__file__)),quantity_guard_sha256=digest(Path(quantity.__file__)),realm_war_guard_sha256=digest(Path(realm_war.__file__)),siege_guard_sha256=digest(Path(siege.__file__)),ground_target_guard_sha256=digest(Path(ground_target.__file__)))
    (root/'install_simulation.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve())))
