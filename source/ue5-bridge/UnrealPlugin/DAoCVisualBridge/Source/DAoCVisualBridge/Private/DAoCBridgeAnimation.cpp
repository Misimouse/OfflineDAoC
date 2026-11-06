#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovementKeys.h"
#include "Dom/JsonObject.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace {
bool PoseFlag(const TSharedPtr<FJsonObject>& O,const TCHAR* K){bool V=false;if(O.IsValid())O->TryGetBoolField(K,V);return V;}
double PoseNum(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
}
void UDAoCBridgeSubsystem::UpdatePoseVisualTest(double Elapsed){
    if(!PoseFlag(PlayerState,TEXT("ready")))return;
    if(Elapsed>20&&!(PoseVisualTestSteps&1)){RequestSit(true);PoseVisualTestSteps|=1;}
    if(Elapsed>28&&!(PoseVisualTestSteps&2)){FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/TEXT("Pose_Sitting.png"),true,false);PoseVisualTestSteps|=2;}
    if(Elapsed>35&&!(PoseVisualTestSteps&4)){RequestSit(false);PoseVisualTestSteps|=4;}
    if(Elapsed>45&&!(PoseVisualTestSteps&8)){FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/TEXT("Pose_Standing.png"),true,false);PoseVisualTestSteps|=8;}
}
void UDAoCBridgeSubsystem::SetEntityAnimation(const FString& Id,const FString& Requested){
    auto* Row=EntityRows.Find(Id);auto* Found=Entities.Find(Id);if(!Row||!Found||!IsValid(*Found))return;
    auto* Skel=Cast<ASkeletalMeshActor>(*Found);if(!Skel)return;auto* Mesh=Skel->GetSkeletalMeshComponent();
    auto* Entry=ModelCatalog.Find(FString::FromInt((*Row)->GetIntegerField(TEXT("model_id"))));if(!Entry)return;
    const double Now=FPlatformTime::Seconds();auto& Pose=PosePlayback.FindOrAdd(Id);const bool Local=Id==TEXT("player:local");
    const TSharedPtr<FJsonObject>* VitalsPtr=nullptr;TSharedPtr<FJsonObject> Vitals;
    if(PlayerState.IsValid()&&PlayerState->TryGetObjectField(TEXT("vitals"),VitalsPtr))Vitals=*VitalsPtr;
    const bool Ready=Local&&PoseFlag(PlayerState,TEXT("ready"));
    const bool Dead=Local?(Ready?PoseNum(Vitals,TEXT("health_pct"))<=0:Pose.Dead):Requested==TEXT("dead");
    const bool Mounted=!Dead&&(Local?(bLocalMounted&&bLocalSeatReady):(*Row)->HasField(TEXT("riding_steed_entity_id")));
    const bool Sitting=Ready&&!Mounted&&!Dead&&PoseFlag(Vitals,TEXT("sitting"));
    const bool Moving=Requested==TEXT("walk")||Requested==TEXT("run")||Requested==TEXT("swim")||Requested==TEXT("jump")||Requested==TEXT("walk_back");
    auto Clip=[&](const FString& Key)->UAnimSequenceBase*{FString Path;return (*Entry)->TryGetStringField(Key,Path)?LoadObject<UAnimSequenceBase>(nullptr,*Path):nullptr;};
    if(Dead){
        if(!Pose.Dead){
            Pose.DiedAt=Now;const TSharedPtr<FJsonObject>* Motion=nullptr;FString Event;double Age=0;
            if(!Local&&(*Row)->TryGetObjectField(TEXT("motion"),Motion)&&(*Motion)->TryGetStringField(TEXT("event"),Event)&&Event==TEXT("death")&&(*Motion)->TryGetNumberField(TEXT("age_ms"),Age)&&FMath::IsFinite(Age)&&Age>=0)Pose.DiedAt=Now-FMath::Min(Age/1000.,3600.);
        }
        Pose.Transition.Empty();Pose.TransitionUntil=0;Pose.ActionClip.Empty();Pose.ActionUntil=0;
    }
    else if(Pose.Initialized&&Local&&Ready&&Sitting!=Pose.Sitting){
        if(auto* Sit=Clip(TEXT("sit_down"))){Pose.Transition=Sitting?TEXT("sit_down"):TEXT("sit_down_reverse");Pose.TransitionUntil=Now+Sit->GetPlayLength();}
        else{Pose.Transition.Empty();Pose.TransitionUntil=0;}
    }
    Pose.Initialized=true;Pose.Sitting=Sitting;Pose.Dead=Dead;
    // Original Godot rises by reversing sit_down. Its stand_up clip is an 8 s idle.
    if(Now>=Pose.TransitionUntil||(Moving&&!Sitting)){Pose.Transition.Empty();Pose.TransitionUntil=0;}
    const TSharedPtr<FJsonObject>* Combat=nullptr;const TArray<TSharedPtr<FJsonValue>>* Events=nullptr;
    if((*Row)->TryGetObjectField(TEXT("combat_visual"),Combat)&&(*Combat)->TryGetArrayField(TEXT("events"),Events)&&Events->Num()<=8){
        for(const auto& Value:*Events){
            if(Value->Type!=EJson::Object)continue;auto Event=Value->AsObject();double Seq=0,Age=0;FString EventClip,Kind;
            if(!Event->TryGetNumberField(TEXT("seq"),Seq)||!FMath::IsFinite(Seq)||Seq<1||Seq>9e15||FMath::FloorToDouble(Seq)!=Seq||int64(Seq)<=Pose.LastCombatSeq)continue;
            Pose.LastCombatSeq=int64(Seq);
            if(Dead||!Event->TryGetNumberField(TEXT("age_ms"),Age)||!FMath::IsFinite(Age)||Age<0||Age>5000||!Event->TryGetStringField(TEXT("clip"),EventClip)||!Event->TryGetStringField(TEXT("kind"),Kind))continue;
            const bool Attack=Kind==TEXT("attack")||Kind==TEXT("style");const bool Defence=Kind==TEXT("parry")||Kind==TEXT("block")||Kind==TEXT("evade")||Kind==TEXT("flinch");if(!Attack&&!Defence)continue;
            auto* Animation=Clip(EventClip);if(!Animation)continue;
            const double Began=Now-Age/1000.,Until=Began+Animation->GetPlayLength();if(Until<=Now)continue;
            if(Defence&&(Pose.ActionUntil>Now||Pose.TransitionUntil>Now))continue;
            Pose.ActionClip=EventClip;Pose.ActiveActionSeq=int64(Seq);Pose.ActionStartedAt=Began;Pose.ActionUntil=Until;Pose.Transition.Empty();Pose.TransitionUntil=0;
        }
    }
    if(Pose.ActionUntil<=Now){Pose.ActionClip.Empty();Pose.ActionUntil=0;}
    bool SpellPose=false,SpellLoop=false;FString SpellKey;double SpellAt=0;int64 SpellSeq=0;
    const TSharedPtr<FJsonObject>* CastData=nullptr;
    if(!Dead&&!Mounted&&!Sitting&&!Moving&&(*Row)->TryGetObjectField(TEXT("spell_cast"),CastData)){
        auto C=*CastData;FString Phase;C->TryGetStringField(TEXT("phase"),Phase);const double Age=PoseNum(C,TEXT("age_ms"))/1000.+(LastSnapshot>0?FMath::Max(0.,Now-LastSnapshot):0.);const double Duration=PoseNum(C,TEXT("duration_ms"))/1000.;SpellSeq=int64(PoseNum(C,TEXT("seq")));
        const TArray<TSharedPtr<FJsonValue>>* Names=nullptr;C->TryGetArrayField(TEXT("anims"),Names);
        auto CastingClip=[&](int32 I,const FString& Fallback){FString K=Names&&Names->IsValidIndex(I)&&(*Names)[I]->Type==EJson::String?(*Names)[I]->AsString():Fallback;return Clip(K)?K:Fallback;};
        if(SpellSeq>0&&Age>=0&&Phase==TEXT("casting")&&Duration>0&&Age<=Duration+1.5){
            const FString Start=CastingClip(0,TEXT("cast_start"));auto* A=Clip(Start);const double Length=A?A->GetPlayLength():0;
            if(A&&Age<Length){SpellKey=Start;SpellAt=Age;}
            else{SpellKey=CastingClip(1,TEXT("cast_mid"));SpellLoop=true;if(auto* Mid=Clip(SpellKey))SpellAt=FMath::Fmod(FMath::Max(0.,Age-Length),FMath::Max(.001,double(Mid->GetPlayLength())));}
            SpellPose=Clip(SpellKey)!=nullptr;
        }else if(SpellSeq>0&&Age>=0&&Phase==TEXT("released")&&!PoseFlag(C,TEXT("instant"))){SpellKey=CastingClip(2,TEXT("cast_end"));if(auto* End=Clip(SpellKey)){SpellPose=Age<End->GetPlayLength();SpellAt=Age;}}
    }
    if(SpellPose){Pose.ActionClip.Empty();Pose.ActionUntil=0;Pose.Transition.Empty();Pose.TransitionUntil=0;}
    const bool Action=!Dead&&!Mounted&&!Pose.ActionClip.IsEmpty()&&Pose.ActionUntil>Now;
    FString Key=Requested;bool Loop=true,Reverse=false;
    if(Dead){Key=TEXT("death");Loop=false;}
    else if(Mounted){Key=TEXT("ride_horse");Pose.ActionClip.Empty();Pose.ActionUntil=0;Pose.Transition.Empty();Pose.TransitionUntil=0;}
    else if(SpellPose){Key=SpellKey;Loop=SpellLoop;}
    else if(Action){Key=Pose.ActionClip;Loop=false;}
    else if(!Pose.Transition.IsEmpty()){Reverse=Pose.Transition==TEXT("sit_down_reverse");Key=TEXT("sit_down");Loop=false;}
    else if(Sitting)Key=TEXT("sit_idle");
    else if(Local&&Ready&&PoseFlag(PlayerState,TEXT("attack_on"))&&!Moving){
        Key=TEXT("combat_idle");FString Stance;PlayerState->TryGetStringField(TEXT("weapon_stance"),Stance);
        const FString Variant=Stance==TEXT("xbow")?TEXT("xbow_idle"):Key+TEXT("_")+Stance;
        if(!Stance.IsEmpty()&&(*Entry)->HasField(Variant))Key=Variant;
    }
    else if(!Local&&!Moving&&PoseFlag(*Row,TEXT("combat_active"))){
        Key=TEXT("combat_idle");FString Stance;(*Row)->TryGetStringField(TEXT("combat_stance"),Stance);const FString Variant=Stance==TEXT("xbow")?TEXT("xbow_idle"):Key+TEXT("_")+Stance;if(!Stance.IsEmpty()&&(*Entry)->HasField(Variant))Key=Variant;
    }
    if(Key==TEXT("jump"))Loop=false;
    if(!(*Entry)->HasField(Key)&&!Dead&&!Sitting&&Pose.Transition.IsEmpty())Key=Moving&&(*Entry)->HasField(TEXT("walk"))?TEXT("walk"):TEXT("idle");
    const float PlayRate=Local&&Key==TEXT("walk_back")&&MovementKeys&&PlayerPawn?MovementKeys->BackwardRate((*Row)->GetIntegerField(TEXT("model_id")),PlayerPawn->GetVelocity().Size2D()/100):1.f;
    Mesh->SetPlayRate(Reverse?-PlayRate:PlayRate);
    const FString StateKey=Reverse?TEXT("sit_down_reverse"):Key;
    const bool NewAction=Action&&Pose.PlayedActionSeq!=Pose.ActiveActionSeq;
    const bool NewCast=SpellPose&&Pose.PlayedCastSeq!=SpellSeq;
    if(AnimationStates.FindRef(Id)==StateKey&&!NewAction&&!NewCast){
        // Off-screen skeletal components pause their own animation ticks. Keep
        // authoritative death age so looking back does not replay an old death.
        if(Dead)if(auto* Animation=Clip(Key))if(auto* Instance=Mesh->GetSingleNodeInstance()){
            const float At=FMath::Clamp(float(Now-Pose.DiedAt),0.f,Animation->GetPlayLength());if(!FMath::IsNearlyEqual(Instance->GetCurrentTime(),At,.001f))Mesh->SetPosition(At,false);
        }
        if(Action)if(auto* Animation=Clip(Key))if(auto* Instance=Mesh->GetSingleNodeInstance()){
            const float At=FMath::Clamp(float(Now-Pose.ActionStartedAt),0.f,Animation->GetPlayLength());if(!FMath::IsNearlyEqual(Instance->GetCurrentTime(),At,.001f))Mesh->SetPosition(At,false);
        }
        if(SpellPose)Mesh->SetPosition(float(SpellAt),false);
        return;
    }
    if(auto* Animation=Clip(Key)){
        Mesh->PlayAnimation(Animation,Loop);Mesh->SetPlayRate(Reverse?-PlayRate:PlayRate);if(Reverse)Mesh->SetPosition(Animation->GetPlayLength(),false);
        if(Dead)Mesh->SetPosition(FMath::Clamp(float(Now-Pose.DiedAt),0.f,Animation->GetPlayLength()),false);
        if(Action){Mesh->SetPosition(FMath::Clamp(float(Now-Pose.ActionStartedAt),0.f,Animation->GetPlayLength()),false);Pose.PlayedActionSeq=Pose.ActiveActionSeq;}
        if(SpellPose){Mesh->SetPosition(float(SpellAt),false);Pose.PlayedCastSeq=SpellSeq;}
        AnimationStates.Add(Id,StateKey);
    }else{
        // An absent death/posture clip must not restart a living idle animation.
        Mesh->Stop();AnimationStates.Add(Id,StateKey);
    }
}
