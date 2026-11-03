"""Exercise launcher target selection without credentials, server or game startup."""
import argparse,datetime,json,subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--launcher',required=True,type=Path)
parser.add_argument('--dotnet',required=True,type=Path)
parser.add_argument('--report',required=True,type=Path)
args=parser.parse_args()
args.report.parent.mkdir(parents=True,exist_ok=True)
folder=args.report.parent/('target_fixtures_'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
folder.mkdir();results=[]
default_map='/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba'
shared_map='/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba_Limpieza_v01'
for case in ['legacy','relative','absolute','missing_project','missing_map','invalid_map','invalid_plugin']:
    root=folder/case;legacy=root/'Client/DAoCBridgeClient.uproject';legacy.parent.mkdir(parents=True);legacy.write_text('{}')
    legacy_map=legacy.parent/'Content'/(default_map[6:]+'.umap');legacy_map.parent.mkdir(parents=True);legacy_map.write_bytes(b'fixture')
    shared=root/'Shared art project/Unified.uproject';shared.parent.mkdir();shared.write_text('{}')
    shared_level=shared.parent/'Content'/(shared_map[6:]+'.umap');shared_level.parent.mkdir(parents=True);shared_level.write_bytes(b'fixture')
    target={'project':str(shared.relative_to(root)),'map':shared_map,'enable_plugins':['DAoCVisualBridge']}
    if case=='absolute':target['project']=str(shared)
    if case=='missing_project':target['project']='Absent.uproject'
    if case=='missing_map':target['map']='/Game/Missing'
    if case=='invalid_map':target['map']=shared_map+' -ExecCmds=quit'
    if case=='invalid_plugin':target['enable_plugins']=['DAoCVisualBridge,Other']
    if case!='legacy':(root/'playable_project.json').write_text(json.dumps(target))
    process=subprocess.run([str(args.dotnet),str(args.launcher),'--show-target','--bridge-root='+str(root)],capture_output=True,text=True,timeout=15)
    valid=case in ['legacy','relative','absolute']
    if valid:
        assert process.returncode==0,(case,process.stderr[-500:])
        data=json.loads(process.stdout);expected=legacy if case=='legacy' else shared
        assert Path(data['project']).resolve()==expected.resolve(),(case,data)
        assert data['map']==(default_map if case=='legacy' else shared_map),(case,data)
        assert data['enable_plugins']==([] if case=='legacy' else ['DAoCVisualBridge']),(case,data)
    else:assert process.returncode!=0,(case,'Invalid target accepted')
    results.append({'case':case,'passed':True})
result={'passed':True,'checks':len(results),'cases':results,'launcher_selection_only':True,'game_started':False,'credentials_used':False}
args.report.write_text(json.dumps(result,indent=2));print(json.dumps(result))
