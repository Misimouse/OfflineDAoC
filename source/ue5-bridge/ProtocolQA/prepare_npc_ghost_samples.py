"""Run the private UE sample import after original model export; protect the installed catalogue/binary."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,engine):
 lab=workspace/'NpcVisualFlagsLab';project=lab/'RenderHost/GhostRenderHost.uproject';assert project.is_file();rows=json.loads((lab/'SourceModels/exported.json').read_text());assert {r['id'] for r in rows}=={'110','307'}
 protected=[workspace/'models.json',workspace/'Client/Plugins/DAoCVisualBridge/Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'];before={str(p):digest(p) for p in protected};script=Path(__file__).with_name('import_npc_ghost_samples_unreal.py');env=dict(os.environ,DAOC_NPC_GHOST_LAB=str(lab));args=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(project),'-run=pythonscript','-script='+str(script),'-unattended','-nop4','-nosplash','-nullrhi','-abslog='+str(lab/'sample_import.log')]
 with (lab/'sample_import_stdout.log').open('w') as log:result=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0,str(lab/'sample_import.log');data=json.loads((lab/'samples_imported.json').read_text());assert data['passed'] and all(digest(Path(p))==h for p,h in before.items());data['protected_files_unchanged']=before;(lab/'samples_imported.json').write_text(json.dumps(data,indent=2));return dict(passed=True,models=len(data['models']),materials=len(data['materials']),installed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','engine']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.engine.resolve())))
