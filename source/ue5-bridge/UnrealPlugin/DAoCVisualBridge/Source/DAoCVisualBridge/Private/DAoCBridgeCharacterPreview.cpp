#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/PointLightComponent.h"
#include "Engine/Scene.h"
#include "ContentStreaming.h"

namespace {
FString PreviewString(TSharedPtr<FJsonObject> O,const TCHAR* K){FString S;if(O)O->TryGetStringField(K,S);return S;}
TSharedPtr<FJsonObject> PreviewObject(TSharedPtr<FJsonObject> O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
double PreviewNumber(TSharedPtr<FJsonObject> O,const TCHAR* K,double Default=0){if(O)O->TryGetNumberField(K,Default);return Default;}
}

void UDAoCBridgeSubsystem::ClearCharacterLobbyPreview(){
    for(auto* Actor:{CharacterLobbyPreviewActor.Get(),CharacterLobbyBackdropActor.Get(),CharacterLobbyCaptureActor.Get()})if(IsValid(Actor))Actor->Destroy();
    CharacterLobbyPreviewActor=nullptr;CharacterLobbyBackdropActor=nullptr;CharacterLobbyCaptureActor=nullptr;CharacterLobbyCapture=nullptr;CharacterLobbyTarget=nullptr;CharacterLobbyPreviewBrush.Reset();CharacterLobbyPreviewSignature.Empty();
}

void UDAoCBridgeSubsystem::RefreshCharacterLobbyPreview(TSharedPtr<FJsonObject> Row){
    FString Signature;FJsonSerializer::Serialize(Row.ToSharedRef(),TJsonWriterFactory<>::Create(&Signature));
    if(Signature==CharacterLobbyPreviewSignature&&CharacterLobbyTarget)return;
    ClearCharacterLobbyPreview();CharacterLobbyPreviewSignature=Signature;
    FActorSpawnParameters Parameters;Parameters.ObjectFlags|=RF_Transient;Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const FVector Origin(0,0,-200000);
    // glTF -> Unreal coordinates: metres (x,y,z) become centimetres (x,z,y).
    auto Point=[Origin](FVector P){return Origin+FVector(P.X,P.Z,P.Y)*100;};
    auto* Backdrop=GetWorld()->SpawnActor<AStaticMeshActor>(Origin,FRotator::ZeroRotator,Parameters);CharacterLobbyBackdropActor=Backdrop;
    if(Backdrop){auto* Mesh=Backdrop->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/DAoCVisualBridge/Pregame_v02/hibernia_lobby/StaticMeshes/hibernia_lobby.hibernia_lobby")));Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetVisibleInSceneCaptureOnly(true);}
    const TMap<FString,int32> Models={{TEXT("cel_m"),1984},{TEXT("cel_f"),310},{TEXT("elf_m"),382},{TEXT("elf_f"),388},{TEXT("fir_m"),352},{TEXT("fir_f"),1983},{TEXT("lur_m"),318},{TEXT("lur_f"),378},{TEXT("syl_m"),700},{TEXT("syl_f"),708}};
    const int32 Model=Models.FindRef(PreviewString(Row,TEXT("prefix")));auto* Definition=ModelCatalog.Find(FString::FromInt(Model));
    auto* Figure=Definition?LoadObject<USkeletalMesh>(nullptr,*PreviewString(*Definition,TEXT("asset"))):nullptr;
    if(Figure){
        auto* Actor=GetWorld()->SpawnActor<ASkeletalMeshActor>(Point(FVector(-4.09,-4.98,-.679)),FRotator(0,225,0),Parameters);CharacterLobbyPreviewActor=Actor;
        Actor->SetActorScale3D(FVector(PreviewNumber(*Definition,TEXT("scale"),1)));Actor->SetActorEnableCollision(false);auto* Body=Actor->GetSkeletalMeshComponent();Body->SetSkeletalMesh(Figure);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(auto* Idle=LoadObject<UAnimSequenceBase>(nullptr,*PreviewString(*Definition,TEXT("idle"))))Body->PlayAnimation(Idle,false);
        Body->TickAnimation(0,false);Body->RefreshBoneTransforms();Body->bPauseAnims=true;Body->SetComponentTickEnabled(false);
        auto Gear=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Items;auto Overview=PreviewObject(Row,TEXT("overview"));auto Worn=PreviewObject(Overview,TEXT("models")),Colors=PreviewObject(Overview,TEXT("colors"));
        const TMap<FString,int32> Slots={{TEXT("helmet"),21},{TEXT("gloves"),22},{TEXT("boots"),23},{TEXT("torso"),25},{TEXT("cloak"),26},{TEXT("legs"),27},{TEXT("arms"),28}};
        for(const auto& Slot:Slots){int32 Id=int32(PreviewNumber(Worn,*Slot.Key))&0x1fff;if(Id<=0)continue;auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),Slot.Value);Item->SetNumberField(TEXT("model"),Id);const int32 Color=int32(PreviewNumber(Colors,*Slot.Key));Item->SetNumberField(TEXT("color"),Color<=255?Color:0);Item->SetNumberField(TEXT("emblem"),Color>255?Color:0);Items.Add(MakeShared<FJsonValueObject>(Item));}
        Gear->SetArrayField(TEXT("items"),Items);ApplyBodyArmour(Actor,Gear);
        const TMap<int32,FString> WeaponKeys={{10,TEXT("right_hand")},{11,TEXT("left_hand")},{12,TEXT("two_hand")},{13,TEXT("distance")}};
        const TArray<int32> Active=(PreviewNumber(Worn,TEXT("right_hand"))>0||PreviewNumber(Worn,TEXT("left_hand"))>0)?TArray<int32>{10,11}:PreviewNumber(Worn,TEXT("two_hand"))>0?TArray<int32>{12}:TArray<int32>{13};
        TMap<int32,FEquipmentBinding> Bindings;int32 MissingModels=0,MissingBones=0;
        for(int32 Slot:Active){const FString Key=WeaponKeys.FindRef(Slot);const int32 Id=int32(PreviewNumber(Worn,*Key))&0x1fff;if(Id<=0)continue;auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("model"),Id);Item->SetNumberField(TEXT("color"),PreviewNumber(Colors,*Key));AttachEquipment(Actor,Slot,Item,false,Bindings,MissingModels,MissingBones);}
        TArray<UMeshComponent*> Meshes;Actor->GetComponents(Meshes);for(auto* Mesh:Meshes){Mesh->SetVisibleInSceneCaptureOnly(true);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetLightingChannels(false,true,false);}
        for(int32 I=0;I<2;++I){auto* Light=NewObject<UPointLightComponent>(Actor);Actor->AddInstanceComponent(Light);Light->SetupAttachment(Actor->GetRootComponent());Light->SetRelativeLocation(I==0?FVector(170,180,220):FVector(-120,-120,120));Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(I==0?800:200);Light->SetAttenuationRadius(600);Light->SetLightingChannels(false,true,false);Light->SetCastShadows(false);Light->RegisterComponent();}
    }
    CharacterLobbyCaptureActor=GetWorld()->SpawnActor<AActor>(Origin,FRotator::ZeroRotator,Parameters);CharacterLobbyCapture=NewObject<USceneCaptureComponent2D>(CharacterLobbyCaptureActor);CharacterLobbyCaptureActor->SetRootComponent(CharacterLobbyCapture);CharacterLobbyCapture->RegisterComponent();
    auto* Capture=CharacterLobbyCapture;Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Capture->FOVAngle=40;
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetMotionBlur(false);Capture->ShowFlags.SetGlobalIllumination(false);Capture->ShowFlags.SetDynamicShadows(false);Capture->ShowFlags.SetPostProcessMaterial(false);
    Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
    Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0;
    FVector2D ViewSize;GetWorld()->GetGameViewport()->GetViewportSize(ViewSize);const int32 TargetHeight=FMath::Clamp(FMath::RoundToInt(ViewSize.Y),768,2160);
    const double Aspect=ViewSize.X/FMath::Max(1.,ViewSize.Y);Capture->FOVAngle=FMath::RadiansToDegrees(2*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(20.))*Aspect));
    CharacterLobbyTarget=NewObject<UTextureRenderTarget2D>(this);CharacterLobbyTarget->ClearColor=FLinearColor(.02,.03,.02,1);CharacterLobbyTarget->InitAutoFormat(FMath::RoundToInt(TargetHeight*Aspect),TargetHeight);Capture->TextureTarget=CharacterLobbyTarget;
    if(CharacterLobbyBackdropActor)Capture->ShowOnlyActorComponents(CharacterLobbyBackdropActor,true);if(CharacterLobbyPreviewActor)Capture->ShowOnlyActorComponents(CharacterLobbyPreviewActor,true);
    const FVector Eye=Point(FVector(-.727,-3.81,-4.28)),Look=Point(FVector(-4.5,-3.865,-1));Capture->SetWorldLocationAndRotation(Eye,(Look-Eye).Rotation());
    IStreamingManager::Get().AddViewInformation(Eye,CharacterLobbyTarget->SizeX,CharacterLobbyTarget->SizeX/FMath::Tan(FMath::DegreesToRadians(Capture->FOVAngle*.5f)),1,false,.5f,CharacterLobbyPreviewActor.Get(),GetWorld());Capture->CaptureScene();
    CharacterLobbyPreviewBrush=MakeShared<FSlateBrush>();CharacterLobbyPreviewBrush->SetResourceObject(CharacterLobbyTarget);CharacterLobbyPreviewBrush->ImageSize=FVector2D(CharacterLobbyTarget->SizeX,CharacterLobbyTarget->SizeY);
}
