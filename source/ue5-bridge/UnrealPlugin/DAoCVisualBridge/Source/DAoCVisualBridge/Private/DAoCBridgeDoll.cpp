#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"

namespace {
FString DollString(TSharedPtr<FJsonObject> O,const TCHAR* Key){FString S;if(O)O->TryGetStringField(Key,S);return S;}
void DollMaterials(UMeshComponent* From,UMeshComponent* To){
    for(int32 I=0;I<From->GetNumMaterials();++I)To->SetMaterial(I,From->GetMaterial(I));
    To->SetCollisionEnabled(ECollisionEnabled::NoCollision);To->SetCastShadow(false);To->SetCanEverAffectNavigation(false);To->SetGenerateOverlapEvents(false);To->SetVisibleInSceneCaptureOnly(true);
}
}

void UDAoCBridgeSubsystem::UpdateClassicDoll(){
    auto* Found=Entities.Find(TEXT("player:local"));
    auto* Local=Found&&IsValid(*Found)?Cast<ASkeletalMeshActor>(Found->Get()):nullptr;
    if(!Local)return;
    auto* Original=Local->GetSkeletalMeshComponent();if(!Original||!Original->GetSkeletalMeshAsset())return;
    double Revision=0;if(InventoryState)InventoryState->TryGetNumberField(TEXT("state_revision"),Revision);
    const FString Signature=Original->GetSkeletalMeshAsset()->GetPathName()+FString::Printf(TEXT(":%lld:%d"),int64(Revision),Local->GetUniqueID());
    if(!IsValid(ClassicDollActor)||ClassicDollSignature!=Signature){
        if(IsValid(ClassicDollActor))ClassicDollActor->Destroy();
        FActorSpawnParameters P;P.ObjectFlags|=RF_Transient;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Doll=GetWorld()->SpawnActor<ASkeletalMeshActor>(FVector(0,0,-100000),FRotator::ZeroRotator,P);if(!Doll)return;
        ClassicDollActor=Doll;ClassicDollSignature=Signature;Doll->SetActorScale3D(Local->GetActorScale3D());Doll->SetActorEnableCollision(false);
        auto* Body=Doll->GetSkeletalMeshComponent();Body->SetSkeletalMesh(Original->GetSkeletalMeshAsset());Body->SetRelativeTransform(Original->GetRelativeTransform());Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        auto* Definition=ModelCatalog.Find(TEXT("0"));const FString Idle=Definition?DollString(*Definition,TEXT("idle")):TEXT("");
        if(!Idle.IsEmpty())if(auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Idle))Body->PlayAnimation(Clip,false);
        Body->TickAnimation(0,false);Body->RefreshBoneTransforms();Body->bPauseAnims=true;Body->SetComponentTickEnabled(false);DollMaterials(Original,Body);
        TArray<UMeshComponent*> Components;Local->GetComponents(Components);
        for(auto* Source:Components){
            if(Source==Original||!Source->IsVisible())continue;UMeshComponent* Copy=nullptr;
            if(auto* Skel=Cast<USkeletalMeshComponent>(Source)){
                auto* C=NewObject<USkeletalMeshComponent>(Doll);C->SetSkeletalMesh(Skel->GetSkeletalMeshAsset());C->SetAnimationMode(EAnimationMode::AnimationSingleNode);Doll->AddInstanceComponent(C);C->RegisterComponent();
                if(Skel->LeaderPoseComponent.Get()==Original)C->SetLeaderPoseComponent(Body);
                else for(const auto& Pair:LocalEquipment)if(Pair.Value.Component.Get()==Source){
                    const TSharedPtr<FJsonObject>* Clips=nullptr;
                    if(Pair.Value.Descriptor&&Pair.Value.Descriptor->TryGetObjectField(TEXT("animations"),Clips)){
                        const FString ClipPath=DollString(*Clips,TEXT("idle"));if(!ClipPath.IsEmpty())if(auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*ClipPath))C->PlayAnimation(Clip,false);
                    }
                }
                C->TickAnimation(0,false);C->RefreshBoneTransforms();C->bPauseAnims=true;C->SetComponentTickEnabled(false);Copy=C;
            }else if(auto* Rigid=Cast<UStaticMeshComponent>(Source)){
                auto* C=NewObject<UStaticMeshComponent>(Doll);C->SetStaticMesh(Rigid->GetStaticMesh());Doll->AddInstanceComponent(C);C->RegisterComponent();Copy=C;
            }
            if(Copy){Copy->AttachToComponent(Body,FAttachmentTransformRules::KeepRelativeTransform,Source->GetAttachSocketName());Copy->SetRelativeTransform(Source->GetRelativeTransform());DollMaterials(Source,Copy);}
        }
    }
    if(!ClassicCapture){
        ClassicCaptureActor=GetWorld()->SpawnActor<AActor>();ClassicCapture=NewObject<USceneCaptureComponent2D>(ClassicCaptureActor);ClassicCaptureActor->SetRootComponent(ClassicCapture);ClassicCapture->RegisterComponent();
        ClassicCapture->bCaptureEveryFrame=false;ClassicCapture->bCaptureOnMovement=false;ClassicCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;ClassicCapture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;ClassicCapture->FOVAngle=40;
        ClassicCapture->ShowFlags.SetAtmosphere(false);ClassicCapture->ShowFlags.SetFog(false);ClassicCapture->ShowFlags.SetMotionBlur(false);ClassicCapture->ShowFlags.SetGlobalIllumination(false);ClassicCapture->ShowFlags.SetDynamicShadows(false);ClassicCapture->ShowFlags.SetAmbientOcclusion(false);
        ClassicDollTarget=NewObject<UTextureRenderTarget2D>(this);ClassicDollTarget->ClearColor=FLinearColor(.08,.08,.08,1);ClassicDollTarget->InitAutoFormat(256,384);ClassicCapture->TextureTarget=ClassicDollTarget;RefreshClassicPanel();
    }
    ClassicCapture->ClearShowOnlyComponents();ClassicCapture->ShowOnlyActorComponents(ClassicDollActor,true);
    const FVector Feet=ClassicDollActor->GetActorLocation(),Forward=FRotator(0,90+ClassicDollYaw,0).Vector();const FVector Eye=Feet+Forward*200+FVector(0,0,100);
    ClassicCapture->SetWorldLocationAndRotation(Eye,(Feet+FVector(0,0,90)-Eye).Rotation());ClassicCapture->CaptureScene();
}
