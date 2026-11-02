#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Animation/AnimationAsset.h"

namespace {
bool MotionPoint(const TSharedPtr<FJsonObject>& O,const TCHAR* Key,FVector& Out){
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;if(!O->TryGetArrayField(Key,Values)||Values->Num()!=3)return false;
    double P[3];for(int I=0;I<3;++I)if(!(*Values)[I]->TryGetNumber(P[I])||!FMath::IsFinite(P[I])||FMath::Abs(P[I])>100000)return false;
    Out=FVector((P[0]-1364)*100,(P[2]-1263)*100,(P[1]-130)*100);return true;
}
bool RemoteFloor(UWorld* World,AActor* Actor,AActor* Player,const FVector& Feet,FHitResult& Floor,FBridgeRemoteMotion& Motion){
    FCollisionQueryParams Q(SCENE_QUERY_STAT(BridgeRemoteFloor),true);Q.AddIgnoredActor(Actor);if(Player)Q.AddIgnoredActor(Player);
    for(int32 I=0;I<6;++I){FHitResult Hit;if(!World->LineTraceSingleByChannel(Hit,Feet+FVector(0,0,45),Feet-FVector(0,0,120),ECC_Pawn,Q))return false;
        auto* C=Hit.GetComponent();if(C&&C->ComponentHasTag(TEXT("DAoCBridgeTree"))){Q.AddIgnoredComponent(C);++Motion.RejectedTreeFloors;continue;}
        if(Hit.ImpactNormal.Z>=.64&&Hit.ImpactPoint.Z-Feet.Z<=45){Floor=Hit;return true;}return false;
    }return false;
}
FVector ConstrainRemote(UWorld* World,AActor* Actor,AActor* Player,const FVector& From,FVector To,FBridgeRemoteMotion& Motion){
    FCollisionQueryParams Q(SCENE_QUERY_STAT(BridgeRemoteBody),true);Q.AddIgnoredActor(Actor);if(Player)Q.AddIgnoredActor(Player);
    double Radius=20,Half=80;if(auto* Root=Cast<UPrimitiveComponent>(Actor->GetRootComponent())){auto E=Root->Bounds.BoxExtent;Radius=FMath::Clamp(double(FMath::Min(E.X,E.Y))*.7,10.,100.);Half=FMath::Clamp(double(E.Z),Radius,180.);}
    const FVector Offset(0,0,Half+2);const FCollisionShape Shape=FCollisionShape::MakeCapsule(float(Radius),float(Half));
    if(Motion.Grounded){FHitResult Floor;if(RemoteFloor(World,Actor,Player,To,Floor,Motion)){const double Height=Floor.ImpactPoint.Z+Motion.GroundOffset;if(FMath::Abs(Height-From.Z)<=FMath::Clamp(Half*.5,5.,45.))To.Z=Height;else To.Z=From.Z;}else To.Z=From.Z;}
    FHitResult Hit;if(!World->SweepSingleByChannel(Hit,From+Offset,To+Offset,FQuat::Identity,ECC_Pawn,Shape,Q))return To;
    ++Motion.CollisionContacts;Motion.Blocked=true;
    if(Hit.bStartPenetrating)return From;
    const double Distance=FVector::Distance(From,To);FVector Safe=FMath::Lerp(From,To,FMath::Max(0.,double(Hit.Time)-2./FMath::Max(1.,Distance)));
    FVector Rest=To-Safe,Normal=Hit.ImpactNormal.GetSafeNormal2D();FVector Slide=Rest-Normal*FVector::DotProduct(Rest,Normal);Slide.Z=To.Z-Safe.Z;
    if(Slide.SizeSquared()>.01){FHitResult Second;const FVector End=Safe+Slide;if(!World->SweepSingleByChannel(Second,Safe+Offset,End+Offset,FQuat::Identity,ECC_Pawn,Shape,Q))Safe=End;else if(!Second.bStartPenetrating)Safe=FMath::Lerp(Safe,End,FMath::Max(0.,double(Second.Time)-2./FMath::Max(1.,Slide.Size())));}
    Motion.Blocked=Safe.Equals(From,.05);return Safe;
}
}
void UDAoCBridgeSubsystem::ApplyRemoteMotion(const FString& Id,AActor* Actor,TSharedPtr<FJsonObject> Row,const FVector& Position){
    const TSharedPtr<FJsonObject>* Data=nullptr;if(!Row->TryGetObjectField(TEXT("motion"),Data))return;
    double Seq=0,Age=0,Speed=0,Interval=500;
    if(!(*Data)->TryGetNumberField(TEXT("seq"),Seq)||!FMath::IsFinite(Seq)||Seq<0||Seq>9e15)return;
    (*Data)->TryGetNumberField(TEXT("age_ms"),Age);(*Data)->TryGetNumberField(TEXT("speed_mps"),Speed);(*Data)->TryGetNumberField(TEXT("interval_ms"),Interval);
    if(!FMath::IsFinite(Age)||!FMath::IsFinite(Speed)||!FMath::IsFinite(Interval))return;
    const auto& Forward=Row->GetArrayField(TEXT("forward_xz"));const FVector Direction(Forward[0]->AsNumber(),Forward[1]->AsNumber(),0);
    FVector Goal;const bool HasGoal=MotionPoint(*Data,TEXT("destination_m"),Goal);FString State;Row->TryGetStringField(TEXT("state"),State);
    auto& Motion=RemoteMotion.FindOrAdd(Id);
    bool PositionValid=true;(*Data)->TryGetBoolField(TEXT("position_valid"),PositionValid);const FVector SamplePosition=(!PositionValid&&Motion.Initialized)?Motion.Rendered:Position;
    if(Motion.Sample(int64(Seq),FPlatformTime::Seconds(),Age/1000,SamplePosition,Direction,Speed,Interval/1000,HasGoal?&Goal:nullptr,State==TEXT("dead"))){
        const FVector Before=Actor->GetActorLocation();FString Kind;Row->TryGetStringField(TEXT("kind"),Kind);bool Flying=false;Row->TryGetBoolField(TEXT("flying"),Flying);
        Motion.ConstrainToWorld=Kind==TEXT("npc")&&!Motion.Dead;
        Motion.Grounded=false;if(Motion.ConstrainToWorld&&!Flying){FHitResult Floor;if(RemoteFloor(GetWorld(),Actor,PlayerPawn,Position,Floor,Motion)&&FMath::Abs(Position.Z-Floor.ImpactPoint.Z)<=45){Motion.Grounded=true;Motion.GroundOffset=FMath::Clamp(Position.Z-Floor.ImpactPoint.Z,-20.,20.);}}
        if(Motion.ConstrainToWorld&&FVector::Dist(Before,Motion.Rendered)<2500){
            const FVector Safe=ConstrainRemote(GetWorld(),Actor,PlayerPawn,Before,Motion.Rendered,Motion);
            if(!Safe.Equals(Motion.Rendered,.1)){++Motion.BlockedCorrections;Motion.Rendered=Safe;Motion.Correction=Safe-Motion.Predict(FPlatformTime::Seconds());Motion.CorrectionAt=FPlatformTime::Seconds();}
        }
        Actor->SetActorLocation(Motion.Rendered);

    }
}
void UDAoCBridgeSubsystem::TickRemoteMotion(float Dt){
    const double TickBegan=FPlatformTime::Seconds();const double Now=TickBegan;
    for(auto& Pair:RemoteMotion){
        auto* Found=Entities.Find(Pair.Key);if(!Found||!IsValid(*Found))continue;AActor* Actor=Found->Get();auto& Motion=Pair.Value;
        const FVector Previous=Actor->GetActorLocation();const int32 BeforeFrames=Motion.MovingFrames;Motion.Blocked=false;
        FVector Desired=Motion.Tick(Now,Dt);
        // Sweep every displayed correction and prediction. Never project feet onto a tree.
        const double Range=Quality==TEXT("accessible")?6500:Quality==TEXT("balanced")?9500:Quality==TEXT("high")?13000:15500;
        if(Motion.ConstrainToWorld&&FVector::DistSquared(PlayerPosition,Previous)<Range*Range&&!Desired.Equals(Previous,.01))Desired=ConstrainRemote(GetWorld(),Actor,PlayerPawn,Previous,Desired,Motion);
        Motion.Rendered=Desired;Actor->SetActorLocation(Desired);
        if(Desired.Equals(Previous,.05)&&Motion.MovingFrames>BeforeFrames)--Motion.MovingFrames;
        SetEntityAnimation(Pair.Key,Motion.Dead?TEXT("dead"):Motion.ForecastActive(Now)?(Motion.Speed>375?TEXT("run"):TEXT("walk")):TEXT("idle"));
    }
    RemoteMotionLastMs=(FPlatformTime::Seconds()-TickBegan)*1000;RemoteMotionPeakMs=FMath::Max(RemoteMotionPeakMs,RemoteMotionLastMs);
}

void UDAoCBridgeSubsystem::UpdateRemoteMotionProbe(){
    if(RemoteMotionProbePath.IsEmpty()||!bLocalAvailable)return;
    const double Now=FPlatformTime::Seconds();if(PlayerStartedAt==0||Now-PlayerStartedAt<8)return;
    auto* Actor=Entities.Find(RemoteMotionProbeId);
    if(!Actor||!IsValid(*Actor)||Now-RemoteProbeFocusAt>7){
        FString Id;double Best=6000;
        for(auto& Pair:RemoteMotion){auto* Found=Entities.Find(Pair.Key);if(!Found||!IsValid(*Found)||!Pair.Value.ForecastActive(Now))continue;const double Distance=FVector::Dist(PlayerPosition,(*Found)->GetActorLocation());if(Distance<Best){Best=Distance;Id=Pair.Key;}}
        if(Id.IsEmpty())return;RemoteMotionProbeId=Id;RemoteProbeFocusAt=Now;Actor=Entities.Find(Id);SelectEntity(Id);
    }
    auto* Motion=RemoteMotion.Find(RemoteMotionProbeId);if(!Motion)return;
    const FVector Position=(*Actor)->GetActorLocation();const FVector Delta=Position-PlayerPosition;
    CameraYaw=Delta.Rotation().Yaw;CameraPitch=-12;
    if(Now-LastRemoteProbeAt<1/30.||RemoteMotionProbeSamples.Num()>=4000)return;LastRemoteProbeAt=Now;
    auto Sample=MakeShared<FJsonObject>();Sample->SetStringField(TEXT("id"),RemoteMotionProbeId);Sample->SetNumberField(TEXT("time"),Now-PlayerStartedAt);Sample->SetNumberField(TEXT("seq"),Motion->Revision);Sample->SetNumberField(TEXT("speed_mps"),Motion->Speed/100);Sample->SetNumberField(TEXT("age_s"),Now-Motion->SampleAt);Sample->SetNumberField(TEXT("corrections"),Motion->HardCorrections);Sample->SetBoolField(TEXT("active"),Motion->ForecastActive(Now));Sample->SetBoolField(TEXT("blocked"),Motion->Blocked);
    auto Point=[](const FVector& P){return TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(P.X/100),MakeShared<FJsonValueNumber>(P.Y/100),MakeShared<FJsonValueNumber>(P.Z/100)};};Sample->SetArrayField(TEXT("visual_m"),Point(Position));Sample->SetArrayField(TEXT("server_anchor_m"),Point(Motion->Anchor));RemoteMotionProbeSamples.Add(MakeShared<FJsonValueObject>(Sample));
}
