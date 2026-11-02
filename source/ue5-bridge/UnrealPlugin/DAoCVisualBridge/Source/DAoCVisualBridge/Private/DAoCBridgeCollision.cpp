#include "DAoCBridgeSubsystem.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Dom/JsonObject.h"
#include "DAoCBridgeCharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UDAoCBridgeSubsystem::ConfigureCollisions(){
    if(bCollisionConfigured)return;bCollisionConfigured=true;
    struct FSource{TWeakObjectPtr<UStaticMeshComponent> Component;FString Asset;bool Visible;};
    TArray<FSource> Sources;
    for(TActorIterator<AActor> It(GetWorld());It;++It){
        TInlineComponentArray<UStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* C:Components){
            UStaticMesh* Mesh=C->GetStaticMesh();if(!Mesh)continue;
            Sources.Add({C,Mesh->GetPathName(),!It->IsHidden()&&C->IsVisible()&&!C->bHiddenInGame});
            // The scene's sky, water, old proxies and visual foliage must not
            // become solid volumes. This private layer owns gameplay queries.
            C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
        }
    }
    FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto MakeActor=[&](){AActor* A=GetWorld()->SpawnActor<AActor>(FVector::ZeroVector,FRotator::ZeroRotator,Params);A->Tags.Add(TEXT("DAoCBridgeCollision"));A->SetActorHiddenInGame(true);return A;};
    for(const auto& Source:Sources){
        UStaticMeshComponent* C=Source.Component.Get();auto* Record=NavigationMeshes.Find(Source.Asset);
        if(!C||!Source.Visible||!Record)continue;
        FString VisualAsset;if((*Record)->TryGetStringField(TEXT("visual_asset"),VisualAsset)){
            if(auto* Visual=LoadObject<UStaticMesh>(nullptr,*VisualAsset)){if(!C->SetStaticMesh(Visual)){C->UnregisterComponent();C->SetStaticMesh(Visual);C->RegisterComponent();}}
            SetupDoors(C,*Record);
        }
        FString Kind,Shape;(*Record)->TryGetStringField(TEXT("kind"),Kind);(*Record)->TryGetStringField(TEXT("shape"),Shape);
        TArray<FTransform> Transforms;
        if(auto* Instances=Cast<UInstancedStaticMeshComponent>(C)){
            Transforms.Reserve(Instances->GetInstanceCount());for(int32 I=0;I<Instances->GetInstanceCount();++I){FTransform T;if(Instances->GetInstanceTransform(I,T,true))Transforms.Add(T);}
        }else Transforms.Add(C->GetComponentTransform());
        if(Transforms.IsEmpty())continue;
        if(Shape==TEXT("capsule")){
            double Radius=20,Half=150,Base=0;(*Record)->TryGetNumberField(TEXT("radius_cm"),Radius);(*Record)->TryGetNumberField(TEXT("half_height_cm"),Half);(*Record)->TryGetNumberField(TEXT("base_z_cm"),Base);
            for(const auto& T:Transforms){
                AActor* A=MakeActor();auto* Capsule=NewObject<UCapsuleComponent>(A);A->SetRootComponent(Capsule);
                Capsule->InitCapsuleSize(FMath::Clamp(Radius,5.,300.),FMath::Max(Half,Radius));
                Capsule->ComponentTags.Add(TEXT("DAoCBridgeTree"));Capsule->CanCharacterStepUpOn=ECB_No;
                Capsule->SetWorldTransform(T);Capsule->AddLocalOffset(FVector(0,0,Base+Half));Capsule->SetCollisionProfileName(TEXT("BlockAll"));
                Capsule->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Capsule->SetCanEverAffectNavigation(false);Capsule->RegisterComponent();++TreeColliderInstances;
            }
            continue;
        }
        FString Asset;if(!(*Record)->TryGetStringField(TEXT("asset"),Asset))continue;
        UStaticMesh* Mesh=LoadObject<UStaticMesh>(nullptr,*Asset);if(!Mesh)continue;
        if(Kind==TEXT("tree")){
            AActor* A=MakeActor();auto* Instances=NewObject<UInstancedStaticMeshComponent>(A);A->SetRootComponent(Instances);
            Instances->ComponentTags.Add(TEXT("DAoCBridgeTree"));Instances->CanCharacterStepUpOn=ECB_No;
            Instances->SetStaticMesh(Mesh);Instances->SetCollisionProfileName(TEXT("BlockAll"));Instances->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Instances->SetVisibility(false);Instances->SetCastShadow(false);Instances->SetCanEverAffectNavigation(false);
            Instances->AddInstances(Transforms,false,true,false);Instances->RegisterComponent();TreeColliderInstances+=Transforms.Num();
        }else{
            for(const auto& T:Transforms){
                auto* A=GetWorld()->SpawnActor<AStaticMeshActor>(FVector::ZeroVector,FRotator::ZeroRotator,Params);A->Tags.Add(TEXT("DAoCBridgeCollision"));
                auto* Body=A->GetStaticMeshComponent();Body->SetMobility(EComponentMobility::Movable);Body->SetStaticMesh(Mesh);Body->SetWorldTransform(T);
                Body->CanCharacterStepUpOn=ECB_Yes;
                Body->SetCollisionProfileName(TEXT("BlockAll"));Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Body->SetCanEverAffectNavigation(false);
                Body->SetCastShadow(false);Body->SetVisibility(false);A->SetActorHiddenInGame(true);Body->SetMobility(EComponentMobility::Static);
                if(Kind==TEXT("terrain")){Body->ComponentTags.Add(TEXT("DAoCBridgeTerrain"));++TerrainColliders;}else ++StructureColliders;
                const TArray<TSharedPtr<FJsonValue>>* Parts;
                if((*Record)->TryGetArrayField(TEXT("sub_colliders"),Parts))for(const auto& Value:*Parts){
                    auto Part=Value->AsObject();auto* PartMesh=LoadObject<UStaticMesh>(nullptr,*Part->GetStringField(TEXT("asset")));if(!PartMesh)continue;
                    auto* Extra=GetWorld()->SpawnActor<AStaticMeshActor>(FVector::ZeroVector,FRotator::ZeroRotator,Params);Extra->Tags.Add(TEXT("DAoCBridgeCollision"));
                    auto* ExtraBody=Extra->GetStaticMeshComponent();ExtraBody->SetMobility(EComponentMobility::Movable);ExtraBody->SetStaticMesh(PartMesh);ExtraBody->SetWorldTransform(T);
                    ExtraBody->CanCharacterStepUpOn=ECB_Yes;ExtraBody->SetCollisionProfileName(TEXT("BlockAll"));ExtraBody->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
                    ExtraBody->SetWalkableSlopeOverride(FWalkableSlopeOverride(WalkableSlope_Increase,FMath::Clamp(float(Part->GetNumberField(TEXT("walkable_angle"))),0.f,65.f)));
                    ExtraBody->SetCanEverAffectNavigation(false);ExtraBody->SetCastShadow(false);ExtraBody->SetVisibility(false);Extra->SetActorHiddenInGame(true);ExtraBody->SetMobility(EComponentMobility::Static);++StructureColliders;
                }
            }
        }
    }
    bNavigationReady=TerrainColliders>0;
}

// Opt-in, read-only queries against the actual private collision geometry.
// This is a smoke test; it does not certify every doorway or every tree.
void UDAoCBridgeSubsystem::ProbeNavigation(){
    if(bNavigationProbed||!PlayerPawn||!FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeNavigationProbe")))return;
    bNavigationProbed=true;NavigationProbe=MakeShared<FJsonObject>();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeNavigation),false,PlayerPawn);
    FHitResult Floor;const FVector Feet=PlayerPawn->FeetPosition();
    const bool FloorHit=GetWorld()->LineTraceSingleByChannel(Floor,Feet+FVector(0,0,50),Feet-FVector(0,0,100),ECC_Pawn,Query);
    NavigationProbe->SetBoolField(TEXT("floor_hit"),FloorHit&&Floor.GetActor()&&Floor.GetActor()->ActorHasTag(TEXT("DAoCBridgeCollision")));
    NavigationProbe->SetBoolField(TEXT("grounded"),PlayerPawn->GetCharacterMovement()->IsMovingOnGround());
    int32 StructureHits=0,TreeHits=0,CapsuleHits=0,CameraHits=0;auto NewTreeHits=MakeShared<FJsonObject>();
    for(TActorIterator<AActor> It(GetWorld());It;++It){
        if(!It->ActorHasTag(TEXT("DAoCBridgeCollision")))continue;
        TInlineComponentArray<UStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* C:Components){
            UStaticMesh* Mesh=C->GetStaticMesh();if(!Mesh||Mesh->GetName().Contains(TEXT("Terrain")))continue;
            const bool Tree=Cast<UInstancedStaticMeshComponent>(C)!=nullptr;
            TArray<FTransform> Transforms;
            if(auto* Inst=Cast<UInstancedStaticMeshComponent>(C)){for(int32 I=0;I<Inst->GetInstanceCount();++I){FTransform T;if(Inst->GetInstanceTransform(I,T,true))Transforms.Add(T);}}
            else Transforms.Add(C->GetComponentTransform());
            for(const auto& T:Transforms){
                const FBox Box=Mesh->GetBoundingBox().TransformBy(T.ToMatrixWithScale());
                bool HitThis=false;
                for(int32 Axis=0;Axis<2&&!HitThis;++Axis)for(int32 Slice=0;Slice<4&&!HitThis;++Slice){
                    FVector A=Box.GetCenter(),Z=A;A.Z=Z.Z=Box.Min.Z+FMath::Min(150.,double(Box.GetSize().Z*.5));
                    const int32 Cross=1-Axis;A[Cross]=Z[Cross]=Slice==3?T.GetLocation()[Cross]:FMath::Lerp(Box.Min[Cross],Box.Max[Cross],.25f+.25f*Slice);
                    A[Axis]=Box.Min[Axis]-100;Z[Axis]=Box.Max[Axis]+100;
                    FHitResult Hit;if(!C->LineTraceComponent(Hit,A,Z,Query))continue;
                    HitThis=true;if(Tree){++TreeHits;if(Mesh->GetPathName().Contains(TEXT("NavigationCollision_v02"))){double Count=0;NewTreeHits->TryGetNumberField(Mesh->GetPathName(),Count);NewTreeHits->SetNumberField(Mesh->GetPathName(),Count+1);}}else ++StructureHits;
                    FHitResult Swept;
                    if(GetWorld()->SweepSingleByChannel(Swept,A,Z,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(28,88),Query))++CapsuleHits;
                    if(GetWorld()->SweepSingleByChannel(Swept,A,Z,FQuat::Identity,ECC_Camera,FCollisionShape::MakeSphere(12),Query))++CameraHits;
                }
            }
        }
    }
    NavigationProbe->SetObjectField(TEXT("new_tree_instances_blocked"),NewTreeHits);
    NavigationProbe->SetNumberField(TEXT("structure_samples_blocked"),StructureHits);
    NavigationProbe->SetNumberField(TEXT("trunk_samples_blocked"),TreeHits);
    NavigationProbe->SetNumberField(TEXT("capsule_sweeps_blocked"),CapsuleHits);
    NavigationProbe->SetNumberField(TEXT("camera_sweeps_blocked"),CameraHits);
    NavigationProbe->SetBoolField(TEXT("passed"),FloorHit&&PlayerPawn->GetCharacterMovement()->IsMovingOnGround()&&StructureHits>0&&TreeHits>0&&CapsuleHits>0&&CameraHits>0);
}
