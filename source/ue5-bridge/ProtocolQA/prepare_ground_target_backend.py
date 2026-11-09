"""Stage a private Godot backend build with the original controlled header fix."""
import argparse,json,shutil,hashlib
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(workspace,install):
    lab=workspace/'GroundTargetLab';root=lab/'BackendSource';root.mkdir(exist_ok=True)
    source=install/'new-client/godot';repo=Path(__file__).resolve().parents[3];network=repo/'source/new-client/godot/game/net/DaocClient.cs';original=source/'game/net/DaocClient.cs'
    assert digest(original)=='29d0982123ea234d819e0c209d43d34cc9b2907315746f0f8f5ff909d9d89410'
    before=original.read_text();after=network.read_text();assert '_bridgeGroundTargetInView = true;' in after and 'BridgeGroundTargetSight(bool visible)' in after
    expected=before.replace('\tvoid UseHeader(Writer w, float x, float y, float z, float speed, int heading, bool targetInView)','\t// The UE bridge supplies its own physical ground-target visibility. Keep the\n\t// legacy default for existing Godot callers until they opt into this setter.\n\tbool _bridgeGroundTargetInView = true;\n\tpublic void BridgeGroundTargetSight(bool visible) => _bridgeGroundTargetInView = visible;\n\n\tvoid UseHeader(Writer w, float x, float y, float z, float speed, int heading, bool targetInView)').replace('w.Short((ushort)(targetInView ? 0xB000 : 0x1000));','w.Short((ushort)((targetInView ? 0xA000 : 0) | (_bridgeGroundTargetInView ? 0x1000 : 0)));')
    assert after==expected,'Refuse unrelated network-client source changes'
    inputs={str(network):digest(network)}
    for p in sorted(source.rglob('*.cs')):
        if '.godot' in p.parts:continue
        target=root/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);origin=network if p==original else p;inputs[str(origin)]=digest(origin);shutil.copy2(origin,target)
    shutil.copy2(source/'MMOEngine.csproj',root/'MMOEngine.csproj');inputs[str(source/'MMOEngine.csproj')]=digest(source/'MMOEngine.csproj')
    feed=install/'new-client/tools/godot_net/GodotSharp/Tools/nupkgs';assert feed.is_dir();(root/'nuget.config').write_text('<configuration><packageSources><clear/><add key="godot-local" value="'+str(feed)+'"/></packageSources></configuration>')
    (lab/'backend_prepared.json').write_text(json.dumps(dict(passed=True,source_inputs=inputs,original_network_source_sha256=digest(original),network_source_sha256=digest(network),project=str(root/'MMOEngine.csproj'),normal_runtime_modified=False),indent=2));return dict(passed=True,source_files=len(inputs),project=str(root/'MMOEngine.csproj'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--install',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.workspace.resolve(),a.install.resolve())))
