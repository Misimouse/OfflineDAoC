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

bool UDAoCBridgeSubsystem::TickSpellAudioAcceptance(){
    if(TickServerSoundAcceptance()||TickFootstepAcceptance()||TickDoorAudioAcceptance()||TickCombatAudioAcceptance())return true;
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSpellAudioTest="),File))return false;
    struct FRun {bool Started=false,Done=false;int32 Stage=0,Checks=0;double Began=0;TArray<FString> Failures;};
    static FRun Run;
    if(Run.Done)return true;
    auto Check=[&](bool Value,const TCHAR* Name){++Run.Checks;if(!Value)Run.Failures.Add(Name);};
    auto Count=[&](const TCHAR* Key){double Value=0;SpellAudioReport()->TryGetNumberField(Key,Value);return Value;};
    auto Event=[&](int32 Seq,const TCHAR* Kind,int32 Effect,bool Quiet=false,const TCHAR* Reason=TEXT(""),double Age=0){
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),TEXT("private-spell-audio-acceptance"));
        auto E=MakeShared<FJsonObject>();E->SetNumberField(TEXT("seq"),Seq);E->SetStringField(TEXT("kind"),Kind);
        E->SetStringField(TEXT("caster"),TEXT("player:local"));E->SetStringField(TEXT("target"),TEXT("player:local"));
        E->SetNumberField(TEXT("effect_id"),Effect);E->SetNumberField(TEXT("duration_ms"),3000);E->SetNumberField(TEXT("age_ms"),Age);
        E->SetBoolField(TEXT("no_sound"),Quiet);E->SetStringField(TEXT("reason"),Reason);
        Snapshot->SetArrayField(TEXT("spell_visuals"),{MakeShared<FJsonValueObject>(E)});ApplySpellAudio(Snapshot);TickSpellAudio();
    };
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;
        auto* Fixture=GetWorld()->SpawnActor<AActor>();Entities.Add(TEXT("player:local"),Fixture);
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();
        if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);
        Event(1,TEXT("cast"),4101);
        Check(SpellAudioReport()->GetBoolField(TEXT("ready")),TEXT("original sound and effect catalogs loaded"));
        Check(Count(TEXT("played_clips"))>=1,TEXT("original Gleam Ray gather creates an audio component"));
        const double Played=Count(TEXT("played_clips"));Event(1,TEXT("cast"),4101);
        Check(Count(TEXT("played_clips"))==Played,TEXT("repeated snapshots do not replay sounds"));
    }
    TickSpellAudio();const double Age=Now-Run.Began;
    if(Run.Stage==0&&Age>.5){
        if(Count(TEXT("pcm_consumed_bytes"))<=0&&Age<2)return true;
        Check(Count(TEXT("pcm_consumed_bytes"))>0,TEXT("audio engine actually consumes original PCM samples"));
        const double Played=Count(TEXT("played_clips"));Event(2,TEXT("release"),4101,true);
        Check(Count(TEXT("played_clips"))==Played&&Count(TEXT("active_gather"))==0,TEXT("silent pulse stops gathering without cast or hit audio"));
        Event(3,TEXT("cast"),13200);
        Check(SpellAudioReport()->GetStringField(TEXT("last_sound_name")).Contains(TEXT("MagicMissle_Gather")),TEXT("source spelling alias selects original Magic Missile WAV"));
        Run.Stage=1;
    }
    if(Run.Stage==1&&Age>2.1){
        Event(4,TEXT("release"),13200);const double Played=Count(TEXT("played_clips"));
        Event(4,TEXT("release"),13200);Event(5,TEXT("release"),13200);
        Check(Count(TEXT("played_clips"))==Played,TEXT("one release burst does not stack duplicate group-target audio"));
        Check(Count(TEXT("active_gather"))==0,TEXT("release cancels the gathering voice"));Run.Stage=2;
    }
    if(Run.Stage==2&&Age>2.4){
        Event(6,TEXT("cast"),4101);Event(7,TEXT("cancel"),0,false,TEXT("interrupt"));
        Check(Count(TEXT("active_gather"))==0,TEXT("interruption cancels pending and active gathering voices"));
        const double Before=Count(TEXT("played_clips"));Event(8,TEXT("release"),4101,false,TEXT(""),9000);
        Check(Count(TEXT("played_clips"))==Before,TEXT("stale events do not produce delayed catch-up audio"));
        const double Missing=Count(TEXT("unresolved_references"));Event(9,TEXT("cast"),5921);
        Check(Count(TEXT("played_clips"))==Before&&Count(TEXT("unresolved_references"))==Missing+1,TEXT("missing original sound set 332 stays silent instead of substituting"));
        Event(10,TEXT("cast"),4101);Event(11,TEXT("release"),4101);Run.Stage=3;
    }
    if(Run.Stage==3&&Age>4.3){
        Check(Count(TEXT("pcm_consumed_bytes"))>0,TEXT("original cast and hit sequence retains a functioning audio stream"));
        Check(Count(TEXT("invalid_resources"))==0,TEXT("original WAVs are accepted without malformed audio or component errors"));
        Check(Count(TEXT("quiet_events"))==1&&Count(TEXT("duplicates_suppressed"))>=2,TEXT("quiet and duplicate packet protections remain observable"));
        ClearSpellAudio();Check(Count(TEXT("active_voices"))==0&&Count(TEXT("pending_clips"))==0,TEXT("session cleanup stops every voice and delayed clip"));
        auto Report=SpellAudioReport();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);
        TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Report->SetArrayField(TEXT("failures"),Failures);
        Report->SetBoolField(TEXT("real_audio_engine_consumption_tested"),true);Report->SetNumberField(TEXT("test_gain_multiplier"),.03);
        Report->SetBoolField(TEXT("audible_owner_acceptance"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
        Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
