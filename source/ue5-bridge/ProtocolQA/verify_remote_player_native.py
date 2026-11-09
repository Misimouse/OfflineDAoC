"""Replay player poses, NPC collisions and combat inside the candidate or installed Unreal client."""
import argparse,json,subprocess,shutil
from pathlib import Path
from datetime import datetime
from prepare_combined_expansion_data import digest

def verify(workspace,engine,installed=False):
 root=workspace/'RemotePlayerLab';bp=root/'native_build.json';build=json.loads(bp.read_text());assert build['passed'];normal=workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll';expected=build['binaries_sha256']['UnrealEditor-DAoCVisualBridge.dll'] if installed else build['normal_binary_sha256'];assert digest(normal)==expected
 out=root/('InstalledNativeAcceptance' if installed else 'NativeRegression')/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True);project=str(workspace/'Client/DAoCBridgeClient.uproject') if installed else build['project'];reports=[]
 for name,source,flag,suffix,minimum in [('pose',None,'DaocBridgePoseTest','',55),('combat',workspace/'Reports/combat_visual/fixture.json','DaocBridgeCombatVisualTest','.native.json',25),('motion',workspace/'Reports/movement/server_trace.json','DaocBridgeMotionTest','.motion-results.json',387)]:
  fixture=out/(name+'.json')
  if source:shutil.copy2(source,fixture)
  args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),project,'/Engine/Maps/Entry','-game','-DaocBridge','-DaocBridgeReadOnly','-DaocBridgeCatalog='+str(workspace/'models.json'),'-'+flag+'='+str(fixture),'-unattended','-nosound','-nosplash','-abslog='+str(out/(name+'.log'))]
  args+=['-DaocBridgeRemotePlayerTest','-d3d11','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720'] if name=='pose' else ['-nullrhi']
  for key,file in [('DisplaySettings','display.ini'),('InterfaceSettings','interface.ini'),('KeyConfiguration','keys.ini'),('ControlsSettings','camera.json'),('AudioSettings','audio.ini')]:args.append('-DaocBridge'+key+'='+str(out/file))
  with (out/(name+'_stdout.log')).open('w') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  report=Path(str(fixture)+suffix);assert result.returncode==0 and report.exists(),str(out);data=json.loads(report.read_text(encoding='utf-8-sig'));assert data['passed'] and data['checks']>=minimum,data
  reports.append(dict(name=name,report=str(report),sha256=digest(report),checks=data['checks']))
 assert digest(normal)==expected
 result=dict(passed=True,reports=reports,build_sha256=digest(bp),installed_client=installed,real_server=False,normal_binary_unchanged=True);(out/'verified.json').write_text(json.dumps(result,indent=2));return dict(passed=True,reports=reports,output=str(out))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','engine']:p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--installed',action='store_true');a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.engine.resolve(),a.installed)))
