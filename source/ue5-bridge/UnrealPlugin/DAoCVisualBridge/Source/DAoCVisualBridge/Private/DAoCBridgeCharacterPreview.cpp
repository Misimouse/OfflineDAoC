#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeLobbyMotion.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/PointLightComponent.h"
#include "Engine/Scene.h"
#include "ContentStreaming.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Framework/Application/SlateApplication.h"
#include "Layout/WidgetPath.h"
#include "InputCoreTypes.h"

namespace {
FString PreviewString(TSharedPtr<FJsonObject> O,const TCHAR* K){FString S;if(O)O->TryGetStringField(K,S);return S;}
TSharedPtr<FJsonObject> PreviewObject(TSharedPtr<FJsonObject> O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
double PreviewNumber(TSharedPtr<FJsonObject> O,const TCHAR* K,double Default=0){if(O)O->TryGetNumberField(K,Default);return Default;}
}

void UDAoCBridgeSubsystem::ClearCharacterLobbyPreview(){
    CharacterLobbyMotion.Reset();
    CharacterLobbyLookSignature.Empty();
    CharacterLobbyPreviewWorn.Reset();
    CharacterLobbySceneInput.Reset();bLobbyLeftHeld=bLobbyRightHeld=false;
    LobbyFigureYaw=LobbyOrbitYaw=LobbyOrbitPitch=0;LobbyZoom=1;
    for(auto* Actor:{CharacterLobbyPreviewActor.Get(),CharacterLobbyBackdropActor.Get(),CharacterLobbyCaptureActor.Get()})if(IsValid(Actor))Actor->Destroy();
    CharacterLobbyPreviewActor=nullptr;CharacterLobbyBackdropActor=nullptr;CharacterLobbyCaptureActor=nullptr;CharacterLobbyCapture=nullptr;CharacterLobbyTarget=nullptr;CharacterLobbyPreviewBrush.Reset();CharacterLobbyPreviewSignature.Empty();
}

void UDAoCBridgeSubsystem::RefreshCharacterLobbyPreview(TSharedPtr<FJsonObject> Row){
    auto Structure=MakeShared<FJsonObject>(*Row);Structure->RemoveField(TEXT("look"));
    FString Signature;FJsonSerializer::Serialize(Structure,TJsonWriterFactory<>::Create(&Signature));
    Signature+=CharacterLobbyScreen;
    if(Signature==CharacterLobbyPreviewSignature&&CharacterLobbyTarget){UpdateCharacterLobbyAppearance(PreviewObject(Row,TEXT("look")));return;}
    ClearCharacterLobbyPreview();CharacterLobbyPreviewSignature=Signature;
    FActorSpawnParameters Parameters;Parameters.ObjectFlags|=RF_Transient;Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const FVector Origin(0,0,-200000);
    // glTF -> Unreal coordinates: metres (x,y,z) become centimetres (x,z,y).
    auto Point=[Origin](FVector P){return Origin+FVector(P.X,P.Z,P.Y)*100;};
    auto* Backdrop=GetWorld()->SpawnActor<AStaticMeshActor>(Origin,FRotator::ZeroRotator,Parameters);CharacterLobbyBackdropActor=Backdrop;
    FString BackdropPath=TEXT("/DAoCVisualBridge/Pregame_v03/hibernia_lobby/StaticMeshes/hibernia_lobby.hibernia_lobby");
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyBackdrop="),BackdropPath);
    if(Backdrop){auto* Mesh=Backdrop->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*BackdropPath));Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetVisibleInSceneCaptureOnly(true);}
    // The original panorama has a finite upper edge. Retain it, with an
    // enclosing original-cloud layer visible only where the panorama ends.
    if(Backdrop)if(auto* SkyMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/DAoCVisualBridge/PregameSky_v01/M_OriginalClouds.M_OriginalClouds"))){
        auto* Sky=NewObject<UStaticMeshComponent>(Backdrop);Backdrop->AddInstanceComponent(Sky);Sky->SetupAttachment(Backdrop->GetRootComponent());Sky->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Sphere.Sphere")));Sky->SetMaterial(0,SkyMaterial);Sky->SetRelativeScale3D(FVector(1000));Sky->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sky->SetCastShadow(false);Sky->SetVisibleInSceneCaptureOnly(true);Sky->ComponentTags.Add(TEXT("DAoCLobbySky"));Sky->RegisterComponent();
    }
    FString MotionFile=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/Pregame/lobby_motion.json");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyMotion="),MotionFile);if(FPaths::FileExists(MotionFile))CharacterLobbyMotion=FDAoCLobbyMotion::Load(Backdrop,MotionFile);
    const TMap<FString,int32> Models={{TEXT("cel_m"),1984},{TEXT("cel_f"),310},{TEXT("elf_m"),382},{TEXT("elf_f"),388},{TEXT("fir_m"),352},{TEXT("fir_f"),1983},{TEXT("lur_m"),318},{TEXT("lur_f"),378},{TEXT("syl_m"),700},{TEXT("syl_f"),708},{TEXT("sha_m"),1075},{TEXT("sha_f"),1087},{TEXT("mino"),1419}};
    FString Prefix=PreviewString(Row,TEXT("prefix"));FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestPrefix="),Prefix);
    const int32 Model=Models.FindRef(Prefix);auto* Definition=ModelCatalog.Find(FString::FromInt(Model));
    CharacterLobbyPreviewModel=Model;CharacterLobbyPreviewScale=PreviewNumber(Definition?*Definition:nullptr,TEXT("scale"),1);
    auto* Figure=Definition?LoadObject<USkeletalMesh>(nullptr,*PreviewString(*Definition,TEXT("asset"))):nullptr;
    if(Figure){
        auto* Actor=GetWorld()->SpawnActor<ASkeletalMeshActor>(Point(FVector(-4.09,-4.98,-.679)),FRotator(0,225+LobbyFigureYaw,0),Parameters);CharacterLobbyPreviewActor=Actor;
        Actor->SetActorScale3D(FVector(PreviewNumber(*Definition,TEXT("scale"),1)));Actor->SetActorEnableCollision(false);auto* Body=Actor->GetSkeletalMeshComponent();Body->SetSkeletalMesh(Figure);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        if(auto* Idle=LoadObject<UAnimSequenceBase>(nullptr,*PreviewString(*Definition,TEXT("idle"))))Body->PlayAnimation(Idle,false);
        Body->TickAnimation(0,false);Body->RefreshBoneTransforms();Body->bPauseAnims=true;Body->SetComponentTickEnabled(false);
        auto Gear=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Items;auto Overview=PreviewObject(Row,TEXT("overview"));auto Worn=PreviewObject(Overview,TEXT("models")),Colors=PreviewObject(Overview,TEXT("colors"));
        CharacterLobbyPreviewWorn=Worn;
        const TMap<FString,int32> Slots={{TEXT("helmet"),21},{TEXT("gloves"),22},{TEXT("boots"),23},{TEXT("torso"),25},{TEXT("cloak"),26},{TEXT("legs"),27},{TEXT("arms"),28}};
        for(const auto& Slot:Slots){int32 Id=int32(PreviewNumber(Worn,*Slot.Key))&0x1fff;if(Id<=0)continue;auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),Slot.Value);Item->SetNumberField(TEXT("model"),Id);const int32 Color=int32(PreviewNumber(Colors,*Slot.Key));Item->SetNumberField(TEXT("color"),Color<=255?Color:0);Item->SetNumberField(TEXT("emblem"),Color>255?Color:0);Items.Add(MakeShared<FJsonValueObject>(Item));}
        Gear->SetArrayField(TEXT("items"),Items);ApplyBodyArmour(Actor,Gear);
        // Candidate-only until appearance bytes and headwear have been verified.
        UpdateCharacterLobbyAppearance(PreviewObject(Row,TEXT("look")));
        const TMap<int32,FString> WeaponKeys={{10,TEXT("right_hand")},{11,TEXT("left_hand")},{12,TEXT("two_hand")},{13,TEXT("distance")}};
        const TArray<int32> Active=(PreviewNumber(Worn,TEXT("right_hand"))>0||PreviewNumber(Worn,TEXT("left_hand"))>0)?TArray<int32>{10,11}:PreviewNumber(Worn,TEXT("two_hand"))>0?TArray<int32>{12}:TArray<int32>{13};
        TMap<int32,FEquipmentBinding> Bindings;int32 MissingModels=0,MissingBones=0;
        for(int32 Slot:Active){const FString Key=WeaponKeys.FindRef(Slot);const int32 Id=int32(PreviewNumber(Worn,*Key))&0x1fff;if(Id<=0)continue;auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("model"),Id);Item->SetNumberField(TEXT("color"),PreviewNumber(Colors,*Key));AttachEquipment(Actor,Slot,Item,false,Bindings,MissingModels,MissingBones);}
        TArray<UMeshComponent*> Meshes;Actor->GetComponents(Meshes);for(auto* Mesh:Meshes){Mesh->SetVisibleInSceneCaptureOnly(true);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetLightingChannels(false,true,false);Mesh->SetTextureForceResidentFlag(true);Mesh->PrestreamTextures(30,true);if(auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh))Skeletal->SetForcedLOD(1);}
        int32 LightPercent=25;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyLightPercent="),LightPercent);const float LightScale=FMath::Clamp(LightPercent,0,200)*.01f;
        for(int32 I=0;I<2;++I){auto* Light=NewObject<UPointLightComponent>(Actor);Actor->AddInstanceComponent(Light);Light->SetupAttachment(Actor->GetRootComponent());Light->SetRelativeLocation(I==0?FVector(170,180,220):FVector(-120,-120,120));Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity((I==0?500:300)*LightScale);Light->SetAttenuationRadius(600);Light->SetLightingChannels(false,true,false);Light->SetCastShadows(false);Light->RegisterComponent();}
    }
    CharacterLobbyCaptureActor=GetWorld()->SpawnActor<AActor>(Origin,FRotator::ZeroRotator,Parameters);CharacterLobbyCapture=NewObject<USceneCaptureComponent2D>(CharacterLobbyCaptureActor);CharacterLobbyCaptureActor->SetRootComponent(CharacterLobbyCapture);CharacterLobbyCapture->RegisterComponent();
    // Slate expects a linear image and applies display gamma itself. Supplying
    // final LDR here applied gamma twice; the cinematic tone curve also crushed
    // the original lobby's dark colours. Keep the original linear presentation.
    auto* Capture=CharacterLobbyCapture;Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorHDR;Capture->FOVAngle=40;
    ConfigureCharacterPreviewCapture(Capture);
    FVector2D ViewSize;GetWorld()->GetGameViewport()->GetViewportSize(ViewSize);const int32 TargetHeight=FMath::Clamp(FMath::RoundToInt(ViewSize.Y),768,2160);
    const double Aspect=ViewSize.X/FMath::Max(1.,ViewSize.Y);Capture->FOVAngle=FMath::RadiansToDegrees(2*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(20.))*Aspect));
    CharacterLobbyTarget=NewObject<UTextureRenderTarget2D>(this);CharacterLobbyTarget->ClearColor=FLinearColor(.02,.03,.02,1);CharacterLobbyTarget->InitAutoFormat(FMath::RoundToInt(TargetHeight*Aspect),TargetHeight);Capture->TextureTarget=CharacterLobbyTarget;
    if(CharacterLobbyBackdropActor)Capture->ShowOnlyActorComponents(CharacterLobbyBackdropActor,true);if(CharacterLobbyPreviewActor)Capture->ShowOnlyActorComponents(CharacterLobbyPreviewActor,true);
    UpdateLobbyCamera();const FVector Eye=Capture->GetComponentLocation();
    IStreamingManager::Get().AddViewInformation(Eye,CharacterLobbyTarget->SizeX,CharacterLobbyTarget->SizeX/FMath::Tan(FMath::DegreesToRadians(Capture->FOVAngle*.5f)),1,false,.5f,CharacterLobbyPreviewActor.Get(),GetWorld());Capture->CaptureScene();
    CharacterLobbyPreviewBrush=MakeShared<FSlateBrush>();CharacterLobbyPreviewBrush->SetResourceObject(CharacterLobbyTarget);CharacterLobbyPreviewBrush->ImageSize=FVector2D(CharacterLobbyTarget->SizeX,CharacterLobbyTarget->SizeY);
}
bool UDAoCBridgeSubsystem::UpdateCharacterLobbyAppearance(TSharedPtr<FJsonObject> Look){
    auto* Actor=Cast<ASkeletalMeshActor>(CharacterLobbyPreviewActor.Get());const FString Path=DAoCAppearancePath();
    if(!Actor||Path.IsEmpty())return false;
    if(!Look)Look=MakeShared<FJsonObject>();FString Signature;FJsonSerializer::Serialize(Look.ToSharedRef(),TJsonWriterFactory<>::Create(&Signature));
    if(Signature==CharacterLobbyLookSignature)return true;
    if(!ApplyCharacterAppearance(Actor,CharacterLobbyPreviewModel,Look,ArmourCatalog,Path,CharacterLobbyPreviewWorn))return false;
    CharacterLobbyLookSignature=Signature;const int32 Size=FMath::Clamp(int32(PreviewNumber(Look,TEXT("size"),1)),0,2);Actor->SetActorScale3D(FVector(CharacterLobbyPreviewScale*(Size==0?.95f:Size==2?1.05f:1.f)));
    TArray<UMeshComponent*> Meshes;Actor->GetComponents(Meshes);for(auto* Mesh:Meshes){Mesh->SetVisibleInSceneCaptureOnly(true);Mesh->SetLightingChannels(false,true,false);Mesh->SetTextureForceResidentFlag(true);Mesh->PrestreamTextures(30,true);}
    if(CharacterLobbyCapture){CharacterLobbyCapture->ClearShowOnlyComponents();if(CharacterLobbyBackdropActor)CharacterLobbyCapture->ShowOnlyActorComponents(CharacterLobbyBackdropActor,true);CharacterLobbyCapture->ShowOnlyActorComponents(Actor,true);UpdateLobbyCamera();}
    return true;
}
void UDAoCBridgeSubsystem::TickCharacterLobbyMotion(){if(CharacterLobbyMotion)CharacterLobbyMotion->Tick();}
bool UDAoCBridgeSubsystem::LobbySceneHit(FVector2D Point)const{
    if(!CharacterLobbySceneInput||!FSlateApplication::IsInitialized())return false;
    auto& Slate=FSlateApplication::Get();const auto Path=Slate.LocateWindowUnderMouse(Point,Slate.GetInteractiveTopLevelWindows());
    for(int32 I=0;I<Path.Widgets.Num();++I)if(Path.Widgets[I].Widget==CharacterLobbySceneInput)return true;
    return false;
}
bool UDAoCBridgeSubsystem::HandleLobbyPointer(FKey Key,bool Down,FVector2D Point,bool Motion){
    if(!CharacterLobbyOverlay)return false;
    if(CharacterLobbyScreen!=TEXT("customize")){bLobbyLeftHeld=bLobbyRightHeld=false;return true;}
    if(!Motion&&!Down){if(Key==EKeys::LeftMouseButton)bLobbyLeftHeld=false;if(Key==EKeys::RightMouseButton)bLobbyRightHeld=false;return true;}
    if(Motion){
        const FVector2D Delta=Point-LobbyLastPointer;LobbyLastPointer=Point;
        if(bLobbyLeftHeld&&CharacterLobbyPreviewActor){LobbyFigureYaw+=Delta.X*.45f;CharacterLobbyPreviewActor->SetActorRotation(FRotator(0,225+LobbyFigureYaw,0));}
        if(bLobbyRightHeld){LobbyOrbitYaw-=Delta.X*.3f;LobbyOrbitPitch=FMath::Clamp(LobbyOrbitPitch+float(Delta.Y)*.2f,-65.f,65.f);UpdateLobbyCamera();}
        return true;
    }
    if(Down&&LobbySceneHit(Point)){LobbyLastPointer=Point;if(Key==EKeys::LeftMouseButton)bLobbyLeftHeld=true;if(Key==EKeys::RightMouseButton)bLobbyRightHeld=true;}
    return true;
}
bool UDAoCBridgeSubsystem::HandleLobbyWheel(float Steps,FVector2D Point){
    if(!CharacterLobbyOverlay||(CharacterLobbyScreen!=TEXT("customize")&&CharacterLobbyScreen!=TEXT("select"))||!LobbySceneHit(Point)||!FMath::IsFinite(Steps)||FMath::Abs(Steps)>10)return false;
    LobbyZoom=FMath::Clamp(LobbyZoom*FMath::Pow(.9f,Steps),.25f,CharacterLobbyScreen==TEXT("customize")?5.f:2.5f);UpdateLobbyCamera();return true;
}
void UDAoCBridgeSubsystem::UpdateLobbyCamera(){
    if(!CharacterLobbyCapture||!CharacterLobbyPreviewActor)return;
    const FVector Origin(0,0,-200000);FVector Center=CharacterLobbyPreviewActor->GetActorLocation()+FVector(0,0,110);
    // Shar's original figure is taller at this fixed creation camera. Keep its
    // feet above the lower UI frame without changing the established races.
    if(CharacterLobbyScreen==TEXT("create")&&(CharacterLobbyPreviewModel==1075||CharacterLobbyPreviewModel==1087))Center.Z-=30;
    if(CharacterLobbyScreen==TEXT("create")&&CharacterLobbyPreviewModel==1419)Center.Z-=10;
    const FVector OriginalEye=Origin+FVector(-.727,-4.28,-3.81)*100;
    FVector Offset=OriginalEye-Center;
    // The Minotaur's horns extend above the shared creation framing. Keep
    // the complete original mesh inside the UI opening without shrinking it.
    if(CharacterLobbyScreen==TEXT("create")&&CharacterLobbyPreviewModel==1419)Offset*=1.15f;
    if(CharacterLobbyScreen==TEXT("customize")){
        const float Scale=CharacterLobbyPreviewActor->GetActorScale3D().X;Center=CharacterLobbyPreviewActor->GetActorLocation()+FVector(0,0,160*Scale);
        if(auto* Figure=Cast<ASkeletalMeshActor>(CharacterLobbyPreviewActor.Get())){auto* Body=Figure->GetSkeletalMeshComponent();for(const FName Bone:{FName(TEXT("Bip01_Head")),FName(TEXT("Bip01 Head"))})if(Body->GetBoneIndex(Bone)>=0){Center=Body->GetBoneLocation(Bone)+FVector(0,0,4*Scale);break;}}
        if(CharacterLobbyPreviewModel==1075||CharacterLobbyPreviewModel==1087||CharacterLobbyPreviewModel==1419){if(auto* Figure=Cast<ASkeletalMeshActor>(CharacterLobbyPreviewActor.Get())){auto* Body=Figure->GetSkeletalMeshComponent();const FName Bone(TEXT("Bip01-Head"));if(Body->GetBoneIndex(Bone)>=0)Center=Body->GetBoneLocation(Bone)+FVector(0,0,4*Scale);}}
        // At close range frame the face; pull the pivot down to the body as we
        // zoom out, instead of keeping feet below the bottom of the viewport.
        const FVector Feet=CharacterLobbyPreviewActor->GetActorLocation();
        const FVector BodyCenter=Feet+FVector(0,0,(Center.Z-Feet.Z)*.52f);
        Center=FMath::Lerp(Center,BodyCenter,FMath::Clamp((LobbyZoom-1.f)/3.f,0.f,1.f));
        Offset=(OriginalEye-Feet).GetSafeNormal()*(CharacterLobbyPreviewModel==1419?145:95)*Scale;
    }
    Offset=FQuat(FVector::UpVector,FMath::DegreesToRadians(LobbyOrbitYaw)).RotateVector(Offset);
    const FVector Right=FVector::CrossProduct(Offset.GetSafeNormal(),FVector::UpVector).GetSafeNormal();Offset=FQuat(Right,FMath::DegreesToRadians(LobbyOrbitPitch)).RotateVector(Offset);
    FVector Eye=Center+Offset*LobbyZoom;
    FVector Look=Center;
    if(CharacterLobbyScreen==TEXT("select")){
        const FVector OriginalLook=Origin+FVector(-4.5,-1,-3.865)*100;
        const FVector BodyCenter=CharacterLobbyPreviewActor->GetActorLocation()+FVector(0,0,90*CharacterLobbyPreviewActor->GetActorScale3D().X);
        Look=FMath::Lerp(OriginalLook,BodyCenter,FMath::Clamp((LobbyZoom-1.f)/1.5f,0.f,1.f));
        // Translate along the original camera direction; selection never orbits.
        Eye=Look+(OriginalEye-OriginalLook)*LobbyZoom;
    }
    CharacterLobbyCapture->SetWorldLocationAndRotation(Eye,(Look-Eye).Rotation());
    if(CharacterLobbyScreen==TEXT("customize")){FVector2D View;GetWorld()->GetGameViewport()->GetViewportSize(View);const double Width=FMath::Max(1024.,768.*View.X/FMath::Max(View.Y,1.));const double Ndc=-268./Width;const double Half=FMath::Tan(FMath::DegreesToRadians(CharacterLobbyCapture->FOVAngle*.5));CharacterLobbyCapture->AddLocalRotation(FRotator(0,-FMath::RadiansToDegrees(FMath::Atan(Ndc*Half)),0));}
    if(CharacterLobbyMotion)CharacterLobbyMotion->SetCamera(Eye-Origin);
    CharacterLobbyCapture->CaptureScene();
}
