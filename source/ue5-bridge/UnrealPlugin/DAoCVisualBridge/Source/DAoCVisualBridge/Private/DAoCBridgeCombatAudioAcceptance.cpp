#include "DAoCBridgeSubsystem.h"
#include "Camera/CameraActor.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickCombatAudioAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCombatAudioTest="),File))return false;
    struct FRun {bool Started=false,Done=false;int32 Stage=0,Checks=0;double Began=0;TArray<FString> Failures;};
    static FRun Run;
    if(Run.Done)return true;
    auto Check=[&](bool Value,const TCHAR* Name){++Run.Checks;if(!Value)Run.Failures.Add(Name);};
    auto Count=[&](const TCHAR* Key){double Value=0;SpellAudioReport()->TryGetNumberField(Key,Value);return Value;};
    auto Scheduled=[&](){return Count(TEXT("played_clips"))+Count(TEXT("pending_clips"));};
    auto Event=[&](int32 Seq,const TCHAR* Sheet,int32 Set,const TCHAR* Name,double Age=0){
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),TEXT("private-combat-audio-acceptance"));
        auto E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("seq"),Seq);E->SetNumberField(TEXT("age_ms"),Age);
        E->SetStringField(TEXT("owner"),TEXT("qa:removed-actor"));E->SetStringField(TEXT("sheet"),Sheet);
        E->SetStringField(TEXT("event"),Name);E->SetNumberField(TEXT("set"),Set);
        E->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(1364),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});
        Snapshot->SetArrayField(TEXT("combat_audio"),{MakeShared<FJsonValueObject>(E)});ApplySpellAudio(Snapshot);TickSpellAudio();
    };
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();
        if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);
        Event(1,TEXT("weapons"),25,TEXT("use"));
        Check(SpellAudioReport()->GetBoolField(TEXT("combat_ready")),TEXT("separate original combat catalog loaded"));
        Check(Count(TEXT("played_clips"))==1,TEXT("original weapon use creates one voice at packet location"));
        Event(1,TEXT("weapons"),25,TEXT("use"));
        Check(Count(TEXT("played_clips"))==1,TEXT("repeated combat snapshots do not stack voices"));
        Event(2,TEXT("creatures"),8,TEXT("pain_light"));
        Check(Scheduled()==2,TEXT("original creature pain group retains its source offset"));
        Event(3,TEXT("weapons"),19,TEXT("style_hit"));
        Check(Scheduled()==3,TEXT("weaponless style hit uses original hit-medium rule"));
        Event(4,TEXT("creatures"),3,TEXT("die"));
        Check(Scheduled()==4,TEXT("death voice schedules after actor identity is removed"));
        const double Missing=Count(TEXT("unresolved_references"));
        Event(5,TEXT("weapons"),25,TEXT("activate"));
        Check(Scheduled()==4&&Count(TEXT("unresolved_references"))==Missing,TEXT("empty original draw slot remains silent"));
        Event(6,TEXT("creatures"),8,TEXT("idle"));
        Check(Count(TEXT("combat_events_seen"))==5,TEXT("unscoped idle audio is not activated"));
        Event(7,TEXT("weapons"),99999,TEXT("use"));
        Check(Count(TEXT("unresolved_references"))==Missing+1,TEXT("unknown sound set does not invent a substitute"));
        Event(8,TEXT("weapons"),25,TEXT("use"),9000);
        Check(Scheduled()==4,TEXT("stale combat events stay silent"));
    }
    TickSpellAudio();
    if(Run.Stage==0&&Now-Run.Began>1){
        if((Count(TEXT("pcm_consumed_bytes"))<=0||Count(TEXT("played_clips"))<4)&&Now-Run.Began<3)return true;
        Check(Count(TEXT("played_clips"))==4,TEXT("all four original scheduled voices reach actual playback"));
        Check(Count(TEXT("pcm_consumed_bytes"))>0,TEXT("audio engine consumes original combat PCM samples"));
        Check(Count(TEXT("invalid_resources"))==0,TEXT("original mono and stereo WAV resources are valid"));
        ClearSpellAudio();
        Check(Count(TEXT("active_voices"))==0&&Count(TEXT("pending_clips"))==0,TEXT("logout cleanup stops every combat voice"));
        auto Report=SpellAudioReport();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);
        TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Report->SetArrayField(TEXT("failures"),Failures);
        Report->SetBoolField(TEXT("audible_owner_acceptance"),false);Report->SetBoolField(TEXT("real_server_protocol_tested"),false);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
        Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
