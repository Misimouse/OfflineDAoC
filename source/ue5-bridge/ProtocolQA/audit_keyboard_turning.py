"""Pin original keyboard turning without changing accepted native controls."""
import argparse
import json
from pathlib import Path
from prepare_combined_expansion_data import digest


def audit(workspace,install):
    source = Path(__file__).resolve().parents[1]
    original = install/'new-client/godot/game/player.gd'
    native = source/'UnrealPlugin/DAoCVisualBridge/Source/DAoCVisualBridge/Private'
    paths = [original,install/'new-client/godot/content/ui/keybinds.json',native/'DAoCBridgeSubsystem.cpp',
             native/'DAoCBridgeKeyConfiguration.cpp',native/'DAoCBridgeTargetTracking.h']
    inputs = {str(p):digest(p) for p in paths}
    text = original.read_text(encoding='utf-8-sig')
    assert 'const TURN_RATE := PI' in text
    assert 'if rmb and not classic:' in text
    assert 'turn += (1.0 if left else 0.0) - (1.0 if right else 0.0)' in text
    assert 'char_yaw += turn * TURN_RATE * delta' in text
    assert 'not lmb and (moving or absf(turn) > 0.0)' in text
    assert 'track_mode != "face" and (left or right)' in text
    lab = workspace/'KeyboardTurningLab';lab.mkdir(exist_ok=True)
    result = dict(passed=True,installed=False,source_inputs=inputs,normal_runtime_modified=False,
        original_turn_degrees_per_second=180,
        contracts=['Keep accepted A/D strafing; add editable Left/Right arrow defaults.',
                   'Modern right-mouse-held turn keys strafe rather than rotate.',
                   'Otherwise turn character at original rate, including while stationary.',
                   'Left-button camera orbit remains independent of character turning.',
                   'Turning cancels follow/stick; original face tracking is treated separately.',
                   'No rotation while dead/seated/typing/options/unfocused/mounted or without local session.',
                   'No position, speed, collision or server permission fabrication.'],
        scope='Original modern movement keyboard turn keys only; full classic mode and keyboard presets remain separate')
    assert all(digest(Path(p))==sha for p,sha in inputs.items())
    output = lab/('audit_current.json' if (lab/'installed.json').exists() else 'audit.json')
    output.write_text(json.dumps(result,indent=2))
    if (lab/'installed.json').exists():
        return {k:v for k,v in result.items() if k!='source_inputs'}
    (lab/'checkpoint.json').write_text(json.dumps(dict(active_block='CLIENT-KEYBOARD-TURNING',
        installed=False,phase='original_contract_audited',next_step='Implement bounded native turn/strafe helper and replay actual input, corpse/seated locks and tracking before installation.'),indent=2))
    return {k:v for k,v in result.items() if k!='source_inputs'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--install',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.workspace.resolve(),args.install.resolve())))
