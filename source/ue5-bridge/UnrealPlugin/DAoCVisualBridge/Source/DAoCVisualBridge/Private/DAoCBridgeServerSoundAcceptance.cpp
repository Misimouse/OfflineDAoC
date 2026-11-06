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

bool UDAoCBridgeSubsystem::TickServerSoundAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeServerSoundTest="),File))return false;
    struct FRun {bool Started=false,Done=false;int32 Checks=0,Seq=0;double Began=0;TArray<FString> Failures;};
    static FRun Run;if(Run.Done)return true;
    auto Check=[&](bool V,const TCHAR* Name){++Run.Checks;if(!V)Run.Failures.Add(Name);};
    auto Count=[&](const TCHAR* Key){double V=0;SpellAudioReport()->TryGetNumberField(Key,V);return V;};
    auto Event=[&](int32 Id,bool Placed=false,double X=1364,double Radius=10,double Age=0,int32 Sequence=-1){
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),TEXT("private-server-sound"));
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("seq"),Sequence<0?++Run.Seq:Sequence);
        Row->SetNumberField(TEXT("age_ms"),Age);Row->SetNumberField(TEXT("sound_id"),Id);Row->SetBoolField(TEXT("placed"),Placed);
        Row->SetNumberField(TEXT("radius_m"),Radius);
        Row->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});
        Snapshot->SetArrayField(TEXT("server_sound_audio"),{MakeShared<FJsonValueObject>(Row)});ApplySpellAudio(Snapshot);TickSpellAudio();
    };
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();
        Camera->SetActorLocation(FVector(1000000,1000000,1000000));
        if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);
        auto* Player=GetWorld()->SpawnActor<ACameraActor>();Player->SetActorLocation(FVector::ZeroVector);Entities.Add(TEXT("player:local"),Player);
        for(int32 Id:TArray<int32>{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,163,216,217,218,219,220,2452,2467}){
            const double Before=Count(TEXT("server_sound_events"));Event(Id);
            Check(Count(TEXT("server_sound_events"))==Before+1,TEXT("original requested id reaches native scheduling independently of camera distance"));
        }
        Check(SpellAudioReport()->GetBoolField(TEXT("server_sound_ready")),TEXT("separate original catalog loaded"));
        const double Before=Count(TEXT("server_sound_events"));Event(7,false,1364,10,0,Run.Seq);
        Check(Count(TEXT("server_sound_events"))==Before,TEXT("snapshot replay silent"));
        Event(7,false,1364,10,1001);Check(Count(TEXT("server_sound_events"))==Before,TEXT("stale announcement silent"));
        Event(65535);Check(Count(TEXT("server_sound_events"))==Before,TEXT("unknown id has no substitute"));
        Event(12,true,1375,10);Check(Count(TEXT("server_sound_events"))==Before,TEXT("player outside radius silent even with distant camera"));
        Event(12,true,1374,10);Check(Count(TEXT("server_sound_events"))==Before+1,TEXT("player on exact radius boundary hears sound"));
        Event(12,true,1364,0);Check(Count(TEXT("server_sound_events"))==Before+1,TEXT("malformed placed zero radius rejected"));
        Event(12,true,1364,10);Check(Count(TEXT("server_sound_events"))==Before+2,TEXT("placed sound inside radius ignores camera distance"));
    }
    TickSpellAudio();
    if(Now-Run.Began>2){
        if(Count(TEXT("pcm_consumed_bytes"))<=0&&Now-Run.Began<5)return true;
        Check(Count(TEXT("server_sound_clips"))==30,TEXT("all original event and placed resources play"));
        Check(Count(TEXT("pcm_consumed_bytes"))>0,TEXT("audio engine consumes original event PCM"));
        Check(Count(TEXT("invalid_resources"))==0,TEXT("original WAV and decoded ADPCM resources valid"));
        ClearSpellAudio();Check(Count(TEXT("active_voices"))==0&&Count(TEXT("pending_clips"))==0,TEXT("logout clears direct and placed voices"));
        auto Report=SpellAudioReport();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);
        TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Report->SetArrayField(TEXT("failures"),Failures);
        Report->SetBoolField(TEXT("audible_owner_acceptance"),false);Report->SetBoolField(TEXT("real_server_protocol_tested"),false);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
        Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
