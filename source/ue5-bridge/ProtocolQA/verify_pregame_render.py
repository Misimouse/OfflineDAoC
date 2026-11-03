"""Capture the real lobby render, without an account, server or playable map.

The fixture must be a disposable lobby snapshot. Structural results alone do
not establish visual acceptance: review both PNGs against the Godot reference.
"""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--fixture', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--engine', type=Path, default=Path(os.environ.get('DAOC_UE_ENGINE', r'C:/Program Files/Epic Games/UE_5.8/Engine')))
    parser.add_argument('--width', type=int, default=1920)
    parser.add_argument('--height', type=int, default=1080)
    parser.add_argument('--screen', choices=('select', 'create'), default='select')
    args = parser.parse_args()
    assert 640 <= args.width <= 7680 and 480 <= args.height <= 2160
    fixture = json.loads(args.fixture.read_text(encoding='utf-8-sig'))
    assert isinstance(fixture.get('character_lobby'), dict)
    args.output.mkdir(parents=True, exist_ok=True)
    staged = args.output / 'fixture.json'
    staged.write_text(json.dumps(fixture), encoding='utf-8')
    shot = args.output / (args.screen + '.png')
    command = [str(args.engine / 'Binaries/Win64/UnrealEditor-Cmd.exe'), str(args.project),
               '/Engine/Maps/Entry', '-game', '-EnablePlugins=DAoCVisualBridge', '-DaocBridge',
               '-DaocBridgeCatalog=' + str(args.workspace / 'models.json'),
               '-DaocBridgeEquipmentCatalog=' + str(args.workspace / 'equipment_catalog_v01.json'),
               '-DaocBridgeCharacterLobbyTest=' + str(staged),
               '-DaocBridgeCharacterLobbyCapture=' + str(shot),
               '-DaocBridgeCharacterLobbyScreen=' + args.screen,
               '-unattended', '-nosound', '-nosplash', '-d3d11', '-RenderOffscreen',
               '-windowed', '-ForceRes', '-ResX=' + str(args.width), '-ResY=' + str(args.height)]
    started = time.time()
    with (args.output / 'native.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    assert result.returncode == 0, result.returncode
    report_path = Path(str(staged) + '.native.json')
    assert report_path.exists() and report_path.stat().st_mtime >= started, 'No fresh result'
    report = json.loads(report_path.read_text(encoding='utf-8-sig'))
    assert report['passed'] and not report['live_account'], report
    assert (report['preview_width'], report['preview_height']) == (args.width, args.height), report
    assert report['backdrop_lods'] == [{'triangles': 62798, 'uv_channels': 4}], report
    for image in (shot, Path(str(shot) + '.scene.png')):
        assert image.exists() and image.stat().st_mtime >= started
        header = image.read_bytes()[:24]
        assert header[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II', header[16:24]) == (args.width, args.height), image
    print(json.dumps(dict(report, visual_acceptance='pending_manual_review')))


if __name__ == '__main__':
    main()
