"""Record the original compass UI, input defaults and heading conversion used as reference."""
import argparse,json
from pathlib import Path
import struct
from prepare_combined_expansion_data import digest
from central_activation_receipts import COMPASS_ART_SHA256

def verify(workspace,install):
    original=install/'new-client/godot'
    ui=original/'game/ui/game_ui.gd';keys=original/'content/ui/keybinds.json';server=original/'game/net/server.gd';art=original/'content/ui/classic/x4plus/compass_bar.png'
    text=ui.read_text(encoding='utf-8');net=server.read_text(encoding='utf-8')
    assert 'Vector2(112, 22)' in text and 'Vector2(108, 16)' in text and 'Vector2(256, 16)' in text
    assert '54.0 - 256.0 - x' in text and 'show_compass' in text
    assert '180.0' in net and 'func compass_of' in net
    assert art.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',art.read_bytes()[16:24])==(2048,128) and digest(art)==COMPASS_ART_SHA256
    root=workspace/'CompassLab';assert digest(root/'Art/compass_bar.png')==digest(art)
    result=dict(passed=True,logical_size=[112,22],original_pixels_unchanged=True,heading_reference='Server.compass_of plus bridge coordinate conversion',source_inputs={str(p):digest(p) for p in [ui,keys,server,art]})
    (root/'reference_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['workspace','install']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=verify(a.workspace.resolve(),a.install.resolve());print(json.dumps({k:v for k,v in r.items() if k!='source_inputs'}))
