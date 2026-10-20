"""Read-only Hibernia landscape planner. Writes versioned overlays, never game assets or databases."""
import argparse,sys,json,hashlib,time,uuid,os,math
from pathlib import Path
if '--libs' in sys.argv:sys.path.insert(0,sys.argv[sys.argv.index('--libs')+1])
import numpy as np
from PIL import Image,ImageFilter

SCHEMA=1
REGIONS={200:'Hibernia clasica',181:'Hibernia Shrouded Isles'}
CLASSIC={0:1,1:2,2:1,6:3,7:3,9:1,10:1}
ISLES={0:1,1:3,6:2,7:2,8:2,9:2,11:3,12:1,13:2,14:2}

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def atomic(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    # Windows readers can briefly hold the destination without FILE_SHARE_DELETE.
    for attempt in range(40):
        try:os.replace(temp,p);return
        except PermissionError:
            if attempt==39:raise
            time.sleep(0.025)

def catalog(root):
    index=json.loads((root/'zones_index.json').read_text(encoding='utf-8-sig'));out=[]
    for key,entry in sorted(index.items(),key=lambda x:int(x[0])):
        region=int(entry.get('region',-1))
        if region not in REGIONS:continue  # Explicit ToA, Albion and Midgard exclusion.
        path=root/f'zone{int(key):03d}'/'zone.json'
        if not path.exists():continue
        d=json.loads(path.read_text(encoding='utf-8-sig'));c=d.get('clutter') or {}
        atlas=c.get('atlas','');why=[]
        if d.get('city') or d.get('dungeon') or entry.get('type')!=0:why.append('Ciudad o interior')
        if atlas not in ('grass_hib','grass_hibexp'):why.append('Sin conjunto Hibernia reconocido')
        for file in [c.get('grassmap',''),c.get('densemap',''),d.get('heights_2x',d.get('heights',''))]:
            if not file or not (path.parent/file).is_file():why.append('Faltan mapas originales');break
        out.append({'id':int(key),'name':entry['name'],'region':region,'edition':REGIONS[region],
                    'eligible':not why,'reason':'; '.join(why),'atlas':atlas,'size_m':d.get('size_m',0),
                    'source':str(path.parent),'zone_sha256':digest(path)})
    return out

def image_plane(p):return np.asarray(Image.open(p).convert('L').resize((256,256),Image.Resampling.NEAREST))

def plan_zone(zone,options,dest):
    source=Path(zone['source']);d=json.loads((source/'zone.json').read_text(encoding='utf-8-sig'));c=d['clutter'];inputs={}
    def track(name):
        p=source/name;inputs[name]=digest(p);return p
    track('zone.json');groups=image_plane(track(c['grassmap']))//10
    density=image_plane(track(c['densemap'])).astype(np.float32)/255
    habitat=np.zeros((256,256),dtype=np.uint8)
    mapping=ISLES if c['atlas']=='grass_hibexp' else CLASSIC
    for group,kind in mapping.items():habitat[groups==group]=kind
    size=float(d['size_m']);heights_name=d.get('heights_2x',d['heights']);n=int(d.get('heights_2x_size',d['heights_size']))
    height=np.fromfile(track(heights_name),dtype='<f4').reshape(n,n)
    # The same bilinear surface grid as ZoneLoader.height_at, sampled at clutter cell centres.
    coordinates=(np.arange(256)+0.5)/256*(n-1);lo=np.floor(coordinates).astype(int);hi=np.minimum(lo+1,n-1);f=coordinates-lo
    h=(height[lo[:,None],lo[None,:]]*(1-f[:,None])*(1-f[None,:])+
       height[hi[:,None],lo[None,:]]*f[:,None]*(1-f[None,:])+
       height[lo[:,None],hi[None,:]]*(1-f[:,None])*f[None,:]+
       height[hi[:,None],hi[None,:]]*f[:,None]*f[None,:])
    dz,dx=np.gradient(h,size/256);slope=np.degrees(np.arctan(np.hypot(dx,dz)))
    slope_ok=slope<float(options.get('max_slope',32))
    water_ok=np.ones_like(h,dtype=bool)
    if d.get('water_mask'):
        water=image_plane(track(d['water_mask']))
        for body in d.get('water',[]):water_ok &= ~((water==int(body['id'])) & (h<float(body['height'])+0.25))
    # Painted whole-zone colour overlays do not define land use. Only explicit road materials veto planting.
    roads=np.zeros_like(h,dtype=bool)
    for key,patch in (d.get('ground_splat')or{}).get('patches',{}).items():
        cx,cz=map(int,key.split('_'));layers=patch.get('layers',[])
        road_indices=[i-1 for i,l in enumerate(layers) if i>0 and any(t in l.get('tex','').lower() for t in ('road','path','cobble','pavement','floor'))]
        if not road_indices:continue
        for k in road_indices:
            weights=patch.get('weights',[])
            if k//4>=len(weights):continue
            p=track(weights[k//4]);rgba=np.asarray(Image.open(p).convert('RGBA').resize((32,32),Image.Resampling.BILINEAR))
            roads[cz*32:(cz+1)*32,cx*32:(cx+1)*32] |= rgba[:,:,k%4]>100
    fixture_excluded=np.zeros_like(h,dtype=bool);axis=(np.arange(256)+0.5)*size/256;xx,zz=np.meshgrid(axis,axis)
    protected=[]
    for fixture in d.get('fixtures',[]):
        name=str(fixture.get('name','')).lower()
        is_building=any(t in name for t in ('hut','shack','shop','tavern','house','hall','keep','castle','tower','fort','barn','stable','bridge','gate','wall','well','portal','ruin'))
        if not is_building:continue
        radius=4 if 'well' in name else (20 if any(t in name for t in ('keep','castle','fort')) else 12)
        radius*=float(fixture.get('scale',1));x,_,z=fixture['pos'];fixture_excluded|=(xx-x)**2+(zz-z)**2<radius**2
        protected.append({'id':fixture['id'],'name':fixture.get('name'),'x':x,'z':z,'radius':radius})
    for area in options.get('exclusions',{}).get(str(zone['id']),[]):
        fixture_excluded|=(xx-float(area['x']))**2+(zz-float(area['z']))**2<float(area['radius'])**2
    allowed=(habitat>0)&(density>0)&slope_ok&water_ok&~roads&~fixture_excluded
    density=np.where(allowed,density,0)
    habitat=np.where(allowed,habitat,0).astype(np.uint8)
    folder=dest/f"zone{zone['id']:03d}";folder.mkdir(parents=True)
    Image.fromarray(np.uint8(np.round(density*255))).save(folder/'density.png')
    Image.fromarray(habitat).save(folder/'habitat.png')
    palette=np.array([[0,0,0,0],[70,160,65,170],[160,130,65,170],[40,120,105,170]],dtype=np.uint8)
    overlay=palette[habitat].copy();overlay[:,:,3]=np.uint8(density*175);Image.fromarray(overlay).save(folder/'overlay.png')
    eligible_cells=int(allowed.sum());area=eligible_cells*(size/256)**2
    result={'schema':SCHEMA,'zone':zone['id'],'name':zone['name'],'realm':'hib','region':zone['region'],
      'edition':zone['edition'],'atlas':c['atlas'],'size_m':size,'grid':256,'density':'density.png','habitat':'habitat.png',
      'source':zone['source'],'inputs':inputs,'outputs':{n:digest(folder/n)for n in ['density.png','habitat.png','overlay.png']},
      'preserve_ground':True,'preserve_tall':True,'options':options,'protected_fixtures':protected,
      'summary':{'plantable_cells':eligible_cells,'plantable_m2':round(area),'habitats':{str(k):int((habitat==k).sum())for k in [1,2,3]},
       'wet_or_rock_or_snow_cells':int((np.where(np.isin(groups,list(mapping)),0,1)).sum()),'slope_excluded':int((~slope_ok).sum()),
       'water_excluded':int((~water_ok).sum()),'road_excluded':int(roads.sum()),'fixture_excluded':int(fixture_excluded.sum())},
      'caveat':'Masks follow original clutter data; road-name and fixture buffers are conservative heuristics. Runtime surface collision and slope checks are also required. No global visual acceptance implied.'}
    # Find well-populated preview locations; avoid automatically starting inside a house.
    scores=np.asarray(Image.fromarray(np.uint8(density*255)).filter(ImageFilter.GaussianBlur(3))).astype(float)/255
    scores[~allowed]=0;scores[:12]=0;scores[-12:]=0;scores[:,:12]=0;scores[:,-12:]=0
    points=[]
    for kind in [1,3,2]:
        candidate=np.where(habitat==kind,scores,0)
        if candidate.max()>0:
            iz,ix=np.unravel_index(candidate.argmax(),candidate.shape);points.append({'kind':kind,'x':float(axis[ix]),'z':float(axis[iz])})
    if zone['id']==207:points.insert(0,{'kind':1,'x':1190.0,'z':1180.0})
    result['preview_points']=points;atomic(folder/'plan.json',result)
    return result

def validate_pointer(pointer):
    bundle=Path(pointer['bundle']).resolve()
    if digest(bundle/'manifest.json')!=pointer['sha256']:raise ValueError('Hash del paquete no coincide')
    m=json.loads((bundle/'manifest.json').read_text(encoding='utf-8'))
    if m.get('realm')!='hib' or m.get('exclude_toa') is not True or set(m['regions'])!={181,200}:raise ValueError('Paquete fuera de Hibernia Classic/SI')
    seen=set()
    for entry in m['zones']:
        if entry['id'] in seen:raise ValueError('Zona duplicada')
        seen.add(entry['id']);p=(bundle/entry['path']).resolve()
        if not p.is_relative_to(bundle):raise ValueError('Ruta fuera del paquete')
        if digest(p)!=entry['sha256']:raise ValueError('Plan modificado')
        plan=json.loads(p.read_text(encoding='utf-8'));source=Path(plan['source']).resolve()
        if plan['region'] not in REGIONS or plan['realm']!='hib' or plan['zone']!=entry['id']:raise ValueError('Zona incompatible')
        original=json.loads((source/'zone.json').read_text(encoding='utf-8-sig'))
        if int(original['id'])!=plan['zone'] or int(json.loads((source.parent/'zones_index.json').read_text(encoding='utf-8-sig'))[str(plan['zone'])]['region'])!=plan['region']:raise ValueError('Identidad original incompatible')
        for name,sha in plan['inputs'].items():
            f=(source/name).resolve()
            if not f.is_relative_to(source) or digest(f)!=sha:raise ValueError('Datos originales cambiados: '+name)
        for name,sha in plan['outputs'].items():
            f=(p.parent/name).resolve()
            if not f.is_relative_to(p.parent) or digest(f)!=sha:raise ValueError('Mascara modificada: '+name)
    return m

def manage(state,action):
    active=state/'active.json';previous=state/'previous.json'
    if action=='verify':
        pointer=json.loads((state/'latest.json').read_text(encoding='utf-8'));m=validate_pointer(pointer)
        atomic(state/'job.json',{'status':'done','message':f"Verificados {len(m['zones'])} planes y todos sus hashes. ToA excluido."});return
    candidate={'disabled':True}
    if action=='activate':candidate=json.loads((state/'latest.json').read_text(encoding='utf-8'));validate_pointer(candidate)
    if action=='rollback':
        if not previous.exists():raise ValueError('No hay estado anterior para restaurar')
        candidate=json.loads(previous.read_text(encoding='utf-8'))
        if not candidate.get('disabled'):validate_pointer(candidate)
    old=json.loads(active.read_text(encoding='utf-8')) if active.exists() else {'disabled':True}
    atomic(previous,old);atomic(active,candidate)
    with (state/'history.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'time':time.time(),'action':action,'before':old,'after':candidate})+'\n')
    atomic(state/'job.json',{'status':'done','message':{'activate':'Activo solo en el cliente de desarrollo. Reiniciar vista/juego para cargar.', 'disable':'Vegetacion original restaurada en desarrollo. Reiniciar vista/juego.', 'rollback':'Estado anterior restaurado. Reiniciar vista/juego.'}[action]})

def run(args):
    root=Path(args.source).resolve();state=Path(args.state).resolve();state.mkdir(parents=True,exist_ok=True)
    if args.action:
        manage(state,args.action);return
    rows=catalog(root);atomic(state/'catalog.json',{'schema':SCHEMA,'source':str(root),'zones':rows,'exclude_toa':True})
    if args.scan:
        atomic(state/'job.json',{'status':'done','message':f"{sum(z['eligible']for z in rows)} zonas exteriores disponibles. ToA excluido."});return
    options=json.loads(Path(args.options).read_text(encoding='utf-8-sig')) if args.options else {}
    selected=set(map(int,args.zones.split(','))) if args.zones else {z['id']for z in rows if z['eligible']}
    eligible=[z for z in rows if z['eligible'] and z['id']in selected]
    if selected != {z['id'] for z in eligible}:raise ValueError('Seleccion contiene zonas fuera de Hibernia exterior Classic/SI; ToA no permitido')
    if not eligible:raise ValueError('No hay zonas elegibles seleccionadas')
    bundle=state/'bundles'/(time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]);bundle.mkdir(parents=True)
    plans=[]
    for i,z in enumerate(eligible):
        atomic(state/'job.json',{'status':'working','progress':i/len(eligible),'message':f"Preparando {z['name']} ({i+1}/{len(eligible)})"})
        plan=plan_zone(z,options,bundle);plans.append({'id':z['id'],'name':z['name'],'path':f"zone{z['id']:03d}/plan.json",'sha256':digest(bundle/f"zone{z['id']:03d}/plan.json"),'summary':plan['summary']})
    manifest={'schema':SCHEMA,'realm':'hib','regions':[200,181],'exclude_toa':True,'zones':plans,'options':options,'source':str(root),'created':time.time(),'state':'prepared'}
    atomic(bundle/'manifest.json',manifest);atomic(state/'latest.json',{'bundle':str(bundle),'sha256':digest(bundle/'manifest.json')})
    atomic(state/'job.json',{'status':'done','progress':1,'bundle':str(bundle),'message':f"{len(plans)} zonas preparadas. Recursos originales intactos."})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--state',required=True);p.add_argument('--libs');p.add_argument('--scan',action='store_true');p.add_argument('--zones');p.add_argument('--options');p.add_argument('--action',choices=['activate','rollback','disable','verify']);a=p.parse_args()
    try:run(a)
    except Exception as e:
        atomic(Path(a.state)/'job.json',{'status':'error','message':str(e)});raise
