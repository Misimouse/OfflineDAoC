"""Build a new, inactive skin material and calibrated catalog in a private host."""
import json,os,sys
from pathlib import Path
import unreal
sys.path.insert(0,str(Path(__file__).resolve().parent))
from appearance_material_unreal import build_appearance_material
from calibrate_character_colour import calibrate

root=Path(os.environ['DAOC_CHARACTER_LAB'])
source=Path(os.environ['DAOC_APPEARANCE_CATALOG'])
assert source.resolve()!=(root/'appearance_catalog_feedback_candidate.json').resolve()
catalog=calibrate(json.loads(source.read_text(encoding='utf-8-sig')))
default=unreal.load_asset(catalog['textures']['cel_m_head01'])
material=build_appearance_material('/DAoCVisualBridge/AppearanceColour_v03/Materials','M_SourceMaskColourSkin',default,False)
catalog['materials']['skin']=material.get_path_name()
(root/'appearance_catalog_feedback_candidate.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
(root/'material_build.json').write_text(json.dumps({'passed':True,'installed':False,'material':material.get_path_name(),'source_mask':'OriginalColorTexture.A','celt_tint_chroma':.35},indent=2))
