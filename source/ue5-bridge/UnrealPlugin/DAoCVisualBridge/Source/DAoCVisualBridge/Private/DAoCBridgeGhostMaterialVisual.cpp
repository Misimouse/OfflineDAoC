#include "DAoCBridgeGhostMaterials.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimationAsset.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "HAL/IConsoleManager.h"

// Private game-world capture: exercises the exact controller and a real leader pose.
// It is inactive unless explicitly requested by the isolated QA runner.
bool TickPrivateNpcGhostVisual(UWorld* World){
    FString Output;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostCapture="),Output))return false;
    static int32 Model=0,Pose=0,Phase=0;static double Ready=0;
    static ASkeletalMeshActor* Avatar=nullptr;static AStaticMeshActor* Backdrop=nullptr;
    static AActor* Lamp=nullptr;static AActor* CaptureOwner=nullptr;
    static USceneCaptureComponent2D* Capture=nullptr;static UTextureRenderTarget2D* Target=nullptr;
    static TSharedPtr<FJsonObject> Models;static TUniquePtr<FBridgeGhostMaterials> Ghost;
    static TArray<TSharedPtr<FJsonValue>> Failures;static int32 Captures=0;
    if(Phase==99)return true;
    auto Finish=[&](const FString& Error){
        if(!Error.IsEmpty())Failures.Add(MakeShared<FJsonValueString>(Error));
        if(Ghost)Ghost->Restore();Ghost.Reset();
        for(auto* A:{static_cast<AActor*>(Avatar),static_cast<AActor*>(Backdrop),Lamp,CaptureOwner})if(IsValid(A))A->Destroy();
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetNumberField(TEXT("captures"),Captures);Report->SetBoolField(TEXT("installed"),false);Report->SetBoolField(TEXT("real_server"),false);
        FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Output,TEXT("native.json")));Phase=99;UKismetSystemLibrary::QuitGame(World,nullptr,EQuitPreference::Quit,false);
    };
    if(!World)return true;
    if(!Models.IsValid()){
        FString Samples,Manifest,Text;TSharedPtr<FJsonObject> Root;
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostSamples="),Samples);FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostMaterials="),Manifest);
        const TSharedPtr<FJsonObject>* Values=nullptr;
        if(!FFileHelper::LoadFileToString(Text,*Samples)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid()||!Root->TryGetObjectField(TEXT("models"),Values)){Finish(TEXT("private samples unavailable"));return true;}
        Models=*Values;Ghost=MakeUnique<FBridgeGhostMaterials>();if(!Ghost->Load(Manifest)){Finish(TEXT("private ghost library unavailable"));return true;}
        if(auto* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("r.CustomDepth")))CVar->Set(3,ECVF_SetByCode);
    }
    const FString Id=Model==0?TEXT("110"):TEXT("307");
    if(Phase==0){
        const TSharedPtr<FJsonObject>* Row=nullptr;if(!Models->TryGetObjectField(Id,Row)){Finish(TEXT("missing sample model"));return true;}
        FString Asset,Idle;(*Row)->TryGetStringField(TEXT("asset"),Asset);(*Row)->TryGetStringField(TEXT("idle"),Idle);
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Asset);auto* Clip=LoadObject<UAnimationAsset>(nullptr,*Idle);
        if(!Mesh||!Clip){Finish(TEXT("original model or idle clip unavailable"));return true;}
        Avatar=World->SpawnActor<ASkeletalMeshActor>();auto* Body=Avatar->GetSkeletalMeshComponent();Body->SetSkeletalMeshAsset(Mesh);Body->SetCastShadow(false);Body->PlayAnimation(Clip,false);Body->SetPosition(.25f,false);Body->bPauseAnims=true;Body->RefreshBoneTransforms();
        const FBox Bounds=Avatar->GetComponentsBoundingBox(true);const FVector Center=Bounds.GetCenter();
        Backdrop=World->SpawnActor<AStaticMeshActor>();auto* Panel=Backdrop->GetStaticMeshComponent();Panel->SetMobility(EComponentMobility::Movable);Panel->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Panel->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial")));Panel->SetCastShadow(false);Backdrop->SetActorLocation(Center+FVector(0,-100,0));Backdrop->SetActorScale3D(FVector(6,.05,5));
        Lamp=World->SpawnActor<AActor>();auto* Light=NewObject<UPointLightComponent>(Lamp);Lamp->SetRootComponent(Light);Lamp->AddInstanceComponent(Light);Light->SetMobility(EComponentMobility::Movable);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(800);Light->SetAttenuationRadius(3000);Light->SetCastShadows(false);Light->SetIndirectLightingIntensity(0);Light->RegisterComponent();Lamp->SetActorLocation(Center+FVector(0,150,100));
        CaptureOwner=World->SpawnActor<AActor>();Capture=NewObject<USceneCaptureComponent2D>(CaptureOwner);CaptureOwner->SetRootComponent(Capture);Capture->RegisterComponent();Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->FOVAngle=40;
        Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Capture->ShowFlags.SetTemporalAA(false);Capture->ShowFlags.SetEyeAdaptation(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
        Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0;
        Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
        Capture->PostProcessSettings.bOverride_BloomIntensity=true;Capture->PostProcessSettings.BloomIntensity=0;
        Target=NewObject<UTextureRenderTarget2D>(CaptureOwner);Target->ClearColor=FLinearColor::Black;Target->InitAutoFormat(512,768);Capture->TextureTarget=Target;
        const double Distance=FMath::Max(Bounds.GetExtent().X/.364,Bounds.GetExtent().Z/(.364*1.5))*1.35+Bounds.GetExtent().Y;
        const FVector Eye=Center+FVector(0,Distance,0);Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());Phase=1;
    }
    if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;
    if(Phase==3){if(!Ghost->Apply(Avatar,true,true,Model==1)){Finish(TEXT("actor-local ghost application rejected"));return true;}}
    else Ghost->Restore();
    Capture->ClearShowOnlyComponents();Capture->ShowOnlyActorComponents(Backdrop,true);if(Phase!=1)Capture->ShowOnlyActorComponents(Avatar,true);
    const double Now=FPlatformTime::Seconds();if(Ready==0)Ready=Now;Capture->CaptureScene();if(Now-Ready<1.)return true;
    FlushRenderingCommands();FBufferArchive Bytes;
    const FString State=Phase==1?TEXT("background"):Phase==2?TEXT("ordinary"):Phase==3?TEXT("ghost"):TEXT("restored");
    const FString Name=FString::Printf(TEXT("%s_pose%d_%s.png"),*Id,Pose,*State);
    if(!FImageUtils::ExportRenderTarget2DAsPNG(Target,Bytes)||!FFileHelper::SaveArrayToFile(Bytes,*FPaths::Combine(Output,Name))){Finish(TEXT("capture export failed"));return true;}
    ++Captures;Ready=0;++Phase;
    if(Phase<=4)return true;
    if(Pose==0){Pose=1;auto* Body=Avatar->GetSkeletalMeshComponent();Body->SetPosition(.75f,false);Body->RefreshBoneTransforms();Phase=1;return true;}
    Ghost->Restore();for(auto* A:{static_cast<AActor*>(Avatar),static_cast<AActor*>(Backdrop),Lamp,CaptureOwner})if(IsValid(A))A->Destroy();Avatar=nullptr;Backdrop=nullptr;Lamp=nullptr;CaptureOwner=nullptr;Capture=nullptr;Target=nullptr;
    Pose=0;Phase=0;if(++Model>=2)Finish(FString());return true;
}
