"""Prepare a scoped DOL data proposal against marked QA data. Never applies it to a database."""
import argparse
import hashlib
import json
import re
import csv,io,importlib.util
from pathlib import Path
import sqlite3

COMMIT='b5b29c2ada7695414b94f5fa110eb505a477d007'
HASHES={'LineXSpell.json':'0d049c9e73907085a52df392d3a41a84eb2ffe14e59e57e4e5b5e6864069aabe',
        'Spell.json':'5f1e64c65f1da9f9b8a200192157ecd7ed642010c862dda270e5b316ae975232'}
LINES={'Spectral Force','Spectral Guard','Ethereal Shriek','Phantasmal Wail'}
CLASS_LINES={39:LINES,58:{'Dementia','Shadow Mastery','Vampiiric Embrace'},62:{'Aura Manipulation','Magnetism','Power Strikes'}}
CLASS_COUNTS={39:(123,130),58:(123,124),62:(123,123)}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--server-source',required=True,type=Path,help='This fork GameServer source, used to audit concrete spell handlers')
    parser.add_argument('--client',type=Path,help='Original client app folder, used to resolve the two known icon/effect ID mismatches')
    parser.add_argument('--class-id',type=int,choices=[39,58,62],default=39,help='Proposal scope only; does not enable the class')
    parser.add_argument('--reserve-proposal',type=Path,action='append',default=[],help='Reserve aliases from other private proposals before allocating a new ID')
    args=parser.parse_args();root=args.workspace.resolve()
    lines=CLASS_LINES[args.class_id]
    prefix='daoc_bridge_bainshee_' if args.class_id==39 else 'daoc_bridge_class_'+str(args.class_id)+'_'
    assert args.output.resolve().is_relative_to(root/'Reports'),'Keep proposals in private reports, outside databases and game content'
    prepared=json.loads((root/'Reports/protocol_qa/prepared.json').read_text())
    run=Path(prepared['root']).resolve();database=Path(prepared['database']).resolve()
    assert run.is_relative_to(root/'ProtocolQA') and database.is_relative_to(run)
    folder=root/'References'/('DOLPublic_'+COMMIT[:12]);source={}
    for name,expected in HASHES.items():
        raw=(folder/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,name
        source[name]=json.loads(raw)
    spells={int(x['SpellID']):x for x in source['Spell.json']}
    links=[x for x in source['LineXSpell.json'] if x['LineName'] in lines]
    ids=sorted({int(x['SpellID']) for x in links});assert (len(ids),len(links))==CLASS_COUNTS[args.class_id]
    report={'source':'https://github.com/Dawn-of-Light/db-public','source_commit':COMMIT,'source_hashes':HASHES,
            'database_modified':False,'proposal_only':True,'class_id':args.class_id,'spells':[],'line_spells':[],'remapped_ids':{},'preserved_rows':{},'missing_effect_definitions':[], 'type_adaptations':[], 'client_effect_adaptations':[], 'reserved_proposals':[], 'source_line_associations':len(links),'duplicate_line_spells':[]}
    reserved=set()
    for path in args.reserve_proposal:
        assert path.resolve().is_relative_to(root/'Reports') and path.resolve()!=args.output.resolve()
        raw=path.read_bytes();other=json.loads(raw)
        assert other['proposal_only'] and other['source_commit']==COMMIT and int(other.get('class_id',39))!=args.class_id
        aliases={int(value['candidate']) for value in other['remapped_ids'].values()}
        assert not reserved.intersection(aliases),'Existing proposals already have colliding aliases'
        reserved.update(aliases);report['reserved_proposals'].append({'class_id':int(other.get('class_id',39)),'sha256':hashlib.sha256(raw).hexdigest(),'aliases':sorted(aliases)})
    effect_map={}
    if args.client and args.class_id==39:
        pipeline=args.server_source.resolve().parents[1]/'new-client/pipeline/daoc_mpk.py';assert pipeline.exists()
        spec=importlib.util.spec_from_file_location('original_client_mpk',pipeline)
        mpk=importlib.util.module_from_spec(spec);spec.loader.exec_module(mpk)
        archive=args.client/'gamedata.mpk';tables=mpk.read_mpk(str(archive))
        rows=list(csv.reader(io.StringIO(tables['spells.csv'].decode('latin1'))))
        report['client_gamedata_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
        for spell_id,old_id,new_id in [(13518,3332,13515),(13519,3334,13516)]:
            original=spells[spell_id]
            assert original['Type']=='ArmorAbsorptionBuff' and original['ClientEffect']==old_id and original['Icon']==old_id
            assert not any(row and row[0].strip()==str(old_id) for row in rows)
            matches=[row for row in rows if len(row)>2 and row[0].strip().isdigit() and row[1]==original['Name'] and row[2].strip()==str(original['Icon'])]
            assert len(matches)==1 and int(matches[0][0])==new_id,'Review the original client version before mapping an effect'
            effect_map[old_id]=new_id
            report['client_effect_adaptations'].append({'source_spell_id':spell_id,'from':old_id,'to':new_id,'name':original['Name'],'icon':original['Icon'],'reason':'Unique original client row matches both spell name and icon; old effect ID is absent'})
    handlers={}
    pattern=re.compile(r'\[SpellHandler\(eSpellType\.(\w+)\)\]\s*(?:public|internal)\s+(?:(abstract|sealed)\s+)?class\s+(\w+)',re.S)
    for path in (args.server_source/'spells').rglob('*.cs'):
        for kind,modifier,name in pattern.findall(path.read_text(encoding='utf-8-sig')):
            handlers.setdefault(kind,[]).append({'class':name,'abstract':modifier=='abstract','source':str(path.relative_to(args.server_source))})
    assert any(x['abstract'] for x in handlers.get('ArmorFactorBuff',[]))
    assert any(not x['abstract'] for x in handlers.get('BaseArmorFactorBuff',[]))
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==run.name
        columns={row['name'] for row in db.execute('PRAGMA table_info(Spell)')}
        occupied={int(x[0]) for x in db.execute('SELECT SpellID FROM Spell')}|set(spells)|reserved
        existing={int(row['SpellID']):dict(row) for row in db.execute('SELECT * FROM Spell WHERE SpellID IN ('+','.join('?' for _ in ids)+')',ids)}
        ignored={'Spell_ID','PackageID','LastTimeRowUpdated','TooltipId'}
        for spell_id in ids:
            original=spells[spell_id];current=existing.get(spell_id)
            row={key:value for key,value in original.items() if key in columns}
            if int(row.get('ClientEffect',0)) in effect_map:row['ClientEffect']=effect_map[int(row['ClientEffect'])]
            if row['Type']=='ArmorFactorBuff':
                # DOL's old AF type is abstract in this fork. Adapt only this original baseline.
                original_lines={x['LineName'] for x in links if int(x['SpellID'])==spell_id}
                assert args.class_id==39 and original_lines=={'Spectral Force'}
                assert db.execute('SELECT IsBaseLine FROM SpellLine WHERE KeyName=?',('Spectral Force',)).fetchone()[0]==1
                row['Type']='BaseArmorFactorBuff'
                report['type_adaptations'].append({'source_spell_id':spell_id,'from':'ArmorFactorBuff','to':row['Type'],'reason':'Spectral Force is a baseline; original type is abstract in this fork'})
            if current:
                report['preserved_rows'][str(spell_id)]={'sha256':digest(current),'name':current['Name']}
                differences={key:{'installed':current[key],'source':value} for key,value in row.items() if key not in ignored and current[key]!=value}
                if not differences:continue
                alias=next(i for i in range(60000,65536) if i not in occupied);occupied.add(alias)
                report['remapped_ids'][str(spell_id)]={'candidate':alias,'differences':differences};row['SpellID']=alias
            row['Spell_ID']=prefix+str(row['SpellID']);report['spells'].append(row)
        unique_links={}
        for link in links:
            identity=(link['LineName'],int(link['SpellID']),int(link['Level']))
            if identity in unique_links:
                first=unique_links[identity]
                assert {k:v for k,v in link.items() if k not in ['LineXSpell_ID','PackageID']}=={k:v for k,v in first.items() if k not in ['LineXSpell_ID','PackageID']},'Do not collapse distinct spell definitions'
                report['duplicate_line_spells'].append({'line':link['LineName'],'spell_id':int(link['SpellID']),'level':int(link['Level']),'source_id':link['LineXSpell_ID'],'retained_source_id':first['LineXSpell_ID']})
                continue
            unique_links[identity]=link
            mapped=report['remapped_ids'].get(str(link['SpellID']),{}).get('candidate',int(link['SpellID']))
            key=prefix+digest([link['LineName'],mapped,link['Level']])[:24]
            assert 1<=int(link['Level'])<=50
            report['line_spells'].append({'LineName':link['LineName'],'SpellID':mapped,'Level':int(link['Level']),'LineXSpell_ID':key,'LastTimeRowUpdated':link['LastTimeRowUpdated']})
        report['expected_existing_line_counts']={name:db.execute('SELECT COUNT(*) FROM LineXSpell WHERE LineName=?',(name,)).fetchone()[0] for name in sorted(lines)}
        assert all(count==0 for count in report['expected_existing_line_counts'].values()),'Review changed baseline before preparing this proposal'
        assert {row[0] for row in db.execute('SELECT KeyName FROM SpellLine WHERE KeyName IN ('+','.join('?' for _ in lines)+')',sorted(lines))}==lines
    catalog=json.loads((root/'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json').read_text())
    effect_ids={str(effect_map.get(int(spells[i]['ClientEffect']),int(spells[i]['ClientEffect']))) for i in ids if int(spells[i]['ClientEffect'])>0};needed=set()
    for effect_id in effect_ids:
        definition=catalog['effects'].get(effect_id)
        if not definition:report['missing_effect_definitions'].append(effect_id);continue
        needed.update(int(x) for x in definition.get('gather',[])+definition.get('cast_fx',[]) if int(x)>0)
        needed.update(int(definition[key]) for key in ['projectile','target','buildup','pulse','resist'] if int(definition.get(key,0))>0)
    report['missing_effect_definitions'].sort();report['referenced_fx_resources']=len(needed)
    report['missing_fx_resources']=sorted(x for x in needed if str(x) not in catalog['fx'])
    report['concrete_handler_source_coverage']={kind:[x for x in handlers.get(kind,[]) if not x['abstract']] for kind in sorted({x['Type'] for x in report['spells']})}
    assert all(report['concrete_handler_source_coverage'].values()),'A candidate type lacks a concrete handler in this fork'
    report['not_certified']=['creation eligibility','runtime handler coverage','Bainshee form changes','combat semantics','visual acceptance','all levels and training']
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'proposal_only':True,'spells':len(report['spells']),'line_spells':len(report['line_spells']),'type_adaptations':len(report['type_adaptations']),'client_effect_adaptations':len(report['client_effect_adaptations']),'handler_types':len(report['concrete_handler_source_coverage']),'remapped_ids':report['remapped_ids'],'missing_effect_definitions':report['missing_effect_definitions'],'missing_fx_resources':report['missing_fx_resources']}))


if __name__=='__main__':main()
