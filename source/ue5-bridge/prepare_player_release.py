from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
R=Path(str(ROOT))
s='''extends RefCounted
## Request the original server release; never heal, relocate or simulate revival.
var pending:=false
var until_ms:=0
var revision:=0
var feedback:=""
var requests:=0
var rejected:=0
func reset()->void:
    pending=false;until_ms=0;feedback="";revision+=1
func request(value:Dictionary,state:RefCounted,client:Node,now:int)->bool:
    var epoch=value.get("player_generation",-1)
    if not (epoch is int or epoch is float) or not is_finite(float(epoch)) or float(epoch)!=float(state.generation):return fail("El estado del personaje ha cambiado.")
    if not state.ready or int(state.vitals.get("health_pct",100))!=0:return fail("Solo puedes regresar después de morir.")
    if pending:return false
    client.call("Command","&release")
    pending=true;until_ms=now+8000;requests+=1;feedback="Regreso solicitado. Esperando al servidor…";revision+=1;return true
func fail(text:String)->bool:
    feedback=text;rejected+=1;revision+=1;return false
func consume(kind:String,data:Dictionary,me:int)->void:
    if kind in ["you","region_changed","quit"]:reset();return
    if pending and kind=="status":
        var hp=data.get("health_pct",-1)
        if (hp is int or hp is float) and is_finite(float(hp)) and float(hp)>0 and float(hp)<=100 and float(hp)==floor(float(hp)):reset()
func advance(now:int)->void:
    if pending and now>=until_ms:
        pending=false;until_ms=0;feedback="El servidor aún no ha confirmado el regreso. Puedes volver a solicitarlo.";revision+=1
func snapshot()->Dictionary:return {"pending":pending,"feedback":feedback,"requests":requests}
'''
(R/'Godot/player_release.gd').write_text(s,encoding='utf-8')
p=R/'Godot/live_gateway.gd';s=p.read_text(encoding='utf-8');s=s.replace('var gm_mode:RefCounted','var gm_mode:RefCounted\nvar release_state:RefCounted');s=s.replace('gm_mode=load(folder.path_join("gm_test_mode.gd")).new()','gm_mode=load(folder.path_join("gm_test_mode.gd")).new()\n    release_state=load(folder.path_join("player_release.gd")).new()')
s=s.replace('player_state.consume(kind,data,int(server.me_oid),Time.get_ticks_msec())','player_state.consume(kind,data,int(server.me_oid),Time.get_ticks_msec())\n    var release_revision:int=release_state.revision\n    release_state.consume(kind,data,int(server.me_oid))\n    if release_state.revision!=release_revision:player_state.revision+=1')
s=s.replace('elif action=="gm_test_mode":','elif action=="player_release":\n        if int(server.entry.get("zone",-1))==207:\n            release_state.request(value,player_state,server.client,Time.get_ticks_msec());player_state.revision+=1\n    elif action=="gm_test_mode":')
s=s.replace('adapter.advance_corpses(now)','var release_revision:int=release_state.revision\n    release_state.advance(now)\n    if release_state.revision!=release_revision:player_state.revision+=1\n    adapter.advance_corpses(now)');s=s.replace('player_snapshot["gm_mode"]=gm_mode.snapshot()','player_snapshot["gm_mode"]=gm_mode.snapshot()\n        player_snapshot["release"]=release_state.snapshot()');p.write_text(s,encoding='utf-8')
p=R/'Godot/visual_bridge.gd';s=p.read_text(encoding='utf-8').replace('"player_sit","gm_test_mode"','"player_sit","gm_test_mode","player_release"');p.write_text(s,encoding='utf-8')
for root in [R/'UnrealPlugin/DAoCVisualBridge',R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge']:
 p=root/'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h';s=p.read_text(encoding='utf-8').replace('void RequestGMMode(bool CombatTest);','void RequestGMMode(bool CombatTest);\n    void RequestRelease();');assert 'void RequestRelease();'in s;p.write_text(s,encoding='utf-8')
 p=root/'Source/DAoCVisualBridge/Private/DAoCBridgePlayerStatus.cpp';s=p.read_text(encoding='utf-8');anchor='void UDAoCBridgeSubsystem::RequestGMMode(bool CombatTest){';new='''void UDAoCBridgeSubsystem::RequestRelease(){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting||!PlayerFlag(PlayerState,TEXT("ready"))||PlayerNum(PlayerVitals(PlayerState),TEXT("health_pct"),100)!=0)return;
    const TSharedPtr<FJsonObject>* Release=nullptr;if(PlayerState->TryGetObjectField(TEXT("release"),Release)&&PlayerFlag(*Release,TEXT("pending")))return;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));Send(TEXT("player_release"),V);
}
''';s=s.replace(anchor,new+anchor)
 s=s.replace('if(Dead)PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(TEXT("Personaje muerto"))];','''if(Dead){
        const TSharedPtr<FJsonObject>* Release=nullptr;State->TryGetObjectField(TEXT("release"),Release);const bool Waiting=Release&&PlayerFlag(*Release,TEXT("pending"));
        PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(TEXT("Personaje muerto"))];
        PlayerStatusPanel->AddSlot().AutoHeight()[SNew(SButton).IsFocusable(false).IsEnabled(!Waiting).OnClicked_Lambda([this](){RequestRelease();return FReply::Handled();})[PlayerLabel(Waiting?TEXT("Esperando regreso…"):TEXT("Regresar al punto de vínculo"))]];
        FString Message;if(Release)(*Release)->TryGetStringField(TEXT("feedback"),Message);if(!Message.IsEmpty())PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(Message)];
    }''');p.write_text(s,encoding='utf-8')
 p=root/'Source/DAoCVisualBridge/Private/DAoCBridgePlayerStatusAcceptance.cpp';s=p.read_text(encoding='utf-8');anchor='        bLocalAvailable=false;RequestAttack(false);';insert='''        Vitals->SetNumberField(TEXT("health_pct"),100);RequestRelease();Check(Outgoing.IsEmpty(),TEXT("living player cannot release"));
        Vitals->SetNumberField(TEXT("health_pct"),0);auto Release=MakeShared<FJsonObject>();Release->SetBoolField(TEXT("pending"),false);State->SetObjectField(TEXT("release"),Release);RequestRelease();auto ReleaseCommand=Capture(TEXT("player_release"));if(ReleaseCommand.IsValid())Check(ReleaseCommand->GetIntegerField(TEXT("player_generation"))==State->GetIntegerField(TEXT("generation")),TEXT("release request bound to player generation"));Check(Vitals->GetNumberField(TEXT("health_pct"))==0,TEXT("release never revives locally"));
        Release->SetBoolField(TEXT("pending"),true);RequestRelease();Check(Outgoing.IsEmpty(),TEXT("pending release cannot duplicate"));State->SetNumberField(TEXT("revision"),State->GetNumberField(TEXT("revision"))+1);ApplyPlayerStatus(State);Check(PlayerStatusPanel->GetChildren()->Num()>=8,TEXT("dead player sees native release control"));Vitals->SetNumberField(TEXT("health_pct"),SavedHP);
''';assert anchor in s;s=s.replace(anchor,insert+anchor);p.write_text(s,encoding='utf-8')
print('Release preparado en fuentes, aún sin instalar')
