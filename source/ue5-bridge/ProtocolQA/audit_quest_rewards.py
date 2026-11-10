"""Resolve the original reward-dialog gap without changing runtime or quest data."""
import argparse,json,re
from pathlib import Path
from prepare_combined_expansion_data import digest

def audit(workspace,install):
    repo=Path(__file__).resolve().parents[3];server=repo/'source/server/GameServer';packets=server/'packets/Server';inputs={}
    def read(path):inputs[str(path)]=digest(path);return path.read_text(encoding='utf-8-sig')
    name='PacketLib1127';chain=[]
    while True:
        text=read(packets/(name+'.cs'));chain.append(name)
        if re.search(r'\b(?:override|virtual)\s+void\s+SendQuestWindow\s*\(',text):break
        name=re.search(r'class\s+'+name+r'\s*:\s*(PacketLib\d+)',text)[1]
    assert name=='PacketLib194'
    for token in ['pak.WriteShort(QuestID)','quest.NumOptionalRewardsChoice','quest.OptionalRewards','quest.FinalRewards','WriteItemData(pak, GameInventoryItem.Create(reward))']:
        assert token in text,token
    handler=read(server/'packets/Client/168/QuestRewardChosenHandler.cs')
    assert all(t in handler for t in ['response != 1','countChosen','i < 8','ushort questId','ushort questGiverId','GamePlayerEvent.QuestRewardChosen'])
    codes=read(packets/'IPacketLib.cs');assert re.search(r'QuestRewardChosen\s*=\s*0x40,\s*//\s*0xE8',codes)
    offer_handler=read(server/'packets/Client/168/DialogResponseHandler.cs')
    assert 'case eDialogCode.QuestSubscribe:' in offer_handler and re.search(r'QuestSubscribe\s*=\s*0x64',codes)
    items=read(packets/'PacketLib1124.cs');assert 'override void WriteItemData' in items
    network=read(repo/'source/new-client/godot/game/net/DaocClient.cs')
    start=network.index('case 0x81:');end=network.index('case 0xFB:',start);dialog=network[start:end]
    assert 'r.FixedRaw(storyLen)' in dialog and 'ReadItem' not in dialog
    assert 'public void QuestRewardChosen' not in network
    state=read(repo/'source/ue5-bridge/Godot/interaction_state.gd');assert 'client.call("DialogResponse"' in state
    dataquest=read(server/'quests/QuestsMgr/DataQuest.cs');assert 'ClientQuestID != rewardArgs.QuestID' in dataquest and 'm_optionalRewardChoice.Add(OptionalRewards[rewardArgs.ItemsChosen[reward]])' in dataquest
    assets=[]
    for variant in ['original','x4plus']:
        for filename in ['dialog_bg.png','dialog.png','questbg.png']:
            path=install/'new-client/godot/content/ui/classic'/variant/filename
            assert path.is_file();inputs[str(path)]=digest(path);assets.append(str(path))
    result=dict(passed=True,scope='Source contract audit only; not reward quest gameplay acceptance',server_implementation=name,inheritance=chain,item_format='PacketLib1124.WriteItemData without inventory slot prefix',incoming_dialog=0x81,offer_code=0x22,reward_code=0x21,
        original_offer_response=dict(wire_code=0x82,dialog_code=0x64,body_bytes=10),
        missing_client_fields=['goal list','money reward','experience percentage','fixed reward items','required choice count','optional reward items'],
        missing_original_request=dict(wire_code=0x40,historical_pre_xor_code=0xE8,response=1,count='number selected',indices='eight bytes; unused entries zero',reserved_words=3,quest_id='ushort',quest_giver_id='ushort',body_bytes=20),
        original_assets=assets,source_inputs=inputs,normal_runtime_modified=False,database_modified=False,
        next_package='Strict inactive reward-dialog codec and request builder, then original UI/state and ordinary-server choices before guarded activation',
        modernization_deferred=True)
    out=workspace/'QuestRewardsLab';out.mkdir(exist_ok=True)
    assert all(digest(Path(p))==h for p,h in inputs.items());(out/'contract_verified.json').write_text(json.dumps(result,indent=2));return {k:v for k,v in result.items() if k not in ['source_inputs','original_assets','inheritance']}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['workspace','install']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.workspace.resolve(),a.install.resolve())))
