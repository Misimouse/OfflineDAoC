#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMeshActor.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickSiegeWorldAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSiegeWorldTest="),Path))return false;
    struct FRun{int32 Index=0,Phase=0,Checks=0;double At=0;TArray<FString> Failures;TArray<TSharedPtr<FJsonValue>> Captures;USceneCaptureComponent2D* Capture=nullptr;UTextureRenderTarget2D* Target=nullptr;};static FRun Run;
    const int32 Models[]={2598,2599,2600,2601,2602,2604,2605,2606,2607,2645};
    auto Check=[&](bool Good,const FString& Label){++Run.Checks;if(!Good)Run.Failures.Add(Label);};
    if(Run.Phase==99)return true;
    if(!Run.Capture){
        for(auto Rotation:{FRotator(-35,-45,0),FRotator(-25,135,0)}){auto* Light=GetWorld()->SpawnActor<ADirectionalLight>(FVector::ZeroVector,Rotation);auto* C=Cast<UDirectionalLightComponent>(Light->GetLightComponent());C->SetMobility(EComponentMobility::Movable);C->SetIntensity(2.5);C->SetCastShadows(false);}
        auto* Owner=GetWorld()->SpawnActor<AActor>();Run.Capture=NewObject<USceneCaptureComponent2D>(Owner);Owner->SetRootComponent(Run.Capture);Run.Capture->RegisterComponent();Run.Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Run.Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Run.Capture->bCaptureEveryFrame=false;Run.Capture->bAlwaysPersistRenderingState=true;Run.Capture->FOVAngle=40;
        Run.Capture->ShowFlags.SetMotionBlur(false);Run.Capture->ShowFlags.SetAntiAliasing(false);Run.Target=NewObject<UTextureRenderTarget2D>(Owner);Run.Target->ClearColor=FLinearColor(.015,.02,.025,1);Run.Target->InitAutoFormat(512,512);Run.Capture->TextureTarget=Run.Target;
    }
    if(Run.Index>=UE_ARRAY_COUNT(Models)){
        ClearEntities();Check(Socket==nullptr,TEXT("private scene never opens a server connection"));Check(PosePlayback.IsEmpty(),TEXT("session cleanup removes all animation state"));
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetBoolField(TEXT("server_started"),false);Report->SetNumberField(TEXT("checks"),Run.Checks);Report->SetArrayField(TEXT("captures"),Run.Captures);TArray<TSharedPtr<FJsonValue>> Failures;for(auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
    }
    const FString Model=FString::FromInt(Models[Run.Index]),Id=TEXT("npc:100");
    if(Run.Phase==0){
        ClearEntities();auto* Entry=ModelCatalog.Find(Model);Check(Entry!=nullptr,Model+TEXT(" original model catalogue entry"));
        if(!Entry){++Run.Index;return true;}
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),Id);Row->SetStringField(TEXT("kind"),TEXT("npc"));Row->SetNumberField(TEXT("model_id"),Models[Run.Index]);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);EntityRows.Add(Id,Row);auto* Actor=CreateEntity(Id,Row,FVector::ZeroVector);Check(Actor!=nullptr,Model+TEXT(" original complete actor created"));
        if(!Actor){++Run.Index;return true;}
        const bool Animated=(*Entry)->GetStringField(TEXT("type"))==TEXT("skeletal");auto* Skel=Cast<ASkeletalMeshActor>(Actor);Check(Animated==(Skel!=nullptr),Model+TEXT(" original static or skinned representation preserved"));
        SetEntityAnimation(Id,TEXT("idle"));
        if(Skel){
            auto* Mesh=Skel->GetSkeletalMeshComponent();auto* Anim=Mesh->GetSingleNodeInstance();FString Idle;(*Entry)->TryGetStringField(TEXT("idle"),Idle);Check(Anim&&Anim->GetAnimationAsset()==LoadObject<UAnimationAsset>(nullptr,*Idle)&&Anim->IsLooping(),Model+TEXT(" original idle pose loops"));int64 Seq=1;
            for(auto Key:{TEXT("load"),TEXT("fire")}){
                FString Asset;if(!(*Entry)->TryGetStringField(Key,Asset))continue;auto Event=MakeShared<FJsonObject>();Event->SetNumberField(TEXT("seq"),Seq++);Event->SetNumberField(TEXT("age_ms"),0);Event->SetStringField(TEXT("kind"),TEXT("siege"));Event->SetStringField(TEXT("clip"),Key);auto Events=MakeShared<FJsonObject>();Events->SetArrayField(TEXT("events"),{MakeShared<FJsonValueObject>(Event)});Row->SetObjectField(TEXT("combat_visual"),Events);SetEntityAnimation(Id,TEXT("idle"));Anim=Mesh->GetSingleNodeInstance();Check(Anim&&Anim->GetAnimationAsset()==LoadObject<UAnimationAsset>(nullptr,*Asset)&&!Anim->IsLooping(),Model+TEXT(" announced ")+Key+TEXT(" uses original one-shot clip"));
                auto* Clip=Cast<UAnimSequenceBase>(Anim?Anim->GetAnimationAsset():nullptr);if(Clip){Mesh->SetPosition(Clip->GetPlayLength()*.2,false);Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();TArray<FTransform> First;for(int32 B=0;B<Mesh->GetNumBones();++B)First.Add(Mesh->GetBoneTransform(B));Mesh->SetPosition(Clip->GetPlayLength()*.8,false);Mesh->TickAnimation(0,false);Mesh->RefreshBoneTransforms();bool Finite=Mesh->GetNumBones()>0,Moved=false;for(int32 B=0;B<Mesh->GetNumBones();++B){const FTransform T=Mesh->GetBoneTransform(B);Finite&=T.IsValid();Moved|=!T.Equals(First[B],.001);}Check(Finite,Model+TEXT(" animated skeleton evaluates finite transforms"));Check(Moved,Model+TEXT(" original action actually changes bones between samples"));}
                PosePlayback[Id].ActionUntil=FPlatformTime::Seconds()-1;SetEntityAnimation(Id,TEXT("idle"));Check(AnimationStates.FindRef(Id)==TEXT("idle"),Model+TEXT(" finished action returns to original idle"));
            }
            Row->RemoveField(TEXT("combat_visual"));if((*Entry)->HasField(TEXT("walk"))){SetEntityAnimation(Id,TEXT("walk"));Check(AnimationStates.FindRef(Id)==TEXT("walk"),Model+TEXT(" original moving ram walk retained"));SetEntityAnimation(Id,TEXT("idle"));}
        }
        FVector Center,Extent;Actor->GetActorBounds(false,Center,Extent);Check(Extent.GetMax()>30&&Extent.GetMax()<1500,Model+TEXT(" original world dimensions retained"));Run.Capture->ClearShowOnlyComponents();Run.Capture->ShowOnlyActorComponents(Actor,true);const float Distance=Extent.Size()*3.5f;const FVector Eye=Center+FVector(-1.1f,-1.5f,.9f).GetSafeNormal()*Distance;Run.Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());Run.At=0;Run.Phase=1;return true;
    }
    if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;const double Now=FPlatformTime::Seconds();if(Run.At==0)Run.At=Now;Run.Capture->CaptureScene();if(Now-Run.At<2)return true;FlushRenderingCommands();
    const FString Image=FPaths::GetPath(Path)/FString::Printf(TEXT("model_%s.png"),*Model);FBufferArchive Bytes;Check(FImageUtils::ExportRenderTarget2DAsPNG(Run.Target,Bytes)&&FFileHelper::SaveArrayToFile(Bytes,*Image),Model+TEXT(" actual model image exported"));TArray<FColor> Pixels;const bool Read=Run.Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);int32 Colored=0;for(auto P:Pixels)if(FMath::Max3(P.R,P.G,P.B)-FMath::Min3(P.R,P.G,P.B)>12&&FMath::Max3(P.R,P.G,P.B)>50)++Colored;Check(Read&&Colored>500,Model+TEXT(" original textured body visible in rendered pixels"));
    auto Capture=MakeShared<FJsonObject>();Capture->SetStringField(TEXT("model"),Model);Capture->SetStringField(TEXT("image"),Image);Capture->SetNumberField(TEXT("colored_pixels"),Colored);Run.Captures.Add(MakeShared<FJsonValueObject>(Capture));++Run.Index;Run.Phase=0;return true;
}
