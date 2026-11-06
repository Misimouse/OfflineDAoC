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

bool UDAoCBridgeSubsystem::TickDoorAudioAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDoorAudioTest="),File))return false;
    struct FRun {bool Started=false,Done=false;int32 Checks=0;double Began=0;TArray<FString> Failures;};
    static FRun Run;if(Run.Done)return true;
    auto Check=[&](bool Value,const TCHAR* Name){++Run.Checks;if(!Value)Run.Failures.Add(Name);};
    auto Count=[&](const TCHAR* Key){double Value=0;SpellAudioReport()->TryGetNumberField(Key,Value);return Value;};
    auto Scheduled=[&](){return Count(TEXT("played_clips"))+Count(TEXT("pending_clips"));};
    auto Event=[&](int32 Seq,int32 Set,const TCHAR* Name,double Age=0,double X=1364){
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),TEXT("private-door-audio-acceptance"));
        auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("seq"),Seq);Row->SetNumberField(TEXT("age_ms"),Age);
        Row->SetStringField(TEXT("owner"),TEXT("door:207033603"));Row->SetStringField(TEXT("sheet"),TEXT("doors"));
        Row->SetStringField(TEXT("event"),Name);Row->SetNumberField(TEXT("set"),Set);
        Row->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});
        Snapshot->SetArrayField(TEXT("combat_audio"),{MakeShared<FJsonValueObject>(Row)});ApplySpellAudio(Snapshot);TickSpellAudio();
    };
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();
        if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);
        Event(1,1,TEXT("open"));
        Check(SpellAudioReport()->GetBoolField(TEXT("door_ready")),TEXT("original door catalog loaded separately"));
        Check(Scheduled()==1,TEXT("acknowledged opening schedules original audio without a creature actor"));
        Event(1,1,TEXT("open"));Check(Scheduled()==1,TEXT("repeated snapshot is silent"));
        Event(2,1,TEXT("close"));Check(Scheduled()==2,TEXT("closing schedules original audio"));
        Event(3,0,TEXT("open"));Check(Scheduled()==2,TEXT("zero flag has no invented sound"));
        Event(4,12,TEXT("close"));Check(Scheduled()==2,TEXT("original empty close slot stays silent"));
        Event(5,10,TEXT("open"));Check(Scheduled()==2,TEXT("unresolved bridge structure stays silent"));
        Event(6,99999,TEXT("open"));Check(Scheduled()==2,TEXT("unknown set stays silent"));
        Event(7,1,TEXT("open"),9000);Check(Scheduled()==2,TEXT("stale event stays silent"));
        Event(8,1,TEXT("idle"));Check(Scheduled()==2,TEXT("only door open and close are enabled"));
        const double Culled=Count(TEXT("culled_clips"));Event(9,1,TEXT("open"),0,100000);
        Check(Scheduled()==2&&Count(TEXT("culled_clips"))==Culled+1,TEXT("source distance culls distant door"));
    }
    TickSpellAudio();
    if(Now-Run.Began>1){
        if((Count(TEXT("pcm_consumed_bytes"))<=0||Count(TEXT("played_clips"))<2)&&Now-Run.Began<4)return true;
        Check(Count(TEXT("played_clips"))==2,TEXT("opening and closing reach actual playback"));
        Check(Count(TEXT("pcm_consumed_bytes"))>0,TEXT("audio engine consumes original door PCM"));
        Check(Count(TEXT("invalid_resources"))==0,TEXT("door WAV resources are valid"));
        ClearSpellAudio();Check(Count(TEXT("active_voices"))==0&&Count(TEXT("pending_clips"))==0,TEXT("logout clears anchored door voices"));
        auto Report=SpellAudioReport();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);
        TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Report->SetArrayField(TEXT("failures"),Failures);
        Report->SetBoolField(TEXT("audible_owner_acceptance"),false);Report->SetBoolField(TEXT("real_server_protocol_tested"),false);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
        Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
