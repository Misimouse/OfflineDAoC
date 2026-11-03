"""Prepare original appearance textures and shader masters; do not activate the candidate."""
import os,hashlib,json,traceback
from pathlib import Path
import unreal,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from appearance_material_unreal import build_appearance_material
R=Path(os.environ.get('DAOC_BRIDGE_WORKSPACE',Path(__file__).resolve().parent));D=R/'Reports/appearance';root='/DAoCVisualBridge/Appearance_v01';A=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem);T=unreal.AssetToolsHelpers.get_asset_tools();M=unreal.MaterialEditingLibrary
report={'passed':False,'installed':False,'textures':{},'errors':[]}
try:
 guarded=[R/'models.json',R/'equipment_catalog_v01.json'];hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded]
 exported=json.loads((R/'SourceAppearance/exported.json').read_text());catalog=json.loads((R/'appearance_catalog_candidate.json').read_text());assert not catalog['activated']
 for key,row in exported['textures'].items():
  file=Path(row['file']);sha=hashlib.sha256(file.read_bytes()).hexdigest();name='T_'+sha[:20];texture=unreal.load_asset(root+'/Textures/'+name)
  if not texture:
   task=unreal.AssetImportTask();task.filename=str(file);task.destination_path=root+'/Textures';task.destination_name=name;task.automated=True;task.save=True;task.replace_existing=False;T.import_asset_tasks([task]);texture=unreal.load_asset(root+'/Textures/'+name)
  assert isinstance(texture,unreal.Texture2D),(key,'not a texture')
  assert texture.blueprint_get_size_x()==row['width'] and texture.blueprint_get_size_y()==row['height'],(key,'dimensions changed')
  assert texture.get_editor_property('srgb'),(key,'source colour texture must be sRGB')
  report['textures'][key.lower()]={'asset':texture.get_path_name(),'sha256':sha,'width':row['width'],'height':row['height']}
  if len(report['textures'])%25==0:unreal.SystemLibrary.collect_garbage()
 default=unreal.load_asset(report['textures']['cel_m_head01']['asset']);masters={}
 for name,cutout in [('M_OriginalAppearanceSkin',False),('M_OriginalAppearanceHair',True)]:
  material=build_appearance_material(root+'/Materials',name,default,cutout);masters['hair' if cutout else 'skin']=material.get_path_name()
  assert bool(material.get_editor_property('two_sided')) and material.get_editor_property('blend_mode')==(unreal.BlendMode.BLEND_MASKED if cutout else unreal.BlendMode.BLEND_OPAQUE)
 for figure in catalog['figures'].values():
  meta=figure['meta'];required=[f['tex'] for f in meta.get('faces',[])]+meta.get('eyes',[])+[r['tex'] for r in meta.get('tattoos',[]) if r.get('tex')]+[c['tex'] for h in meta.get('hair_styles',[]) for c in h.get('colours',[]) if c.get('tex')]
  assert all(t.lower() in report['textures'] for t in required),(figure['race'],'incomplete original texture coverage')
 catalog['textures']={key:row['asset'] for key,row in report['textures'].items()};catalog['materials']=masters
 assert hashes==[hashlib.sha256(p.read_bytes()).hexdigest() for p in guarded]
 (R/'appearance_catalog_candidate.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8');report['passed']=True;report['active_catalogues_unchanged']=True;report['materials']=masters
except Exception:report['errors'].append(traceback.format_exc())
(D/'prepare_materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8');assert report['passed'],report['errors']
