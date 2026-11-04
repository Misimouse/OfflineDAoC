"""Apply only the verified Bainshee proposal to an explicitly marked disposable database."""
import hashlib,json

def install(db,proposal_path,run_id):
    assert db.execute('SELECT RunId FROM CodexQaIsolationMarker').fetchone()[0]==run_id
    proposal=json.loads(proposal_path.read_text())
    assert proposal['proposal_only'] and proposal['source_commit']=='b5b29c2ada7695414b94f5fa110eb505a477d007'
    assert len(proposal['spells'])==123 and len(proposal['line_spells'])==130
    assert len(proposal.get('type_adaptations',[]))==10 and len(proposal.get('concrete_handler_source_coverage',{}))==15
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
    return {'source_commit':proposal['source_commit'],'new_spells':123,'line_spells':130,'preserved_existing_spell_ids':list(proposal['preserved_rows']),'remapped_ids':proposal['remapped_ids'],'type_adaptations':proposal['type_adaptations'],'client_effect_adaptations':proposal.get('client_effect_adaptations',[]),'not_creation_enablement':True}
