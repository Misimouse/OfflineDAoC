"""Read-only DOL zone/content comparison; never import progress or delete content."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


def audit(reference, database, workspace, output, zone_id):
    reference, database, workspace, output = (p.resolve() for p in (reference,database,workspace,output))
    assert database.is_file() and output.is_relative_to(workspace) and output!=database
    manifest=json.loads((reference/'downloaded_tables.json').read_text(encoding='utf-8-sig'))
    assert manifest['passed'] and manifest['repository']=='Dawn-of-Light/db-public'
    sources={row['name']:row for row in manifest['tables']}
    source_counts={}
    def load(name):
        file=reference/name;expected=sources[name]
        assert file.stat().st_size==expected['bytes']
        digest=hashlib.sha256()
        with file.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        assert digest.hexdigest()==expected['sha256'],name
        with file.open(encoding='utf-8-sig') as stream:rows=json.load(stream)
        assert isinstance(rows,list)
        source_counts[name]=len(rows)
        return rows
    zone=next(row for row in load('Zones.json') if row['ZoneID']==zone_id)
    region=int(zone['RegionID']);xmin=int(zone['OffsetX'])*8192;ymin=int(zone['OffsetY'])*8192
    xmax=xmin+int(zone['Width'])*8192;ymax=ymin+int(zone['Height'])*8192
    mobs={}
    for name in sorted(n for n in sources if n.startswith('Mob.') and n.endswith('.json')):
        rows=load(name)
        for row in rows:
            if int(row['Region'])==region and xmin<=int(row['X'])<xmax and ymin<=int(row['Y'])<ymax:
                ident=str(row['Mob_ID']);assert ident not in mobs,('Duplicate source spawn ID',ident);mobs[ident]=row
        del rows
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True,timeout=3) as db:
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        current={str(row['Mob_ID']):dict(row) for row in db.execute('SELECT * FROM Mob WHERE Region=? AND X>=? AND X<? AND Y>=? AND Y<?',(region,xmin,xmax,ymin,ymax))}
        semantic=lambda row:(str(row['Name']).lower(),int(row['Region']),int(row['X']),int(row['Y']),int(row['Z']))
        by_position={semantic(row):ident for ident,row in current.items()}
        shared=set(mobs)&set(current);differences=Counter();changed=0
        fields=['Name','Guild','ClassType','Model','Size','Level','Heading','X','Y','Z','Flags','Realm','Race','Gender','NPCTemplateID','EquipmentTemplateID','ItemsListTemplateID','PathID','FactionID','AggroLevel','AggroRange','RespawnInterval','RoamingRange']
        for ident in shared:
            changed_here=False
            for key in fields:
                if key in current[ident] and current[ident][key]!=mobs[ident].get(key):differences[key]+=1;changed_here=True
            changed+=int(changed_here)
        candidates=set(mobs)-set(current)
        possible_duplicates=[ident for ident in sorted(candidates) if semantic(mobs[ident]) in by_position]
        installed_counts={}
        for table in ['Mob','NpcTemplate','NPCEquipment','MerchantItem','DataQuest','Path','PathPoints']:
            installed_counts[table]=db.execute('SELECT COUNT(*) FROM "'+table+'"').fetchone()[0]
    templates={int(row['TemplateId']):row for row in load('NpcTemplate.json')}
    template_ids={int(row['NPCTemplateID']) for row in mobs.values() if row.get('NPCTemplateID')}
    missing_templates=sorted(template_ids-templates.keys())
    needed_templates=[templates[ident] for ident in template_ids if ident in templates]
    ids=lambda key:{str(row[key]) for row in list(mobs.values())+needed_templates if row.get(key)}
    equipment_ids=ids('EquipmentTemplateID');merchant_ids=ids('ItemsListTemplateID');path_ids=ids('PathID')
    equipment=load('NPCEquipment.json');merchants=load('MerchantItem.json');paths=load('Path.json');points=load('PathPoints.json')
    quests=load('DataQuest.json')
    result={'passed':True,'read_only':True,'database_written':False,'personal_tables_read':False,'source_repository':manifest['repository'],'source_commit':manifest['commit'],
            'zone':{'id':zone_id,'name':zone['Name'],'region':region,'bounds_daoc_units':[xmin,ymin,xmax,ymax]},
            'source_table_counts':source_counts,'installed_world_counts':installed_counts,
            'comparison':'Raw database fields; template replacement/default semantics require a separate compatibility review, not an automatic gameplay verdict.',
            'spawns':{'dol':len(mobs),'installed':len(current),'shared_ids':len(shared),'shared_ids_with_differences':changed,'differences_by_field':dict(differences),
                      'dol_ids_absent_installed':len(candidates),'same_name_position_under_other_id':len(possible_duplicates),'installed_ids_not_in_reference':len(set(current)-set(mobs)),
                      'source_class_types':dict(Counter(row['ClassType'] for row in mobs.values()))},
            'source_dependencies':{'npc_templates':len(template_ids),'missing_npc_templates':missing_templates,
                'equipment_sets':len(equipment_ids),'equipment_rows':sum(str(row['TemplateID']) in equipment_ids for row in equipment),
                'merchant_lists':len(merchant_ids),'merchant_rows':sum(str(row['ItemListID']) in merchant_ids for row in merchants),
                'paths':len(path_ids),'path_rows':sum(str(row['PathID']) in path_ids for row in paths),'path_points':sum(str(row['PathID']) in path_ids for row in points)},
            'quests':{'dol_dataquest_definitions':len(quests),'dol_starting_in_region':sum(int(row['StartRegionID'])==region for row in quests),
                      'current_quest_system':'preserved','existing_definitions_not_deleted':True,'quest_progress_table_excluded':True,'ui_modernization':'deferred by owner'},
            'policy':'DOL is the reference; differences require a scoped compatibility candidate. No bulk replacement, deletion, movement or activation was performed.'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['reference','database','workspace','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--zone',type=int,default=207)
    args=parser.parse_args();result=audit(args.reference,args.database,args.workspace,args.output,args.zone)
    print(json.dumps({key:result[key] for key in ['passed','zone','spawns','source_dependencies','quests']}))
