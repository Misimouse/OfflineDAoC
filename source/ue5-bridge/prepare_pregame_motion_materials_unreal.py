"""Separate animated pregame materials; no map or existing resource is saved."""
import json,os,sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from pregame_material_unreal import build
workspace=Path(os.environ['DAOC_BRIDGE_WORKSPACE'])
folder=workspace/'SourcePregame_v03'
definitions=json.loads((folder/'hibernia_lobby.glb.materials.json').read_text())
root='/DAoCVisualBridge/PregameMotion_v01'
paths=[]
for definition in definitions:
    material=build(root,'M_Layered_'+definition['name'],definition,folder,source_uniforms=True)
    paths.append(material.get_path_name())
assert len(paths)==30
out=workspace/'Reports/pregame_motion/materials.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'passed':True,'map_saved':False,'materials':paths},indent=2))
