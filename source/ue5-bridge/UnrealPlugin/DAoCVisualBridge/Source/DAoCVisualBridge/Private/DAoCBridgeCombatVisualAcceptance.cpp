#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickCombatVisualAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCombatVisualTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    TArray<TSharedPtr<FJsonValue>> Failures;int32 Checks=0;auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Input;TSharedPtr<FJsonObject> Fixture;Check(FFileHelper::LoadFileToString(Input,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Fixture),TEXT("Godot combat announcements parsed"));
    if(Fixture.IsValid()){
        Check(Socket==nullptr,TEXT("native replay has no live account"));
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),TEXT("player:local"));Row->SetStringField(TEXT("kind"),TEXT("player"));Row->SetStringField(TEXT("name"),TEXT("Offline combat sample"));Row->SetNumberField(TEXT("model_id"),0);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);EntityRows.Add(TEXT("player:local"),Row);
        auto* Actor=Cast<ASkeletalMeshActor>(CreateEntity(TEXT("player:local"),Row,FVector::ZeroVector));Check(Actor!=nullptr,TEXT("original humanoid mesh loaded"));
        if(Actor){
            auto* Mesh=Actor->GetSkeletalMeshComponent();auto State=MakeShared<FJsonObject>();auto Vitals=MakeShared<FJsonObject>();State->SetBoolField(TEXT("ready"),true);State->SetBoolField(TEXT("attack_on"),true);Vitals->SetNumberField(TEXT("health_pct"),100);Vitals->SetBoolField(TEXT("sitting"),false);State->SetObjectField(TEXT("vitals"),Vitals);PlayerState=State;
            Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("local_attack")));SetEntityAnimation(TEXT("player:local"),TEXT("idle"));auto* Anim=Mesh->GetSingleNodeInstance();Check(Anim!=nullptr,TEXT("skeletal animation instance exists"));
            if(Anim){
                const FString Clip=AnimationStates.FindRef(TEXT("player:local"));Check(Clip.StartsWith(TEXT("attack_"))&&!Anim->IsLooping(),TEXT("actual packet selects original one-shot swing"));Check(FMath::IsNearlyEqual(Anim->GetCurrentTime(),.1f,.015f),TEXT("original source age is applied"));
                auto& Pose=PosePlayback[TEXT("player:local")];const int64 FirstSeq=Pose.ActiveActionSeq;const float Advanced=FMath::Min(.25f,Anim->GetLength()*.5f);Pose.ActionStartedAt=FPlatformTime::Seconds()-Advanced;Pose.ActionUntil=Pose.ActionStartedAt+Anim->GetLength();
                SetEntityAnimation(TEXT("player:local"),TEXT("run"));Check(AnimationStates.FindRef(TEXT("player:local"))==Clip&&FMath::IsNearlyEqual(Anim->GetCurrentTime(),Advanced,.015f),TEXT("repeated snapshots do not restart swing and movement does not cut it"));Check(Pose.ActiveActionSeq==FirstSeq,TEXT("snapshot does not create an action"));
                Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("second_attack")));SetEntityAnimation(TEXT("player:local"),TEXT("run"));Check(AnimationStates.FindRef(TEXT("player:local"))==Clip&&Pose.ActiveActionSeq>FirstSeq&&FMath::IsNearlyEqual(Anim->GetCurrentTime(),.1f,.015f),TEXT("new real packet restarts same clip once"));
                Pose.ActionUntil=FPlatformTime::Seconds()-1;SetEntityAnimation(TEXT("player:local"),TEXT("run"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("run")&&Anim->IsLooping(),TEXT("completed action returns to ongoing locomotion"));
                Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("attack_then_flinch")));SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==Clip,TEXT("queued flinch cannot overwrite earlier swing"));Check(Pose.LastCombatSeq>Pose.ActiveActionSeq,TEXT("skipped defence is acknowledged and not deferred"));Pose.ActionUntil=FPlatformTime::Seconds()-1;SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("combat_idle"),TEXT("skipped flinch cannot appear after swing finishes"));
                Vitals->SetNumberField(TEXT("health_pct"),0);Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("death_attack")));SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("death")&&Pose.ActionClip.IsEmpty(),TEXT("real death overrides and clears announced attack"));
                Vitals->SetNumberField(TEXT("health_pct"),50);State->SetBoolField(TEXT("attack_on"),false);SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("idle"),TEXT("revival cannot replay already acknowledged attack"));
                Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("stale_attack")));SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("idle")&&Pose.ActionClip.IsEmpty(),TEXT("announcement older than its clip is discarded"));
                Row->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("local_flinch")));SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("flinch")&&!Anim->IsLooping(),TEXT("idle defender plays original flinch"));
                Check(Vitals->GetIntegerField(TEXT("health_pct"))==50,TEXT("native animations never apply damage"));Check(Actor->GetActorLocation().Equals(FVector::ZeroVector),TEXT("native animations never move authoritative actor"));
            }
        }
        auto MobRow=MakeShared<FJsonObject>();MobRow->Values=Row->Values;MobRow->SetStringField(TEXT("id"),TEXT("npc:2"));MobRow->SetStringField(TEXT("kind"),TEXT("npc"));MobRow->SetNumberField(TEXT("model_id"),123);MobRow->SetObjectField(TEXT("combat_visual"),Fixture->GetObjectField(TEXT("npc_attack")));EntityRows.Add(TEXT("npc:2"),MobRow);auto* Mob=Cast<ASkeletalMeshActor>(CreateEntity(TEXT("npc:2"),MobRow,FVector(300,0,0)));Check(Mob!=nullptr,TEXT("original creature mesh loaded"));
        if(Mob){SetEntityAnimation(TEXT("npc:2"),TEXT("walk"));Check(AnimationStates.FindRef(TEXT("npc:2")).StartsWith(TEXT("attack_")),TEXT("creature uses its own actual attack clip"));auto& Pose=PosePlayback[TEXT("npc:2")];Pose.ActionUntil=FPlatformTime::Seconds()-1;MobRow->SetBoolField(TEXT("combat_active"),true);MobRow->SetStringField(TEXT("combat_stance"),TEXT(""));SetEntityAnimation(TEXT("npc:2"),TEXT("idle"));Check(AnimationStates.FindRef(TEXT("npc:2"))==TEXT("combat_idle"),TEXT("stationary fighting creature uses combat idle"));SetEntityAnimation(TEXT("npc:2"),TEXT("walk"));Check(AnimationStates.FindRef(TEXT("npc:2"))==TEXT("walk"),TEXT("moving creature returns to locomotion after action"));}
        ClearEntities();Check(PosePlayback.IsEmpty()&&AnimationStates.IsEmpty(),TEXT("session cleanup removes action queues"));Check(Socket==nullptr,TEXT("replay never connects to server"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("checks"),Checks);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".native.json")));UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
