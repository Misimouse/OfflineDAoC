"""Prepare a scoped DOL data proposal against marked QA data. Never applies it to a database."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

COMMIT='b5b29c2ada7695414b94f5fa110eb505a477d007'
HASHES={'LineXSpell.json':'0d049c9e73907085a52df392d3a41a84eb2ffe14e59e57e4e5b5e6864069aabe',
        'Spell.json':'5f1e64c65f1da9f9b8a200192157ecd7ed642010c862dda270e5b316ae975232'}
LINES={'Spectral Force','Spectral Guard','Ethereal Shriek','Phantasmal Wail'}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();root=args.workspace.resolve()
    assert args.output.resolve().is_relative_to(root/'Reports'),'Keep proposals in private reports, outside databases and game content'
    prepared=json.loads((root/'Reports/protocol_qa/prepared.json').read_text())
    run=Path(prepared['root']).resolve();database=Path(prepared['database']).resolve()
    assert run.is_relative_to(root/'ProtocolQA') and database.is_relative_to(run)
    folder=root/'References'/('DOLPublic_'+COMMIT[:12]);source={}
    for name,expected in HASHES.items():
        raw=(folder/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,name
        source[name]=json.loads(raw)
    spells={int(x['SpellID']):x for x in source['Spell.json']}
    links=[x for x in source['LineXSpell.json'] if x['LineName'] in LINES]
    ids=sorted({int(x['SpellID']) for x in links});assert len(ids)==123 and len(links)==130
    report={'source':'https://github.com/Dawn-of-Light/db-public','source_commit':COMMIT,'source_hashes':HASHES,
            'database_modified':False,'proposal_only':True,'spells':[],'line_spells':[],'remapped_ids':{},'preserved_rows':{},'missing_effect_definitions':[]}
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==run.name
        columns={row['name'] for row in db.execute('PRAGMA table_info(Spell)')}
        occupied={int(x[0]) for x in db.execute('SELECT SpellID FROM Spell')}|set(spells)
        existing={int(row['SpellID']):dict(row) for row in db.execute('SELECT * FROM Spell WHERE SpellID IN ('+','.join('?' for _ in ids)+')',ids)}
        ignored={'Spell_ID','PackageID','LastTimeRowUpdated','TooltipId'}
        for spell_id in ids:
            original=spells[spell_id];current=existing.get(spell_id)
            row={key:value for key,value in original.items() if key in columns}
            if current:
                report['preserved_rows'][str(spell_id)]={'sha256':digest(current),'name':current['Name']}
                differences={key:{'installed':current[key],'source':value} for key,value in row.items() if key not in ignored and current[key]!=value}
                if not differences:continue
                alias=next(i for i in range(60000,65536) if i not in occupied);occupied.add(alias)
                report['remapped_ids'][str(spell_id)]={'candidate':alias,'differences':differences};row['SpellID']=alias
            row['Spell_ID']='daoc_bridge_bainshee_'+str(row['SpellID']);report['spells'].append(row)
        for link in links:
            mapped=report['remapped_ids'].get(str(link['SpellID']),{}).get('candidate',int(link['SpellID']))
            key='daoc_bridge_bainshee_'+digest([link['LineName'],mapped,link['Level']])[:24]
            assert 1<=int(link['Level'])<=50
            report['line_spells'].append({'LineName':link['LineName'],'SpellID':mapped,'Level':int(link['Level']),'LineXSpell_ID':key,'LastTimeRowUpdated':link['LastTimeRowUpdated']})
        report['expected_existing_line_counts']={name:db.execute('SELECT COUNT(*) FROM LineXSpell WHERE LineName=?',(name,)).fetchone()[0] for name in sorted(LINES)}
        assert all(count==0 for count in report['expected_existing_line_counts'].values()),'Review changed baseline before preparing this proposal'
        assert {row[0] for row in db.execute('SELECT KeyName FROM SpellLine WHERE KeyName IN (?,?,?,?)',sorted(LINES))}==LINES
    catalog=json.loads((root/'Client/Plugins/DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json').read_text())
    effect_ids={str(int(spells[i]['ClientEffect'])) for i in ids if int(spells[i]['ClientEffect'])>0};needed=set()
    for effect_id in effect_ids:
        definition=catalog['effects'].get(effect_id)
        if not definition:report['missing_effect_definitions'].append(effect_id);continue
        needed.update(int(x) for x in definition.get('gather',[])+definition.get('cast_fx',[]) if int(x)>0)
        needed.update(int(definition[key]) for key in ['projectile','target','buildup','pulse','resist'] if int(definition.get(key,0))>0)
    report['missing_effect_definitions'].sort();report['referenced_fx_resources']=len(needed)
    report['missing_fx_resources']=sorted(x for x in needed if str(x) not in catalog['fx'])
    report['not_certified']=['creation eligibility','runtime handler coverage','Bainshee form changes','combat semantics','visual acceptance','all levels and training']
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'proposal_only':True,'spells':len(report['spells']),'line_spells':len(report['line_spells']),'remapped_ids':report['remapped_ids'],'missing_effect_definitions':report['missing_effect_definitions'],'missing_fx_resources':report['missing_fx_resources']}))


if __name__=='__main__':main()
