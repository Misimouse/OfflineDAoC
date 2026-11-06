"""Read-only live Riding contract and stable path bounds; never copy private DB content to Git."""
import argparse,json,sqlite3
from pathlib import Path
from contextlib import closing
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    repo=Path(__file__).resolve().parents[3];game=install/'new-client/godot';server=repo/'source/server/GameServer'
    paths=[game/'game/net/DaocClient.cs',game/'game/net/server_world.gd',game/'game/zone_viewer.gd',
        game/'content/zones/zones_index.json',game/'content/world/routes.json',
        server/'gameobjects/CustomNPC/GameStableMaster.cs',server/'packets/Client/168/PlayerDismountRequestHandler.cs',
        repo/'source/ue5-bridge/Godot/live_gateway.gd']
    hashes={str(p):digest(p) for p in paths};texts=[p.read_text(encoding='utf-8-sig') for p in paths]
    assert 'case 0xC8:' in texts[0] and 'd["rider"] = r.Short()' in texts[0] and 'public void Dismount()' in texts[0]
    assert 'func _riding(' in texts[1] and 'func seat_of(' in texts[1] and 'func _server_mount(' in texts[2]
    zone=json.loads(texts[3])['207'];assert zone['region']==200 and zone['x']==35 and zone['y']==51
    lo=(zone['x']*8192,zone['y']*8192);hi=((zone['x']+zone['w'])*8192,(zone['y']+zone['h'])*8192)
    contains=lambda x,y:lo[0]<=x<hi[0] and lo[1]<=y<hi[1]
    db=install/'runtime/data/opendaoc.sqlite3.db';rows=[]
    with closing(sqlite3.connect('file:'+db.as_posix()+'?mode=ro',uri=True)) as con:
        con.execute('PRAGMA query_only=ON');assert con.execute('PRAGMA query_only').fetchone()[0]==1
        con.row_factory=sqlite3.Row
        stables=con.execute("SELECT Name,ItemsListTemplateID,X,Y,Z,Model FROM Mob WHERE Region=? AND ClassType LIKE '%Stable%' AND X>=? AND X<? AND Y>=? AND Y<?",(zone['region'],lo[0],hi[0],lo[1],hi[1])).fetchall()
        for stable in stables:
            for item in con.execute('SELECT ItemTemplateID,PageNumber,SlotPosition FROM MerchantItem WHERE ItemListID=?',(stable['ItemsListTemplateID'],)):
                points=con.execute('SELECT Step,X,Y,Z,MaxSpeed,WaitTime FROM PathPoints WHERE PathID=? ORDER BY Step',(item[0],)).fetchall()
                if not points:continue
                mask=[contains(p['X'],p['Y']) for p in points]
                definition=con.execute('SELECT Color,Name,Model,Price,Object_Type FROM ItemTemplate WHERE Id_nb=?',(item[0],)).fetchone()
                template=con.execute('SELECT Model FROM NpcTemplate WHERE TemplateId=?',(definition[0],)).fetchone() if definition else None
                rows.append(dict(stable=stable['Name'],stable_position_m=[(stable['X']-lo[0])*.025,stable['Z']*.025,(stable['Y']-lo[1])*.025],stable_model=stable['Model'],page=item['PageNumber'],index=item['SlotPosition'],name=definition['Name'],model=definition['Model'],price=definition['Price'],object_type=definition['Object_Type'],ticket=item[0],steed_template_id=definition[0] if definition else None,steed_model=template[0] if template else None,point_count=len(points),inside_points=sum(mask),fully_inside_zone207=all(mask),first_outside_step=next((p['Step'] for p,ok in zip(points,mask) if not ok),None),starts_near_stable=abs(points[0]['X']-stable['X'])<500 and abs(points[0]['Y']-stable['Y'])<500))
    assert rows and all(r['starts_near_stable'] for r in rows)
    result=dict(passed=True,scope='Read-only public stable/path contract, not live riding implementation',zone=207,region=200,
        server_packet='Riding 0xC8: rider u16, steed u16, mount u8, slot u8',client_request='Dismount 0xC8 with zero u16 payload',
        authority='Server owns ticket consumption, mount identity/size, 400ms mount delay, 4s start delay, path and speed',
        offline_routes_region_values=sorted(set(v.get('region') for v in json.loads(texts[4])['routes'].values())),
        offline_catalog_warning='All offline catalog region fields are zero; do not use them as live server region IDs',
        saddle='Original live ServerWorld uses per-steed saddle offset, scaled for that instance, fallback 1.3m; player yaw + PI',
        paths=rows,fully_supported_candidate_paths=[r['ticket'] for r in rows if r['fully_inside_zone207']],
        map_limits='Point bounds alone do not certify segment collision, terrain, saddle, animation, or end-to-end travel',
        input_hashes=hashes,database_open_mode='ro + query_only',database_modified=False,normal_installation_modified=False)
    assert all(digest(Path(p))==sha for p,sha in hashes.items())
    root=workspace/'LiveRidingLab';root.mkdir(exist_ok=True);(root/'reference_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return dict(passed=True,paths=len(rows),fully_inside_zone207=len(result['fully_supported_candidate_paths']),report=str(root/'reference_audit.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['workspace','install']:p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
