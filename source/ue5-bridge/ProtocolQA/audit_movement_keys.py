"""Export original run/walk defaults and model-specific backward animation rates."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    root=workspace/'MovementKeysLab';root.mkdir(exist_ok=True)
    game=install/'new-client/godot';source=Path(__file__).resolve().parents[1]
    keys=game/'content/ui/keybinds.json';player=game/'game/player.gd';profiles=workspace/'FootstepAudioLab/OriginalFootstepAudio_v01/sounds.json'
    rows=json.loads(profiles.read_text())['local_player_models'];inputs={str(p):digest(p) for p in [keys,player,profiles,workspace/'JumpLandingLab/installed.json']};models={}
    for model,row in rows.items():
        race='mino' if model=='1419' else row['race'];assert race
        path=game/'content/characters/races'/race/'figure.json';meta=json.loads(path.read_text());inputs[str(path)]=digest(path)
        stride=meta['strides_units']['back'];length=meta['clip_seconds']['walk_back'];assert stride>0 and length>0
        models[model]=dict(stride_units=stride,clip_seconds=length,race=race)
    assert len(models)==13
    actions={r['id']:r for r in json.loads(keys.read_text())['actions']}
    assert actions['run_lock']['presets']['rpg']==['NumLock'] and actions['walk']['presets']['rpg']==['ScrollLock']
    catalog=root/'movement.json';catalog.write_text(json.dumps(dict(version=1,models=models),indent=2),encoding='utf-8')
    report=dict(passed=True,installed=False,input_hashes=inputs,catalog=str(catalog),catalog_sha256=digest(catalog),models=len(models),scope='run-lock/walk-toggle/modern backpedal; existing mouse controls retained')
    (root/'resources.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return dict(passed=True,models=len(models),catalog=str(catalog))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
