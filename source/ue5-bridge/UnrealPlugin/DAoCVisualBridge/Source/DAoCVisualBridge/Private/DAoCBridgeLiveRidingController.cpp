#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeLiveRiding.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovementKeys.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Misc/CommandLine.h"
#include "Dom/JsonObject.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameViewportClient.h"
#include "HAL/FileManager.h"
namespace {bool RidingSpaceKeySent=false;int32 RidingKeyReleaseFrames=0;}
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequenceBase.h"

void UDAoCBridgeSubsystem::ClearLiveRiding(){
    const bool WasMounted=bLocalMounted;bLocalMounted=false;bLocalSeatReady=false;LocalSteedId.Empty();RidingState.Reset();RidingRevision=-1;RidingSpeedMps=0;LastDismountRequest=-100;
    if(WasMounted&&PlayerPawn&&bNavigationReady){PlayerPawn->SetActorEnableCollision(true);if(!PlayerIsDead())PlayerPawn->GetCharacterMovement()->SetMovementMode(MOVE_Falling);PlayerPawn->PendingLandingSpeedMps=0;}
}
void UDAoCBridgeSubsystem::ApplyLiveRiding(const TSharedPtr<FJsonObject>& Snapshot){
    const TSharedPtr<FJsonObject>* Value=nullptr;if(!Snapshot->TryGetObjectField(TEXT("riding"),Value)){if(bLocalMounted)ClearLiveRiding();return;}
    double Revision=0;bool Mounted=false,Ready=false;FString Id;const TArray<TSharedPtr<FJsonValue>>* Remote=nullptr;
    if(!(*Value)->TryGetNumberField(TEXT("revision"),Revision)||!FMath::IsFinite(Revision)||Revision<0||Revision>9e15||FMath::FloorToDouble(Revision)!=Revision||Revision<RidingRevision||!(*Value)->TryGetBoolField(TEXT("mounted"),Mounted)||!(*Value)->TryGetBoolField(TEXT("steed_ready"),Ready)||!(*Value)->TryGetStringField(TEXT("steed_entity_id"),Id)||Id.Len()>128||!(*Value)->TryGetArrayField(TEXT("remote"),Remote)||Remote->Num()>128)return;
    if(Mounted&&Ready&&(!Id.StartsWith(TEXT("npc:"))||Id==TEXT("player:local")))return;
    const bool Changed=bLocalMounted!=Mounted||LocalSteedId!=Id;
    if(!Mounted&&bLocalMounted)ClearLiveRiding();
    RidingRevision=int64(Revision);RidingState=*Value;bLocalMounted=Mounted;LocalSteedId=Ready?Id:FString();
    if(Changed){bLocalSeatReady=false;LastDismountRequest=-100;StopTargetTracking(true);if(MovementKeys)MovementKeys->RunLock=false;}
}
void UDAoCBridgeSubsystem::RequestDismount(){
    const double Now=FPlatformTime::Seconds();if(!bLocalMounted||Session.IsEmpty()||bExiting||Now-LastDismountRequest<1.5)return;
    Send(TEXT("dismount"));LastDismountRequest=Now;
}
void UDAoCBridgeSubsystem::TickLiveRiding(float DeltaTime){
    if(!RidingState.IsValid())return;
    FString KeyRequest;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRidingSpaceRequest="),KeyRequest))if(auto* PC=GetWorld()->GetFirstPlayerController()){
        auto* View=GetWorld()->GetGameViewport();
        if(RidingKeyReleaseFrames>0&&--RidingKeyReleaseFrames==0)PC->InputKey(FInputKeyEventArgs(View?View->Viewport:nullptr,FInputDeviceId::CreateFromInternalId(0),EKeys::SpaceBar,IE_Released,FPlatformTime::Cycles64()));
        if(bLocalMounted&&bLocalSeatReady&&!RidingSpaceKeySent&&IFileManager::Get().FileExists(*KeyRequest)){
            PC->InputKey(FInputKeyEventArgs(View?View->Viewport:nullptr,FInputDeviceId::CreateFromInternalId(0),EKeys::SpaceBar,IE_Pressed,FPlatformTime::Cycles64()));RidingSpaceKeySent=true;RidingKeyReleaseFrames=2;
        }
    }

    if(!RidingData){RidingData=MakeShared<FBridgeLiveRidingData>();FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/LiveRiding_v01/riding.json");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRidingCatalog="),Path);RidingData->Load(Path);}
    auto Seat=[&](const FString& Id,FVector& Point,FRotator& Facing)->bool{
        auto* Found=Entities.Find(Id);auto* Row=EntityRows.Find(Id);if(!Found||!Row||!IsValid(*Found))return false;
        auto* Horse=Cast<ASkeletalMeshActor>(*Found);double Health=1,Model=0;if(!Horse||!(*Row)->TryGetNumberField(TEXT("model_id"),Model)||!FMath::IsFinite(Model))return false;
        (*Row)->TryGetNumberField(TEXT("health"),Health);if(!FMath::IsFinite(Health)||Health<=0)return false;
        auto* Mesh=Horse->GetSkeletalMeshComponent();Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        if(!RidingData->Resolve(Mesh,int32(Model),Point))return false;
        // Catalog yaw offsets are already applied to every imported entity.
        if(auto* Motion=RemoteMotion.Find(Id))if(auto* Instance=Mesh->GetSingleNodeInstance())if(auto* Clip=Cast<UAnimSequenceBase>(Instance->GetCurrentAsset())){
            const double Speed=Motion->ForecastActive(FPlatformTime::Seconds())?FMath::Min(37.5,Motion->Speed/100):0;
            Mesh->SetPlayRate(RidingData->GaitRate(int32(Model),AnimationStates.FindRef(Id),Speed,Clip->GetPlayLength(),Mesh->GetComponentScale().GetAbsMax()));
        }
        Facing=Horse->GetActorRotation();return true;
    };
    if(bLocalMounted&&PlayerPawn&&!PlayerIsDead()){
        PlayerPawn->ConsumeMovementInputVector();PlayerPawn->GetCharacterMovement()->DisableMovement();PlayerPawn->SetActorEnableCollision(false);PlayerPawn->PendingLandingSpeedMps=0;
        FVector Point;FRotator Rotation;double Slot=-1;RidingState->TryGetNumberField(TEXT("slot"),Slot);bLocalSeatReady=Slot==0&&Seat(LocalSteedId,Point,Rotation);RidingSpeedMps=0;
        if(bLocalSeatReady){
            PlayerPawn->SetActorLocation(Point+FVector(0,0,PlayerPawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);
            PlayerPawn->SetActorRotation(FRotator(0,Rotation.Yaw+90,0));
            if(auto* Motion=RemoteMotion.Find(LocalSteedId))RidingSpeedMps=Motion->ForecastActive(FPlatformTime::Seconds())?FMath::Min(37.5,Motion->Speed/100):0;
            FString Capture;static int32 CaptureFrames=0;
            if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRidingCapture="),Capture)&&++CaptureFrames==20)FScreenshotRequest::RequestScreenshot(Capture,true,false);
        }else if(!LocalSteedId.IsEmpty())RequestDismount();
    }
    const TArray<TSharedPtr<FJsonValue>>* Remote=nullptr;if(!RidingState->TryGetArrayField(TEXT("remote"),Remote))return;
    for(auto& Pair:EntityRows)Pair.Value->RemoveField(TEXT("riding_steed_entity_id"));
    for(const auto& Value:*Remote){
        if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();FString Rider,Steed;
        double Slot=-1;if(!Row->TryGetNumberField(TEXT("slot"),Slot)||Slot!=0)continue;
        if(!Row->TryGetStringField(TEXT("rider_entity_id"),Rider)||!Row->TryGetStringField(TEXT("steed_entity_id"),Steed)||Rider==TEXT("player:local")||Rider==Steed||Rider.Len()>128||Steed.Len()>128)continue;
        auto* Found=Entities.Find(Rider);auto* Data=EntityRows.Find(Rider);FVector Point;FRotator Rotation;
        if(!Found||!Data||!IsValid(*Found)||!Seat(Steed,Point,Rotation))continue;
        (*Data)->SetStringField(TEXT("riding_steed_entity_id"),Steed);(*Found)->SetActorLocation(Point);(*Found)->SetActorRotation(Rotation);SetEntityAnimation(Rider,TEXT("ride_horse"));
    }
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::LiveRidingReport()const{
    auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("qa_space_key_sent"),RidingSpaceKeySent);R->SetBoolField(TEXT("mounted"),bLocalMounted);R->SetBoolField(TEXT("seat_ready"),bLocalSeatReady);R->SetStringField(TEXT("steed_entity_id"),LocalSteedId);R->SetNumberField(TEXT("revision"),RidingRevision);R->SetNumberField(TEXT("speed_mps"),RidingSpeedMps);return R;
}
