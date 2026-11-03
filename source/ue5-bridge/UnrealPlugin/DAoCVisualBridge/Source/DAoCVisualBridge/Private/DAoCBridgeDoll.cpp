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
#include "Components/PointLightComponent.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"

namespace {
FString DollString(TSharedPtr<FJsonObject> O,const TCHAR* Key){FString S;if(O)O->TryGetStringField(Key,S);return S;}
void DollMaterials(UMeshComponent* From,UMeshComponent* To){
    for(int32 I=0;I<From->GetNumMaterials();++I)To->SetMaterial(I,From->GetMaterial(I));
    To->SetCollisionEnabled(ECollisionEnabled::NoCollision);To->SetCastShadow(false);To->SetCanEverAffectNavigation(false);To->SetGenerateOverlapEvents(false);To->SetVisibleInSceneCaptureOnly(true);
    auto* Source=Cast<USkeletalMeshComponent>(From);auto* Target=Cast<USkeletalMeshComponent>(To);
    if(Source&&Target&&Source->GetSkeletalMeshAsset())if(auto* Render=Source->GetSkeletalMeshAsset()->GetResourceForRendering())for(int32 LOD=0;LOD<Render->LODRenderData.Num();++LOD){const auto& Data=Render->LODRenderData[LOD];for(int32 Index=0;Index<Data.RenderSections.Num();++Index){const int32 Material=Data.RenderSections[Index].MaterialIndex;Target->ShowMaterialSection(Material,Index,Source->IsMaterialSectionShown(Material,LOD),LOD);}}
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
        for(int32 I=0;I<2;++I){auto* Light=NewObject<UPointLightComponent>(Doll);Doll->AddInstanceComponent(Light);Light->SetupAttachment(Doll->GetRootComponent());Light->SetRelativeLocation(I==0?FVector(180,150,200):FVector(-150,-100,130));Light->SetIntensity(I==0?12000.f:6000.f);Light->SetAttenuationRadius(500);Light->SetCastShadows(false);Light->RegisterComponent();}
        auto* Body=Doll->GetSkeletalMeshComponent();Body->SetSkeletalMesh(Original->GetSkeletalMeshAsset());Body->SetRelativeTransform(Original->GetRelativeTransform());Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
        auto* Definition=ModelCatalog.Find(FString::FromInt(EntityModels.FindRef(TEXT("player:local"))));const FString Idle=Definition?DollString(*Definition,TEXT("idle")):TEXT("");
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
        ClassicCapture->bCaptureEveryFrame=false;ClassicCapture->bCaptureOnMovement=false;ClassicCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;ClassicCapture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;ClassicCapture->FOVAngle=40;ClassicCapture->PostProcessSettings.bOverride_AutoExposureBias=true;ClassicCapture->PostProcessSettings.AutoExposureBias=2.f;
        ClassicCapture->ShowFlags.SetAtmosphere(false);ClassicCapture->ShowFlags.SetFog(false);ClassicCapture->ShowFlags.SetMotionBlur(false);ClassicCapture->ShowFlags.SetGlobalIllumination(false);ClassicCapture->ShowFlags.SetDynamicShadows(false);ClassicCapture->ShowFlags.SetAmbientOcclusion(false);
        ClassicDollTarget=NewObject<UTextureRenderTarget2D>(this);ClassicDollTarget->ClearColor=FLinearColor(.08,.08,.08,1);ClassicDollTarget->InitAutoFormat(256,384);ClassicCapture->TextureTarget=ClassicDollTarget;RefreshClassicPanel();
    }
    ClassicCapture->ClearShowOnlyComponents();ClassicCapture->ShowOnlyActorComponents(ClassicDollActor,true);
    const FVector Feet=ClassicDollActor->GetActorLocation(),Forward=FRotator(0,90+ClassicDollYaw,0).Vector();const FVector Eye=Feet+Forward*200+FVector(0,0,100);
    ClassicCapture->SetWorldLocationAndRotation(Eye,(Feet+FVector(0,0,90)-Eye).Rotation());ClassicCapture->CaptureScene();
}
