"""Build a separate repaired shield material and an inactive candidate catalogue.

Run from the private bridge directory, with shield_emblem_material.py beside it.
Never saves maps, changes original textures, or activates the candidate catalogue.
"""
import hashlib
import json
from pathlib import Path
import sys
import unreal

R=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from shield_emblem_material import build_shield_material

D=R/'Reports/shield_material'
D.mkdir(parents=True,exist_ok=True)
catalog_path=R/'equipment_catalog_v01.json'
before=hashlib.sha256(catalog_path.read_bytes()).hexdigest()
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
old=catalog['emblems']['material']
root='/DAoCVisualBridge/Emblems_v01'
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([root],True)
material=build_shield_material(root,'M_OriginalShieldEmblem_v02')
catalog['emblems']['material']=material.get_path_name()
candidate=R/'equipment_catalog_shield_candidate.json'
candidate.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
assert hashlib.sha256(catalog_path.read_bytes()).hexdigest()==before
(D/'import.json').write_text(json.dumps({
    'passed':True,'original_material':old,'candidate_material':material.get_path_name(),
    'candidate_catalog':str(candidate),'active_catalog_unchanged':True,
    'original_textures_unchanged':True,'maps_saved':False,
},indent=2),encoding='utf-8')
