#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Components/StaticMeshComponent.h"
#include "Widgets/SViewport.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Kismet/KismetSystemLibrary.h"

extern bool VerifyDAoCItemHandoverDrag();
bool UDAoCBridgeSubsystem::TickItemHandoverAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeItemHandoverTest="),Path))return false;
    static double Began=0;static bool Done=false;static AStaticMeshActor* Body=nullptr;static ACameraActor* HandoverCamera=nullptr;
    if(Done)return true;if(!GetWorld()||!GetWorld()->GetGameViewport()||!GetWorld()->GetFirstPlayerController())return true;
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC->PlayerCameraManager)return true;
    if(Began==0){
        Began=FPlatformTime::Seconds();Session=TEXT("isolated-item-handover");bLocalAvailable=true;bExiting=bOptionsOpen=false;
        Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private handover command capture"),false);Outgoing.Empty();
        Body=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,0,100),FRotator::ZeroRotator);auto* Mesh=Body->GetStaticMeshComponent();Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Mesh->SetWorldScale3D(FVector(1,1,2));Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Entities.Add(TEXT("npc:7"),Body);auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("kind"),TEXT("npc"));Row->SetStringField(TEXT("name"),TEXT("QA Emblemer"));Row->SetNumberField(TEXT("model_id"),1984);Row->SetNumberField(TEXT("health"),1);EntityRows.Add(TEXT("npc:7"),Row);PlayerPosition=FVector::ZeroVector;
        InventoryState=MakeShared<FJsonObject>();InventoryState->SetBoolField(TEXT("ready"),true);InventoryState->SetBoolField(TEXT("pending"),false);InventoryState->SetNumberField(TEXT("state_revision"),4);
        auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),40);Item->SetStringField(TEXT("token"),TEXT("held-item"));Item->SetNumberField(TEXT("count"),1);InventoryState->SetArrayField(TEXT("items"),{MakeShared<FJsonValueObject>(Item)});
        InteractionState=MakeShared<FJsonObject>();auto Target=MakeShared<FJsonObject>();Target->SetStringField(TEXT("id"),TEXT("npc:previous"));InteractionState->SetObjectField(TEXT("target"),Target);
        HandoverCamera=GetWorld()->SpawnActor<ACameraActor>(FVector(0,-600,150),FRotator(0,90,0));PC->SetViewTarget(HandoverCamera);PC->PlayerCameraManager->UpdateCamera(0);
        return true;
    }
    if(FPlatformTime::Seconds()-Began<1.5)return true;int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Value,const TCHAR* Label){++Checks;if(!Value)Failures.Add(MakeShared<FJsonValueString>(Label));};
    Check(VerifyDAoCItemHandoverDrag(),TEXT("actual inventory drag delivers once on unhandled left drop; handled UI, right-click and Escape cancel safely"));
    FVector2D Pixel,Size;auto* View=GetWorld()->GetGameViewport();View->GetViewportSize(Size);const auto Geometry=View->GetGameViewportWidget()->GetCachedGeometry();
    Check(PC->ProjectWorldLocationToScreen(FVector(0,0,130),Pixel)&&TargetAtCursor(false,Pixel)==TEXT("npc:7"),TEXT("actual rendered NPC body is picked under the drop cursor"));
    const FVector2D Absolute=Geometry.LocalToAbsolute(Pixel/Size*Geometry.GetLocalSize());
    GiveInventoryItemAtCursor(40,TEXT("stale-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("stale held-item identity rejected before dispatch"));
    GiveInventoryItemAtCursor(110,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("vault slot cannot be handed over directly"));
    InventoryState->SetBoolField(TEXT("pending"),true);GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("pending inventory operation blocks drop"));InventoryState->SetBoolField(TEXT("pending"),false);
    InventoryState->SetBoolField(TEXT("ready"),false);GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("initial inventory delivery blocks drop"));InventoryState->SetBoolField(TEXT("ready"),true);
    bOptionsOpen=true;GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("options intercept world drop"));bOptionsOpen=false;
    bExiting=true;GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("saving session blocks drop"));bExiting=false;
    auto Dead=MakeShared<FJsonObject>();auto Vitals=MakeShared<FJsonObject>();Vitals->SetNumberField(TEXT("health_pct"),0);Dead->SetObjectField(TEXT("vitals"),Vitals);PlayerState=Dead;
    GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("dead player cannot hand over items"));PlayerState.Reset();
    auto Row=EntityRows[TEXT("npc:7")];Row->SetStringField(TEXT("kind"),TEXT("player"));GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("mismatched NPC key and player kind cannot hand over"));Row->SetStringField(TEXT("kind"),TEXT("npc"));
    GiveInventoryItemAtCursor(40,TEXT("held-item"),FVector2D(-1000,-1000));Check(Outgoing.IsEmpty(),TEXT("drop outside actual viewport sends no packet"));
    GiveInventoryItemAtCursor(40,TEXT("held-item"),Geometry.LocalToAbsolute(FVector2D(5,5)));Check(Outgoing.IsEmpty(),TEXT("empty-world drop has no ground-item fallback"));
    auto* Wall=GetWorld()->SpawnActor<AStaticMeshActor>(FVector(0,-300,100),FRotator::ZeroRotator);auto* WallMesh=Wall->GetStaticMeshComponent();WallMesh->SetMobility(EComponentMobility::Movable);WallMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));WallMesh->SetWorldScale3D(FVector(4,1,4));WallMesh->SetCollisionEnabled(ECollisionEnabled::QueryOnly);WallMesh->SetCollisionResponseToAllChannels(ECR_Ignore);WallMesh->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);
    GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("actual intervening wall prevents giving through geometry"));WallMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Wall->Destroy();
    GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Request;
    const bool Parsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Request)&&Request.IsValid();Check(Parsed,TEXT("actual viewport drop dispatches one structured command"));
    if(Parsed){Check(Request->GetStringField(TEXT("action"))==TEXT("inventory_give")&&Request->GetStringField(TEXT("entity_id"))==TEXT("npc:7"),TEXT("drop uses rendered NPC rather than the previous target"));Check(Request->GetIntegerField(TEXT("slot"))==40&&Request->GetStringField(TEXT("item_token"))==TEXT("held-item")&&Request->GetIntegerField(TEXT("inventory_revision"))==4,TEXT("handover carries current inventory identity and revision"));Check(Request->GetStringField(TEXT("target_name"))==TEXT("QA Emblemer")&&Request->GetIntegerField(TEXT("target_model"))==1984,TEXT("handover captures the NPC identity seen by the player"));Check(!Request->HasField(TEXT("to_slot")),TEXT("client cannot select an arbitrary destination slot"));}
    Check(CurrentTarget()==TEXT("npc:previous")&&InventoryItem(40).IsValid(),TEXT("drag does not invent a selection change or remove an item"));
    Entities.Remove(TEXT("npc:7"));EntityRows.Remove(TEXT("npc:7"));Entities.Add(TEXT("player:7"),Body);EntityRows.Add(TEXT("player:7"),Row);Row->SetStringField(TEXT("kind"),TEXT("player"));Row->SetStringField(TEXT("name"),TEXT("QA Friend"));Row->SetNumberField(TEXT("session_id"),2);
    Check(TargetAtCursor(false,Pixel)==TEXT("player:7"),TEXT("actual rendered player body picked for trade"));
    GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Outgoing.Add(0);Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();Request.Reset();
    const bool PlayerParsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Request)&&Request.IsValid();Check(PlayerParsed,TEXT("actual player drop dispatches structured trade opening"));
    if(PlayerParsed){Check(Request->GetStringField(TEXT("action"))==TEXT("player_trade_begin")&&Request->GetStringField(TEXT("entity_id"))==TEXT("player:7"),TEXT("player drop uses player-trade action and actual target"));Check(Request->GetIntegerField(TEXT("target_session"))==2&&Request->GetStringField(TEXT("target_name"))==TEXT("QA Friend"),TEXT("player opening captures session and name"));Check(Request->GetIntegerField(TEXT("slot"))==40&&Request->GetStringField(TEXT("item_token"))==TEXT("held-item")&&Request->GetIntegerField(TEXT("inventory_revision"))==4,TEXT("player opening preserves actual inventory identity"));Check(!Request->HasField(TEXT("to_slot")),TEXT("player destination remains server-owned"));}
    Row->SetNumberField(TEXT("session_id"),0);GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("unknown player session cannot start trade"));Row->SetNumberField(TEXT("session_id"),2);
    Entities.Remove(TEXT("player:7"));EntityRows.Remove(TEXT("player:7"));Entities.Add(TEXT("player:local"),Body);EntityRows.Add(TEXT("player:local"),Row);GiveInventoryItemAtCursor(40,TEXT("held-item"),Absolute);Check(Outgoing.IsEmpty(),TEXT("local character cannot be a trade recipient"));Entities.Remove(TEXT("player:local"));EntityRows.Remove(TEXT("player:local"));
    Entities.Remove(TEXT("npc:7"));EntityRows.Remove(TEXT("npc:7"));Body->Destroy();HandoverCamera->Destroy();InventoryState.Reset();InteractionState.Reset();Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*Path);Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),PC,EQuitPreference::Quit,false);return true;
}
