"""Run deterministic physics acceptance on the saved Ardee world, without login."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import argparse,json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parent;D=R/'Reports/navigation/traversal'
def run(name):
    file=D/(name+'.json');output=Path(str(file)+'.results.json');started=time.time()
    command=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'Client/DAoCBridgeClient.uproject'),
        '/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba','-game','-DaocBridge',f'-DaocBridgeTraversal={file}',
        f'-DaocBridgeCollisionCatalog={R/"collision_catalog.json"}','-nullrhi','-unattended','-nosound','-nosplash']
    with (D/(name+'.log')).open('w')as log:
        result=subprocess.run(command,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    assert result.returncode==0,(name,result.returncode)
    assert output.exists() and output.stat().st_mtime>=started,'Missing fresh traversal report'
    report=json.loads(output.read_text(encoding='utf-8-sig'));expected=json.loads(file.read_text())['routes']
    assert len(report['routes'])==len(expected),'Missing test routes'
    passed=all(r['passed']for r in report['routes'])
    if json.loads(file.read_text()).get('expect_doors_closed'):passed&=bool(report.get('doors')) and all(not d['open']and d['alpha']<.02 for d in report['doors'])
    for row in report['routes']:
        if row['id']=='running_speed_reference':passed&=4.7<=row.get('peak_speed_mps',0)<=4.8
    summary=dict(suite=name,passed=passed,routes=len(report['routes']),real_character_movement=True,real_server=False,
                 failures=[r for r in report['routes']if not r['passed']])
    (D/(name+'_summary.json')).write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    return passed
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--suite',default='routes');a=p.parse_args()
    if not run(a.suite):raise SystemExit(1)
