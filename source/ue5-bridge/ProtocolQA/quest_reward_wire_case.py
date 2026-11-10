"""Synthetic disposable reward quest exercising original DOL rules and packets."""
import json,os
from pathlib import Path
from prepare_combined_expansion_data import digest
QUEST=31001

def prepare(db,leader,world,result):
    assert {r[0] for r in db.execute("SELECT Id_nb FROM ItemTemplate WHERE Id_nb IN ('club','cloak','minor_lethal_poison')")}=={'club','cloak','minor_lethal_poison'}
    quest=dict(world['quest']);quest.update(ID=QUEST,Name='Codex Reward Protocol',StartType=200,StartName='Codex Reward Keeper',StartRegionID=200,
        AcceptText='',Description='Choose a reward after speaking again.',SourceText='Original protocol reward story',StepType='5',StepText='Speak to the keeper.',StepItemTemplates='',AdvanceText='',TargetName='Codex Reward Keeper;200',TargetText='',CollectItemTemplate='',MaxCount=1,MinLevel=1,MaxLevel=50,RewardMoney='321',RewardXP='123',RewardCLXP='',RewardRP='',RewardBP='',OptionalRewardItemTemplates='1club|cloak',FinalRewardItemTemplates='minor_lethal_poison',FinishText='Choose one item.',QuestDependency='',AllowedClasses='',ClassType='')
    npc=dict(world['npc']);npc.update(Mob_ID='codex-private-reward-keeper',Name='Codex Reward Keeper',ClassType='DOL.GS.GameNPC',NPCTemplateID=0,ItemsListTemplateID='',EquipmentTemplateID='',Guild='Private reward test',X=leader['Xpos']+40,Y=leader['Ypos'],Z=leader['Zpos'],Speed=0,PathID='')
    for table,row in [('DataQuest',quest),('Mob',npc)]:
        keys=list(row);db.execute('INSERT OR REPLACE INTO '+table+' ('+','.join('"'+k+'"' for k in keys)+') VALUES ('+','.join('?' for k in keys)+')',[row[k] for k in keys])
    db.execute('DELETE FROM CharacterXDataQuest WHERE DataQuestID=?',(QUEST,))
    result['source_inputs'][str(Path(__file__).resolve())]=digest(Path(__file__).resolve())
    proof=Path(os.environ['DAOC_QUEST_REWARD_BACKEND_PROOF']);result['source_inputs'][str(proof)]=digest(proof)
    result['synthetic_protocol_fixture']=True;result['original_world_quest_imported']=False

def run(a,b,wait,settle,result,checked,output,world,leader):
    def inv(peer=a):return peer.snapshot.get('inventory',{})
    def journal(peer=a):return peer.snapshot.get('classic_ui',{}).get('journal',{}).get('entries',[])
    def dialog():return a.snapshot.get('qa_quest_dialog',{})
    def count(name,peer=a):return sum(i.get('count',1) for i in inv(peer).get('items',[]) if i.get('name','').lower()==name)
    def money(peer=a):return sum(inv(peer).get('money',{}).get(k,0)*v for k,v in [('copper',1),('silver',100),('gold',10000),('platinum',10000000),('mithril',10000000000)])
    def request(peer,mode,window,**extra):
        before=peer.snapshot.get('qa_quest_request',{}).get('serial',0)
        peer.send('chat',text='/qa-quest-reward '+json.dumps(dict(mode=mode,quest_id=window['quest_id'],giver_id=window['giver_id'],required_choices=window.get('required_choices',0),option_count=len(window.get('optional_items',[])),**extra)))
        wait(lambda:peer.snapshot.get('qa_quest_request',{}).get('serial',0)>before,'Candidate request encoder result')
        return peer.snapshot['qa_quest_request']['encoded']
    wait(lambda:all(inv(p).get('ready') for p in [a,b]) and any(r.get('name')=='Codex Reward Keeper' for r in a.snapshot['entities']),'Private reward fixture ready')
    npc=next(r for r in a.snapshot['entities'] if r.get('name')=='Codex Reward Keeper')
    baseline_money=money();baseline_other=money(b);other_cloak=count('cloak',b);cloak=count('cloak');club=count('club');poison=count('minor lethal poison')
    a.send('interact',entity_id=npc['id']);wait(lambda:dialog().get('code')==0x22,'Original reward offer decoded')
    offer=dict(dialog());result['checks']['actual_original_offer_identity']=offer['quest_id']==QUEST+32767 and offer['giver_id']==int(npc['id'].split(':')[1])
    result['checks']['actual_modern_reward_item_records']=len(offer['fixed_items'])==1 and len(offer['optional_items'])==2 and offer['required_choices']==1 and offer['money']==321
    assert request(a,'offer',offer,accept=False)
    settle(.4);result['checks']['decline_does_not_grant_quest_or_reward']=not journal() and money()==baseline_money
    before=dialog()['revision'];settle(1)
    a.send('interact',entity_id=npc['id']);wait(lambda:dialog().get('revision',0)>before and dialog().get('code')==0x22,'Original offer reopened')
    offer=dict(dialog());assert request(a,'offer',offer,accept=True)
    wait(lambda:any('Codex Reward Protocol' in q['name'] for q in journal()),'Original QuestSubscribe acceptance')
    result['checks']['original_offer_acceptance_creates_journal']=True
    before=dialog()['revision'];settle(1)
    a.send('interact',entity_id=npc['id']);wait(lambda:dialog().get('revision',0)>before and dialog().get('code')==0x21,'Original reward choice window')
    reward=dict(dialog());result['checks']['original_reward_window_separate_from_offer']=reward['goals']==offer['goals'] and reward['story']=='Choose one item.'
    assert not request(a,'reward',reward,choices=[-1])
    settle(.3);result['checks']['invalid_choice_not_encoded_or_granted']=money()==baseline_money and bool(journal())
    assert request(b,'reward',reward,choices=[1]);settle(.5)
    result['checks']['other_account_cannot_claim_reward']=money(b)==baseline_other and count('cloak',b)==other_cloak
    assert request(a,'reward',reward,choices=[1])
    wait(lambda:not any('Codex Reward Protocol' in q['name'] for q in journal()) and money()==baseline_money+321 and count('cloak')==cloak+1 and count('minor lethal poison')>poison,'Original server grants selected/fixed rewards and money')
    result['checks']['selected_item_and_exact_money_awarded']=True
    result['checks']['unchosen_option_not_awarded']=count('club')==club
    fixed_count=count('minor lethal poison');result['checks']['fixed_reward_quantity_matches_original_packet']=fixed_count==poison+int(reward['fixed_items'][0]['value1'])
    assert request(a,'reward',reward,choices=[1]);settle(.5)
    result['checks']['repeat_reward_cannot_duplicate']=money()==baseline_money+321 and count('cloak')==cloak+1 and count('minor lethal poison')==fixed_count
    for peer in [a,b]:
        peer.send('chat',text='/quit');wait(lambda:not peer.snapshot.get('in_game',True) and peer.snapshot.get('character_lobby',{}).get('ready'),'Original reward saved logout',90)
    with checked() as db:
        row=db.execute('SELECT Step,Count FROM CharacterXDataQuest WHERE Character_ID=? AND DataQuestID=?',(leader['DOLCharacters_ID'],QUEST)).fetchone()
        result['checks']['original_reward_completion_saved']=row is not None and row['Step']<=0 and row['Count']==1
        saved={r['ITemplate_Id']:r['Count'] for r in db.execute("SELECT ITemplate_Id, SUM(Count) AS Count FROM Inventory WHERE OwnerID=? AND ITemplate_Id IN ('cloak','minor_lethal_poison') GROUP BY ITemplate_Id",(leader['DOLCharacters_ID'],))}
        result['checks']['selected_and_fixed_items_saved']=saved.get('cloak')==cloak+1 and saved.get('minor_lethal_poison')==fixed_count
    (output/'reward_outcome.json').write_text(json.dumps(dict(checks=result['checks'],synthetic_fixture=True,offer=offer,reward=reward),indent=2))
