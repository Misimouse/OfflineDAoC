"""Compare the private torch state against the actual original Godot sky phase function."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
 source=Path(__file__).resolve().parents[1]/'Godot';lab=workspace/'PersonalTorchLab';project=lab/'StateProject';project.mkdir(parents=True,exist_ok=True);original=install/'new-client/godot/game/sky_system.gd';text=original.read_text(encoding='utf-8-sig');phase=re.search(r'const PHASE_KEYS := (\[\[.*?\]\])',text,re.S).group(0);method=text[text.index('func _phase_weights('):text.index('\n\nfunc _blend(')].rstrip();reference=project/'original_phase_reference.gd';reference.write_text('extends RefCounted\n'+phase+'\n'+method+'\n')
 (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="PrivateTorchState"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
 for name in ['personal_torch_state.gd','test_personal_torch_state.gd']:shutil.copy2(source/name,project/name)
 report=project/'state_tests.json';report.unlink(missing_ok=True)
 with (lab/'state_tests.log').open('w') as log:
  result=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script',str(project/'test_personal_torch_state.gd'),'--quit-after','120'],stdout=log,stderr=subprocess.STDOUT,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0 and report.exists(),str(lab/'state_tests.log');data=json.loads(report.read_text());assert data['passed'] and data['checks']>=1502 and data['candidate_only'] and not data['installed'];data['source_inputs']={str(p):digest(p) for p in [original,source/'personal_torch_state.gd',source/'test_personal_torch_state.gd',reference]};(lab/'state_tests.json').write_text(json.dumps(data,indent=2));return {k:v for k,v in data.items() if k!='source_inputs'}
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','install']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
