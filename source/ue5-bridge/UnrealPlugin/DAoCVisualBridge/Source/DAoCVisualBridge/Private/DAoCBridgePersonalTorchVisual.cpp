#include "DAoCBridgeSubsystem.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/SkeletalMeshActor.h"
#include "Engine/World.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"

bool UDAoCBridgeSubsystem::TickPersonalTorchVisual(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePersonalTorchVisual="),Path))return false;
    static int32 Phase=0;static double Ready=0;static USceneCaptureComponent2D* Capture=nullptr;static UTextureRenderTarget2D* Target=nullptr;
    if(Phase==99)return true;
    if(Phase==0){
        FString Input,Text;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePersonalTorchFixture="),Input);
        if(!FFileHelper::LoadFileToString(Text,*Input)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture)){Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;}
        TSharedPtr<FJsonObject> Row;for(const auto& V:Fixture->GetArrayField(TEXT("entities")))if(V->AsObject()->GetStringField(TEXT("id"))==TEXT("player:local"))Row=V->AsObject();
        auto* Avatar=Row.IsValid()?Cast<ASkeletalMeshActor>(CreateEntity(TEXT("player:local"),Row,FVector::ZeroVector)):nullptr;
        if(!Avatar){Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;}
        Entities.Add(TEXT("player:local"),Avatar);EntityRows.Add(TEXT("player:local"),Row);PlayerPosition=FVector::ZeroVector;bLocalAvailable=true;bControls=false;Session=TEXT("PrivateTorchVisual");
        const FBox Bounds=Avatar->GetComponentsBoundingBox(true);const FVector Center=Bounds.GetCenter();
        TArray<USkeletalMeshComponent*> Parts;Avatar->GetComponents(Parts);for(auto* Part:Parts){Part->bPauseAnims=true;Part->RefreshBoneTransforms();}
        auto* Owner=GetWorld()->SpawnActor<AActor>();Capture=NewObject<USceneCaptureComponent2D>(Owner);Owner->SetRootComponent(Capture);Capture->RegisterComponent();Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->ShowOnlyActorComponents(Avatar,true);Capture->FOVAngle=40;
        Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Capture->ShowFlags.SetTemporalAA(false);Capture->ShowFlags.SetEyeAdaptation(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
        Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0;
        Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
        Capture->PostProcessSettings.bOverride_BloomIntensity=true;Capture->PostProcessSettings.BloomIntensity=0;
        Target=NewObject<UTextureRenderTarget2D>(Owner);Target->ClearColor=FLinearColor::Black;Target->InitAutoFormat(512,768);Capture->TextureTarget=Target;
        const double Distance=FMath::Max(Bounds.GetExtent().X/.364,Bounds.GetExtent().Z/(.364*1.5))*1.35+Bounds.GetExtent().Y;const FVector Eye=Center+FVector(0,Distance,0);Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());Phase=1;
    }
    if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;
    auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("enabled"),Phase!=1);State->SetNumberField(TEXT("energy_scale"),Phase==2?.15:1.);LastSnapshot=FPlatformTime::Seconds();ApplyPersonalTorch(State);TickPersonalTorch();
    const double Now=FPlatformTime::Seconds();if(Ready==0)Ready=Now;Capture->CaptureScene();if(Now-Ready<2)return true;
    FlushRenderingCommands();FBufferArchive Bytes;const FString Name=Phase==1?TEXT("off.png"):Phase==2?TEXT("day.png"):TEXT("night.png");FImageUtils::ExportRenderTarget2DAsPNG(Target,Bytes);FFileHelper::SaveArrayToFile(Bytes,*FPaths::Combine(Path,Name));
    if(++Phase<=3){Ready=0;return true;}
    ClearPersonalTorch();Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
