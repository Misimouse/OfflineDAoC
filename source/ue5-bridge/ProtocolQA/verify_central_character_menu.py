"""Smoke-test the installed character menu without entering or changing a character."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from central_activation_receipts import verify_files


def verify(workspace, install, engine):
    receipt = json.loads((workspace/'ExpansionRaceLab/CentralDelivery/MinotaurActivation/installed.json').read_text())
    assert receipt['installed'] and receipt['only_race_enabled'] == 21
    verify_files(workspace)
    for port in (10300, 19727):
        with socket.socket() as guard:
            guard.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            guard.bind(('127.0.0.1', port))
    sdk = engine/'Binaries/ThirdParty/DotNet/10.0/win-x64'
    env = dict(os.environ, DAOC_INSTALL=str(install), DAOC_UE_ENGINE=str(engine),
               DOTNET_ROOT=str(sdk), DOTNET_ROOT_X64=str(sdk))
    output = workspace/'Reports/central_character_menu'
    output.mkdir(parents=True, exist_ok=True)
    probe = workspace/'Reports/character_lobby/live_menu.json'
    probe.unlink(missing_ok=True)
    report = {'passed': False, 'world_entered': False, 'normal_shutdown': False}
    server = launcher = None
    try:
        with (output/'server.log').open('w') as server_log, (output/'launcher.log').open('w') as launcher_log:
            try:
                server = subprocess.Popen([str(sdk/'dotnet.exe'), str(install/'runtime/server/CoreServer.dll'), '--start'],
                    cwd=install/'runtime/server', env=env, stdin=subprocess.PIPE, stdout=server_log,
                    stderr=subprocess.STDOUT, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                deadline = time.monotonic()+120
                while True:
                    assert server.poll() is None, 'Normal server exited before readiness'
                    try:
                        with socket.create_connection(('127.0.0.1', 10300), timeout=.25):
                            break
                    except OSError:
                        assert time.monotonic() < deadline, 'Normal server readiness timed out'
                        time.sleep(.5)
                launcher = subprocess.Popen([str(sdk/'dotnet.exe'),
                    str(workspace/'Launcher/bin/Release/net10.0/BridgeLauncher.dll'), '--menu-test',
                    '--bridge-root='+str(workspace)], cwd=workspace, env=env, stdout=launcher_log,
                    stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                launcher.wait(timeout=240)
                assert launcher.returncode == 0
                raw = probe.read_bytes()
                menu = json.loads(raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'))
                assert menu['passed'] and not menu['world_entered'] and menu['choices'] > 0
                report.update(menu)
            finally:
                # Ask only our own processes to finish; never kill an existing session.
                (workspace/'Reports/live/logout.request').write_text('logout', encoding='utf-8')
                try:
                    if launcher is not None and launcher.poll() is None:
                        launcher.wait(timeout=110)
                finally:
                    if server is not None and server.poll() is None:
                        server.stdin.write('exit\n')
                        server.stdin.flush()
                        server.wait(timeout=90)
                report['normal_shutdown'] = server is not None and server.returncode == 0 and launcher is not None and launcher.returncode == 0
        assert report['normal_shutdown']
        return report
    finally:
        (output/'verified.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('workspace', 'install', 'engine'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.workspace.resolve(), args.install.resolve(), args.engine.resolve())))
