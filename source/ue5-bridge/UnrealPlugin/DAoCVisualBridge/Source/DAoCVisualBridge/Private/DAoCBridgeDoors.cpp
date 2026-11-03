#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
namespace {
FVector DoorPoint(const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
}
void UDAoCBridgeSubsystem::SetupDoors(UStaticMeshComponent* Source,const TSharedPtr<FJsonObject>& Record){
    const TArray<TSharedPtr<FJsonValue>>* Fixtures;const TArray<TSharedPtr<FJsonValue>>* Leaves;
    if(!Record->TryGetArrayField(TEXT("door_fixtures"),Fixtures)||!Record->TryGetArrayField(TEXT("door_leaves"),Leaves))return;
    for(const auto& Value:*Fixtures){
        auto Fixture=Value->AsObject();FString Component=Fixture->GetStringField(TEXT("component"));
        FString Suffix=Component.Mid(Component.Find(TEXT(":PersistentLevel.")));
        const FVector P=DoorPoint(Fixture->GetArrayField(TEXT("position_m")));const FVector Centre((P.X-1364)*100,(P.Z-1263)*100,(P.Y-130)*100);
        if(!Source->GetPathName().EndsWith(Suffix)&&!Source->Bounds.GetBox().ExpandBy(50).IsInsideOrOn(Centre))continue;
        auto Groups=Fixture->GetObjectField(TEXT("groups"));
        for(const auto& Item:*Leaves){
            auto Leaf=Item->AsObject();const int64 Id=int64(Groups->GetNumberField(Leaf->GetStringField(TEXT("group"))));
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Leaf->GetStringField(TEXT("asset")));if(!Mesh)continue;
            FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Actor=GetWorld()->SpawnActor<AStaticMeshActor>(FVector::ZeroVector,FRotator::ZeroRotator,Params);Actor->Tags.Add(TEXT("DAoCBridgeDoor"));
            auto* Body=Actor->GetStaticMeshComponent();Body->SetMobility(EComponentMobility::Movable);Body->SetStaticMesh(Mesh);
            Body->SetCollisionProfileName(TEXT("BlockAll"));Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Body->SetCanEverAffectNavigation(false);Body->SetCullDistance(35000);
            FDoorLeaf State;State.Actor=Actor;State.Source=Source;State.Seconds=Leaf->GetNumberField(TEXT("seconds"));
            State.Closed=FTransform(FQuat::Identity,DoorPoint(Leaf->GetArrayField(TEXT("pivot_cm"))))*Source->GetComponentTransform();
            const auto& Q=Leaf->GetArrayField(TEXT("open_quat"));
            State.Opened=FTransform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),DoorPoint(Leaf->GetArrayField(TEXT("open_pivot_cm"))))*Source->GetComponentTransform();
            Actor->SetActorTransform(State.Closed);auto& Group=Doors.FindOrAdd(Id);Group.Leaves.Add(State);
            Group.Centre=Centre;
        }
    }
}
void UDAoCBridgeSubsystem::TickDoors(float Dt){
    for(auto It=Doors.CreateIterator();It;++It){It.Value().Leaves.RemoveAll([](const FDoorLeaf& Leaf){if(Leaf.Source.IsStale()){if(Leaf.Actor.IsValid())Leaf.Actor->Destroy();return true;}return !Leaf.Actor.IsValid();});if(It.Value().Leaves.IsEmpty())It.RemoveCurrent();}
    for(auto& Pair:Doors){auto& Group=Pair.Value;
        const float Seconds=Group.Leaves.Num()?FMath::Max(.1f,Group.Leaves[0].Seconds):1.f;
        const float NextAlpha=FMath::FInterpConstantTo(Group.Alpha,Group.Open?1.f:0.f,Dt,1.f/Seconds);
        bool Occupied=false;
        if(!Group.Open&&Group.Alpha>0){
            for(const auto& Leaf:Group.Leaves)if(auto* Actor=Leaf.Actor.Get()){
                const FBox Box=Actor->GetStaticMeshComponent()->GetStaticMesh()->GetBoundingBox().TransformBy(Leaf.Closed.ToMatrixWithScale());
                FTransform Next;Next.Blend(Leaf.Closed,Leaf.Opened,NextAlpha);
                const FBox NextBox=Actor->GetStaticMeshComponent()->GetStaticMesh()->GetBoundingBox().TransformBy(Next.ToMatrixWithScale());
                for(TActorIterator<ADAoCBridgeCharacter> It(GetWorld());It;++It)if(It->GetActorEnableCollision()){
                    auto* Capsule=It->GetCapsuleComponent();const FVector Extent(Capsule->GetScaledCapsuleRadius()+5,Capsule->GetScaledCapsuleRadius()+5,Capsule->GetScaledCapsuleHalfHeight()+5);
                    if(Box.ExpandBy(Extent).IsInside(It->GetActorLocation())||NextBox.ExpandBy(Extent).IsInside(It->GetActorLocation())){Occupied=true;break;}
                }
            }
        }
        if(Occupied)continue;
        Group.Alpha=NextAlpha;
        for(const auto& Leaf:Group.Leaves)if(auto* Actor=Leaf.Actor.Get()){
            FTransform T;T.Blend(Leaf.Closed,Leaf.Opened,Group.Alpha);Actor->SetActorTransform(T,false,nullptr,ETeleportType::TeleportPhysics);
        }
    }
}
bool UDAoCBridgeSubsystem::RequestDoor(int64 Id,bool Open){
    auto* Door=Doors.Find(Id);if(!Door||Session.IsEmpty()||bExiting||FVector::Dist2D(PlayerPosition,Door->Centre)>400||FMath::Abs(PlayerPosition.Z-Door->Centre.Z)>400)return false;
    auto Values=MakeShared<FJsonObject>();Values->SetNumberField(TEXT("door_id"),double(Id));Values->SetBoolField(TEXT("open"),Open);Send(TEXT("door"),Values);++DoorRequests;return true;
}
bool UDAoCBridgeSubsystem::InteractDoor(){
    int64 Best=0;double Distance=300;
    for(auto& Pair:Doors){double D=FVector::Dist2D(PlayerPosition,Pair.Value.Centre);if(D<Distance&&FMath::Abs(PlayerPosition.Z-Pair.Value.Centre.Z)<400){Best=Pair.Key;Distance=D;}}
    if(auto* Door=Doors.Find(Best)){
        // Ardee's unregistered decorative doors are opened temporarily by the
        // server. A close request creates another temporary open door there.
        // Leave closing to DoorState, which also handles registered doors.
        if(Door->Open)return true;return RequestDoor(Best,true);
    }
    return false;
}
bool UDAoCBridgeSubsystem::ClickDoor(FVector2D ScreenPoint){
    auto* PC=GetWorld()->GetFirstPlayerController();FVector Origin,Direction;
    if(!PC||!PC->DeprojectScreenPositionToWorld(ScreenPoint.X,ScreenPoint.Y,Origin,Direction))return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeDoorClick),true);if(PlayerPawn)Query.AddIgnoredActor(PlayerPawn);
    FHitResult Hit;if(!GetWorld()->LineTraceSingleByChannel(Hit,Origin,Origin+Direction*5000,ECC_Visibility,Query))return false;
    for(auto& Pair:Doors)for(const auto& Leaf:Pair.Value.Leaves)if(Leaf.Actor.Get()==Hit.GetActor())return Pair.Value.Open||RequestDoor(Pair.Key,true);
    return false;
}
void UDAoCBridgeSubsystem::UpdateDoorTest(float Elapsed,FVector& Desired){
    int64 Id=0;double Best=10000;for(const auto& Pair:Doors){double D=FVector::Dist2D(StartPosition,Pair.Value.Centre);if(D<Best){Id=Pair.Key;Best=D;}}
    const float Times[]={8,18};
    for(uint32 I=0;I<2;++I)if(Elapsed>=Times[I]&&!(DoorTestCommands&(1u<<I)))if(RequestDoor(Id,true))DoorTestCommands|=1u<<I;
    Desired=FVector::ZeroVector;float Forward=-1;
    if((Elapsed>=6&&Elapsed<8)||(Elapsed>=10&&Elapsed<13))Forward=650;
    if((Elapsed>=16&&Elapsed<18)||(Elapsed>=20&&Elapsed<23))Forward=0;
    if(Forward>=0){const FVector Delta=StartPosition+FRotator(0,CameraYaw,0).Vector()*Forward-PlayerPosition;const float Distance=Delta.Size2D();
        if(Distance>12)Desired=FVector(Delta.X,Delta.Y,0).GetSafeNormal()*FMath::Clamp(Distance/90.f,.12f,1.f);
    }
}
