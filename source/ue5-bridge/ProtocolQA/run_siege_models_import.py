"""Create a small private import host; retain approved content as checked junctions."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def run(workspace,engine):
 root=workspace/'SiegeWorldLab';host=root/'AssetHost';plugin=host/'Plugins/DAoCVisualBridge';central=workspace/'Client/Plugins/DAoCVisualBridge'
 proof=json.loads((root/'export_verified.json').read_text());assert proof['passed'] and all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
 out=root/'SourceModels';rows=json.loads((out/'exported.json').read_text());assert digest(out/'exported.json')==proof['exported_sha256']
 proof['exported_files']={r['file']:digest(Path(r['file'])) for r in rows};(root/'export_verified.json').write_text(json.dumps(proof,indent=2))
 content=plugin/'Content';content.mkdir(parents=True,exist_ok=True);assert not content.is_junction()
 quote=lambda p:"'"+str(p).replace("'","''")+"'"
 for source in central.joinpath('Content').iterdir():
  target=content/source.name
  if source.is_dir():
   if target.exists():assert target.is_junction() and target.resolve()==source.resolve()
   else:subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(target)+' -Target '+quote(source)+' | Out-Null'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  elif not target.exists():shutil.copy2(source,target)
 namespace=content/'SiegeWorld_v01';namespace.mkdir(exist_ok=True);assert not namespace.is_junction()
 shutil.copy2(central/'DAoCVisualBridge.uplugin',plugin/'DAoCVisualBridge.uplugin')
 binary=plugin/'Binaries/Win64';binary.mkdir(parents=True,exist_ok=True)
 for name in ['UnrealEditor-DAoCVisualBridge.dll','UnrealEditor.modules']:shutil.copy2(central/'Binaries/Win64'/name,binary/name)
 project=host/'SiegeWorldAssets.uproject';project.write_text(json.dumps(dict(FileVersion=3,EngineAssociation='5.8',Plugins=[dict(Name=n,Enabled=True) for n in ['DAoCVisualBridge','PythonScriptPlugin','EditorScriptingUtilities']])))
 script=Path(__file__).with_name('import_siege_models_unreal.py');target=root/script.name;shutil.copy2(script,target)
 args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'-run=pythonscript','-script='+str(target),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'asset_import_engine.log')]
 with (root/'asset_import_stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=360,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0,'See SiegeWorldLab/asset_import.json'
 data=json.loads((root/'asset_import.json').read_text());assert data['passed'] and len(data['models'])==10
 assert all(digest(Path(p))==h for p,h in proof['source_inputs'].items())
 return dict(passed=True,models=len(data['models']),normal_content_modified=False)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();print(json.dumps(run(a.workspace.resolve(),a.engine.resolve())))
