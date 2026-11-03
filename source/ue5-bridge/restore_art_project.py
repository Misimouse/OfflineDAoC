"""Hash-guarded rollback of the shared project binding; no art/map rollback."""
import argparse,ctypes,hashlib,json,os
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--bridge-root',required=True,type=Path)
parser.add_argument('--apply',action='store_true')
args=parser.parse_args();bridge=args.bridge_root.resolve(strict=True)
report=bridge/'Reports/shared_project/installation.json'
installation=json.loads(report.read_text())
assert installation['managed_by']=='DAoCVisualBridge' and installation['applied']
project=Path(installation['project']).resolve(strict=True)
backup=Path(installation['backup']).resolve(strict=True)
assert backup.is_relative_to(bridge/'Backups') and project.suffix=='.uproject'
config=bridge/'playable_project.json';link=project.parent/'Plugins/DAoCVisualBridge'
source=(bridge/'Client/Plugins/DAoCVisualBridge').resolve(strict=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(project)==installation['project_sha256'],'Project settings changed later; preserve them.'
assert digest(config)==installation['configuration_sha256'],'Launcher settings changed later; preserve them.'
assert digest(backup/project.name)==installation['previous_project_sha256']
assert link.resolve()==source and source.is_relative_to(bridge)
if installation['plugin_link_created']:
    assert link.is_junction(), 'The managed plugin link was replaced; preserve it.'
owned=[]
for item in installation['profiles']:
    if item['action']!='copied':continue
    path=project.parent/'Saved'/item['name']
    assert path.parent.resolve()==(project.parent/'Saved').resolve()
    assert path.exists() and digest(path)==item['sha256'],'An imported interface profile changed later; preserve it.'
    owned.append(path)
if args.apply:
    # Exclusive access refuses rollback while the native DLL is in use.
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
    kernel.CreateFileW.restype=ctypes.c_void_p
    handle=kernel.CreateFileW(str(source/'Binaries/Win64/UnrealEditor-DAoCVisualBridge.dll'),0xC0000000,0,None,3,0,None)
    if handle==ctypes.c_void_p(-1).value:raise OSError(ctypes.get_last_error(),'Close the game before restoring the project binding.')
    kernel.CloseHandle.argtypes=[ctypes.c_void_p];kernel.CloseHandle(handle)
    project.write_bytes((backup/project.name).read_bytes())
    if (backup/config.name).exists():config.write_bytes((backup/config.name).read_bytes())
    else:config.unlink()
    for path in owned:path.unlink()
    if installation['plugin_link_created']:
        # Windows RemoveDirectory removes this junction only, without traversing its target.
        os.rmdir(link)
result={'restored':args.apply,'project':str(project),'art_content_modified':False,'profiles_removed':len(owned) if args.apply else 0}
(report.parent/'rollback.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
