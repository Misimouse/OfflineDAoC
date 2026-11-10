"""Isolated progression/UI regression; no played DB, server, or installed files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(workspace, install):
    source = Path(__file__).resolve().parents[1] / 'Godot'
    root = workspace / 'ProgressionLab/State' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    project = root / 'Project'
    project.mkdir(parents=True)
    (project / 'project.godot').write_text('[application]\nconfig/name="Private progression UI regression"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
    inputs = {str(p): digest(p) for p in source.glob('*.gd')}
    for name in inputs:
        shutil.copy2(name, project / Path(name).name)
    env = dict(os.environ, APPDATA=str(root/'AppData'), LOCALAPPDATA=str(root/'LocalAppData'))
    for key in ['APPDATA', 'LOCALAPPDATA']:
        Path(env[key]).mkdir()
    result = subprocess.run([str(install/'new-client/tools/godot_net/Godot_v4.7.2-stable_mono_win64_console.exe'), '--headless', '--audio-driver', 'Dummy', '--path', str(project), '--script', 'res://test_progression_ui.gd'], env=env, capture_output=True, text=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
    output = result.stdout + result.stderr
    (root/'godot.log').write_text(output, encoding='utf-8')
    assert result.returncode == 0 and 'ERROR:' not in output, output
    report = json.loads(next(line for line in output.splitlines() if line.startswith('{') and '"passed"' in line))
    assert report['passed'] and not report['failures'] and report['checks'] >= 24, report
    assert all(digest(Path(name)) == value for name, value in inputs.items())
    report.update(source_inputs=inputs, server_started=False, normal_installation_modified=False)
    (root/'verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return dict(passed=True, checks=report['checks'], proof=str(root/'verified.json'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for key in ['workspace', 'install']:
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.install.resolve())))
