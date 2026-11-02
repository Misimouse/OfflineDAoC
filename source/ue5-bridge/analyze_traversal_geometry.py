import json,sys
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'DAoC-Enhanced-Unreal/.terrain-python'))
import numpy as np
from PIL import Image,ImageDraw
import colorsys
D=R/'Reports/navigation/traversal';survey=json.loads((D/'survey.json').read_text())
names=['helfshack','hshop','elftavern2','hlurikhut','h_bridge1']
image=Image.new('RGB',(1800,2500),'white');draw=ImageDraw.Draw(image)
summary={}
for row,name in enumerate(names):
    path,entry=next((p,e)for p,e in survey['meshes'].items()if p.rsplit('/',1)[-1]==name+'.'+name)
    mesh=json.loads((D/entry['file']).read_text());v=np.array(mesh['vertices']);tri=np.array(mesh['triangles']);t=v[tri];mids=np.array(mesh['materials'])
    cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=cross/np.maximum(np.linalg.norm(cross,axis=1)[:,None],1e-9)
    floors=np.abs(norm[:,2])>.9
    heights=np.round(t[floors].mean(1)[:,2],1);values,counts=np.unique(heights,return_counts=True)
    summary[name]={'bounds':[v.min(0).tolist(),v.max(0).tolist()], 'horizontal_levels':sorted(zip(values.tolist(),counts.tolist()),key=lambda x:-x[1])[:35]}
    lo=v.min(0)[:2];hi=v.max(0)[:2];scale=430/max(hi-lo)
    def project(point,col):return (col*600+300+(point[0]-(lo[0]+hi[0])/2)*scale,row*500+250-(point[1]-(lo[1]+hi[1])/2)*scale)
    def frame(col,title):
        draw.rectangle((col*600+2,row*500+2,col*600+598,row*500+498),outline='gray');draw.text((col*600+20,row*500+10),title,fill='black')
        for axis in range(2):
            for tick in range(int(lo[axis]/100)-1,int(hi[axis]/100)+2):
                if axis==0:a=project([tick*100,lo[1]],col);b=project([tick*100,hi[1]],col)
                else:a=project([lo[0],tick*100],col);b=project([hi[0],tick*100],col)
                draw.line((a,b),fill='#eeeeee');draw.text(a,str(tick),fill='gray')
    frame(0,name+' horizontal faces (metres)')
    for triangle in t[floors]:
        colour=tuple(int(c*255)for c in colorsys.hsv_to_rgb((float(triangle[:,2].mean())/600)%1,.6,.8))
        draw.polygon([project(p,0)for p in triangle],fill=colour,outline='gray')
    for col,z in enumerate([100,350],1):
        segments=[]
        for triangle in t:
            points=[]
            for a,b in zip(triangle,np.roll(triangle,-1,axis=0)):
                if (a[2]<=z<b[2])or(b[2]<=z<a[2]):points.append((a+(b-a)*(z-a[2])/(b[2]-a[2]))[:2]/100)
            if len(points)==2:segments.append(points)
        frame(col,f'{name} section z={z/100}m')
        for segment in segments:draw.line([project(p*100,col)for p in segment],fill='black',width=2)
image.save(D/'sections.png');(D/'geometry_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
