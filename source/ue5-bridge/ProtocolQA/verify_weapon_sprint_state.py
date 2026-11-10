"""Private input guards executing the original Godot weapon-switch function."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from prepare_combined_expansion_data import digest


def verify(workspace, install):
    source = Path(__file__).resolve().parents[1]/'Godot'
    lab = workspace/'OriginalControlsLab'
    project = lab/'StateProject'
    project.mkdir(parents=True,exist_ok=True)
    original = install/'new-client/godot/game/net/server.gd'
    text = original.read_text(encoding='utf-8-sig')
    method = text[text.index('func switch_weapon('):text.index('\n\n## Your quickbars')]
    reference = project/'original_weapon_reference.gd'
    reference.write_text('''extends Node
var playing:=true
var entry:Dictionary={"zone":207}
var commands:Array=[]
var slots:Array=[]
var client:Node
func _init()->void:client=self
func command(text:String)->void:commands.append(text)
func to_region(_zone:int,pos:Vector3)->Vector3i:return Vector3i(pos)
func heading_of(degrees:float)->int:return int(degrees*4096.0/360.0)
func UseSlot(x:int,y:int,z:int,speed:float,heading:int,on:bool,slot:int,kind:int)->void:slots.append([x,y,z,speed,heading,on,slot,kind])
'''+method+'\n')
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="PrivateWeaponSprint"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    names = ['weapon_sprint_state.gd','test_weapon_sprint_state.gd','ui_player_pose.gd']
    inputs = {str(p):digest(p) for p in [original,reference]+[source/n for n in names]}
    for name in names:
        shutil.copy2(source/name,project/name)
    report = project/'state_tests.json'
    report.unlink(missing_ok=True)
    with (lab/'state_tests.log').open('w') as log:
        result = subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),
            '--headless','--path',str(project),'--script',str(project/'test_weapon_sprint_state.gd'),'--quit-after','120'],
            stdout=log,stderr=subprocess.STDOUT,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0 and report.exists(),str(lab/'state_tests.log')
    data = json.loads(report.read_text())
    assert data['passed'] and data['checks'] >= 50 and data['original_switch_weapon_executed']
    assert all(digest(Path(p)) == sha for p,sha in inputs.items())
    data['source_inputs'] = inputs
    (lab/'state_tests.json').write_text(json.dumps(data,indent=2))
    return {k:v for k,v in data.items() if k!='source_inputs'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--install',type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(),args.install.resolve())))
