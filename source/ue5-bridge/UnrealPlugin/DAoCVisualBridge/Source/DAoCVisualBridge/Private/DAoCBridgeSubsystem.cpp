#include "DAoCBridgeKeyConfiguration.h"
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeApprovedEnvironment.h"
#include "Misc/ScopeExit.h"
#include "HAL/FileManager.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovementKeys.h"
#include "DAoCBridgeTargetTracking.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "IPAddress.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimationAsset.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/HUD.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/PlayerInput.h"
#include "Engine/GameViewportClient.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UnrealClient.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/App.h"
#include "InputCoreTypes.h"
#include "RenderTimer.h"
#include "DynamicRHI.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture.h"

namespace {
double SnapshotLastMs=0,SnapshotPeakMs=0,NetworkFrameMs=0,EquipmentFrameMs=0,ClassicFrameMs=0,MaximumGameplayFrameMs=0;int64 GameplayStalls=0;
struct FBarkCompatibilityStats {int32 Bindings=0,Instances=0,ParametersMatched=0,Failures=0;};
TMap<TWeakObjectPtr<UWorld>,FBarkCompatibilityStats> BarkCompatibilityWorlds;
void ApplyApprovedBarkCompatibility(UWorld* World){
    for(auto It=BarkCompatibilityWorlds.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
    auto& Stats=BarkCompatibilityWorlds.FindOrAdd(TWeakObjectPtr<UWorld>(World));Stats=FBarkCompatibilityStats();
    struct FBinding {UStaticMeshComponent* Component;int32 Slot;UMaterialInterface* Source;};TArray<FBinding> Bindings;
    const FString Prefix=TEXT("/Game/DAoC/Connacht_v01/Ardee_Giant_Grove_v01/Approved_Dark_Bark_v01/Materials/MI_GiantOak_");
    for(TActorIterator<AActor> It(World);It;++It){TInlineComponentArray<UStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components)for(int32 Slot=0;Slot<Component->GetNumMaterials();++Slot){auto* Source=Component->GetMaterial(Slot);if(!Source)continue;const FString Path=Source->GetPathName();
            if(Path==Prefix+TEXT("02_Dark_Willow.MI_GiantOak_02_Dark_Willow")||Path==Prefix+TEXT("03_Dark_Willow.MI_GiantOak_03_Dark_Willow")||Path==Prefix+TEXT("04_Dark_Willow.MI_GiantOak_04_Dark_Willow"))Bindings.Add({Component,Slot,Source});
        }
    }
    if(Bindings.IsEmpty())return;
    auto* Master=LoadObject<UMaterialInterface>(nullptr,TEXT("/DAoCVisualBridge/Compatibility/GroveBark_v01/M_GroveBark_Instanced.M_GroveBark_Instanced"));
    if(!Master||!Master->CheckMaterialUsage_Concurrent(MATUSAGE_InstancedStaticMeshes)){Stats.Failures=Bindings.Num();return;}
    for(const auto& Binding:Bindings){
        auto* Copy=UMaterialInstanceDynamic::Create(Master,Binding.Component);if(!Copy){++Stats.Failures;continue;}
        Copy->CopyMaterialUniformParameters(Binding.Source);
        bool Matched=true;
        for(const TCHAR* Name:{TEXT("UV_U"),TEXT("UV_V")}){float A=0,B=0;const FMaterialParameterInfo Info{FName(Name)};Matched&=Binding.Source->GetScalarParameterValue(Info,A)&&Copy->GetScalarParameterValue(Info,B)&&FMath::IsNearlyEqual(A,B);}
        for(const TCHAR* Name:{TEXT("Color"),TEXT("Normal"),TEXT("Roughness")}){UTexture* A=nullptr;UTexture* B=nullptr;const FMaterialParameterInfo Info{FName(Name)};Matched&=Binding.Source->GetTextureParameterValue(Info,A)&&Copy->GetTextureParameterValue(Info,B)&&A==B;}
        if(!Matched){++Stats.Failures;continue;}
        Binding.Component->SetMaterial(Binding.Slot,Copy);++Stats.Bindings;++Stats.ParametersMatched;
        if(auto* Instances=Cast<UInstancedStaticMeshComponent>(Binding.Component))Stats.Instances+=Instances->GetInstanceCount();else ++Stats.Instances;
    }
}
constexpr int32 MaxFrame=1048576;
double ProfileEndTime(){double Seconds=105;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeProfileSeconds="),Seconds);return FMath::Clamp(Seconds,30.,FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeExtendedRidingTest"))?300.:105.);}
FVector UEPoint(const TArray<TSharedPtr<FJsonValue>>& P) {return FVector((P[0]->AsNumber()-1364)*100,(P[2]->AsNumber()-1263)*100,(P[1]->AsNumber()-130)*100);}
TArray<TSharedPtr<FJsonValue>> JsonPoint(const FVector& P) {return {MakeShared<FJsonValueNumber>(P.X/100+1364),MakeShared<FJsonValueNumber>(P.Z/100+130),MakeShared<FJsonValueNumber>(P.Y/100+1263)};}
bool ValidPoint(const TArray<TSharedPtr<FJsonValue>>& P,int32 Count) {
    if(P.Num()!=Count)return false;
    for(auto& V:P){double N;if(!V.IsValid()||!V->TryGetNumber(N)||!FMath::IsFinite(N)||FMath::Abs(N)>100000)return false;}
    return true;
}
}
bool UDAoCBridgeSubsystem::ShouldCreateSubsystem(UObject* Outer) const {
    UWorld* W=Cast<UWorld>(Outer);
    return W&&W->IsGameWorld()&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridge"));
}
void UDAoCBridgeSubsystem::Initialize(FSubsystemCollectionBase& C) {
    Super::Initialize(C);LoadInterfaceSettings();bAutoInteractionTest=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoInteractionTest"));Status=TEXT("Waiting for the Godot client...");
    ControlsFile=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("DAoCControls.json"));
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeControlsSettings="),ControlsFile);
    FString ControlText;TSharedPtr<FJsonObject> ControlSettings;
    if(FFileHelper::LoadFileToString(ControlText,*ControlsFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(ControlText),ControlSettings)&&ControlSettings.IsValid()){
        double Sensitivity;if(ControlSettings->TryGetNumberField(TEXT("mouse_sensitivity"),Sensitivity)&&FMath::IsFinite(Sensitivity))MouseSensitivity=FMath::Clamp(float(Sensitivity),.05f,1.5f);
        ControlSettings->TryGetBoolField(TEXT("invert_mouse"),bInvertMouse);
    }
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePort="),Port);
    bControls=!FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeReadOnly"));
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeYaw="),CameraYaw);
    bAutoTest=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoTest"));
    bAutoWalk=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoWalk"));
    bAutoDoorTest=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoDoorTest"));
    bProfile=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeProfile"));
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeQuality="),Quality);
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCapture="),CaptureFile);
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRemoteMotionProbe="),RemoteMotionProbePath);
    FString Grid;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeHeights="),Grid)) {
        TArray<uint8> Bytes;if(FFileHelper::LoadFileToArray(Bytes,*Grid)&&Bytes.Num()==257*257*4) {
            Heights.SetNumUninitialized(257*257);FMemory::Memcpy(Heights.GetData(),Bytes.GetData(),Bytes.Num());
        }
    }
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCatalog="),CatalogPath)) {
        FString Text;TSharedPtr<FJsonObject> Catalog;
        if(FFileHelper::LoadFileToString(Text,*CatalogPath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog)&&Catalog.IsValid())
            for(const auto& Pair:Catalog->Values)if(Pair.Value->Type==EJson::Object)ModelCatalog.Add(FString(*Pair.Key),Pair.Value->AsObject());
    }
    LoadEquipmentCatalog();
    FString FoliageFile;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeFoliageCatalog="),FoliageFile)){
        FString Text;TSharedPtr<FJsonObject> Catalog;
        if(FFileHelper::LoadFileToString(Text,*FoliageFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog)&&Catalog.IsValid())
            for(const auto& Pair:Catalog->Values){auto Entry=Pair.Value->AsObject();FString Asset;if(Entry.IsValid()&&(Entry->TryGetStringField(Quality+TEXT("_asset"),Asset)||Entry->TryGetStringField(TEXT("asset"),Asset)))FoliageLODAssets.Add(FString(*Pair.Key),Asset);}
    }
    FString CollisionFile;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCollisionCatalog="),CollisionFile)){
        FString Text;TSharedPtr<FJsonObject> Catalog;
        if(FFileHelper::LoadFileToString(Text,*CollisionFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog)&&Catalog.IsValid()&&Catalog->GetIntegerField(TEXT("zone_id"))==207){
            const TSharedPtr<FJsonObject>* Models;
            if(Catalog->TryGetObjectField(TEXT("models"),Models))for(const auto& Pair:(*Models)->Values)if(Pair.Value->Type==EJson::Object)NavigationMeshes.Add(FString(*Pair.Key),Pair.Value->AsObject());
        }
    }
}
void UDAoCBridgeSubsystem::Deinitialize() {
    FWorldDelegates::LevelAddedToWorld.RemoveAll(this);FWorldDelegates::LevelRemovedFromWorld.RemoveAll(this);
    RemoveWorldPointerInput();
    SetMouseLook(false);
    if(bConnected&&!bExiting)Send(TEXT("logout"));
    if(Socket&&Outgoing.Num()){int32 Sent=0;Socket->Send(Outgoing.GetData(),Outgoing.Num(),Sent);}
    if(NameplateDrawHandle.IsValid())AHUD::OnHUDPostRender.Remove(NameplateDrawHandle);
    RemoveClassicUI();RemoveChat();RemovePlayerStatusUI();RemoveInventoryUI();RemoveInteractionUI();Disconnect();Super::Deinitialize();
}
void UDAoCBridgeSubsystem::OnWorldBeginPlay(UWorld& InWorld){Super::OnWorldBeginPlay(InWorld);FWorldDelegates::LevelAddedToWorld.AddUObject(this,&UDAoCBridgeSubsystem::GeometryLevelChanged);FWorldDelegates::LevelRemovedFromWorld.AddUObject(this,&UDAoCBridgeSubsystem::GeometryLevelChanged);ConfigureCollisions();ApplyQuality();ApplyApprovedBarkCompatibility(&InWorld);}
TStatId UDAoCBridgeSubsystem::GetStatId() const {RETURN_QUICK_DECLARE_CYCLE_STAT(DAoCBridge,STATGROUP_Tickables);}
void UDAoCBridgeSubsystem::ClearEntities(){WorldClockHour=-1.;ClearLiveRiding();if(TargetTracking)TargetTracking->Reset();if(MovementKeys)MovementKeys->Reset();CloseOptions();RemoveCharacterLobby();ClearSpellVisuals();ClearSpellAudio();ClearFootsteps();ClearWaterMovement();AnsweredSightQueries.Empty();RemoveClassicUI();RemoveChat();ClearLocalEquipment();RemovePlayerStatusUI();PlayerState.Reset();PlayerStatusRevision=-1;RemoveInventoryUI();InventoryState.Reset();InventoryRevision=-1;bInventoryOpen=false;SelectedItemSlot=-1;bInventoryMoving=false;bConfirmSale=false;RemoveInteractionUI();for(auto& P:Entities)if(IsValid(P.Value))P.Value->Destroy();Entities.Empty();AnimationStates.Empty();PosePlayback.Empty();EntityModels.Empty();RemoteMotion.Empty();EntityRows.Empty();NameplateVisibility.Empty();InteractionState.Reset();InteractionRevision=-1;bInteractionHovered=false;LocalPositionRevision=-1;bLocalAvailable=false;NpcCount=0;}
void UDAoCBridgeSubsystem::Disconnect(){
    if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}
    bConnected=false;Incoming.Empty();Outgoing.Empty();Session.Empty();Sequence=0;ClearEntities();RetryAt=FPlatformTime::Seconds()+1;
}
void UDAoCBridgeSubsystem::Connect(){
    if(Port<1024||Port>65535)return;
    ISocketSubsystem* SS=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
    Socket=SS->CreateSocket(NAME_Stream,TEXT("DAoC loopback visual bridge"),false);if(!Socket)return;
    Socket->SetNonBlocking(true);Socket->SetNoDelay(true);
    auto Address=SS->CreateInternetAddr();bool Valid=false;Address->SetIp(TEXT("127.0.0.1"),Valid);Address->SetPort(Port);
    Socket->Connect(*Address);RetryAt=FPlatformTime::Seconds()+1;
}
void UDAoCBridgeSubsystem::Send(const FString& Action,TSharedPtr<FJsonObject> Values){
    if(Session.IsEmpty()||!Socket)return;
    auto Obj=Values.IsValid()?Values:MakeShared<FJsonObject>();
    Obj->SetStringField(TEXT("type"),TEXT("command"));Obj->SetStringField(TEXT("session"),Session);
    Obj->SetStringField(TEXT("id"),FString::Printf(TEXT("native:%d"),++CommandId));Obj->SetStringField(TEXT("action"),Action);
    FString Text;auto Writer=TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text);FJsonSerializer::Serialize(Obj,Writer);Text+=TEXT("\n");
    FTCHARToUTF8 Utf8(*Text);if(Outgoing.Num()+Utf8.Length()<MaxFrame)Outgoing.Append(reinterpret_cast<const uint8*>(Utf8.Get()),Utf8.Length());
}
void UDAoCBridgeSubsystem::Handle(TSharedPtr<FJsonObject> M){
    FString Type;if(!M->TryGetStringField(TEXT("type"),Type))return;
    if(Type==TEXT("hello")){
        FString Protocol,NewSession;double Version=0;
        if(!M->TryGetStringField(TEXT("protocol"),Protocol)||Protocol!=TEXT("daoc-visual-bridge")||!M->TryGetNumberField(TEXT("version"),Version)||Version!=1||!M->TryGetStringField(TEXT("session"),NewSession))return;
        if(NewSession!=Session){ClearEntities();Sequence=0;}Session=NewSession;LastSnapshot=FPlatformTime::Seconds();Send(TEXT("ping"));
    }else if(Type==TEXT("snapshot"))ApplySnapshot(M);
}
AActor* UDAoCBridgeSubsystem::CreateEntity(const FString& Id,TSharedPtr<FJsonObject> Row,const FVector& Pos){
    FString Model=FString::FromInt(Row->GetIntegerField(TEXT("model_id")));AActor* Actor=nullptr;
    const float EntityCull=Id==TEXT("player:local")?0.f:Quality==TEXT("accessible")?6000.f:Quality==TEXT("balanced")?9000.f:Quality==TEXT("high")?12500.f:15000.f;
    const float NameCull=Quality==TEXT("accessible")?2500.f:Quality==TEXT("balanced")?3500.f:Quality==TEXT("high")?5000.f:6000.f;
    auto* Entry=ModelCatalog.Find(Model);FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    FString Asset,Kind;
    if(Entry&&(*Entry)->TryGetStringField(TEXT("type"),Kind)&&Kind==TEXT("hidden"))return nullptr;
    if(Entry&&(*Entry)->TryGetStringField(TEXT("asset"),Asset)&&(*Entry)->TryGetStringField(TEXT("type"),Kind)){
        if(Kind==TEXT("skeletal")){
            if(auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Asset)){
                auto* A=GetWorld()->SpawnActor<ASkeletalMeshActor>(Pos,FRotator::ZeroRotator,Params);
                A->GetSkeletalMeshComponent()->SetSkeletalMeshAsset(Mesh);A->GetSkeletalMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);Actor=A;
                A->GetSkeletalMeshComponent()->SetCullDistance(EntityCull);A->GetSkeletalMeshComponent()->SetCastShadow(false);
                A->GetSkeletalMeshComponent()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
                A->GetSkeletalMeshComponent()->bEnableUpdateRateOptimizations=Id!=TEXT("player:local");
                if(Id==TEXT("player:local")){A->GetSkeletalMeshComponent()->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;A->GetSkeletalMeshComponent()->bPerBoneMotionBlur=true;}
                FString Idle;if((*Entry)->TryGetStringField(TEXT("idle"),Idle))if(auto* Anim=LoadObject<UAnimationAsset>(nullptr,*Idle))A->GetSkeletalMeshComponent()->PlayAnimation(Anim,true);
            }
        }else if(auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Asset)){
            auto* A=GetWorld()->SpawnActor<AStaticMeshActor>(Pos,FRotator::ZeroRotator,Params);
            A->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);A->GetStaticMeshComponent()->SetStaticMesh(Mesh);
            A->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);A->GetStaticMeshComponent()->SetCullDistance(EntityCull);Actor=A;
        }
    }
    if(!Actor){
        auto* A=GetWorld()->SpawnActor<AStaticMeshActor>(Pos,FRotator::ZeroRotator,Params);
        A->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        A->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));
        A->GetStaticMeshComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);A->SetActorScale3D(FVector(.5,.5,1.8));Actor=A;
        A->GetStaticMeshComponent()->SetCastShadow(false);A->GetStaticMeshComponent()->SetCullDistance(EntityCull);
    }
    else{
        ++ModeledEntities;double BaseScale=1,Size=50;
        if(Entry)(*Entry)->TryGetNumberField(TEXT("scale"),BaseScale);Row->TryGetNumberField(TEXT("size"),Size);
        Actor->SetActorScale3D(FVector(FMath::Clamp(BaseScale*Size/50.,.01,20.)));
    }
    ApplyBodyArmour(Actor,nullptr);
    Actor->Tags.Add(TEXT("DAoCBridgeEntity"));
    Entities.Add(Id,Actor);EntityModels.Add(Id,FCString::Atoi(*Model));return Actor;
}
void UDAoCBridgeSubsystem::ApplySnapshot(TSharedPtr<FJsonObject> M){
    const double SnapshotBegan=FPlatformTime::Seconds();ON_SCOPE_EXIT{SnapshotLastMs=(FPlatformTime::Seconds()-SnapshotBegan)*1000;SnapshotPeakMs=FMath::Max(SnapshotPeakMs,SnapshotLastMs);};
    FString S;double Seq=0,Zone=0;const TArray<TSharedPtr<FJsonValue>>* Rows;
    const TArray<TSharedPtr<FJsonValue>>* Origin;
    if(!M->TryGetStringField(TEXT("session"),S)||S!=Session||!M->TryGetNumberField(TEXT("seq"),Seq)||Seq<=Sequence||
       !M->TryGetNumberField(TEXT("zone_id"),Zone)||Zone!=207||!M->TryGetArrayField(TEXT("entities"),Rows)||Rows->Num()>2048||
       !M->TryGetArrayField(TEXT("origin_m"),Origin)||!ValidPoint(*Origin,3)||(*Origin)[0]->AsNumber()!=1364||(*Origin)[1]->AsNumber()!=130||(*Origin)[2]->AsNumber()!=1263)return;
    bool InGame=false;M->TryGetBoolField(TEXT("in_game"),InGame);const TSharedPtr<FJsonObject>* Lobby=nullptr;
    if(M->TryGetObjectField(TEXT("character_lobby"),Lobby))ApplyCharacterLobby(*Lobby,InGame);
    if(!CharacterLobbyOverlay.IsValid()){
    const TSharedPtr<FJsonObject>* Interaction=nullptr;
    if(M->TryGetObjectField(TEXT("interaction"),Interaction))ApplyInteraction(*Interaction);
    const TSharedPtr<FJsonObject>* Inventory=nullptr;
    if(M->TryGetObjectField(TEXT("inventory"),Inventory))ApplyInventory(*Inventory);
    const TSharedPtr<FJsonObject>* PlayerStatus=nullptr;if(M->TryGetObjectField(TEXT("player_status"),PlayerStatus))ApplyPlayerStatus(*PlayerStatus);
    const TSharedPtr<FJsonObject>* Clock=nullptr;ApplyWorldClock(M->TryGetObjectField(TEXT("world_clock"),Clock)?*Clock:nullptr);
    const TSharedPtr<FJsonObject>* Classic=nullptr;if(M->TryGetObjectField(TEXT("classic_ui"),Classic))ApplyClassicUI(*Classic);
    ApplyChat(M);
    const TSharedPtr<FJsonObject>* Exchange=nullptr;if(M->TryGetObjectField(TEXT("exchange"),Exchange))ApplyExchange(*Exchange);
    const TSharedPtr<FJsonObject>* Guild=nullptr;if(M->TryGetObjectField(TEXT("guild"),Guild))ApplyGuild(*Guild);
        const TSharedPtr<FJsonObject>* EmblemPicker=nullptr;if(M->TryGetObjectField(TEXT("emblem_picker"),EmblemPicker))ApplyEmblemPicker(*EmblemPicker);
    }
    ApplyZoneLights(M);
    Sequence=static_cast<int64>(Seq);LastSnapshot=FPlatformTime::Seconds();TSet<FString> Seen;NpcCount=0;
    M->TryGetStringField(TEXT("character"),Character);M->TryGetStringField(TEXT("status"),Status);
    double Speed=0;if(M->TryGetNumberField(TEXT("max_speed_mps"),Speed)&&FMath::IsFinite(Speed))ServerRunSpeed=FMath::Clamp(float(Speed*100),0.f,1432.5f);
    const TArray<TSharedPtr<FJsonValue>>* DoorStates;
    if(M->TryGetArrayField(TEXT("doors"),DoorStates)&&DoorStates->Num()<=64)for(const auto& Value:*DoorStates){
        if(Value->Type!=EJson::Object)continue;auto State=Value->AsObject();double Id=0;bool Open=false;
        if(State->TryGetNumberField(TEXT("id"),Id)&&FMath::IsFinite(Id)&&State->TryGetBoolField(TEXT("open"),Open))if(auto* Door=Doors.Find(int64(Id))){if(Door->Open!=Open)++DoorStateChanges;Door->Open=Open;}
    }
    for(auto& Value:*Rows){
        auto Row=Value->AsObject();if(!Row.IsValid())continue;
        FString Id,Kind;const TArray<TSharedPtr<FJsonValue>>* P;const TArray<TSharedPtr<FJsonValue>>* F;
        if(!Row->TryGetStringField(TEXT("id"),Id)||Id.Len()>128||!Row->TryGetStringField(TEXT("kind"),Kind)||
           !Row->TryGetArrayField(TEXT("position_m"),P)||!ValidPoint(*P,3)||!Row->TryGetArrayField(TEXT("forward_xz"),F)||!ValidPoint(*F,2))continue;
        if(Id.IsEmpty()||(Kind!=TEXT("player")&&Kind!=TEXT("npc"))||Seen.Contains(Id))continue;
        Seen.Add(Id);EntityRows.Add(Id,Row);FVector Position=UEPoint(*P);float Yaw=FMath::RadiansToDegrees(FMath::Atan2((*F)[1]->AsNumber(),(*F)[0]->AsNumber()));
        if(Id==TEXT("player:local")&&Kind==TEXT("player")){
            double Revision=-1;Row->TryGetNumberField(TEXT("position_revision"),Revision);
            const bool Corrected=FMath::IsFinite(Revision)&&Revision>=0&&int64(Revision)!=LocalPositionRevision;
            if(!bLocalAvailable||Corrected||(Position-PlayerPosition).Size()>1000){PlayerPosition=Position;bHavePlayer=true;if(IsValid(PlayerPawn)){StopTargetTracking(true);PlayerPawn->TeleportFeet(Position);PreviousFeet=Position;if(IsValid(Camera)){Camera->GetCameraComponent()->bConstrainAspectRatio=false;Camera->AttachToComponent(PlayerPawn->CameraArm,FAttachmentTransformRules::SnapToTargetNotIncludingScale,USpringArmComponent::SocketName);if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);}}}
            bLocalAvailable=true;if(Corrected)LocalPositionRevision=int64(Revision);
            if(PlayerStartedAt==0){PlayerStartedAt=FPlatformTime::Seconds();StartPosition=PlayerPosition;}
            /* Local visuals are updated below; never treat remote players as the local pawn. */
        }
        if(Kind==TEXT("npc"))++NpcCount;
        const int32 Model=Row->GetIntegerField(TEXT("model_id"));
        if(EntityModels.Contains(Id)&&EntityModels[Id]!=Model){
            if(auto* Old=Entities.Find(Id))if(IsValid(*Old))(*Old)->Destroy();
            Entities.Remove(Id);EntityModels.Remove(Id);AnimationStates.Remove(Id);PosePlayback.Remove(Id);
        }
        AActor* A=Entities.Contains(Id)?Entities[Id].Get():CreateEntity(Id,Row,Position);
        if(IsValid(A)){
            double Offset=0;auto* Entry=ModelCatalog.Find(FString::FromInt(Row->GetIntegerField(TEXT("model_id"))));
            if(Entry)(*Entry)->TryGetNumberField(TEXT("yaw_offset"),Offset);
            const bool Smoothed=Id!=TEXT("player:local")&&Row->HasField(TEXT("motion"));
            if(Smoothed)ApplyRemoteMotion(Id,A,Row,Position);
            else if(!A->GetActorLocation().Equals(Position,.01))A->SetActorLocation(Position);
            FRotator Rotation(0,Yaw+Offset,0);if(!(Id==TEXT("player:local")&&!PlayerCanMove())&&!A->GetActorRotation().Equals(Rotation,.01))A->SetActorRotation(Rotation);
            double Size=50,Base=1;Row->TryGetNumberField(TEXT("size"),Size);if(Entry){(*Entry)->TryGetNumberField(TEXT("scale"),Base);A->SetActorScale3D(FVector(FMath::Clamp(Base*Size/50.,.01,20.)));}
            FString State;Row->TryGetStringField(TEXT("state"),State);
            double Heading=0;if(Kind==TEXT("npc")&&Row->TryGetNumberField(TEXT("heading_4096"),Heading))MaxNpcHeadingError=FMath::Max(MaxNpcHeadingError,double(FMath::Abs(FRotator::NormalizeAxis(A->GetActorRotation().Yaw-float(90+Heading*360/4096+Offset)))));
            if(!Smoothed&&Id!=TEXT("player:local"))SetEntityAnimation(Id,State);
        }
    }
    TArray<FString> Gone;for(auto& Pair:Entities)if(!Seen.Contains(Pair.Key))Gone.Add(Pair.Key);
    for(auto& Id:Gone){if(IsValid(Entities[Id]))Entities[Id]->Destroy();Entities.Remove(Id);EntityModels.Remove(Id);RemoteMotion.Remove(Id);EntityRows.Remove(Id);NameplateVisibility.Remove(Id);AnimationStates.Remove(Id);PosePlayback.Remove(Id);}
    if(!Seen.Contains(TEXT("player:local")))bLocalAvailable=false;
    ApplyTargetTracking(M);
    ApplyLiveRiding(M);
    ApplySpellVisuals(M);
    ApplySpellAudio(M);
    AnswerLineOfSightQueries(M);
}
float UDAoCBridgeSubsystem::GroundHeight(float X,float Y) const {
    if(Heights.Num()!=257*257)return PlayerPosition.Z;
    double GX=FMath::Clamp((X/100+1364)/6.4,0.,255.999),GZ=FMath::Clamp((Y/100+1263)/6.4,0.,255.999);
    int I=FMath::FloorToInt(GX),J=FMath::FloorToInt(GZ);double U=GX-I,V=GZ-J;
    float A=Heights[J*257+I],B=Heights[J*257+I+1],C=Heights[(J+1)*257+I],D=Heights[(J+1)*257+I+1];
    return ((U+V<=1)?A+U*(B-A)+V*(C-A):D+(1-U)*(C-D)+(1-V)*(B-D))*100-13000;
}
void UDAoCBridgeSubsystem::SaveControls(){
    auto O=MakeShared<FJsonObject>();FString Existing;TSharedPtr<FJsonObject> Previous;
    if(FFileHelper::LoadFileToString(Existing,*ControlsFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Existing),Previous)&&Previous.IsValid())O=Previous.ToSharedRef();
    O->SetNumberField(TEXT("mouse_sensitivity"),MouseSensitivity);O->SetBoolField(TEXT("invert_mouse"),bInvertMouse);
    FString Text;auto W=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(O,W);FFileHelper::SaveStringToFile(Text,*ControlsFile);
}
void UDAoCBridgeSubsystem::SetMouseLook(bool Enabled){
    if(Enabled==bMouseLook)return;
    APlayerController* PC=GetWorld()?GetWorld()->GetFirstPlayerController():nullptr;if(!PC)return;
    auto* Viewport=GetWorld()->GetGameViewport();
    if(Enabled){
        PC->GetMousePosition(CursorReturnX,CursorReturnY);PC->bShowMouseCursor=false;
        FInputModeGameOnly Mode;Mode.SetConsumeCaptureMouseDown(false);PC->SetInputMode(Mode);
        if(Viewport){Viewport->SetMouseCaptureMode(EMouseCaptureMode::CapturePermanently_IncludingInitialMouseDown);Viewport->SetMouseLockMode(EMouseLockMode::LockAlways);}
        bSkipMouseDelta=true;
    }else{
        PC->bShowMouseCursor=true;
        FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(false);Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC->SetInputMode(Mode);
        if(Viewport){Viewport->SetMouseCaptureMode(EMouseCaptureMode::CaptureDuringRightMouseDown);Viewport->SetMouseLockMode(EMouseLockMode::DoNotLock);}
        PC->SetMouseLocation(FMath::RoundToInt(CursorReturnX),FMath::RoundToInt(CursorReturnY));
    }
    bMouseLook=Enabled;
}
void UDAoCBridgeSubsystem::UpdateControls(float Dt){
    if(CharacterLobbyOverlay.IsValid())return;
    LoadKeyConfiguration();
    APlayerController* PC=GetWorld()->GetFirstPlayerController();if(!PC||!bHavePlayer)return;
    if(!PlayerPawn){
        if(APawn* Old=PC->GetPawn()){
            Old->SetActorHiddenInGame(true);Old->DisableInput(PC);Old->SetActorEnableCollision(false);
            if(auto* OldCharacter=Cast<ACharacter>(Old))OldCharacter->GetCharacterMovement()->DisableMovement();
            PC->UnPossess();
        }
        FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
        PlayerPawn=GetWorld()->SpawnActor<ADAoCBridgeCharacter>(PlayerPosition+FVector(0,0,88),FRotator(0,CameraYaw,0),Params);
        if(!PlayerPawn)return;
        PlayerPawn->Tags.Add(TEXT("DAoCBridgePlayer"));PC->Possess(PlayerPawn);
        if(!bNavigationReady){PlayerPawn->SetActorEnableCollision(false);PlayerPawn->GetCharacterMovement()->DisableMovement();Status=TEXT("Collision data is missing; movement is unavailable");}
        PreviousFeet=PlayerPosition=PlayerPawn->FeetPosition();
        Camera=GetWorld()->SpawnActor<ACameraActor>(FVector::ZeroVector,FRotator::ZeroRotator,Params);
        Camera->GetCameraComponent()->bConstrainAspectRatio=false;Camera->AttachToComponent(PlayerPawn->CameraArm,FAttachmentTransformRules::SnapToTargetNotIncludingScale,USpringArmComponent::SocketName);
        PC->SetViewTarget(Camera);PC->bShowMouseCursor=true;ApplyCameraView();
        if(PC->PlayerInput){
            // Editor -game inherits debug F-key view modes. Reserve our own
            // controls so adjusting sensitivity cannot switch render modes.
            PC->PlayerInput->DebugExecBindings.RemoveAll([](const FKeyBind& Bind){return Bind.Key==EKeys::F1||Bind.Key==EKeys::F2||Bind.Key==EKeys::F3||Bind.Key==EKeys::F4||Bind.Key==EKeys::F5||Bind.Key==EKeys::F6;});
            for(const FKey Key:{EKeys::MouseX,EKeys::MouseY}){FInputAxisProperties Properties;PC->PlayerInput->GetAxisProperties(Key,Properties);Properties.Sensitivity=1;Properties.DeadZone=0;Properties.Exponent=1;Properties.bInvert=false;PC->PlayerInput->SetAxisProperties(Key,Properties);}
        }
        FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(false);Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC->SetInputMode(Mode);
    }
    auto* Viewport=GetWorld()->GetGameViewport();const bool Focused=(Viewport&&Viewport->Viewport&&Viewport->Viewport->HasFocus())||FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoTargetTrackingTest"));
    if(bOptionsOpen&&PC->WasInputKeyJustPressed(EKeys::Escape)){CloseOptions();return;}
    const bool Typing=ExchangeTyping()||bOptionsOpen;const bool Dead=PlayerIsDead();const bool FacingLocked=!PlayerCanMove();
    if(!Focused||Dead||bChatOpen||Typing){bMouseLookToggle=false;bLeftPointerHeld=bRightPointerHeld=bRightPointerDragged=false;}
    if(!bChatOpen&&!Typing&&FPlatformTime::Seconds()-ChatClosedAt>.2&&PC->WasInputKeyJustPressed(EKeys::Enter))OpenChat();
    PlayerPawn->bUseControllerRotationYaw=false;
    if(Dead){PlayerPawn->ConsumeMovementInputVector();PlayerPawn->GetCharacterMovement()->DisableMovement();}
    else if(!bLocalMounted&&bNavigationReady&&PlayerPawn->GetCharacterMovement()->MovementMode==MOVE_None)PlayerPawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    if(!Dead&&!bChatOpen&&!Typing&&PC->WasInputKeyJustPressed(EKeys::F3))bMouseLookToggle=!bMouseLookToggle;
    SetMouseLook(!Dead&&!bChatOpen&&!Typing&&bControls&&!bExiting&&Focused&&!ClassicUIHovered()&&!InventoryHovered()&&!PlayerStatusHovered()&&(bMouseLookToggle||(bRightPointerHeld&&bRightPointerDragged)));
    if(bMouseLook){
        float DX=0,DY=0;PC->GetInputMouseDelta(DX,DY);
        if(!bSkipMouseDelta){CameraYaw=FRotator::NormalizeAxis(CameraYaw+DX*MouseSensitivity);CameraPitch=FMath::Clamp(CameraPitch+DY*MouseSensitivity*(bInvertMouse?-1.f:1.f),-75.f,65.f);}
        bSkipMouseDelta=false;
    }
    if(Focused&&!bChatOpen&&!Typing&&(PC->WasInputKeyJustPressed(EKeys::F4)||PC->WasInputKeyJustPressed(EKeys::F5))){
        MouseSensitivity=FMath::Clamp(MouseSensitivity*(PC->WasInputKeyJustPressed(EKeys::F5)?1.25f:.8f),.05f,1.5f);SaveControls();
    }
    UpdateRemoteMotionProbe();
    if(!Dead)PC->SetControlRotation(FRotator(CameraPitch,CameraYaw,0));
    UpdateWaterMovement(!bLocalMounted&&!Dead&&bNavigationReady&&bLocalAvailable&&!Session.IsEmpty());
    TickLiveRiding(Dt);
    if(!MovementKeys){MovementKeys=MakeShared<FBridgeMovementKeys>();FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/MovementKeys_v01/movement.json");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeMovementKeysCatalog="),Path);MovementKeys->Load(Path);}
    const bool TrackingEnabled=!bLocalMounted&&Focused&&bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&!Dead&&!FacingLocked&&!bChatOpen&&!Typing;
    const bool InputAvailable=TrackingEnabled&&FPlatformTime::Seconds()-ChatClosedAt>.2;
    FBridgeMovementKeys::FFrame Keys;
    if(!FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoMovementKeysTest")))Keys=MovementKeys->Advance(InputAvailable,KeyConfiguration->Pressed(PC,TEXT("run_lock")),KeyConfiguration->Pressed(PC,TEXT("walk")),
        KeyConfiguration->Pressed(PC,TEXT("move_forward")),KeyConfiguration->Pressed(PC,TEXT("move_back")),KeyConfiguration->Held(PC,TEXT("move_forward")),KeyConfiguration->Held(PC,TEXT("move_back")),KeyConfiguration->Held(PC,TEXT("strafe_left")),KeyConfiguration->Held(PC,TEXT("strafe_right")),
        PC->IsInputKeyDown(EKeys::LeftShift)||PC->IsInputKeyDown(EKeys::RightShift),bLeftPointerHeld&&bRightPointerHeld);
    if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoMovementKeysTest"))){
        const double T=FPlatformTime::Seconds()-PlayerStartedAt;
        const bool Run=T>=8&&MovementKeysTestPhase==0,Walk=T>=12&&MovementKeysTestPhase==1,Back=T>=15&&MovementKeysTestPhase==2;
        if(Run||Walk||Back)++MovementKeysTestPhase;
        Keys=MovementKeys->Advance(T>=8&&T<18,Run,Walk,false,Back,false,T>=15&&T<18,false,false,false,false);
    }
    PlayerPawn->GetCharacterMovement()->MaxWalkSpeed=ServerRunSpeed*Keys.SpeedFactor;
    FVector Desired=FVector::ZeroVector;
    if(bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&!bChatOpen&&!Typing&&FPlatformTime::Seconds()-ChatClosedAt>.2){
        if(InputAvailable)for(const TCHAR* Action:{TEXT("face"),TEXT("follow"),TEXT("stick")})if(KeyConfiguration->Pressed(PC,Action))RequestTargetTracking(Action);
        float Fwd=Keys.Forward;
        float Right=Keys.Right;
        FRotator Flat(0,CameraYaw,0);Desired=(Flat.Vector()*Fwd+FRotationMatrix(Flat).GetUnitAxis(EAxis::Y)*Right).GetClampedToMaxSize(1);
        if(bAutoTest){double Elapsed=FPlatformTime::Seconds()-PlayerStartedAt;Desired=(Elapsed>20&&Elapsed<25)?FVector(1,0,0):FVector::ZeroVector;
            if(bAutoWalk){int32 Leg=int32((Elapsed-20)/8);Desired=(Elapsed>=20&&Elapsed<52)?((Leg<2?Flat.Vector():FRotationMatrix(Flat).GetUnitAxis(EAxis::Y))*(Leg%2==0?1:-1)):FVector::ZeroVector;}
        }
        if(!RemoteMotionProbePath.IsEmpty())Desired=FVector::ZeroVector;
        if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeOpenInventory"))||FParse::Param(FCommandLine::Get(),TEXT("DaocBridgePoseVisualTest"))||FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeEquipmentVisualTest"))||FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest")))Desired=FVector::ZeroVector;
        if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoWaterTest"))){const double T=FPlatformTime::Seconds()-PlayerStartedAt;Desired=T>=8&&T<12?FVector(1,0,0):T>=16&&T<28&&PlayerPosition.X>StartPosition.X+15?FVector(-1,0,0):FVector::ZeroVector;}
        if(bAutoDoorTest)UpdateDoorTest(float(FPlatformTime::Seconds()-PlayerStartedAt),Desired);
        if(!PlayerCanMove()||ServerRunSpeed<=0){Desired=FVector::ZeroVector;PlayerPawn->ConsumeMovementInputVector();PlayerPawn->GetCharacterMovement()->StopMovementImmediately();}
        const bool ManualTrackInput=KeyConfiguration->Held(PC,TEXT("move_forward"))||KeyConfiguration->Held(PC,TEXT("move_back"))||KeyConfiguration->Held(PC,TEXT("strafe_left"))||KeyConfiguration->Held(PC,TEXT("strafe_right"))||(bLeftPointerHeld&&bRightPointerHeld)||(MovementKeys&&MovementKeys->RunLock);
        const bool Tracking=UpdateTargetTracking(TrackingEnabled,ManualTrackInput,Desired);
        if(!Tracking&&!FacingLocked&&!Desired.IsNearlyZero())PlayerPawn->SetActorRotation(FRotator(0,CameraYaw,0));
        if(Focused&&KeyConfiguration->Pressed(PC,TEXT("jump"))){if(bLocalMounted)RequestDismount();else if(!FacingLocked&&!bLocalSwimming&&ServerRunSpeed>0&&PlayerPawn->GetCharacterMovement()->IsMovingOnGround())PlayerPawn->Jump();}
        if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeAutoJumpTest"))){
            const double T=FPlatformTime::Seconds()-PlayerStartedAt;
            if(T>=8&&T<8.15&&PlayerPawn->GetCharacterMovement()->IsMovingOnGround())PlayerPawn->Jump();
            Desired=FVector::ZeroVector;
        }
        PlayerPawn->AddMovementInput(Desired,1);
        UpdateClassicInput();
        UpdatePlayerStatusInput();
        if(PC->WasInputKeyJustPressed(EKeys::F1))RequestGMMode(false);
        if(PC->WasInputKeyJustPressed(EKeys::F2)){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("text"),TEXT("/loc"));Send(TEXT("chat"),V);}
        UpdateInteractionInput();
        if(KeyConfiguration->Pressed(PC,TEXT("show_inventory")))ToggleInventory();
        if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeOpenInventory"))&&!bInventoryOpen&&!(ClassicState.IsValid()&&bClassicOpen&&ClassicTab==TEXT("inventory"))&&FPlatformTime::Seconds()-PlayerStartedAt>15)ToggleInventory();
        if(bAutoInteractionTest)UpdateInteractionTest(float(FPlatformTime::Seconds()-PlayerStartedAt));
        if(KeyConfiguration->Pressed(PC,TEXT("interact"))&&!InteractSelected()&&!InteractDoor()){
            FString BestId;double Best=600;for(auto& Pair:Entities){FVector Aim;if(!Pair.Key.StartsWith(TEXT("npc:"))||!CanSelect(Pair.Key,Aim))continue;double Distance=FVector::Dist(Pair.Value->GetActorLocation(),PlayerPosition);if(Distance<Best){Best=Distance;BestId=Pair.Key;}}
            if(!BestId.IsEmpty())SelectEntity(BestId,true);
        }
        if(PC->WasInputKeyJustPressed(EKeys::Escape)&&!CloseClassicPanel()&&!CloseInventory()&&!CloseInteraction())OpenOptions();
    }else{PlayerPawn->ConsumeMovementInputVector();PlayerPawn->GetCharacterMovement()->StopMovementImmediately();}
    if(!TrackingEnabled)StopTargetTracking(true);
    UpdateWaterMovement(!bLocalMounted&&!Dead&&bNavigationReady&&bLocalAvailable&&!Session.IsEmpty(),Desired.IsNearlyZero());
    PlayerPosition=PlayerPawn->FeetPosition();TravelledMetres+=FVector::Dist2D(PreviousFeet,PlayerPosition)/100;PreviousFeet=PlayerPosition;
    PeakMovementSpeed=FMath::Max(PeakMovementSpeed,PlayerPawn->GetVelocity().Size2D()/100);
    if(!Dead&&!bChatOpen&&!Typing&&bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&FPlatformTime::Seconds()-LastMove>.1){
        auto Values=MakeShared<FJsonObject>();Values->SetArrayField(TEXT("position_m"),JsonPoint(PlayerPosition));
        Values->SetArrayField(TEXT("forward_xz"),{MakeShared<FJsonValueNumber>(FMath::Cos(FMath::DegreesToRadians(PlayerPawn->GetActorRotation().Yaw))),MakeShared<FJsonValueNumber>(FMath::Sin(FMath::DegreesToRadians(PlayerPawn->GetActorRotation().Yaw)))});
        Values->SetStringField(TEXT("target_entity_id"),CurrentTarget());Values->SetBoolField(TEXT("target_in_view"),PlayerSeesTarget());
        Values->SetBoolField(TEXT("swimming"),bLocalSwimming);Values->SetBoolField(TEXT("on_ground"),!bLocalMounted&&PlayerPawn->GetCharacterMovement()->IsMovingOnGround());Values->SetNumberField(TEXT("vertical_speed_mps"),bLocalMounted?0:PlayerPawn->GetCharacterMovement()->IsMovingOnGround()&&PlayerPawn->PendingLandingSpeedMps>0?-PlayerPawn->PendingLandingSpeedMps:PlayerPawn->GetVelocity().Z/100);
        Values->SetNumberField(TEXT("speed_mps"),bLocalMounted?RidingSpeedMps:PlayerPawn->GetVelocity().Size2D()/100);Send(TEXT("move"),Values);PlayerPawn->PendingLandingSpeedMps=0;LastMove=FPlatformTime::Seconds();
    }
    if(auto* Local=Entities.Find(TEXT("player:local")))if(IsValid(*Local)){
        if(IsValid(Camera))(*Local)->SetActorHiddenInGame(FVector::DistSquared(Camera->GetActorLocation(),PlayerPosition+FVector(0,0,170))<10000);
        if(auto* Figure=Cast<ASkeletalMeshActor>(*Local))Figure->GetSkeletalMeshComponent()->ForceMotionVector();
        if(!Dead){(*Local)->SetActorLocation(PlayerPosition);if(!FacingLocked||bLocalMounted)(*Local)->SetActorRotation(FRotator(0,PlayerPawn->GetActorRotation().Yaw-90,0));}
        const bool Airborne=PlayerPawn->GetCharacterMovement()->IsFalling();
        if(Airborne&&PlayerPawn->AirborneSince==0)PlayerPawn->AirborneSince=FPlatformTime::Seconds();
        if(!Airborne)PlayerPawn->AirborneSince=0;
        const bool JumpPose=Airborne&&(PlayerPawn->GetVelocity().Z>0||FPlatformTime::Seconds()-PlayerPawn->AirborneSince>.15);
        const bool Backward=PlayerPawn->GetVelocity().Size2D()>5&&FVector::DotProduct(PlayerPawn->GetVelocity(),PlayerPawn->GetActorForwardVector())<-5;
        FString State=bLocalMounted&&bLocalSeatReady?TEXT("ride_horse"):JumpPose?TEXT("jump"):bLocalSwimming?TEXT("swim"):Backward?TEXT("walk_back"):PlayerPawn->GetVelocity().Size2D()>250?TEXT("run"):PlayerPawn->GetVelocity().Size2D()>5?TEXT("walk"):TEXT("idle");
        SetEntityAnimation(TEXT("player:local"),State);
    }
}
void UDAoCBridgeSubsystem::WriteReport(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeReport="),File))return;
    auto O=MakeShared<FJsonObject>();O->SetNumberField(TEXT("snapshot_last_ms"),SnapshotLastMs);O->SetNumberField(TEXT("snapshot_peak_ms"),SnapshotPeakMs);O->SetNumberField(TEXT("network_frame_ms"),NetworkFrameMs);O->SetNumberField(TEXT("equipment_frame_ms"),EquipmentFrameMs);O->SetNumberField(TEXT("classic_frame_ms"),ClassicFrameMs);O->SetStringField(TEXT("character"),Character);O->SetStringField(TEXT("status"),Status);
    if(PlayerState.IsValid())O->SetObjectField(TEXT("player_status"),PlayerState);O->SetStringField(TEXT("local_animation"),AnimationStates.FindRef(TEXT("player:local")));O->SetBoolField(TEXT("target_in_view"),PlayerSeesTarget());
    // Opt-in QA reads the meshes actually assigned to render components.
    // Keep this separate from the requested model ID in the network snapshot.
    if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeVisualProbe"))){
        if(ClassicState.IsValid()&&ClassicTab!=TEXT("inventory"))SetClassicTab(TEXT("inventory"));
        auto Visual=MakeShared<FJsonObject>();
        Visual->SetNumberField(TEXT("model_id"),EntityModels.FindRef(TEXT("player:local")));
        const auto LocalActor=Entities.FindRef(TEXT("player:local"));
        if(auto* Body=Cast<ASkeletalMeshActor>(LocalActor)){
            auto* Mesh=Body->GetSkeletalMeshComponent()->GetSkeletalMeshAsset();
            Visual->SetStringField(TEXT("body_asset"),Mesh?Mesh->GetPathName():FString());
            Visual->SetBoolField(TEXT("body_visible"),Body->GetSkeletalMeshComponent()->IsVisible()&&!Body->IsHidden());
        }
        if(auto* Doll=Cast<ASkeletalMeshActor>(ClassicDollActor.Get())){
            auto* Mesh=Doll->GetSkeletalMeshComponent()->GetSkeletalMeshAsset();
            Visual->SetStringField(TEXT("portrait_asset"),Mesh?Mesh->GetPathName():FString());
        }
        Visual->SetNumberField(TEXT("weapon_components"),LocalEquipment.Num());
        O->SetObjectField(TEXT("player_visual"),Visual);
        static int32 ProbeModel=-1,ProbeStage=0;static double ProbeChangedAt=0;static bool ProbeCaptured=false;
        const int32 CurrentModel=EntityModels.FindRef(TEXT("player:local"));
        if(CurrentModel>0&&Visual->HasField(TEXT("body_asset"))){
            if(CurrentModel!=ProbeModel){ProbeModel=CurrentModel;++ProbeStage;ProbeChangedAt=FPlatformTime::Seconds();ProbeCaptured=false;}
            if(!ProbeCaptured&&FPlatformTime::Seconds()-ProbeChangedAt>1.5){
                const FString Shot=FPaths::GetPath(File)/FString::Printf(TEXT("visual_stage_%d_%d.png"),ProbeStage,CurrentModel);
                FScreenshotRequest::RequestScreenshot(Shot,true,false);ProbeCaptured=true;
            }
        }

    }
    if(InteractionState.IsValid())O->SetObjectField(TEXT("interaction"),InteractionState);
    if(InventoryState.IsValid())O->SetObjectField(TEXT("inventory"),InventoryState);
    if(ClassicState.IsValid()){O->SetObjectField(TEXT("classic_ui"),ClassicState);O->SetStringField(TEXT("classic_tab"),ClassicTab);O->SetBoolField(TEXT("classic_panel_open"),bClassicOpen);O->SetBoolField(TEXT("classic_ui_visible"),ClassicOverlay.IsValid());}
    O->SetNumberField(TEXT("interaction_test_steps"),InteractionTestSteps);O->SetNumberField(TEXT("pose_visual_test_steps"),PoseVisualTestSteps);O->SetObjectField(TEXT("equipment_visual"),EquipmentReport());
    int32 Moving=0,Frames=0,ActiveFrames=0,Samples=0,Snaps=0,Blocked=0;double MaximumStep=0,MaximumError=0;
    for(const auto& Pair:RemoteMotion){const auto& Motion=Pair.Value;Moving+=Motion.ForecastActive(FPlatformTime::Seconds())?1:0;Frames+=Motion.VisualFrames;ActiveFrames+=Motion.MovingFrames;Samples+=Motion.Samples;Snaps+=Motion.HardCorrections;Blocked+=Motion.Blocked?1:0;MaximumStep=FMath::Max(MaximumStep,Motion.MaximumStepCm);MaximumError=FMath::Max(MaximumError,Motion.MaximumErrorCm);}
    if(!RemoteMotionProbePath.IsEmpty()){FString TraceText;FJsonSerializer::Serialize(RemoteMotionProbeSamples,TJsonWriterFactory<>::Create(&TraceText));FFileHelper::SaveStringToFile(TraceText,*RemoteMotionProbePath);}
    auto MotionReport=MakeShared<FJsonObject>();MotionReport->SetNumberField(TEXT("last_cpu_ms"),RemoteMotionLastMs);MotionReport->SetNumberField(TEXT("peak_cpu_ms"),RemoteMotionPeakMs);MotionReport->SetNumberField(TEXT("entities"),RemoteMotion.Num());MotionReport->SetNumberField(TEXT("moving"),Moving);MotionReport->SetNumberField(TEXT("frames"),Frames);MotionReport->SetNumberField(TEXT("moving_frames"),ActiveFrames);MotionReport->SetNumberField(TEXT("samples"),Samples);MotionReport->SetNumberField(TEXT("server_corrections"),Snaps);MotionReport->SetNumberField(TEXT("blocked_predictions"),Blocked);MotionReport->SetNumberField(TEXT("maximum_frame_step_m"),MaximumStep/100);MotionReport->SetNumberField(TEXT("maximum_correction_m"),MaximumError/100);int32 Contacts=0,Clipped=0,TreeFloors=0;double Conflict=0;for(const auto& Pair:RemoteMotion){Contacts+=Pair.Value.CollisionContacts;Clipped+=Pair.Value.BlockedCorrections;TreeFloors+=Pair.Value.RejectedTreeFloors;if(Pair.Value.Blocked)Conflict=FMath::Max(Conflict,FVector::Distance(Pair.Value.Anchor,Pair.Value.Rendered));}MotionReport->SetNumberField(TEXT("collision_contacts"),Contacts);MotionReport->SetNumberField(TEXT("clipped_corrections"),Clipped);MotionReport->SetNumberField(TEXT("rejected_tree_floors"),TreeFloors);MotionReport->SetNumberField(TEXT("max_blocked_anchor_distance_m"),Conflict/100);O->SetObjectField(TEXT("remote_motion"),MotionReport);
    O->SetNumberField(TEXT("npc_heading_error_degrees_max"),MaxNpcHeadingError);
    O->SetNumberField(TEXT("nameplates_visible"),NameplatesVisible);O->SetNumberField(TEXT("nameplates_occluded"),NameplatesOccluded);O->SetBoolField(TEXT("nameplate_font_exists"),FPaths::FileExists(NameplateFontFile));
    O->SetNumberField(TEXT("npcs"),NpcCount);O->SetNumberField(TEXT("sequence"),Sequence);O->SetBoolField(TEXT("connected"),bConnected&&!Session.IsEmpty());
    O->SetArrayField(TEXT("position_m"),JsonPoint(PlayerPosition));O->SetNumberField(TEXT("fps"),1.0/FMath::Max(FApp::GetDeltaTime(),.0001));
    O->SetNumberField(TEXT("modeled_entities_created"),ModeledEntities);O->SetNumberField(TEXT("moved_metres"),(PlayerPosition-StartPosition).Size()/100);
    O->SetObjectField(TEXT("spell_visuals"),SpellVisualReport());
    O->SetObjectField(TEXT("spell_audio"),SpellAudioReport());O->SetObjectField(TEXT("footsteps"),FootstepReport());
    O->SetNumberField(TEXT("travelled_metres"),TravelledMetres);O->SetNumberField(TEXT("camera_yaw"),CameraYaw);O->SetNumberField(TEXT("camera_pitch"),CameraPitch);
    O->SetBoolField(TEXT("mouse_captured"),bMouseLook);O->SetNumberField(TEXT("mouse_sensitivity"),MouseSensitivity);
    O->SetObjectField(TEXT("target_tracking"),TargetTrackingReport());
    O->SetObjectField(TEXT("riding"),LiveRidingReport());
    if(MovementKeys){auto Keys=MakeShared<FJsonObject>();Keys->SetBoolField(TEXT("run_lock"),MovementKeys->RunLock);Keys->SetBoolField(TEXT("walk_toggle"),MovementKeys->WalkToggle);Keys->SetNumberField(TEXT("test_phase"),MovementKeysTestPhase);if(PlayerPawn)Keys->SetNumberField(TEXT("ground_speed_limit_mps"),PlayerPawn->GetCharacterMovement()->MaxWalkSpeed/100);O->SetObjectField(TEXT("movement_keys"),Keys);}
    if(PlayerPawn){O->SetNumberField(TEXT("landing_count"),PlayerPawn->LandingCount);O->SetNumberField(TEXT("last_landing_speed_mps"),PlayerPawn->LastLandingSpeedMps);}
    O->SetBoolField(TEXT("character_grounded"),IsValid(PlayerPawn)&&PlayerPawn->GetCharacterMovement()->IsMovingOnGround());
    if(IsValid(Camera))O->SetArrayField(TEXT("camera_position_m"),JsonPoint(Camera->GetActorLocation()));
    if(IsValid(PlayerPawn))O->SetArrayField(TEXT("pawn_position_m"),JsonPoint(PlayerPawn->FeetPosition()));
    auto* ViewPC=GetWorld()->GetFirstPlayerController();O->SetBoolField(TEXT("view_target_is_bridge_camera"),ViewPC&&ViewPC->GetViewTarget()==Camera);
    O->SetBoolField(TEXT("camera_attached_to_player"),IsValid(Camera)&&IsValid(PlayerPawn)&&Camera->GetAttachParentActor()==PlayerPawn);
    O->SetBoolField(TEXT("camera_collision"),IsValid(PlayerPawn)&&PlayerPawn->CameraArm->IsCollisionFixApplied());
    O->SetBoolField(TEXT("navigation_ready"),bNavigationReady);O->SetNumberField(TEXT("structure_colliders"),StructureColliders);O->SetNumberField(TEXT("tree_collider_instances"),TreeColliderInstances);O->SetNumberField(TEXT("terrain_colliders"),TerrainColliders);
    O->SetObjectField(TEXT("water_movement"),WaterMovementReport());O->SetNumberField(TEXT("run_speed_mps"),ServerRunSpeed/100);O->SetNumberField(TEXT("door_groups"),Doors.Num());O->SetNumberField(TEXT("door_requests"),DoorRequests);O->SetNumberField(TEXT("door_state_changes"),DoorStateChanges);
    O->SetNumberField(TEXT("peak_movement_speed_mps"),PeakMovementSpeed);
    O->SetBoolField(TEXT("door_auto_test"),bAutoDoorTest);O->SetNumberField(TEXT("test_elapsed"),PlayerStartedAt>0?FPlatformTime::Seconds()-PlayerStartedAt:0);
    O->SetNumberField(TEXT("door_test_progress_m"),FVector::DotProduct(PlayerPosition-StartPosition,FRotator(0,CameraYaw,0).Vector())/100);
    TArray<TSharedPtr<FJsonValue>> DoorRows;for(const auto& Pair:Doors){auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("id"),double(Pair.Key));State->SetBoolField(TEXT("open"),Pair.Value.Open);State->SetNumberField(TEXT("alpha"),Pair.Value.Alpha);DoorRows.Add(MakeShared<FJsonValueObject>(State));}O->SetArrayField(TEXT("doors"),DoorRows);O->SetNumberField(TEXT("zone_lights"),ZoneLightActors.Num());
    if(NavigationProbe.IsValid())O->SetObjectField(TEXT("navigation_probe"),NavigationProbe);
    O->SetBoolField(TEXT("standalone_game"),GetWorld()->IsGameWorld());O->SetBoolField(TEXT("capture_requested"),bCaptured);
    double Elapsed=PlayerStartedAt>0?FPlatformTime::Seconds()-PlayerStartedAt:0;O->SetBoolField(TEXT("auto_walk_active"),bAutoWalk&&Elapsed>=20&&Elapsed<52);
    O->SetStringField(TEXT("map"),GetWorld()->GetMapName());
    O->SetObjectField(TEXT("approved_environment"),InspectDAoCApprovedEnvironment(GetWorld()));
    O->SetStringField(TEXT("quality"),Quality);O->SetNumberField(TEXT("foliage_components_optimized"),OptimizedFoliageComponents);O->SetNumberField(TEXT("foliage_instances_with_distance_policy"),OptimizedFoliageInstances);
    O->SetNumberField(TEXT("frame_ms"),FApp::GetDeltaTime()*1000);O->SetNumberField(TEXT("gameplay_stalls_over_2s"),GameplayStalls);O->SetNumberField(TEXT("maximum_gameplay_frame_ms"),MaximumGameplayFrameMs);
    auto* GameViewport=GetWorld()->GetGameViewport();O->SetBoolField(TEXT("viewport_focused"),GameViewport&&GameViewport->Viewport&&GameViewport->Viewport->HasFocus());
    if(const auto* Compat=BarkCompatibilityWorlds.Find(TWeakObjectPtr<UWorld>(GetWorld()))){auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("bindings"),Compat->Bindings);State->SetNumberField(TEXT("instances"),Compat->Instances);State->SetNumberField(TEXT("parameters_matched"),Compat->ParametersMatched);State->SetNumberField(TEXT("failures"),Compat->Failures);O->SetObjectField(TEXT("bark_compatibility"),State);}
    O->SetNumberField(TEXT("foliage_lod_replacements"),FoliageLODReplacements);O->SetNumberField(TEXT("distance_limited_components"),DistanceLimitedComponents);
    O->SetNumberField(TEXT("foliage_lod_failures"),FoliageLODFailures);O->SetNumberField(TEXT("source_foliage_triangle_budget"),SourceFoliageTriangleBudget);O->SetNumberField(TEXT("runtime_foliage_triangle_budget"),RuntimeFoliageTriangleBudget);
    auto Settings=MakeShared<FJsonObject>();for(const TCHAR* Key:{TEXT("foliage.ForceLOD"),TEXT("foliage.LODDistanceScale"),TEXT("r.ForceLOD"),TEXT("r.ForceLODShadow"),TEXT("r.Shadow.CSM.MaxCascades"),TEXT("r.Shadow.DistanceScale"),TEXT("r.Shadow.MaxCSMResolution"),TEXT("t.IdleWhenNotForeground"),TEXT("Slate.bAllowThrottling"),TEXT("t.MaxFPS")})if(auto* V=IConsoleManager::Get().FindConsoleVariable(Key))Settings->SetStringField(Key,V->GetString());O->SetObjectField(TEXT("render_settings"),Settings);
    if(RollingFrameMs.Num()>10){TArray<double> Sorted=RollingFrameMs;Sorted.Sort();O->SetNumberField(TEXT("fps_median"),1000./Sorted[Sorted.Num()/2]);O->SetNumberField(TEXT("frame_ms_p95"),Sorted[FMath::Min(Sorted.Num()-1,int32(Sorted.Num()*.95))]);}
    if(bProfile&&FPlatformTime::Seconds()-PlayerStartedAt>ProfileEndTime())O->SetArrayField(TEXT("profile_samples"),ProfileSamples);
    FString Text;auto W=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(O,W);FFileHelper::SaveStringToFile(Text,*File);
}
void UDAoCBridgeSubsystem::ApplyQuality(){
    if(bQualityApplied)return;bQualityApplied=true;
    if(Quality==TEXT("original"))return;
    const bool High=Quality==TEXT("high"),Superior=Quality==TEXT("superior"),Accessible=Quality==TEXT("accessible");
    auto& Console=IConsoleManager::Get();
    if(auto* V=Console.FindConsoleVariable(TEXT("r.Shadow.CSM.MaxCascades")))V->Set(Superior?4:High?3:2,ECVF_SetByCode);
    if(auto* V=Console.FindConsoleVariable(TEXT("r.Shadow.MaxCSMResolution")))V->Set(Superior?4096:Accessible?1024:2048,ECVF_SetByCode);
    if(auto* V=Console.FindConsoleVariable(TEXT("r.Shadow.DistanceScale")))V->Set(Superior?1.f:High?.75f:Accessible?.35f:.5f,ECVF_SetByCode);
    int32 Near=Superior?5000:High?3500:Accessible?1200:2000,Far=Superior?9000:High?6000:Accessible?2500:4000;
    for(TActorIterator<AActor> It(GetWorld());It;++It){
        if(It->ActorHasTag(TEXT("DAoCBridgeEntity"))||It->ActorHasTag(TEXT("DAoCBridgeCollision")))continue;
        TInlineComponentArray<UInstancedStaticMeshComponent*> Components;It->GetComponents(Components);
        for(auto* Component:Components){
            UStaticMesh* Mesh=Component->GetStaticMesh();if(!Mesh)continue;
            FString Name=Mesh->GetName().ToLower();
            if(auto* Replacement=FoliageLODAssets.Find(Mesh->GetPathName())){
                if(auto* RuntimeMesh=LoadObject<UStaticMesh>(nullptr,**Replacement)){
                    TArray<UMaterialInterface*> Materials;for(int32 I=0;I<Component->GetNumMaterials();++I)Materials.Add(Component->GetMaterial(I));
                    bool Changed=Component->SetStaticMesh(RuntimeMesh);
                    if(!Changed&&Component->GetStaticMesh()!=RuntimeMesh){
                        const bool Registered=Component->IsRegistered();if(Registered)Component->UnregisterComponent();
                        Component->SetStaticMesh(RuntimeMesh);if(Registered)Component->RegisterComponent();
                    }
                    if(Component->GetStaticMesh()!=RuntimeMesh){++FoliageLODFailures;continue;}
                    for(int32 I=0;I<Materials.Num();++I)Component->SetMaterial(I,Materials[I]);
                    const bool Birch=Name.Contains(TEXT("birch"));
                    Component->SetForcedLodModel(0);
                    if(Birch)Component->SetLODDistanceScale(Superior?1.f:High?.5f:Accessible?.1f:.2f);
                    ++FoliageLODReplacements;
                    SourceFoliageTriangleBudget+=double(Mesh->GetNumTriangles(0))*Component->GetInstanceCount();
                    RuntimeFoliageTriangleBudget+=double(RuntimeMesh->GetNumTriangles(0))*Component->GetInstanceCount();
                }
            }
            bool Ground=Name.Contains(TEXT("grass"))||Name.Contains(TEXT("clover"))||Name.Contains(TEXT("celandine"))||Name.Contains(TEXT("fern"))||Name.Contains(TEXT("flora"))||Name.Contains(TEXT("poppy"))||Name.Contains(TEXT("daisy"));
            if(Ground){
                Component->SetCullDistances(Near,Far);Component->SetCastShadow(false);
                ++OptimizedFoliageComponents;OptimizedFoliageInstances+=Component->GetInstanceCount();
            }else{Component->SetCullDistances(28000,35000);++DistanceLimitedComponents;}
        }
        TInlineComponentArray<UStaticMeshComponent*> StaticComponents;It->GetComponents(StaticComponents);
        for(auto* Component:StaticComponents){
            if(Cast<UInstancedStaticMeshComponent>(Component))continue;
            UStaticMesh* Mesh=Component->GetStaticMesh();if(!Mesh)continue;
            FString Path=Mesh->GetPathName().ToLower();
            if(Path.Contains(TEXT("terrain"))||Path.Contains(TEXT("ground"))||Path.Contains(TEXT("water"))||Path.Contains(TEXT("river"))||Path.Contains(TEXT("sky"))||Mesh->GetBounds().BoxExtent.GetMax()>15000)continue;
            Component->SetCullDistance(35000);++DistanceLimitedComponents;
        }
    }
    AExponentialHeightFog* Fog=nullptr;for(TActorIterator<AExponentialHeightFog> It(GetWorld());It;++It){Fog=*It;break;}
    if(!Fog){FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Fog=GetWorld()->SpawnActor<AExponentialHeightFog>(FVector(0,0,-1800),FRotator::ZeroRotator,Params);}
    if(Fog){UExponentialHeightFogComponent* C=Fog->GetComponent();C->SetFogDensity(.18f);C->SetFogHeightFalloff(.001f);C->SetStartDistance(14000);C->SetFogMaxOpacity(1);C->SetFogInscatteringColor(FLinearColor(.45f,.55f,.60f));C->SetVolumetricFogEmissive(FLinearColor(.45f,.55f,.60f));}
}
void UDAoCBridgeSubsystem::UpdateProfile(double Now,double BridgeMs,double WallMs){
    if(!bProfile||PlayerStartedAt==0)return;
    double Elapsed=Now-PlayerStartedAt;
    int32 Phase=FMath::Clamp(int32((Elapsed-15)/15),0,5);
    if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeProfileFixed")))Phase=0;
    static const TCHAR* Names[]={TEXT("baseline"),TEXT("no_foliage"),TEXT("no_shadows"),TEXT("half_resolution"),TEXT("no_npcs"),TEXT("baseline_again")};
    if(Phase!=ProfilePhase){
        auto& CM=IConsoleManager::Get();
        if(ProfilePhase<0){for(TActorIterator<AActor> It(GetWorld());It;++It)if(It->GetClass()->GetName().Contains(TEXT("InstancedFoliageActor")))ProfileFoliage.Add(*It,It->IsHidden());}
        for(auto& Item:ProfileFoliage)if(Item.Key.IsValid())Item.Key->SetActorHiddenInGame(Phase==1?true:Item.Value);
        for(auto& Item:Entities)if(Item.Key!=TEXT("player:local")&&IsValid(Item.Value))Item.Value->SetActorHiddenInGame(Phase==4);
        if(auto* V=CM.FindConsoleVariable(TEXT("r.ShadowQuality")))V->Set(Phase==2?0:5,ECVF_SetByCode);
        if(auto* V=CM.FindConsoleVariable(TEXT("r.ScreenPercentage")))V->Set(Phase==3?50.f:100.f,ECVF_SetByCode);
        ProfilePhase=Phase;
    }
    if(Elapsed>=15){
        auto Sample=MakeShared<FJsonObject>();Sample->SetNumberField(TEXT("elapsed"),Elapsed);Sample->SetStringField(TEXT("phase"),Names[Phase]);
        Sample->SetNumberField(TEXT("frame_ms"),WallMs);Sample->SetNumberField(TEXT("bridge_ms"),BridgeMs);
        Sample->SetNumberField(TEXT("game_ms"),FPlatformTime::ToMilliseconds(GGameThreadTime));
        Sample->SetNumberField(TEXT("render_ms"),FPlatformTime::ToMilliseconds(GRenderThreadTime));
        Sample->SetNumberField(TEXT("rhi_ms"),FPlatformTime::ToMilliseconds(GRHIThreadTime));
        Sample->SetNumberField(TEXT("gpu_ms"),FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()));
        ProfileSamples.Add(MakeShared<FJsonValueObject>(Sample));
    }
    if(Elapsed>(bAutoInteractionTest?17:25)&&!bCaptured&&!CaptureFile.IsEmpty()){FScreenshotRequest::RequestScreenshot(CaptureFile,true,false);bCaptured=true;}
    if(Elapsed>ProfileEndTime()){WriteReport();UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);}
}
void UDAoCBridgeSubsystem::Tick(float Dt){
    if(TickStealthMaterialAcceptance())return;
    if(TickWorldClockAcceptance())return;
    if(TickCompassAcceptance())return;
    if(TickPlayerVitalsAcceptance())return;
    if(TickWindowRecoveryAcceptance())return;
    if(TickInterfaceScaleAcceptance())return;
    if(TickHoverDetailsAcceptance())return;
    if(TickItemHandoverAcceptance())return;
    if(TickEmblemPickerAcceptance())return;
    if(TickGuildAcceptance())return;
    if(TickDisplaySettingsAcceptance())return;
    TickDisplaySettings();
    UpdateEmblemPickerPreview();
    if(TickLiveRidingAssetAcceptance())return;
    if(TickTargetTrackingAcceptance())return;
    if(TickMovementKeysAcceptance())return;
    if(TickJumpLandingAcceptance())return;
    TickCharacterLobbyMotion();
    if(!bCollisionConfigured&&FPlatformTime::Seconds()>=GeometryUpdateAfter)ConfigureCollisions();
    SetupNameplates();
    InstallWorldPointerInput();
    UpdateUILayout();
    UpdateChatInput();
    if(TickExchangeAcceptance())return;
    if(TickKeyConfigurationAcceptance())return;
    if(TickOptionsAudioAcceptance())return;
    if(TickViewportAcceptance())return;
    if(TickCharacterLobbyAcceptance())return;
    if(TickClassicAcceptance())return;
    if(TickCombatVisualAcceptance())return;
    if(TickArmourAcceptance())return;
    if(TickEquipmentAcceptance())return;
    if(TickSpellVisualAcceptance())return;
    if(TickSpellAudioAcceptance())return;
    if(TickTrainingPlacement())return;
    if(TickPoseAcceptance())return;
    if(TickPlayerStatusAcceptance())return;
    if(TickInventoryAcceptance())return;
    if(TickRemoteMotionAcceptance())return;
    if(TickNameplateRenderTest())return;
    TickDoors(Dt);
    if(TickInteractionAcceptance())return;
    if(TickEntityAcceptance())return;
    if(TickTraversal(Dt))return;
    double Now=FPlatformTime::Seconds();double WallMs=PreviousTick>0?(Now-PreviousTick)*1000:Dt*1000;PreviousTick=Now;if(!Socket&&Now>=RetryAt)Connect();
    const double NetworkBegan=FPlatformTime::Seconds();
    if(Socket){
        auto State=Socket->GetConnectionState();
        if(State==SCS_Connected){bConnected=true;
            if(Outgoing.Num()){int32 Sent=0;Socket->Send(Outgoing.GetData(),Outgoing.Num(),Sent);if(Sent>0)Outgoing.RemoveAt(0,Sent,EAllowShrinking::No);}
            uint32 Available=0;int Reads=0;
            while(Reads++<8&&Socket->HasPendingData(Available)){
                uint8 Data[65536];int32 Count=0;if(!Socket->Recv(Data,FMath::Min<int32>(Available,65536),Count)||Count<=0)break;
                Incoming.Append(Data,Count);if(Incoming.Num()>MaxFrame){Disconnect();break;}
            }
            int32 End;int Lines=0;
            TSharedPtr<FJsonObject> LatestSnapshot;
            while(Socket&&Lines++<256&&Incoming.Find(uint8('\n'),End)){
                TArray<uint8> Line;Line.Append(Incoming.GetData(),End);Line.Add(0);Incoming.RemoveAt(0,End+1,EAllowShrinking::No);
                FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Line.GetData()));TSharedPtr<FJsonObject> M;
                if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),M)&&M.IsValid()){
                    FString Type;M->TryGetStringField(TEXT("type"),Type);
                    if(Type==TEXT("snapshot"))LatestSnapshot=M;
                    else{if(Type==TEXT("hello"))LatestSnapshot.Reset();Handle(M);}
                }
            }
            if(LatestSnapshot.IsValid())Handle(LatestSnapshot);
            if(!Session.IsEmpty()&&Now-LastSnapshot>3){if(!bExiting)Status=TEXT("Connection lost; waiting to reconnect");Disconnect();}
        }else if(State==SCS_ConnectionError||Now>RetryAt+2){Disconnect();}
    }
    TickRemoteMotion(Dt);
    NetworkFrameMs=(FPlatformTime::Seconds()-NetworkBegan)*1000;UpdateControls(Dt);const double GearBegan=FPlatformTime::Seconds();UpdateLocalEquipment();UpdateRemoteEquipment();TickEquipmentAnimations();TickLocalStealthMaterials();EquipmentFrameMs=(FPlatformTime::Seconds()-GearBegan)*1000;TickSpellVisuals(Dt);TickFootsteps();TickSpellAudio();const double ClassicBegan=FPlatformTime::Seconds();TickClassicUI();ClassicFrameMs=(FPlatformTime::Seconds()-ClassicBegan)*1000;
    if(PlayerStartedAt>0&&Now-PlayerStartedAt>15)ProbeNavigation();
    ApplyQuality();
    if(bHavePlayer&&Now-PlayerStartedAt>8&&WallMs>0){MaximumGameplayFrameMs=FMath::Max(MaximumGameplayFrameMs,WallMs);if(WallMs>=2000)++GameplayStalls;}
    if(bHavePlayer&&Now-PlayerStartedAt>8&&WallMs>0&&WallMs<2000){RollingFrameMs.Add(WallMs);if(RollingFrameMs.Num()>600)RollingFrameMs.RemoveAt(0,1,EAllowShrinking::No);}
    UpdateProfile(Now,(FPlatformTime::Seconds()-Now)*1000,WallMs);
    if(bExiting&&Session.IsEmpty()){WriteReport();UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);}
    if(bHavePlayer&&bAutoTest){
        double Elapsed=Now-PlayerStartedAt;
        const bool PoseTest=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgePoseVisualTest"));if(PoseTest)UpdatePoseVisualTest(Elapsed);
        const bool EquipmentTest=FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeEquipmentVisualTest"));if(EquipmentTest)UpdateEquipmentVisualTest(Elapsed);
        bool InteractionReady=!bAutoInteractionTest;
        if(bAutoInteractionTest&&InteractionState.IsValid()){const TSharedPtr<FJsonObject>* Merchant=nullptr;const TSharedPtr<FJsonObject>* Pages=nullptr;InteractionReady=InteractionState->TryGetObjectField(TEXT("merchant"),Merchant)&&(*Merchant)->TryGetObjectField(TEXT("pages"),Pages)&&!(*Pages)->Values.IsEmpty();}
        if(!FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest"))&&Elapsed>(bAutoInteractionTest?16:15)&&InteractionReady&&!bCaptured&&!CaptureFile.IsEmpty()){FScreenshotRequest::RequestScreenshot(CaptureFile,true,false);bCaptured=true;}
        bool ClassicCapturesReady=true;if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest")))for(auto Tab:{TEXT("character"),TEXT("inventory"),TEXT("skills"),TEXT("combat"),TEXT("magic"),TEXT("group")})ClassicCapturesReady&=IFileManager::Get().FileExists(*(FPaths::GetPath(CaptureFile)/(FString(TEXT("Classic_"))+Tab+TEXT(".png"))));
        if((ClassicCapturesReady||Elapsed>180)&&Elapsed>(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest"))?55:EquipmentTest?70:PoseTest?60:bAutoWalk?60:30)&&!bExiting){Send(TEXT("logout"));bExiting=true;Status=TEXT("Test complete. Saving session...");}
        if(Elapsed>40&&Session.IsEmpty()){WriteReport();UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);}
    }
    if(GEngine&&!CharacterLobbyOverlay.IsValid())GEngine->AddOnScreenDebugMessage(19727,0,FColor::White,
        FString::Printf(TEXT("DAoC Enhanced | %s | NPC/Mobs: %d | %.0f FPS\n%s\nMovement keys: Esc > Controls | Shift: walk | Right drag/F3: camera | F4/F5: sensitivity %.2f | Click: target | Tab: nearby enemy | Right click/E: interact | I: inventory | M: map | C: attack | N: sit | Enter: chat | F1: GM protection | F6: combat test | F2: loc | Esc: options"),*Character,NpcCount,1./FMath::Max(FApp::GetDeltaTime(),.0001),*Status,MouseSensitivity));
    if(Now-LastReport>1){WriteReport();LastReport=Now;}
}
