"""Extract original effect geometry/controllers/particle metadata; never synthesizes spell rules."""
from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import json,struct,base64,hashlib,shutil
R=Path(__file__).resolve().parent;G=Path(str(INSTALL / 'new-client/godot'));D=R/'UnrealPlugin/DAoCVisualBridge/Content/SpellVisuals_v01';(D/'Data').mkdir(parents=True,exist_ok=True);(R/'SourceSpellVisuals_v01/Textures').mkdir(parents=True,exist_ok=True)
source=json.loads((G/'content/spells/spell_fx.json').read_text());textures={};files={};catalog={'effects':source['effects'],'fx':{},'textures':{},'errors':[]};formats={5120:'b',5121:'B',5122:'h',5123:'H',5125:'I',5126:'f'};widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def texture(folder,name):
 if not name:return ''
 candidates=[folder/'textures/x4plus'/(name+'.png'),folder/'textures/original'/(name+'.png')]
 p=next((p for p in candidates if p.exists()),None)
 if not p:return ''
 key=hashlib.sha256(p.read_bytes()).hexdigest()[:20]
 if key not in textures:
  out=R/'SourceSpellVisuals_v01/Textures'/('T_'+key+'.png');shutil.copy2(p,out);textures[key]=str(out)
 return key
def extract(p):
 gl=json.loads(p.read_text());buf=[]
 for b in gl.get('buffers',[]):
  uri=b['uri'];buf.append(base64.b64decode(uri.split(',',1)[1]) if uri.startswith('data:') else (p.parent/uri).read_bytes())
 def acc(i):
  a=gl['accessors'][i];v=gl['bufferViews'][a['bufferView']];fmt=formats[a['componentType']];n=widths[a['type']];size=struct.calcsize(fmt);offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',size*n)
  return [list(struct.unpack_from('<'+fmt*n,buf[v['buffer']],offset+j*stride)) for j in range(a['count'])]
 extras=gl.get('extras',{});out={'particles':extras.get('nif_particles',[]),'parts':[]}
 for em in out['particles']:em['texture_key']=texture(p.parent,em.get('texture',''))
 for ni,node in enumerate(gl.get('nodes',[])):
  if 'mesh' not in node or node.get('name','').lower().startswith('collision'):continue
  for prim in gl['meshes'][node['mesh']]['primitives']:
   if prim.get('mode',4)!=4:continue
   a=prim['attributes'];mat=extras.get('nif_materials',[]);mi=prim.get('material',0);m=mat[mi] if mi<len(mat) else {};part={'name':node.get('name',''),'positions':acc(a['POSITION']),'indices':[r[0] for r in acc(prim['indices'])] if 'indices' in prim else list(range(len(acc(a['POSITION'])))),'material':m,'node':{k:node[k] for k in ['translation','rotation','scale','matrix'] if k in node},'morph_targets':[acc(t['POSITION']) for t in prim.get('targets',[]) if 'POSITION'in t]}
   for key,attr in [('normals','NORMAL'),('uvs','TEXCOORD_0'),('colors','COLOR_0')]:
    if attr in a:part[key]=acc(a[attr])
   part['texture_key']=texture(p.parent,m.get('slots',{}).get('base',{}).get('tex',''))
   part['anim']=next((a for a in extras.get('nif_node_anims',[]) if part['name'] in a.get('meshes',[])),{})
   part['morph']=next((a for a in extras.get('nif_morphs',[]) if a.get('node')==part['name']),{})
   out['parts'].append(part)
 return out
for ident,row in source['fx'].items():
 p=G/row['nif'].removeprefix('res://')
 if not p.exists():catalog['errors'].append({'id':ident,'missing':row['nif']});continue
 key=hashlib.sha256(row['nif'].encode()).hexdigest()[:16]
 if key not in files:
  data=extract(p);files[key]=data;(D/'Data'/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
 catalog['fx'][ident]=dict(row,data=key)
catalog['figure_models']=json.loads((R/'SourceSpellVisuals_v01/figure_models.json').read_text())
catalog['textures']={key:'/DAoCVisualBridge/SpellVisuals_v01/Textures/T_'+key+'.T_'+key for key in textures}
(D/'catalog.json').write_text(json.dumps(catalog,separators=(',',':')),encoding='utf-8');(R/'SourceSpellVisuals_v01/textures.json').write_text(json.dumps(textures))
report={'passed':not catalog['errors'],'spell_definitions':len(catalog['effects']),'effect_records':len(catalog['fx']),'source_effect_files':len(files),'textures':len(textures),'mesh_parts':sum(len(v['parts'])for v in files.values()),'particle_emitters':sum(len(v['particles'])for v in files.values()),'data_bytes':sum(p.stat().st_size for p in (D/'Data').glob('*.json')),'errors':catalog['errors']}
(R/'Reports/training_staff_fx_pets/fx_export.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
