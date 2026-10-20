from pathlib import Path
import sys,json,importlib.util,shutil,tempfile,argparse
ap=argparse.ArgumentParser(description='Verify a prepared full Hibernia bundle without changing the live state')
ap.add_argument('--state',required=True);ap.add_argument('--libs');ap.add_argument('--work',required=True);ap.add_argument('--report',required=True)
a=ap.parse_args()
if a.libs:sys.path.insert(0,a.libs)
from PIL import Image
import numpy as np
spec=importlib.util.spec_from_file_location('planner',Path(__file__).with_name('planner.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
state=Path(a.state);pointer=json.loads((state/'latest.json').read_text(encoding='utf-8'));bundle=Path(pointer['bundle']);m=p.validate_pointer(pointer)
real_before=(state/'active.json').read_bytes() if (state/'active.json').exists() else None
checks=[]
def check(name,okay):
    assert okay,name
    checks.append(name)
check('21 exterior zones only',len(m['zones'])==21)
for entry in m['zones']:
    folder=bundle/f"zone{entry['id']:03d}";plan=json.loads((folder/'plan.json').read_text(encoding='utf-8'));source=Path(plan['source']);original=json.loads((source/'zone.json').read_text(encoding='utf-8'))
    hab=np.array(Image.open(folder/'habitat.png'));den=np.array(Image.open(folder/'density.png'));groups=p.image_plane(source/original['clutter']['grassmap'])//10
    mapping=p.ISLES if plan['region']==181 else p.CLASSIC
    check(f"{entry['id']} no vegetation outside eligible original groups",not np.any(den[~np.isin(groups,list(mapping))]))
    check(f"{entry['id']} density agrees with habitat",np.array_equal(den>0,hab>0))
    check(f"{entry['id']} realm and region guard",plan['region'] in [181,200] and plan['realm']=='hib')
work=Path(a.work).resolve();work.mkdir(parents=True,exist_ok=True)
scratch=Path(tempfile.mkdtemp(prefix='replant-test-',dir=work))
p.atomic(scratch/'latest.json',pointer)
for action in ['activate','disable','rollback']:
    p.manage(scratch,action)
check('rollback restores exact previous active pointer',json.loads((scratch/'active.json').read_text(encoding='utf-8'))==pointer)
p.manage(scratch,'disable');p.manage(scratch,'rollback')
# A corrupt pointer must be rejected before altering an active setting.
bad=dict(pointer);bad['sha256']='0'*64
try:p.validate_pointer(bad)
except ValueError:checks.append('corrupted manifest rejected')
else:raise AssertionError('corrupt pointer accepted')
# A forged plan with its outer hashes updated must still fail the source/realm guards.
for kind in ['stale_source','toa']:
    folder=scratch/kind;folder.mkdir(exist_ok=True)
    entry=dict(next(z for z in m['zones'] if z['id']==207));src=bundle/entry['path'];dst=folder/entry['path'];dst.parent.mkdir(parents=True,exist_ok=True)
    for image in ['density.png','habitat.png','overlay.png']:shutil.copy2(src.parent/image,dst.parent/image)
    plan=json.loads(src.read_text(encoding='utf-8'))
    if kind=='stale_source':plan['inputs']['zone.json']='0'*64
    else:plan['region']=73
    p.atomic(dst,plan);entry['sha256']=p.digest(dst);forged=dict(m);forged['zones']=[entry];p.atomic(folder/'manifest.json',forged)
    try:p.validate_pointer({'bundle':str(folder),'sha256':p.digest(folder/'manifest.json')})
    except ValueError:checks.append(kind+' rejected despite recomputed outer hashes')
    else:raise AssertionError(kind+' accepted')
from types import SimpleNamespace
try:p.run(SimpleNamespace(source=m['source'],state=str(scratch/'reject_zone'),action=None,scan=False,options=None,zones='207,999'))
except ValueError:checks.append('mixed selection with forbidden zone rejected before preparation')
else:raise AssertionError('forbidden zone silently ignored')
zone=next(z for z in p.catalog(Path(m['source'])) if z['id']==207)
manual=p.plan_zone(zone,{'exclusions':{'207':[{'x':1190,'z':1180,'radius':40}]}},scratch/'exclusion')
den=np.array(Image.open(scratch/'exclusion/zone207/density.png'));axis=(np.arange(256)+.5)*manual['size_m']/256;xx,zz=np.meshgrid(axis,axis)
check('manual exclusion circle applied',not np.any(den[(xx-1190)**2+(zz-1180)**2<40**2]))
# The live development setting is still absent: management testing took place in a scratch state.
check('real client state unchanged by tests',((state/'active.json').read_bytes() if (state/'active.json').exists() else None)==real_before)
result={'passed':len(checks),'checks':checks,'bundle':pointer,'zones':[{'id':x['id'],'name':x['name']}for x in m['zones']]}
Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8');print('PASS',len(checks),'checks; all 21 plans verified; original assets read-only')
