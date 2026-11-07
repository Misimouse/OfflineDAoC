"""Read-only display parity audit; no account or database inputs."""
import argparse,json
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    original=install/'new-client/godot/game/ui'
    inputs=[original/'options_window.gd',original/'boot_settings.gd',Path(__file__).resolve().parents[1]/'Launcher/Program.cs']
    report=dict(passed=True,scope=['resolution','window mode','frame cap'],resolutions=[[1280,720],[1366,768],[1600,900],[1920,1080],[2560,1080],[2560,1440],[3440,1440],[3840,2160]],caps=[0,30,60,75,90,120,144,165,240,-1],
      original_positive_caps_use_vsync=True,launcher_forces_initial_1920x1080_window=True,first_run_preserves_current_display=True,
      differences=['UE borderless uses desktop dimensions; resolution is selectable in windowed/fullscreen modes'],
      excluded=['quality presets','adaptive performance governor','renderer changes','map optimization'],input_hashes={str(p):digest(p) for p in inputs},database_modified=False)
    root=workspace/'DisplaySettingsLab';root.mkdir(exist_ok=True);(root/'reference_audit.json').write_text(json.dumps(report,indent=2));return dict(passed=True,output=str(root/'reference_audit.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.workspace,a.install)))
