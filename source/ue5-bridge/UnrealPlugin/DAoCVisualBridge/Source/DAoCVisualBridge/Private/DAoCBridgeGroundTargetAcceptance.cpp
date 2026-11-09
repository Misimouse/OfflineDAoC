#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/ConfigCacheIni.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"

bool UDAoCBridgeSubsystem::TickGroundTargetAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundTargetTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;TSharedPtr<FJsonObject> State;TWeakObjectPtr<AActor> Floor,Wall;USceneCaptureComponent2D* Capture=nullptr;UTextureRenderTarget2D* Target=nullptr;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Label){++Run.Checks;if(!Good)Run.Failures.Add(Label);};
    auto Command=[&](){FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Outgoing.GetData()),Outgoing.Num());FString Text(Converted.Length(),Converted.Get());TSharedPtr<FJsonObject> V;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),V);Outgoing.Empty();return V;};
    auto Box=[&](FVector Location,FVector Scale){auto* Owner=GetWorld()->SpawnActor<AActor>();auto* Mesh=NewObject<UStaticMeshComponent>(Owner);Owner->SetRootComponent(Mesh);Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Mesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Mesh->SetCollisionResponseToAllChannels(ECR_Block);Mesh->SetWorldLocation(Location);Mesh->SetWorldScale3D(Scale);Mesh->RegisterComponent();auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/DAoCVisualBridge/SpellVisuals_v01/M_SpellAdd.M_SpellAdd"));if(Base){auto* M=UMaterialInstanceDynamic::Create(Base,Mesh);M->SetVectorParameterValue(TEXT("Tint"),{.04f,.04f,.04f,1});Mesh->SetMaterial(0,M);}return Owner;};
    if(Run.Phase==0){
        FBridgeKeyConfiguration Keys;Check(Keys.Find(TEXT("ground_target"))!=nullptr,TEXT("original configurable Ground Target action exists"));Check(Keys.Text(TEXT("ground_target"),0)==TEXT("Ctrl+G"),TEXT("usable nonconflicting default preserves F5 camera control"));
        FConfigFile Config;Config.SetString(TEXT("Bindings"),TEXT("show_inventory0"),TEXT("Ctrl+G"));Config.Write(Path+TEXT(".keys.ini"));Keys.Load(Path+TEXT(".keys.ini"));Check(Keys.Text(TEXT("show_inventory"),0)==TEXT("Ctrl+G"),TEXT("existing customized control remains assigned"));Check(Keys.Find(TEXT("ground_target"))->Bindings[0].IsEmpty(),TEXT("new default yields to existing saved binding"));Check(Keys.Text(TEXT("move_forward"),0)==TEXT("W"),TEXT("binding migration keeps movement controls"));
        Run.Floor=Box({300,0,-5},{20,20,.1});PlayerPosition=FVector::ZeroVector;bLocalAvailable=true;Session=TEXT("private-ground-target");Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private ground target test"),false);Outgoing.Empty();
        ApplyGroundTarget(nullptr);Check(!bHasGroundTarget&&!GroundTargetMarker.IsValid(),TEXT("no invented initial marker"));
        Run.State=MakeShared<FJsonObject>();Run.State->SetNumberField(TEXT("revision"),2);Run.State->SetBoolField(TEXT("has_point"),true);Run.State->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(1367),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});Run.Phase=1;Run.At=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==1){if(FPlatformTime::Seconds()-Run.At<.2)return true;ApplyGroundTarget(Run.State);
        Check(bHasGroundTarget&&GroundTargetMarker.IsValid(),TEXT("original marker created from requested point"));Check(GroundTargetMarker.IsValid()&&GroundTargetMarker->GetActorLocation().Equals(FVector(300,0,0),.01),TEXT("marker uses the bridge coordinate frame"));
        TInlineComponentArray<UProceduralMeshComponent*> Parts;if(GroundTargetMarker.IsValid())GroundTargetMarker->GetComponents(Parts);Check(Parts.Num()==2,TEXT("original central model and original projected bitmap both exist"));bool OriginalModel=false,Projection=false;for(auto* Part:Parts)if(auto* Section=Part->GetProcMeshSection(0)){OriginalModel=OriginalModel||(Section->ProcVertexBuffer.Num()==24&&Section->ProcIndexBuffer.Num()==36);Projection=Projection||Section->ProcVertexBuffer.Num()==81;}Check(OriginalModel,TEXT("original model vertices and indices preserved"));Check(Projection,TEXT("original two metre bitmap projected over world geometry"));
        bool Passive=Parts.Num()==2;for(auto* Part:Parts)Passive=Passive&&Part->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&!Part->CastShadow;Check(Passive,TEXT("marker cannot block movement camera picking or lighting"));Check(GroundTargetVisible(),TEXT("unobstructed point is visible from player eye"));
        Run.Wall=Box({150,0,100},{.2,2,2});Run.Phase=2;Run.At=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==2){if(FPlatformTime::Seconds()-Run.At<.2)return true;Check(!GroundTargetVisible(),TEXT("wall clears independent ground target visibility"));Run.Wall->Destroy();Run.Phase=3;Run.At=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==3){if(FPlatformTime::Seconds()-Run.At<.2)return true;
        FVector Hit;Check(PickGroundTargetRay({300,0,300},{0,0,-1},Hit)&&Hit.Equals(FVector(300,0,0),.1),TEXT("actual ray selects physical ground"));Check(!PickGroundTargetRay({300,0,300},{0,0,1},Hit),TEXT("empty sky ray does not invent a point"));Check(!PickGroundTargetRay({NAN,0,0},{0,0,-1},Hit),TEXT("nonfinite ray rejected"));
        Check(SendGroundTargetPoint({300,0,0},true),TEXT("physical point can be requested"));auto V=Command();auto P=V?V->GetArrayField(TEXT("position_m")):TArray<TSharedPtr<FJsonValue>>();Check(V&&V->GetStringField(TEXT("action"))==TEXT("ground_target")&&P.Num()==3&&P[0]->AsNumber()==1367&&P[1]->AsNumber()==130&&P[2]->AsNumber()==1263&&V->GetBoolField(TEXT("visible")),TEXT("request carries original bridge point and separate visibility"));Check(!SendGroundTargetPoint({30000,0,0},true)&&Outgoing.IsEmpty(),TEXT("point beyond original picking range refused"));
        bChatOpen=true;TickGroundTargetSight();auto Sight=Command();Check(Sight&&Sight->GetStringField(TEXT("action"))==TEXT("ground_target_sight")&&Sight->GetNumberField(TEXT("ground_target_revision"))==2&&Sight->GetBoolField(TEXT("ground_target_in_view")),TEXT("stationary geometry visibility remains fresh while chat is open"));TickGroundTargetSight();Check(Outgoing.IsEmpty(),TEXT("stationary sight reports rate bounded without repeating ground target move request"));bChatOpen=false;
        auto* Previous=GroundTargetMarker.Get();ApplyGroundTarget(Run.State);Check(GroundTargetMarker.Get()==Previous,TEXT("unchanged point does not rebuild marker every snapshot"));
        auto* CaptureOwner=GetWorld()->SpawnActor<AActor>();Run.Capture=NewObject<USceneCaptureComponent2D>(CaptureOwner);CaptureOwner->SetRootComponent(Run.Capture);Run.Capture->RegisterComponent();Run.Capture->bCaptureEveryFrame=false;Run.Capture->bCaptureOnMovement=false;Run.Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Run.Capture->FOVAngle=40;ConfigureCharacterPreviewCapture(Run.Capture);Run.Capture->ShowFlags.SetTemporalAA(false);Run.Capture->ShowFlags.SetTranslucency(true);Run.Target=NewObject<UTextureRenderTarget2D>(CaptureOwner);Run.Target->ClearColor=FLinearColor(.02,.02,.02,1);Run.Target->InitAutoFormat(512,512);Run.Capture->TextureTarget=Run.Target;Run.Capture->ShowOnlyActorComponents(GroundTargetMarker.Get(),true);Run.Capture->ShowOnlyActorComponents(Run.Floor.Get(),true);FVector Eye(300,-350,350);Run.Capture->SetWorldLocationAndRotation(Eye,(FVector(300,0,0)-Eye).Rotation());Run.Phase=4;Run.At=0;return true;
    }
    if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;const double Now=FPlatformTime::Seconds();if(Run.At==0)Run.At=Now;if(Now-Run.At<3){Run.Capture->CaptureScene();return true;}
    Run.Capture->CaptureScene();FlushRenderingCommands();FBufferArchive Bytes;Check(FImageUtils::ExportRenderTarget2DAsPNG(Run.Target,Bytes)&&FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png"))),TEXT("original ground marker rendered and exported"));TArray<FColor> Pixels;bool Read=Run.Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);int32 Yellow=0;for(auto Pixel:Pixels)if(Pixel.R>150&&Pixel.G>100&&Pixel.B<110)++Yellow;Check(Read&&Yellow>100,TEXT("original yellow marker is visible in rendered pixels"));
    Run.State->SetNumberField(TEXT("revision"),3);Run.State->SetBoolField(TEXT("has_point"),false);ApplyGroundTarget(Run.State);Check(!bHasGroundTarget&&!GroundTargetMarker.IsValid()&&!GroundTargetVisible(),TEXT("cleared session point removes marker and geometry visibility"));ResetGroundTarget();if(Run.Floor.IsValid())Run.Floor->Destroy();if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Outgoing.Empty();Session.Empty();bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);Report->SetNumberField(TEXT("yellow_pixels"),Yellow);Report->SetBoolField(TEXT("server_started"),false);TArray<TSharedPtr<FJsonValue>> Failures;for(auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
