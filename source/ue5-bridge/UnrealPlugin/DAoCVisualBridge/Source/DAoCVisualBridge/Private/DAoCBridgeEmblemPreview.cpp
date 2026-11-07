#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/PointLightComponent.h"
#include "Styling/SlateBrush.h"

void UDAoCBridgeSubsystem::ClearEmblemPickerPreview(){
    for(auto* Actor:{Cast<AActor>(EmblemPickerPreviewActor.Get()),EmblemPickerCaptureActor.Get()})if(IsValid(Actor))Actor->Destroy();
    EmblemPickerPreviewActor=nullptr;EmblemPickerCaptureActor=nullptr;EmblemPickerCapture=nullptr;EmblemPickerTarget=nullptr;EmblemPickerPreviewBrush.Reset();EmblemPickerRenderedValue=-1;EmblemPickerCapturedAt=0;
}
void UDAoCBridgeSubsystem::UpdateEmblemPickerPreview(){
    bool Visible=false;if(!EmblemPickerState||!EmblemPickerState->TryGetBoolField(TEXT("visible"),Visible)||!Visible||!GetWorld())return;
    FString Token;EmblemPickerState->TryGetStringField(TEXT("token"),Token);if(Token.IsEmpty()||Token==EmblemPickerDismissedToken)return;
    double Value=512;EmblemPickerState->TryGetNumberField(TEXT("emblem"),Value);if(Value<512||Value>131071)return;
    const double Now=FPlatformTime::Seconds();if(Now-EmblemPickerCapturedAt<.05&&EmblemPickerRenderedValue==int32(Value))return;
    bool New=false;
    if(!IsValid(EmblemPickerPreviewActor)){
        FActorSpawnParameters P;P.ObjectFlags|=RF_Transient;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        EmblemPickerPreviewActor=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,-200000),FRotator::ZeroRotator,P);if(!EmblemPickerPreviewActor)return;
        auto* Component=EmblemPickerPreviewActor->GetStaticMeshComponent();Component->SetMobility(EComponentMobility::Movable);Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCanEverAffectNavigation(false);Component->SetGenerateOverlapEvents(false);Component->SetCastShadow(false);Component->SetLightingChannels(false,true,false);Component->SetVisibleInSceneCaptureOnly(true);EmblemPickerPreviewActor->SetActorEnableCollision(false);New=true;
    }
    auto* Component=EmblemPickerPreviewActor->GetStaticMeshComponent();
    if(New||EmblemPickerRenderedValue!=int32(Value)){
        if(!BuildEmblemPickerShield(Component,int32(Value)))return;
        EmblemPickerRenderedValue=int32(Value);
    }
    if(New||!EmblemPickerCapture){
        const auto Bounds=Component->GetStaticMesh()->GetBoundingBox();const auto E=Bounds.GetExtent();int32 Thin=0,Tall=0;
        for(int32 I=1;I<3;++I){if(E[I]<E[Thin])Thin=I;if(E[I]>E[Tall])Tall=I;}
        if(Thin==Tall||E[Tall]<=0)return;
        FVector Normal=FVector::ZeroVector,Up=FVector::ZeroVector;Normal[Thin]=-1;Up[Tall]=1;
        EmblemPickerBaseRotation=FRotationMatrix::MakeFromXZ(Normal,Up).ToQuat().Inverse();
        // AStaticMeshActor starts with the mesh as its root. Give the preview a
        // separate pivot so centering the mesh cannot move the camera target.
        auto* Pivot=NewObject<USceneComponent>(EmblemPickerPreviewActor);EmblemPickerPreviewActor->AddInstanceComponent(Pivot);Pivot->RegisterComponent();
        EmblemPickerPreviewActor->SetRootComponent(Pivot);Pivot->SetWorldLocation(FVector(0,0,-200000));Component->AttachToComponent(Pivot,FAttachmentTransformRules::KeepRelativeTransform);
        Component->SetRelativeLocation(-Bounds.GetCenter());EmblemPickerPreviewActor->SetActorScale3D(FVector(50./E[Tall]));
        for(int32 I=0;I<2;++I){auto* Light=NewObject<UPointLightComponent>(EmblemPickerPreviewActor);EmblemPickerPreviewActor->AddInstanceComponent(Light);Light->SetupAttachment(Component);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(I?90:150);Light->SetAttenuationRadius(600);Light->SetCastShadows(false);Light->SetLightingChannels(false,true,false);Light->RegisterComponent();}
    }
    if(!EmblemPickerCapture){
        EmblemPickerCaptureActor=GetWorld()->SpawnActor<AActor>();EmblemPickerCapture=NewObject<USceneCaptureComponent2D>(EmblemPickerCaptureActor);EmblemPickerCaptureActor->SetRootComponent(EmblemPickerCapture);EmblemPickerCapture->RegisterComponent();
        EmblemPickerCapture->bCaptureEveryFrame=false;EmblemPickerCapture->bCaptureOnMovement=false;EmblemPickerCapture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;EmblemPickerCapture->FOVAngle=40;ConfigureCharacterPreviewCapture(EmblemPickerCapture);
        EmblemPickerTarget=NewObject<UTextureRenderTarget2D>(this);EmblemPickerTarget->ClearColor=FLinearColor(.025,.025,.025,1);EmblemPickerTarget->InitAutoFormat(168,216);EmblemPickerCapture->TextureTarget=EmblemPickerTarget;
        EmblemPickerPreviewBrush=MakeShared<FSlateBrush>();EmblemPickerPreviewBrush->SetResourceObject(EmblemPickerTarget);EmblemPickerPreviewBrush->ImageSize=FVector2D(84,108);
    }
    const FVector Center=EmblemPickerPreviewActor->GetActorLocation();EmblemPickerPreviewActor->SetActorRotation(FQuat(FVector::UpVector,FMath::Sin(Now*.8)*.35)*EmblemPickerBaseRotation);
    TArray<UPointLightComponent*> Lights;EmblemPickerPreviewActor->GetComponents(Lights);for(int32 I=0;I<Lights.Num();++I)Lights[I]->SetWorldLocation(Center+FVector(120,I?100:-100,80));
    const FVector Eye=Center+FVector(175,0,0);EmblemPickerCapture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());EmblemPickerCapture->ClearShowOnlyComponents();EmblemPickerCapture->ShowOnlyActorComponents(EmblemPickerPreviewActor,true);EmblemPickerCapture->CaptureScene();EmblemPickerCapturedAt=Now;
}
