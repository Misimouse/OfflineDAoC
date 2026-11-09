"""Exercise actual gateway Position/Heading and request routing without a played server."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
 source=Path(__file__).resolve().parents[1]/'Godot';lab=workspace/'PersonalTorchLab';project=lab/'GatewayProject';project.mkdir(exist_ok=True)
 for p in source.glob('*.gd'):shutil.copy2(p,project/p.name)
 (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="PrivateTorchGateway"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
 reports=[]
 for name,minimum in [('test_personal_torch_gateway.gd',261),('test_live_riding_gateway.gd',6),('test_remote_player_state.gd',69)]:
  result=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script',str(project/name),'--quit-after','120'],capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  text=result.stdout+result.stderr;(lab/(name+'.log')).write_text(text);assert result.returncode==0 and 'SCRIPT ERROR' not in text and 'ERROR:' not in text,str(lab/(name+'.log'))
  data=json.loads(next(line for line in text.splitlines() if line.startswith('{')));assert data['passed'] and data['checks']>=minimum,data;reports.append(dict(test=name,checks=data['checks']))
 data=dict(passed=True,reports=reports,installed=False,real_server=False,source_inputs={str(p):digest(p) for p in [source/'live_gateway.gd',source/'personal_torch_state.gd',source/'test_personal_torch_gateway.gd',source/'test_live_riding_gateway.gd',source/'test_remote_player_state.gd']});(lab/'gateway_tests.json').write_text(json.dumps(data,indent=2));return dict(passed=True,reports=reports)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','install']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
