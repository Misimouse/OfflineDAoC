"""Run a guarded original mount import in the isolated native host."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_live_riding_content import prepare

def run(workspace,engine):
    prepare(workspace);root=workspace/'LiveRidingLab';source=Path(__file__).with_name('import_live_riding_unreal.py');target=root/source.name;shutil.copy2(source,target)
    command=[str(engine/'Binaries/Win64/UnrealEditor-Cmd.exe'),str(root/'NativeHost/SpellAudioHost.uproject'),'-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities','-run=pythonscript','-script='+str(target),'-nullrhi','-unattended','-nosound','-nosplash','-abslog='+str(root/'asset_import_engine.log')]
    with (root/'asset_import_stdout.log').open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,'See LiveRidingLab/asset_import_engine.log'
    proof=json.loads((root/'asset_import.json').read_text(encoding='utf-8-sig'));assert proof['passed'] and not proof['errors']
    return dict(passed=True,models=list(proof['models']),files=len(proof['files']),normal_content_modified=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','engine']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.workspace.resolve(),a.engine.resolve())))
