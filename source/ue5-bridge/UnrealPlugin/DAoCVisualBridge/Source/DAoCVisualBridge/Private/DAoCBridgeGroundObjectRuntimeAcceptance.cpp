#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeAppearance.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#endif
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "InputCoreTypes.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Engine/DirectionalLight.h"
#include "Components/LightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Materials/Material.h"
#include "Serialization/BufferArchive.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "Misc/Paths.h"

bool UDAoCBridgeSubsystem::TickGroundObjectRuntimeAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectRuntimeTest="),Path))return false;
    FString CaptureDir;const bool Render=FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectCapture="),CaptureDir);
    static bool Ran=false;if(Ran&&!Render)return true;if(!Render)Ran=true;
    int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    auto Clone=[](const TSharedPtr<FJsonObject>& Input){FString Text;FJsonSerializer::Serialize(Input.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));TSharedPtr<FJsonObject> Out;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Out);return Out;};
    auto Object=[&](int32 Oid,int32 Model,double X,double Y,double Z){auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("id"),FString::Printf(TEXT("object:%d"),Oid));R->SetStringField(TEXT("kind"),TEXT("object"));R->SetStringField(TEXT("name"),TEXT("Isolated ground fixture"));R->SetStringField(TEXT("object_token"),FString::ChrN(64,TEXT('a')));R->SetNumberField(TEXT("oid"),Oid);R->SetNumberField(TEXT("model_id"),Model);R->SetNumberField(TEXT("heading_4096"),0);R->SetNumberField(TEXT("world_generation"),7);R->SetNumberField(TEXT("health"),1);R->SetBoolField(TEXT("targetable"),true);R->SetNumberField(TEXT("realm"),-1);R->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(X),MakeShared<FJsonValueNumber>(Y),MakeShared<FJsonValueNumber>(Z)});return R;};
    if(Render){
        static int32 Phase=0;static double At=0;static USceneCaptureComponent2D* Capture=nullptr;static UTextureRenderTarget2D* Target=nullptr;static AActor* Owner=nullptr;static TArray<TSharedPtr<FJsonValue>> Errors;
        if(Phase==0){
            auto Snapshot=MakeShared<FJsonObject>();auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("generation"),7);State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Object(201,488,1363,130,1263)),MakeShared<FJsonValueObject>(Object(202,637,1365,130,1263)),MakeShared<FJsonValueObject>(Object(203,445,1367,130,1263))});Snapshot->SetObjectField(TEXT("world_objects"),State);PlayerPosition=FVector::ZeroVector;TSet<FString> Seen;ApplyGroundObjects(Snapshot,Seen);
            if(Seen.Num()!=3)Errors.Add(MakeShared<FJsonValueString>(TEXT("three actual runtime bodies must load")));
            Owner=GetWorld()->SpawnActor<AActor>();auto* Floor=NewObject<UStaticMeshComponent>(Owner);Owner->SetRootComponent(Floor);Floor->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Floor->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial")));Floor->SetWorldScale3D(FVector(12,8,.05));Floor->SetWorldLocation(FVector(100,0,-5));Floor->RegisterComponent();
            for(int32 I=0;I<2;++I){auto* Light=GetWorld()->SpawnActor<ADirectionalLight>(FVector::ZeroVector,FRotator(I==0?-40.f:-20.f,I==0?40.f:220.f,0));Light->GetLightComponent()->SetIntensity(I==0?3.f:1.5f);}
            auto* CameraOwner=GetWorld()->SpawnActor<AActor>();Capture=NewObject<USceneCaptureComponent2D>(CameraOwner);CameraOwner->SetRootComponent(Capture);Capture->RegisterComponent();Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->FOVAngle=50;ConfigureCharacterPreviewCapture(Capture);Capture->ShowFlags.SetTemporalAA(false);Capture->ShowOnlyActorComponents(Owner,true);for(const auto& Pair:Entities)Capture->ShowOnlyActorComponents(Pair.Value.Get(),true);
            Target=NewObject<UTextureRenderTarget2D>(CameraOwner);Target->ClearColor=FLinearColor(.08,.08,.08,1);Target->InitAutoFormat(1280,720);Capture->TextureTarget=Target;Phase=1;
        }
        if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;
        const FVector Focus(100,0,30),Eye=Phase==1?FVector(100,-650,260):FVector(500,450,300);Capture->SetWorldLocationAndRotation(Eye,(Focus-Eye).Rotation());Capture->CaptureScene();const double Now=FPlatformTime::Seconds();if(At==0)At=Now;if(Now-At<2)return true;
        FlushRenderingCommands();FBufferArchive Bytes;const FString File=FPaths::Combine(CaptureDir,Phase==1?TEXT("front.png"):TEXT("rear.png"));if(!FImageUtils::ExportRenderTarget2DAsPNG(Target,Bytes)||!FFileHelper::SaveArrayToFile(Bytes,*File))Errors.Add(MakeShared<FJsonValueString>(TEXT("runtime render capture exports")));
        if(Phase==1){Phase=2;At=0;return true;}
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Errors.IsEmpty());Report->SetArrayField(TEXT("failures"),Errors);Report->SetNumberField(TEXT("captures"),2);Report->SetBoolField(TEXT("actual_runtime_bodies"),true);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
    }
    auto Bag=Object(201,488,1364,130,1263),Grave=Object(202,637,1366,130,1263);
    auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("generation"),7);State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Bag),MakeShared<FJsonValueObject>(Grave)});auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetObjectField(TEXT("world_objects"),State);
    PlayerPosition=FVector::ZeroVector;Session=TEXT("isolated-ground-objects");bLocalAvailable=true;bExiting=false;
    Check(Socket==nullptr,TEXT("test starts without a live socket"));Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private ground request capture"),false);
    TSet<FString> Seen;ApplyGroundObjects(Snapshot,Seen);Check(Seen.Num()==2&&Entities.Num()==2,TEXT("bag and gravestone create original non-living bodies"));
    auto* Actor=Entities.FindRef(TEXT("object:201")).Get();const FBox Bounds=EntitySelectionBounds(Actor);
    Check(Actor&&Actor->ActorHasTag(TEXT("DAoCBridgeGroundObject"))&&Bounds.IsValid,TEXT("actual bag mesh defines selectable bounds"));
    FBox Drawn(ForceInit);
#if WITH_EDITOR
    if(Actor){TInlineComponentArray<UStaticMeshComponent*> Parts;Actor->GetComponents(Parts);for(auto* Part:Parts)if(const FMeshDescription* D=Part->GetStaticMesh()->GetMeshDescription(0)){FStaticMeshConstAttributes Attributes(*D);const auto Positions=Attributes.GetVertexPositions();for(const FVertexID V:D->Vertices().GetElementIDs())Drawn+=Part->GetComponentTransform().TransformPosition(FVector(Positions[V]));}}
#endif
    Check(Drawn.IsValid&&Drawn.GetSize().X>40&&Drawn.GetSize().X<45&&Drawn.GetSize().Z>45&&Drawn.GetSize().Z<49,TEXT("actual transformed bag vertices retain original centimetre dimensions"));
    if(Actor){TInlineComponentArray<UStaticMeshComponent*> Parts;Actor->GetComponents(Parts);Check(Parts.Num()==1&&Parts[0]->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("loot does not become a movement obstacle"));}
    Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Entities.FindRef(TEXT("object:201")).Get()==Actor,TEXT("repeated snapshot reuses original body"));
    Bag->SetNumberField(TEXT("heading_4096"),1024);Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Actor&&FMath::Abs(FRotator::NormalizeAxis(Actor->GetActorRotation().Yaw-90))<.001,TEXT("quarter turn uses original world heading without NPC offset"));
    auto Capture=[&](const TCHAR* Action){Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> V;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),V)&&V.IsValid()&&V->GetStringField(TEXT("action"))==Action,TEXT("one exact command captured"));return V;};
    Outgoing.Empty();SelectEntity(TEXT("object:201"),false);auto Selected=Capture(TEXT("target_object"));Check(Selected.IsValid()&&Selected->GetStringField(TEXT("object_token"))==Bag->GetStringField(TEXT("object_token"))&&Selected->GetNumberField(TEXT("world_generation"))==7,TEXT("click pins current identity and generation"));
    SelectEntity(TEXT("object:201"),true);Check(Outgoing.IsEmpty(),TEXT("right click never automatically picks up loot"));
    Check(SendGroundObjectAction(TEXT("get_object"),TEXT("object:201")),TEXT("selected bag can produce explicit Get Item request"));Capture(TEXT("get_object"));
    Check(!SendGroundObjectAction(TEXT("get_object"),TEXT("object:999"))&&Outgoing.IsEmpty(),TEXT("missing body never sends pickup"));
    GroundObjectGeneration=8;Check(!SendGroundObjectAction(TEXT("get_object"),TEXT("object:201"))&&Outgoing.IsEmpty(),TEXT("stale world generation cannot send pickup"));GroundObjectGeneration=7;
    Seen.Empty();Seen.Add(TEXT("npc:201"));ApplyGroundObjects(Snapshot,Seen);Check(!Seen.Contains(TEXT("object:201")),TEXT("living OID replacement takes precedence over stale ground row"));
    auto Bad=Clone(Bag);Bad->SetStringField(TEXT("id"),TEXT("object:999"));State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Bad)});Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Seen.IsEmpty(),TEXT("mismatched OID and entity identity rejected"));
    Bad=Clone(Bag);Bad->SetNumberField(TEXT("world_generation"),6);State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Bad)});Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Seen.IsEmpty(),TEXT("stale packet row rejected"));
    Bad=Object(203,488,1364,130,1100);State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Bad)});Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Seen.IsEmpty(),TEXT("ground rendering obeys bounded view distance"));
    auto Missing=Object(204,32767,1364,130,1265);State->SetArrayField(TEXT("objects"),{MakeShared<FJsonValueObject>(Missing)});Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Seen.Contains(TEXT("object:204"))&&EntitySelectionBounds(Entities.FindRef(TEXT("object:204")).Get()).GetSize().Z<49,TEXT("unavailable model uses original bag fallback rather than NPC cylinder"));
    TArray<TSharedPtr<FJsonValue>> Flood;for(int32 I=0;I<129;++I)Flood.Add(MakeShared<FJsonValueObject>(Bag));State->SetArrayField(TEXT("objects"),Flood);Seen.Empty();ApplyGroundObjects(Snapshot,Seen);Check(Seen.IsEmpty(),TEXT("oversized independent object budget rejected"));
    LoadKeyConfiguration();Check(KeyConfiguration->Text(TEXT("target_loot"),0)==TEXT("Hyphen")&&KeyConfiguration->Text(TEXT("get_item"),0)==TEXT("Equals"),TEXT("original FPS loot/get chords avoid accepted bridge shortcuts"));
    ClearEntities();Check(GroundObjectGeneration==-1&&Entities.IsEmpty()&&EntityRows.IsEmpty(),TEXT("session clear releases all ground identities and actors"));
    Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();Outgoing.Empty();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
