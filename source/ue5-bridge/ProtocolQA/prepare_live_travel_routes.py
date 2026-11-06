"""Stage public stable definitions; enable only an in-bounds, completed real QA route."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace):
    root=workspace/'LiveRidingLab';audit_path=root/'reference_audit.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8-sig'));assert audit['passed'] and not audit['database_modified']
    proofs={}
    for p in sorted((workspace/'Reports/live_riding_real_protocol').glob('*/verified.json')):
        row=json.loads(p.read_text(encoding='utf-8-sig'))
        if row.get('passed') and row.get('normal_shutdown') and row.get('database_restored') and row.get('checks',{}).get('original_route_reaches_final_path_point'):
            proofs[row['route_ticket']]=dict(path=str(p),sha256=digest(p))
    routes=[]
    for row in audit['paths']:
        enabled=row['fully_inside_zone207'] and row['ticket'] in proofs and str(row['steed_model'])=='448'
        routes.append(dict(row,available=enabled,reason='' if enabled else 'This destination is not available in the loaded world yet.'))
    assert len(routes)==6 and sum(row['available'] for row in routes)==1
    result=dict(version=1,zone=207,region=200,routes=routes,reference_sha256=digest(audit_path),completed_route_proofs=proofs,normal_installation_modified=False)
    target=root/'travel_routes.json';target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,available=1,unavailable=5,catalog=str(target),sha256=digest(target))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve())))
