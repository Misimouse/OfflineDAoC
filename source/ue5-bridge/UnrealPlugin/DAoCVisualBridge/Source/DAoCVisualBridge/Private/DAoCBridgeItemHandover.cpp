#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/SViewport.h"

void UDAoCBridgeSubsystem::GiveInventoryItemAtCursor(int32 Slot,const FString& ItemToken,FVector2D Absolute){
    if(!bLocalAvailable||bExiting||Session.IsEmpty()||PlayerIsDead()||CharacterLobbyOverlay||WorldPointerBlocked(Absolute)||!InventoryState)return;
    const TSet<int32> Carried={10,11,12,13,21,22,23,24,25,26,27,28,29,32,33,34,35,36,37};
    if(!Carried.Contains(Slot)&&(Slot<40||Slot>79))return;
    bool Pending=false,Ready=false;InventoryState->TryGetBoolField(TEXT("pending"),Pending);InventoryState->TryGetBoolField(TEXT("ready"),Ready);if(Pending||!Ready)return;
    auto Item=InventoryItem(Slot);FString CurrentToken;if(!Item||!Item->TryGetStringField(TEXT("token"),CurrentToken)||ItemToken.IsEmpty()||ItemToken!=CurrentToken)return;
    auto* View=GetWorld()?GetWorld()->GetGameViewport():nullptr;if(!View||!View->GetGameViewportWidget())return;
    const auto Geometry=View->GetGameViewportWidget()->GetCachedGeometry();if(!Geometry.IsUnderLocation(Absolute)||Geometry.GetLocalSize().GetMin()<=0)return;
    FVector2D Size;View->GetViewportSize(Size);const FVector2D Pixel=Geometry.AbsoluteToLocal(Absolute)/Geometry.GetLocalSize()*Size;
    const FString Id=TargetAtCursor(false,Pixel);if(!Id.StartsWith(TEXT("npc:")))return;
    auto* Found=EntityRows.Find(Id);if(!Found||!Found->IsValid())return;auto Row=*Found;FString Kind,Name;double Model=-1,Revision=-1;
    Row->TryGetStringField(TEXT("kind"),Kind);Row->TryGetStringField(TEXT("name"),Name);Row->TryGetNumberField(TEXT("model_id"),Model);InventoryState->TryGetNumberField(TEXT("state_revision"),Revision);
    if(Kind!=TEXT("npc")||Model<0||Revision<0)return;
    auto Request=MakeShared<FJsonObject>();Request->SetNumberField(TEXT("slot"),Slot);Request->SetStringField(TEXT("item_token"),ItemToken);Request->SetNumberField(TEXT("inventory_revision"),Revision);
    Request->SetStringField(TEXT("entity_id"),Id);Request->SetStringField(TEXT("target_name"),Name);Request->SetNumberField(TEXT("target_model"),Model);
    Send(TEXT("inventory_give"),Request);bInventoryMoving=false;bConfirmSale=false;
}
