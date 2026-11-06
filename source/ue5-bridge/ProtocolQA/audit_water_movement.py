"""Audit original Connacht water and stage gameplay data without changing its visuals."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import struct
import zlib
from prepare_combined_expansion_data import digest

def original_mask(path):
    raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    at=8;compressed=b'';width=height=0
    while at<len(raw):
        length=struct.unpack('>I',raw[at:at+4])[0];kind=raw[at+4:at+8];data=raw[at+8:at+8+length]
        assert zlib.crc32(kind+data)&0xffffffff==struct.unpack('>I',raw[at+8+length:at+12+length])[0]
        if kind==b'IHDR':
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',data)
            assert (width,height)==(256,256) and depth==8 and color==0 and compression==filtering==interlace==0
        elif kind==b'IDAT':compressed+=data
        at+=length+12
        if kind==b'IEND':break
    stream=zlib.decompress(compressed);assert len(stream)==height*(width+1)
    rows=[];previous=[0]*width
    for y in range(height):
        base=y*(width+1);mode=stream[base];row=[];assert mode<=4
        for x,value in enumerate(stream[base+1:base+width+1]):
            a=row[x-1] if x else 0;b=previous[x];c=previous[x-1] if x else 0
            if mode==1:value+=a
            elif mode==2:value+=b
            elif mode==3:value+=(a+b)//2
            elif mode==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);value+=a if pa<=pb and pa<=pc else b if pb<=pc else c
            row.append(value&255)
        rows+=row;previous=row
    return rows


def audit(workspace,install,stage=False):
    repo=Path(__file__).resolve().parents[3];source=repo/'source/new-client/godot/game'
    zone=install/'new-client/godot/content/zones/zone207';info=json.loads((zone/'zone.json').read_text())
    mask=original_mask(zone/info['water_mask'])
    heights=struct.unpack('<66049f',(zone/info['heights']).read_bytes());assert all(math.isfinite(h) for h in heights)
    bodies={int(row['id']):row for row in info['water']};counts=Counter(mask)
    assert set(counts)-{255}==set(bodies)
    prepared=workspace.parent/'DAoC-Enhanced-Unreal/Reports/River_Full_v15/prepared.json'
    river=json.loads(prepared.read_text());assert river['complete'] and river['source_water_cells']==sum(v for k,v in counts.items() if k!=255)
    assert all(abs(float(b['height'])-river['native_water_height_m'])<.001 for b in bodies.values())
    player=(source/'player.gd').read_text(encoding='utf-8-sig')
    def constant(name):return float(re.search(r'^const '+name+r' := ([\d.]+)',player,re.M)[1])
    depth=constant('SWIM_DEPTH');floating=constant('SWIM_FLOAT');points={};deep=shallow=dry_footprint=0
    for cell,body_id in enumerate(mask):
        if body_id==255:continue
        ix=cell%256;iy=cell//256
        bed=sum(heights[(iy+dy)*257+ix+dx] for dx in [0,1] for dy in [0,1])/4
        water=float(bodies[body_id]['height']);kind='swim' if water-bed>depth else 'wade' if water-bed>.1 else 'dry_footprint'
        if kind=='swim':deep+=1
        elif kind=='wade':shallow+=1
        else:dry_footprint+=1
        witness={'position_m':[(ix+.5)*6.4,water-floating if kind=='swim' else bed,(iy+.5)*6.4],'bed_m':bed,'water_m':water,'depth_m':water-bed,'cell':[ix,iy]}
        previous=points.get(kind)
        if previous is None or math.hypot(witness['position_m'][0]-1375.4,witness['position_m'][2]-1250.6)<math.hypot(previous['position_m'][0]-1375.4,previous['position_m'][2]-1250.6):points[kind]=witness
    runs=[]
    for value in mask:
        if runs and runs[-1][0]==value:runs[-1][1]+=1
        else:runs.append([value,1])
    inputs=[zone/'zone.json',zone/info['water_mask'],zone/info['heights'],prepared,source/'player.gd',source/'zone_loader.gd',source/'zone_viewer.gd',
        repo/'source/server/GameServer/packets/Client/168/PlayerPositionUpdateHandler.cs',workspace/'environment_catalog.json']
    models=json.loads((workspace/'models.json').read_text());steps=json.loads((workspace/'FootstepAudioLab/OriginalFootstepAudio_v01/sounds.json').read_text())
    playable=list(steps['local_player_models']);missing=[mid for mid in playable if not models.get(mid,{}).get('swim')]
    report={'passed':deep>0 and shallow>0 and not missing,'zone':207,'water_cells':sum(counts[k] for k in bodies),'deep_cells':deep,'shallow_cells':shallow,'dry_footprint_cells':dry_footprint,
        'bodies':list(bodies.values()),'witnesses':points,'playable_swim_models':len(playable)-len(missing),'missing_swim_models':missing,
        'original_rules':{'swim_depth_m':depth,'feet_below_surface_m':floating,'swim_speed_fraction':.65,'wading_threshold_m':.1,'surface_swimming_only':True,'state_flag':4,'on_ground_while_swimming':False},
        'native_gaps':['No gameplay water field loaded','Native movement uses walking/falling only','Local animation chooses only run/walk/idle','Gateway sends zero swimming state and unconditional onGround=true','Ground-only step sound dispatch has no wet/surface strokes'],
        'approved_river_height_matches':True,'visuals_modified':False,'production_modified':False,'input_hashes':{str(p):digest(p) for p in inputs}}
    out=workspace/'Reports/water_movement';out.mkdir(parents=True,exist_ok=True);(out/'coverage.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if stage:
        assert report['passed'],report
        root=workspace/'WaterMovementLab';assert not (root/'installed.json').exists();root.mkdir(exist_ok=True)
        catalog={'version':1,'zone':207,'size_m':float(info['size_m']),'width':256,'height':256,'dry_id':255,'mask_runs':runs,
            'bodies':{str(k):{'height_m':float(row['height'])} for k,row in bodies.items()},'rules':report['original_rules']}
        path=root/'water_field.json';path.write_text(json.dumps(catalog,separators=(',',':')),encoding='utf-8')
        (root/'resources.json').write_text(json.dumps({'passed':True,'private_staging_only':True,'catalog':str(path),'catalog_sha256':digest(path),'input_hashes':report['input_hashes'],'coverage_sha256':digest(out/'coverage.json')},indent=2),encoding='utf-8')
    return {key:report[key] for key in ['passed','water_cells','deep_cells','shallow_cells','dry_footprint_cells','playable_swim_models','missing_swim_models','approved_river_height_matches','production_modified']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['workspace','install']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--stage',action='store_true');args=parser.parse_args();print(json.dumps(audit(args.workspace.resolve(),args.install.resolve(),args.stage)))
