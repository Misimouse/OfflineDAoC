"""Acceptance routes anchored to measured mesh features, not empty test boxes."""
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'DAoC-Enhanced-Unreal/.terrain-python'));sys.path.insert(0,str(R.parent/'DAoC-Enhanced-Unreal/Tools'))
import numpy as np
from scipy.spatial.transform import Rotation
from connacht_surface_data import height
D=R/'Reports/navigation/traversal';survey=json.loads((D/'survey.json').read_text());routes=[]
def component(name):return next(c for c in survey['components']if c['actor']==name)
def world(c,point):return Rotation.from_quat(c['rotation']).apply(np.array(point)*c['scale'])+c['position']
def ground(c,x,y):
    p=world(c,[x,y,0]);return (height(p[0]/100+1364,p[1]/100+1263)-130)*100-c['position'][2]
def route(ident,c,points,blocked=False,kind='door',timeout=14):
    points=[world(c,p).tolist()for p in points];routes.append(dict(id=ident,kind=kind,actor=c['actor'],start=points[0],points=points[1:],expect_blocked=blocked,timeout_s=timeout))

c=component('helfshack')
p=[[-260,-1100,ground(c,-260,-1100)],[-260,-780,52],[-260,-620,128],[-260,-400,119.1],[-260,-150,119.1]]
route('shack_enter',c,p);route('shack_exit',c,list(reversed(p)))
route('shack_back_wall',c,[[300,800,ground(c,300,800)],[300,100,119.1]],True,'wall',5)
c=component('elftavern2')
p=[[-1550,0,ground(c,-1550,0)],[-1400,0,ground(c,-1400,0)],[-1150,0,42],[-850,0,42]]
route('tavern_enter',c,p);route('tavern_exit',c,list(reversed(p)))
route('tavern_wall',c,[[-1500,400,ground(c,-1500,400)],[-800,400,42]],True,'wall',5)
mesh=json.loads((D/survey['meshes'][c['mesh']]['file']).read_text());t=np.array(mesh['vertices'])[mesh['triangles']]
stairs=[t[i].mean(0).tolist()for i in [3934,3930,3964,3926,3922]]
stairs += [[320,-60,282],[440,-80,281.8],[460,-240,281.8]]
stairs += [t[i].mean(0).tolist()for i in [3952,3948,3944,3940,3968,4060]]
p=[[-150,-285,42]]+stairs+[[70,-450,522.1]]
route('tavern_stairs_up',c,p,False,'stairs',32);route('tavern_stairs_down',c,list(reversed(p)),False,'stairs',32)
for label in ['hlurikhut','hlurikhut_98725908be2b5863ea82b71fafbc4c6f','hlurikhut_f95c8e35b2952829ad56c62b47d3c432']:
    c=component(label);p=[[-50,-650,ground(c,-50,-650)],[-50,-400,ground(c,-50,-400)],[-50,-250,20],[-50,-20,25]]
    route(label+'_enter',c,p);route(label+'_exit',c,list(reversed(p)))
c=component('hshop');centre=np.array([-263.85,-109.27]);direction=np.array([np.cos(np.deg2rad(105)),np.sin(np.deg2rad(105))])
def shop_point(radius,z=None):
    x,y=centre+direction*radius;return [x,y,ground(c,x,y)if z is None else z]
# The measured gap is centred on 105 degrees. A radial line at 270
# crosses a solid fabric panel, not the entrance.
p=[shop_point(900),shop_point(650),shop_point(300,58.2)]
route('shop_enter',c,p);route('shop_exit',c,list(reversed(p)))
route('shop_wall',c,[[0,-650,ground(c,0,-650)],[0,-200,58.2]],True,'wall',5)
c=component('h_bridge1');mesh=json.loads((D/survey['meshes'][c['mesh']]['file']).read_text());t=np.array(mesh['vertices'])[mesh['triangles']]
def deck(x,y):
    a=t[:,0,:2];b=t[:,1,:2]-a;v=t[:,2,:2]-a;q=np.array([x,y])-a;det=b[:,0]*v[:,1]-b[:,1]*v[:,0];safe=np.where(abs(det)>1e-5,det,1)
    u=(q[:,0]*v[:,1]-q[:,1]*v[:,0])/safe;w=(b[:,0]*q[:,1]-b[:,1]*q[:,0])/safe
    z=t[:,0,2]+u*(t[:,1,2]-t[:,0,2])+w*(t[:,2,2]-t[:,0,2]);mask=(abs(det)>1e-5)&(u>=-1e-5)&(w>=-1e-5)&(u+w<=1.00001)&(z<500)&(z>-200)
    return max(float(z[mask].max()),ground(c,x,y)) if mask.any()else ground(c,x,y)
p=[[-4400,170,ground(c,-4400,170)]]+[[x,170,deck(x,170)]for x in range(-3400,3401,200)]+[[4400,170,ground(c,4400,170)]]
route('bridge_west_east',c,p,False,'bridge',50);route('bridge_east_west',c,list(reversed(p)),False,'bridge',50)
route('bridge_parapet',c,[[0,-200,deck(0,-200)],[0,-1100,deck(0,-200)]],True,'wall',6)
c={'actor':'Connacht_Geography_Terrain','position':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}
route('running_speed_reference',c,[[-6400,-2000,ground(c,-6400,-2000)],[-6400,800,ground(c,-6400,800)]],False,'speed',12)
document=dict(schema=1,coordinate_system='UE centimetres',map='/Game/DAoC/Connacht_v01/Ardee_Nwiro_Prueba',doors_open=True,routes=routes)
(D/'routes.json').write_text(json.dumps(document,indent=2));print('routes',len(routes))
closed=[r|{'expect_blocked':True,'timeout_s':6}for r in routes if r['id'] in ['shack_enter','shack_exit','tavern_enter','tavern_exit'] or r['kind']=='wall']
(D/'closed_routes.json').write_text(json.dumps(document|{'doors_open':False,'routes':closed},indent=2))
c=component('elftavern2');p=world(c,[-1260,0,42]).tolist()
occupancy={'id':'door_occupancy_protection','actor':c['actor'],'kind':'door_safety','start':p,'points':[p],
           'timeout_s':7,'minimum_s':4,'require_door_hold':True}
(D/'occupied_routes.json').write_text(json.dumps(document|{'doors_open':True,'close_doors_at_s':1.5,'expect_doors_closed':True,'routes':[occupancy]},indent=2))
p=world(c,[-1050,0,42]).tolist()
swing=occupancy|{'id':'door_swing_protection','start':p,'points':[p]}
(D/'swing_routes.json').write_text(json.dumps(document|{'doors_open':True,'close_doors_at_s':1.5,'expect_doors_closed':True,'routes':[swing]},indent=2))
