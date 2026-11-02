from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
import json,subprocess,time,shutil
from pathlib import Path
R=Path(str(ROOT));D=R/'Reports/connacht_models'
p=json.loads((D/'import.json').read_text(encoding='utf-8'));assert p['passed'];print('Imported', {k:v['clips']for k,v in p['models'].items()},flush=True)
shutil.copytree(R/'Client/Plugins/DAoCVisualBridge/Content/ConnachtMissing_v01',R/'UnrealPlugin/DAoCVisualBridge/Content/ConnachtMissing_v01',dirs_exist_ok=True)
rows=[]
for i,key in enumerate(p['models']):
 rows.append(dict(id='npc:'+str(500+i),kind='npc',name='Imported '+key,model_id=int(key),size=50,health=1,position_m=[1364+i*6,130,1263],forward_xz=[0,1],heading_4096=0,state='idle'))
cases=[]
for index,state in enumerate(['idle','walk','dead','idle']):
 current=json.loads(json.dumps(rows))
 for row in current:row['state']=state;row['health']=0 if state=='dead'else 1
 cases.append({'label':state,'snapshot':dict(type='snapshot',protocol='daoc-visual-bridge',version=1,session='entity-acceptance',seq=index+1,zone_id=207,origin_m=[1364,130,1263],entities=current)})
cases.append({'label':'cleanup','snapshot':dict(type='snapshot',protocol='daoc-visual-bridge',version=1,session='entity-acceptance',seq=5,zone_id=207,origin_m=[1364,130,1263],entities=[])})
f=D/'native_fixture.json';f.write_text(json.dumps({'cases':cases}),encoding='utf-8');start=time.time()
cmd=[str(ENGINE / 'Binaries/Win64/UnrealEditor-Cmd.exe'),str(R/'GMCombatTest/NativeHost/BridgeGmHost.uproject'),'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeCatalog='+str(R/'models_connacht_candidate_v01.json'),'-DaocBridgeEntityTest='+str(f),'-nullrhi','-unattended','-nosound','-nosplash']
with(D/'native.log').open('w',encoding='utf-8')as log:result=subprocess.run(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,timeout=100)
o=Path(str(f)+'.native.json');assert result.returncode==0 and o.stat().st_mtime>=start
report=json.loads(o.read_text(encoding='utf-8-sig'));print(json.dumps(report));assert report['passed']
