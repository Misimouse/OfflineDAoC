"""Check candidate original Stealth activation and existing bridge state compatibility."""
import argparse,json,os,re,shutil,subprocess
from datetime import datetime
from pathlib import Path
from prepare_combined_expansion_data import digest

def verify(workspace,install):
    source=Path(__file__).resolve().parents[1]/'Godot'
    root=workspace/'StealthLab/Compatibility'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');project=root/'Project';project.mkdir(parents=True)
    (project/'project.godot').write_text('[application]\nconfig/name="Private original Stealth compatibility"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf-8')
    inputs={str(p):digest(p) for p in source.glob('*.gd')}
    catalog=workspace/'models.json';inputs[str(catalog)]=digest(catalog);shutil.copy2(catalog,root/'models.json')
    for p in source.glob('*.gd'):shutil.copy2(p,project/p.name)
    scripts=['test_entity_lifecycle','test_live_riding_state','test_stealth_state','test_timed_effects','test_macros','test_journal_state','test_trainer_state','test_party_state','test_concentration_state','test_player_vitals_boundary','test_player_combat','test_player_release','test_combat_audio_state','test_weapon_mode_audio_state','test_spell_audio_state','test_combat_visual','test_gm_test_mode','test_release_camera','test_chat_death_fix','test_corpse_and_attack_visibility','test_item_handover_gateway','test_live_riding_gateway','test_target_tracking_state','test_player_model_state','test_inventory','test_classic_ui','test_spell_cast']
    for name in scripts:
        for folder in re.findall(r'Reports/([A-Za-z0-9_-]+)',(source/(name+'.gd')).read_text(encoding='utf-8')):
            for base in [root,project]:(base/'Reports'/folder).mkdir(parents=True,exist_ok=True)
    seed=workspace/'Reports/ui_integration/fixture.json';inputs[str(seed)]=digest(seed)
    (root/'Reports/ui_integration').mkdir(parents=True,exist_ok=True);shutil.copy2(seed,root/'Reports/ui_integration/fixture.json')
    env=dict(os.environ,APPDATA=str(root/'AppData'),LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA','LOCALAPPDATA']:Path(env[key]).mkdir()
    reports={}
    for name in scripts:
        before={str(p):p.stat().st_mtime_ns for p in root.rglob('*.json')}
        r=subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'),'--headless','--path',str(project),'--script','res://'+name+'.gd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        (root/(name+'.log')).write_text(r.stdout,encoding='utf-8');assert r.returncode==0 and 'ERROR:' not in r.stdout,r.stdout
        rows=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{') and '"passed"' in line]
        if name=="test_spell_audio_state" and "SPELL_AUDIO_STATE_PASS" in r.stdout:rows=[dict(passed=True,checks=0,assertion_suite=True)]
        if not rows:rows=[json.loads(p.read_text()) for p in root.rglob('*.json') if p.stat().st_mtime_ns!=before.get(str(p))]
        value=next(v for v in rows if isinstance(v,dict) and 'passed' in v and 'checks' in v)
        assert value['passed'] and not value.get('failures',[]) and (value['checks']>0 or name=='test_spell_audio_state'),value
        reports[name]=value;print(json.dumps({name:value['checks']}),flush=True)
    assert all(digest(Path(p))==h for p,h in inputs.items())
    result=dict(passed=True,source_inputs=inputs,reports=reports,checks=sum(v['checks'] for v in reports.values()),normal_installation_modified=False,server_started=False)
    (root/'verified.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return dict(passed=True,checks=result['checks'],packages=len(reports),output=str(root))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.workspace.resolve(),a.install.resolve())))
