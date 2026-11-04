"""Apply a scoped expansion proposal to an explicitly marked disposable database."""
import hashlib,json

def install(db,proposal_path,run_id,class_id=39):
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==run_id
    proposal=json.loads(proposal_path.read_text())
    assert proposal['proposal_only'] and proposal['source_commit']=='b5b29c2ada7695414b94f5fa110eb505a477d007'
    assert int(proposal.get('class_id',39))==class_id
    assert class_id in [39,58,62]
    assert len(proposal['spells'])==123 and len(proposal['line_spells'])=={39:130,58:123,62:123}[class_id]
    assert len(proposal.get('duplicate_line_spells',[]))=={39:0,58:1,62:0}[class_id]
    assert len(proposal.get('type_adaptations',[]))=={39:10,58:0,62:0}[class_id] and len(proposal.get('concrete_handler_source_coverage',{}))=={39:15,58:20,62:21}[class_id]
    reserved={int(alias) for row in proposal.get('reserved_proposals',[]) for alias in row['aliases']}
    assert not reserved.intersection(int(row['SpellID']) for row in proposal['spells'])
    for spell_id,expected in proposal['preserved_rows'].items():
        current=dict(db.execute('SELECT * FROM Spell WHERE SpellID=?',(int(spell_id),)).fetchone())
        assert hashlib.sha256(json.dumps(current,sort_keys=True,separators=(',',':')).encode()).hexdigest()==expected['sha256']
    for name,count in proposal['expected_existing_line_counts'].items():
        assert count==0 and db.execute('SELECT COUNT(*) FROM LineXSpell WHERE LineName=?',(name,)).fetchone()[0]==0
    for table,key in [('Spell','spells'),('LineXSpell','line_spells')]:
        columns={row['name'] for row in db.execute('PRAGMA table_info("'+table+'")')}
        for row in proposal[key]:
            assert set(row)<=columns
            if table=='Spell':assert not db.execute('SELECT 1 FROM Spell WHERE SpellID=? OR Spell_ID=?',(row['SpellID'],row['Spell_ID'])).fetchone()
            keys=list(row)
            db.execute('INSERT INTO "'+table+'" ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for _ in keys)+')',[row[k] for k in keys])
    return {'source_commit':proposal['source_commit'],'class_id':class_id,'new_spells':len(proposal['spells']),'line_spells':len(proposal['line_spells']),'preserved_existing_spell_ids':list(proposal['preserved_rows']),'remapped_ids':proposal['remapped_ids'],'type_adaptations':proposal['type_adaptations'],'client_effect_adaptations':proposal.get('client_effect_adaptations',[]),'not_creation_enablement':True}
