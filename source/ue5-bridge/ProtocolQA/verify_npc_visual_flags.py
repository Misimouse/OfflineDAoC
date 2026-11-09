"""Compare candidate spawn flags with an unmodified extracted original Godot normalization block."""
import argparse,json,shutil,subprocess
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
 source=Path(__file__).resolve().parents[1]/'Godot';lab=workspace/'NpcVisualFlagsLab';project=lab/'StateProject';project.mkdir(parents=True,exist_ok=True);original=install/'new-client/godot/game/net/server_world.gd';text=original.read_text(encoding='utf-8-sig');start=text.index('\tvar flags := 0',text.index('func _add_npc('));end=text.index('\tvar p := scene_pos',start);block=text[start:end];reference=project/'original_npc_flags.gd';reference.write_text('extends RefCounted\nfunc normalize(d:Dictionary)->int:\n\tvar f:=int(d.flags)\n\tvar f2:=int(d.flags2)\n'+block+'\treturn flags\n')
 (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="PrivateNPCFlags"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
 for name in ['npc_visual_flags.gd','test_npc_visual_flags.gd','decoded_world_adapter.gd','test_npc_visual_adapter.gd']:shutil.copy2(source/name,project/name)
 report=project/'npc_flags_tests.json';report.unlink(missing_ok=True)
 result=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script',str(project/'test_npc_visual_flags.gd'),'--quit-after','120'],capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);log=result.stdout+result.stderr;(lab/'state_tests.log').write_text(log);assert result.returncode==0 and 'SCRIPT ERROR' not in log and report.exists(),str(lab/'state_tests.log');data=json.loads(report.read_text());assert data['passed'] and data['checks']>=1815
 adapter_report=project/'npc_adapter_tests.json';adapter_report.unlink(missing_ok=True)
 result=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script',str(project/'test_npc_visual_adapter.gd'),'--quit-after','120'],capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);log=result.stdout+result.stderr;(lab/'adapter_tests.log').write_text(log);assert result.returncode==0 and 'SCRIPT ERROR' not in log and adapter_report.exists(),str(lab/'adapter_tests.log');adapter=json.loads(adapter_report.read_text());assert adapter['passed'] and adapter['checks']>=8;data['adapter_checks']=adapter['checks']
 data['source_inputs']={str(p):digest(p) for p in [original,source/'npc_visual_flags.gd',source/'test_npc_visual_flags.gd',source/'decoded_world_adapter.gd',source/'test_npc_visual_adapter.gd',reference]};(lab/'state_tests.json').write_text(json.dumps(data,indent=2));return {k:v for k,v in data.items() if k!='source_inputs'}
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['workspace','install']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
