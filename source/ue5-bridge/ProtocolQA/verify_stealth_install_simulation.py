"""Check the entire receipt chain with an in-memory successor; write no runtime files."""
import argparse,json,hashlib
from pathlib import Path
from unittest.mock import patch
import central_activation_receipts as receipts
from prepare_combined_expansion_data import digest

def verify(workspace):
    root=workspace/'StealthLab';plan=root/'install_plan.json';receipt_path=root/'installed.json'
    data=json.loads(plan.read_text());assert data['phase']=='planned' and not data['installed']
    baseline=receipts.verify_files(workspace);assert baseline['world_clock_installed'] and not baseline['stealth_installed']
    rows={Path(r['target']):r for r in data['files']}
    before={str(p):digest(p) if p.exists() else None for p in rows}
    assert all(before[str(p)]==r['before_sha256'] for p,r in rows.items())
    targets_sha256=hashlib.sha256(json.dumps(data['files'],sort_keys=True).encode()).hexdigest()
    data.update(installed=True,phase='complete')
    exists=Path.exists;read_text=Path.read_text
    catalog=workspace/'Client/Plugins/DAoCVisualBridge/Content/ClassicUI/stealth_materials.json'
    def simulated_digest(p):
        row=rows.get(Path(p))
        return row['after_sha256'] if row else digest(p)
    def simulated_exists(p):return True if p in rows or p==receipt_path else exists(p)
    def simulated_read(p,*args,**kwargs):
        if p==receipt_path:return json.dumps(data)
        if p==catalog:return read_text(Path(rows[p]['source']),*args,**kwargs)
        return read_text(p,*args,**kwargs)
    with patch.object(receipts,'digest',side_effect=simulated_digest),patch.object(Path,'exists',simulated_exists),patch.object(Path,'read_text',simulated_read):
        result=receipts.verify_files(workspace)
        assert result['stealth_installed'] and result['world_clock_installed']
    assert all((digest(Path(p)) if Path(p).exists() else None)==h for p,h in before.items())
    assert not receipts.verify_files(workspace)['stealth_installed']
    report=dict(passed=True,simulated_only=True,normal_runtime_modified=False,plan_sha256=digest(plan),targets_sha256=targets_sha256,
                core_source_sha256=digest(Path(receipts.__file__)),test_source_sha256=digest(Path(__file__)),files=len(rows))
    (root/'install_simulation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.workspace.resolve())))
