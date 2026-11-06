#include "DAoCBridgeTargetTracking.h"
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovementKeys.h"
#include "Dom/JsonObject.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace {
bool TrackTarget(const TMap<FString,TSharedPtr<FJsonObject>>& Rows,const TMap<FString,TObjectPtr<AActor>>& Actors,const FString& Id,FVector& Position){
    const auto* Row=Rows.Find(Id);const auto* Actor=Actors.Find(Id);if(!Row||!Actor||!IsValid(*Actor)||Id==TEXT("player:local"))return false;
    double Health=1;(*Row)->TryGetNumberField(TEXT("health"),Health);bool Targetable=true;(*Row)->TryGetBoolField(TEXT("targetable"),Targetable);
    if(!FMath::IsFinite(Health)||Health<=0||!Targetable)return false;Position=(*Actor)->GetActorLocation();return !Position.ContainsNaN();
}
}
void UDAoCBridgeSubsystem::RequestTargetTracking(const FString& Mode){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting||!PlayerCanMove())return;
    auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("mode"),Mode);Send(TEXT("tracking_request"),V);
}
void UDAoCBridgeSubsystem::TrackingFeedback(const FString& Result){
    if(!TargetTracking||TargetTracking->Sequence<1||TargetTracking->EntityId.IsEmpty())return;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("request_seq"),TargetTracking->Sequence);V->SetStringField(TEXT("target_entity_id"),TargetTracking->EntityId);V->SetStringField(TEXT("result"),Result);Send(TEXT("tracking_feedback"),V);
}
void UDAoCBridgeSubsystem::ApplyTargetTracking(const TSharedPtr<FJsonObject>& Snapshot){
    const TSharedPtr<FJsonObject>* Value=nullptr;if(!Snapshot->TryGetObjectField(TEXT("target_tracking"),Value))return;
    double Seq=0,Age=0;FString Mode,Id,Name;
    if(!(*Value)->TryGetNumberField(TEXT("request_seq"),Seq)||!FMath::IsFinite(Seq)||Seq<1||Seq>9e15||FMath::FloorToDouble(Seq)!=Seq||!(*Value)->TryGetStringField(TEXT("mode"),Mode)||!(*Value)->TryGetStringField(TEXT("target_entity_id"),Id)||Id.Len()>128||!(*Value)->TryGetStringField(TEXT("target_name"),Name)||Name.Len()>128)return;
    if(!TargetTracking)TargetTracking=MakeShared<FBridgeTargetTracking>();if(int64(Seq)<=TargetTracking->Sequence)return;
    FVector Position;const bool Valid=bLocalAvailable&&PlayerCanMove()&&TrackTarget(EntityRows,Entities,Id,Position)&&(*Value)->TryGetNumberField(TEXT("age_ms"),Age)&&FMath::IsFinite(Age)&&Age>=0&&Age<=5000;
    const bool Started=TargetTracking->Begin(int64(Seq),Mode,Id,Name,PlayerPosition,Position,Valid);
    if(Started&&MovementKeys)MovementKeys->RunLock=false;
    if(!Mode.IsEmpty())TrackingFeedback(Started?TEXT("started"):TEXT("rejected"));
}
bool UDAoCBridgeSubsystem::UpdateTargetTracking(bool Enabled,bool Manual,FVector& Desired){
    if(!TargetTracking||!TargetTracking->Active||!PlayerPawn)return false;
    FVector Position,Facing;const bool Valid=TrackTarget(EntityRows,Entities,TargetTracking->EntityId,Position);
    if(!TargetTracking->Advance(PlayerPawn->FeetPosition(),Position,Valid,Enabled,Manual,Desired,Facing)){TrackingFeedback(TEXT("stopped"));return false;}
    if(!Facing.IsNearlyZero())PlayerPawn->SetActorRotation(FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Facing.Y,Facing.X)),0));
    if(Desired.IsNearlyZero()){auto* Move=PlayerPawn->GetCharacterMovement();Move->Velocity.X=0;Move->Velocity.Y=0;}
    return true;
}
void UDAoCBridgeSubsystem::StopTargetTracking(bool Notify){
    if(!TargetTracking||!TargetTracking->Active)return;TargetTracking->Stop(TEXT("reset"));if(Notify)TrackingFeedback(TEXT("stopped"));
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::TargetTrackingReport()const{
    auto O=MakeShared<FJsonObject>();if(TargetTracking){O->SetNumberField(TEXT("request_seq"),TargetTracking->Sequence);O->SetStringField(TEXT("mode"),TargetTracking->Mode);O->SetStringField(TEXT("target_entity_id"),TargetTracking->EntityId);O->SetBoolField(TEXT("active"),TargetTracking->Active);O->SetStringField(TEXT("stop_reason"),TargetTracking->StopReason);}return O;
}
