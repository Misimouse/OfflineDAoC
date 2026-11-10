#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Styling/CoreStyle.h"

namespace {
FString InvStr(const TSharedPtr<FJsonObject>& O,const TCHAR* K){FString V;if(O.IsValid())O->TryGetStringField(K,V);return V;}
double InvNum(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
bool InvBool(const TSharedPtr<FJsonObject>& O,const TCHAR* K){bool V=false;if(O.IsValid())O->TryGetBoolField(K,V);return V;}
TSharedPtr<FJsonObject> InvObj(const TSharedPtr<FJsonObject>& O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O.IsValid()&&O->TryGetObjectField(K,V)?*V:nullptr;}
TSharedRef<STextBlock> InvText(const FString& S){return SNew(STextBlock).Text(FText::FromString(S)).AutoWrapText(true).ColorAndOpacity(FLinearColor(.92f,.91f,.85f));}
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::InventoryItem(int32 Slot) const {
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
    if(InventoryState.IsValid()&&InventoryState->TryGetArrayField(TEXT("items"),Rows))for(const auto& V:*Rows)if(V->Type==EJson::Object&&InvNum(V->AsObject(),TEXT("slot"),-1)==Slot)return V->AsObject();
    return nullptr;
}
bool UDAoCBridgeSubsystem::InventoryHovered() const{return bInventoryOpen&&InventoryOverlay.IsValid()&&InventoryOverlay->GetVisibility().IsVisible()&&InventoryPanel.IsValid()&&InventoryPanel->IsHovered();}
void UDAoCBridgeSubsystem::RemoveInventoryUI(){
    if(InventoryOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(InventoryOverlay.ToSharedRef());
    InventoryOverlay.Reset();InventoryPanel.Reset();
}
void UDAoCBridgeSubsystem::ToggleInventory(){if(ClassicState.IsValid()){if(bClassicOpen&&ClassicTab==TEXT("inventory"))CloseClassicPanel();else SetClassicTab(TEXT("inventory"));return;}bInventoryOpen=!bInventoryOpen;bInventoryMoving=false;bConfirmSale=false;RefreshInventoryUI();}
bool UDAoCBridgeSubsystem::CloseInventory(){
    if(!bInventoryOpen)return false;
    if(bInventoryMoving||bConfirmSale){bInventoryMoving=false;bConfirmSale=false;RefreshInventoryUI();return true;}
    bInventoryOpen=false;RemoveInventoryUI();return true;
}
void UDAoCBridgeSubsystem::ApplyInventory(TSharedPtr<FJsonObject> State){
    const FString OldToken=InvStr(InventoryItem(SelectedItemSlot),TEXT("token"));const int64 OldState=int64(InvNum(InventoryState,TEXT("state_revision"),-1));InventoryState=State;
    if(OldState!=int64(InvNum(State,TEXT("state_revision"),-1))){bInventoryMoving=false;bConfirmSale=false;if(OldToken!=InvStr(InventoryItem(SelectedItemSlot),TEXT("token")))SelectedItemSlot=-1;}
    if(ClassicQuantityCommand.IsValid()&&!ClassicQuantityValid())CloseClassicQuantity();
    const int64 Revision=int64(InvNum(State,TEXT("revision"),-1));if(Revision==InventoryRevision)return;InventoryRevision=Revision;
    RefreshInventoryUI();RefreshClassicVault();RefreshClassicMerchant();if(ClassicState.IsValid()&&ClassicTab==TEXT("inventory"))RefreshClassicPanel();
    if(InteractionState.IsValid()){InteractionRevision=-1;ApplyInteraction(InteractionState);}
}
void UDAoCBridgeSubsystem::SendItemAction(const FString& Action,int32 Slot,int32 ToSlot){
    if(!bLocalAvailable||bExiting||Session.IsEmpty()||InvBool(InventoryState,TEXT("pending")))return;
    auto Item=InventoryItem(Slot);if(!Item.IsValid())return;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("slot"),Slot);V->SetStringField(TEXT("item_token"),InvStr(Item,TEXT("token")));V->SetNumberField(TEXT("inventory_revision"),InvNum(InventoryState,TEXT("state_revision"),-1));
    if(ToSlot>=0)V->SetNumberField(TEXT("to_slot"),ToSlot);
    if(Slot>=110||ToSlot>=110)V->SetStringField(TEXT("vault_token"),InvStr(InvObj(InventoryState,TEXT("vault")),TEXT("token")));
    if(Action==TEXT("merchant_sell")){auto Merchant=InvObj(InteractionState,TEXT("merchant"));V->SetStringField(TEXT("merchant_id"),InvStr(Merchant,TEXT("entity_id")));V->SetNumberField(TEXT("merchant_revision"),InvNum(Merchant,TEXT("catalog_revision"),-1));}
    Send(Action,V);bInventoryMoving=false;bConfirmSale=false;
}
void UDAoCBridgeSubsystem::BuyMerchantItem(int32 Page,int32 Index,const FString& MerchantId,int64 CatalogRevision){
    if(!bLocalAvailable||bExiting||Session.IsEmpty()||InvBool(InventoryState,TEXT("pending")))return;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("page"),Page);V->SetNumberField(TEXT("index"),Index);V->SetNumberField(TEXT("count"),1);V->SetStringField(TEXT("merchant_id"),MerchantId);V->SetNumberField(TEXT("merchant_revision"),CatalogRevision);V->SetNumberField(TEXT("inventory_revision"),InvNum(InventoryState,TEXT("state_revision"),-1));Send(TEXT("merchant_buy"),V);
    if(ClassicState.IsValid())SetClassicTab(TEXT("inventory"));else if(!bInventoryOpen){bInventoryOpen=true;RefreshInventoryUI();}
}
void UDAoCBridgeSubsystem::InventorySlotClicked(int32 Slot){
    if(InvBool(InventoryState,TEXT("pending")))return;
    if(bInventoryMoving){SendItemAction(TEXT("inventory_move"),SelectedItemSlot,Slot);bInventoryMoving=false;}
    else{SelectedItemSlot=InventoryItem(Slot).IsValid()?Slot:-1;bConfirmSale=false;}
    RefreshInventoryUI();
}
void UDAoCBridgeSubsystem::RefreshInventoryUI(){
    if(ClassicState.IsValid()){RemoveInventoryUI();if(ClassicTab==TEXT("inventory"))RefreshClassicPanel();RefreshClassicVault();return;}
    if(!bInventoryOpen){RemoveInventoryUI();return;}
    auto* Viewport=GetWorld()->GetGameViewport();if(!Viewport)return;
    if(!InventoryOverlay.IsValid()){
        auto Overlay=SNew(SOverlay);
        Overlay->AddSlot().HAlign(HAlign_Left).VAlign(VAlign_Center).Padding(20,40,0,55)[SNew(SBox).WidthOverride(430).MaxDesiredHeight(850)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.96f)).Padding(12)[SAssignNew(InventoryPanel,SVerticalBox)]]];
        InventoryOverlay=Overlay;Viewport->AddViewportWidgetContent(Overlay,25);
    }
    InventoryPanel->ClearChildren();auto Body=SNew(SVerticalBox);
    if(!InvBool(InventoryState,TEXT("ready"))){InventoryPanel->AddSlot().AutoHeight()[InvText(TEXT("Receiving inventory from the server... I / Esc to close"))];return;}
    auto Button=[&](const FString& Label,TFunction<void()> Action){Body->AddSlot().AutoHeight().Padding(0,2)[SNew(SButton).IsFocusable(false).IsEnabled(!InvBool(InventoryState,TEXT("pending"))).OnClicked_Lambda([Action](){Action();return FReply::Handled();})[InvText(Label)]];};
    Body->AddSlot().AutoHeight()[InvText(TEXT("Inventory and equipment \u00b7 I / Esc to close"))];
    Button(TEXT("Close"),[this](){bInventoryOpen=false;RemoveInventoryUI();});
    auto Money=InvObj(InventoryState,TEXT("money"));Body->AddSlot().AutoHeight().Padding(0,5)[InvText(FString::Printf(TEXT("%lld mithril \u00b7 %lld platinum \u00b7 %lld gold \u00b7 %lld silver \u00b7 %lld copper\nWeight %.0f / %.0f"),int64(InvNum(Money,TEXT("mithril"))),int64(InvNum(Money,TEXT("platinum"))),int64(InvNum(Money,TEXT("gold"))),int64(InvNum(Money,TEXT("silver"))),int64(InvNum(Money,TEXT("copper"))),InvNum(InventoryState,TEXT("weight_now"),-1),InvNum(InventoryState,TEXT("weight_max"),-1)))];
    const TPair<int32,FString> Slots[]={{25,TEXT("Torso")},{21,TEXT("Head")},{28,TEXT("Arms")},{22,TEXT("Hands")},{27,TEXT("Legs")},{23,TEXT("Feet")},{29,TEXT("Neck")},{26,TEXT("Cloak")},{24,TEXT("Jewel")},{32,TEXT("Waist")},{35,TEXT("Left ring")},{36,TEXT("Right ring")},{33,TEXT("Left wrist")},{34,TEXT("Right wrist")},{10,TEXT("Right hand")},{11,TEXT("Left hand")},{12,TEXT("Two-handed")},{13,TEXT("Ranged")},{37,TEXT("Mythical")}};
    auto Grid=SNew(SUniformGridPanel).SlotPadding(2);
    auto SlotButton=[this](int32 Slot,const FString& Caption){auto Item=InventoryItem(Slot);FString Name=Item.IsValid()?InvStr(Item,TEXT("name")):TEXT("Empty");if(Name.Len()>22)Name=Name.Left(21)+TEXT("\u2026");FString Label=Caption+TEXT(": ")+Name;if(InvNum(Item,TEXT("count"),1)>1)Label+=FString::Printf(TEXT(" x%.0f"),InvNum(Item,TEXT("count")));if(Slot==SelectedItemSlot)Label=TEXT("\u203a ")+Label;
        return SNew(SButton).IsFocusable(false).IsEnabled(!InvBool(InventoryState,TEXT("pending"))).ToolTipText(FText::FromString(InvStr(Item,TEXT("name")))).OnClicked_Lambda([this,Slot](){InventorySlotClicked(Slot);return FReply::Handled();})[InvText(Label)];};
    for(int32 I=0;I<UE_ARRAY_COUNT(Slots);++I)Grid->AddSlot(I%2,I/2)[SlotButton(Slots[I].Key,Slots[I].Value)];
    Body->AddSlot().AutoHeight()[Grid];auto Bags=SNew(SHorizontalBox);
    for(int32 I=0;I<5;++I)Bags->AddSlot().FillWidth(1).Padding(2)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([this,I](){InventoryBag=I;RefreshInventoryUI();return FReply::Handled();})[InvText(FString::Printf(TEXT("%s%d"),I==InventoryBag?TEXT("\u203a "):TEXT("Bag "),I+1))]];
    Body->AddSlot().AutoHeight().Padding(0,6)[Bags];
    for(int32 I=0;I<8;++I){int32 Slot=40+InventoryBag*8+I;Body->AddSlot().AutoHeight().Padding(0,1)[SlotButton(Slot,FString::Printf(TEXT("%d"),I+1))];}
    auto Item=InventoryItem(SelectedItemSlot);
    if(Item.IsValid()){
        Body->AddSlot().AutoHeight().Padding(0,6)[InvText(FString::Printf(TEXT("%s\nLevel %.0f \u00b7 Quality %.0f%% \u00b7 Condition %.0f%%\nDurability %.0f%% \u00b7 Bonus %.0f%%"),*InvStr(Item,TEXT("name")),InvNum(Item,TEXT("level")),InvNum(Item,TEXT("quality")),InvNum(Item,TEXT("condition")),InvNum(Item,TEXT("durability")),InvNum(Item,TEXT("bonus"))))];
        const int32 Slot=SelectedItemSlot;
        Button(Slot>=40?TEXT("Equip"):TEXT("Unequip"),[this,Slot](){SendItemAction(Slot>=40?TEXT("inventory_equip"):TEXT("inventory_unequip"),Slot);});
        Button(bInventoryMoving?TEXT("Cancel move"):TEXT("Move: then choose a slot"),[this](){bInventoryMoving=!bInventoryMoving;bConfirmSale=false;RefreshInventoryUI();});
        auto Merchant=InvObj(InteractionState,TEXT("merchant"));if(Slot>=40&&Merchant.IsValid()&&!InvStr(Merchant,TEXT("entity_id")).IsEmpty()){
            if(bConfirmSale){Body->AddSlot().AutoHeight()[InvText(TEXT("This sells the entire stack. The server determines the price."))];Button(TEXT("Confirm sale"),[this,Slot](){SendItemAction(TEXT("merchant_sell"),Slot);});Button(TEXT("Cancel sale"),[this](){bConfirmSale=false;RefreshInventoryUI();});}
            else Button(TEXT("Sell to merchant..."),[this](){bConfirmSale=true;bInventoryMoving=false;RefreshInventoryUI();});
        }
    }
    if(bInventoryMoving)Body->AddSlot().AutoHeight()[InvText(TEXT("Choose the destination slot. Esc cancels."))];
    const FString Feedback=InvStr(InventoryState,TEXT("feedback"));if(!Feedback.IsEmpty())Body->AddSlot().AutoHeight().Padding(0,5)[InvText(Feedback)];
    InventoryPanel->AddSlot().AutoHeight()[SNew(SBox).MaxDesiredHeight(800)[SNew(SScrollBox)+SScrollBox::Slot()[Body]]];
}
