"""Original Evan's Notes delivery; NPC proximity is private test staging only."""
import json,os
from pathlib import Path
from prepare_combined_expansion_data import digest

def prepare(db,leader,world,result,reference):
    original=json.loads(reference.read_text());assert original['source_read_only']
    row=dict(original['npc']);assert row['Name']=='Meara' and row['Region']==200
    row.update(Mob_ID='codex-private-quest-meara',X=leader['Xpos']+40,Y=leader['Ypos']+40,Z=leader['Zpos'],Speed=0,PathID='')
    keys=list(row)
    db.execute('INSERT OR REPLACE INTO Mob ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for k in keys)+')',[row[k] for k in keys])
    result['source_inputs'][str(reference)]=digest(reference)
    result['source_inputs'][str(Path(__file__).resolve())]=digest(Path(__file__).resolve())
    config=Path(os.environ['DAOC_QUEST_ORIGINAL_CONFIG'])
    result['source_inputs'][str(config)]=digest(config)
    result['private_npc_proximity_staging']=True
    result['original_world_travel_verified']=False

def run(a,b,wait,settle,result,checked,output,world,leader):
    def inventory():return a.snapshot.get('inventory',{})
    def letters():return [i for i in inventory().get('items',[]) if i.get('name') in [r['Name'] for r in world['items']]]
    def journal():return a.snapshot.get('classic_ui',{}).get('journal',{}).get('entries',[])
    def money():return sum(inventory().get('money',{}).get(k,0)*v for k,v in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
    def npc(name):return next(r for r in a.snapshot['entities'] if r.get('kind')=='npc' and r.get('name')==name)
    def deliver(item,target):
        a.send('inventory_give',slot=item['slot'],item_token=item['token'],inventory_revision=inventory()['state_revision'],entity_id=target['id'],target_name=target['name'],target_model=target['model_id'])
    wait(lambda:inventory().get('ready') and all(any(r.get('kind')=='npc' and r.get('name')==n for r in a.snapshot['entities']) for n in ['Evan','Meara']),'Original quest actors and inventory')
    before_money=money()
    with checked() as db:before_xp=db.execute('SELECT Experience FROM DOLCharacters WHERE DOLCharacters_ID=?',(leader['DOLCharacters_ID'],)).fetchone()[0]
    a.send('interact',entity_id=npc('Evan')['id']);settle(.4)
    a.send('chat',text='/whisper '+world['quest']['AcceptText'])
    wait(lambda:any(world['quest']['Name'] in q['name'] for q in journal()) and len(letters())==1,'Server grants original quest and first letter')
    first=dict(letters()[0]);result['checks']['original_accept_grants_one_letter']=first['count']==1
    deliver(first,npc('Meara'))
    wait(lambda:any(world['quest']['StepText'].split('|')[1] in q['text'] for q in journal()) and len(letters())==1 and letters()[0]['token']!=first['token'],'Original delivery advances quest and replaces letter')
    result['checks']['delivery_advances_original_journal']=True
    result['checks']['first_letter_consumed_without_duplicate']=letters()[0]['count']==1 and letters()[0]['name']!=first['name']
    second=dict(letters()[0]);settle(.4)
    deliver(first,npc('Meara'));settle(.4)
    result['checks']['stale_letter_handover_refused']=len(letters())==1 and letters()[0]['token']==second['token']
    deliver(second,npc('Evan'))
    wait(lambda:not any(world['quest']['Name'] in q['name'] for q in journal()) and not letters(),'Original quest finishes and consumes return letter')
    expected=sum(int(v) for v in world['quest']['RewardMoney'].split('|') if v)
    wait(lambda:money()==before_money+expected,'Original quest money reward')
    result['checks']['original_completion_and_exact_money_reward']=True
    after_money=money();deliver(second,npc('Evan'));settle(.5)
    result['checks']['stale_finish_cannot_duplicate_reward']=not letters() and money()==after_money
    for p in [a,b]:
        p.send('chat',text='/quit');wait(lambda:not p.snapshot.get('in_game',True) and p.snapshot.get('character_lobby',{}).get('ready'),'Original quest saved logout',90)
    with checked() as db:
        quest=db.execute('SELECT Step,Count FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=20070',(leader['DOLCharacters_ID'],)).fetchone()
        xp=db.execute('SELECT Experience FROM DOLCharacters WHERE DOLCharacters_ID=?',(leader['DOLCharacters_ID'],)).fetchone()[0]
        remaining=db.execute("SELECT COUNT(*) FROM Inventory WHERE OwnerID=? AND ITemplate_Id IN ('cq_letter_to_meara','cq_letter_to_evan')",(leader['DOLCharacters_ID'],)).fetchone()[0]
        result['checks']['original_saved_completion_count']=quest is not None and quest['Count']==1 and quest['Step']<=0
        result['checks']['original_reward_experience_saved']=xp>before_xp
        result['checks']['no_quest_letter_left_after_saved_completion']=remaining==0
    (output/'quest_outcome.json').write_text(json.dumps(dict(checks=result['checks'],money_reward=expected,experience_before=before_xp,experience_after=xp,private_npc_staging=True,world_travel_verified=False),indent=2))
