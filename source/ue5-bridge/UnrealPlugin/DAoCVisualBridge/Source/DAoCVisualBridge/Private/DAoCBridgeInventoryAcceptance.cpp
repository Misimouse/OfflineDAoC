#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickInventoryAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInventoryTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    TArray<TSharedPtr<FJsonValue>> Failures;int32 Checks=0;auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Input;TSharedPtr<FJsonObject> Fixture;Check(FFileHelper::LoadFileToString(Input,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Fixture),TEXT("Godot fixture parsed"));
    if(Fixture.IsValid()){
        Check(Socket==nullptr,TEXT("test starts offline"));
        ApplyInteraction(Fixture->GetObjectField(TEXT("interaction")));auto State=Fixture->GetObjectField(TEXT("inventory"));ApplyInventory(State);bInventoryOpen=true;SelectedItemSlot=40;RefreshInventoryUI();
        Check(InventoryOverlay.IsValid()&&InventoryPanel.IsValid(),TEXT("inventory widgets created"));Check(InventoryItem(40).IsValid()&&InventoryItem(11).IsValid()&&!InventoryItem(79).IsValid(),TEXT("slot identities"));
        Session=TEXT("offline-inventory-test");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Inventory acceptance unconnected"),false);
        auto Merchant=InteractionState->GetObjectField(TEXT("merchant"));FString Id=Merchant->GetStringField(TEXT("entity_id"));int64 Catalog=Merchant->GetIntegerField(TEXT("catalog_revision"));
        BuyMerchantItem(2,3,Id,Catalog);Check(Outgoing.IsEmpty(),TEXT("pending server operation blocks native repeated purchase"));
        State->SetBoolField(TEXT("pending"),false);State->SetNumberField(TEXT("revision"),State->GetIntegerField(TEXT("revision"))+1);ApplyInventory(State);
        auto CaptureCommand=[&](const FString& Action){Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> V;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),V)&&V.IsValid()&&V->GetStringField(TEXT("action"))==Action,TEXT("command serialized: ")+Action);return V;};
        BuyMerchantItem(2,3,Id,Catalog);auto Buy=CaptureCommand(TEXT("merchant_buy"));if(Buy.IsValid()){Check(Buy->GetIntegerField(TEXT("page"))==2&&Buy->GetIntegerField(TEXT("index"))==3&&Buy->GetIntegerField(TEXT("count"))==1,TEXT("one offered sale unit"));Check(Buy->GetStringField(TEXT("merchant_id"))==Id&&Buy->GetIntegerField(TEXT("merchant_revision"))==Catalog,TEXT("catalog handle retained"));}
        SelectedItemSlot=40;SendItemAction(TEXT("inventory_move"),40,48);auto Move=CaptureCommand(TEXT("inventory_move"));if(Move.IsValid()){Check(Move->GetIntegerField(TEXT("slot"))==40&&Move->GetIntegerField(TEXT("to_slot"))==48,TEXT("backpack move slots"));Check(Move->GetStringField(TEXT("item_token"))==InventoryItem(40)->GetStringField(TEXT("token"))&&Move->GetIntegerField(TEXT("inventory_revision"))==State->GetIntegerField(TEXT("state_revision")),TEXT("current item and inventory handles"));}
        SendItemAction(TEXT("inventory_equip"),40);CaptureCommand(TEXT("inventory_equip"));SendItemAction(TEXT("inventory_unequip"),11);CaptureCommand(TEXT("inventory_unequip"));
        SendItemAction(TEXT("merchant_sell"),40);auto Sell=CaptureCommand(TEXT("merchant_sell"));if(Sell.IsValid())Check(Sell->GetStringField(TEXT("merchant_id"))==Id&&Sell->GetIntegerField(TEXT("merchant_revision"))==Catalog,TEXT("sale bound to current merchant"));
        Check(InventoryItem(40).IsValid()&&InventoryItem(11).IsValid(),TEXT("UI commands do not mutate authoritative items"));
        bInventoryMoving=true;Check(CloseInventory()&&bInventoryOpen&&!bInventoryMoving,TEXT("Escape cancels held move before closing"));Check(CloseInventory()&&!bInventoryOpen&&!InventoryOverlay.IsValid(),TEXT("Escape closes inventory without logout"));
        bInventoryOpen=true;SelectedItemSlot=40;bConfirmSale=true;RefreshInventoryUI();auto Changed=MakeShared<FJsonObject>();Changed->Values=State->Values;Changed->SetNumberField(TEXT("revision"),State->GetIntegerField(TEXT("revision"))+1);Changed->SetNumberField(TEXT("state_revision"),State->GetIntegerField(TEXT("state_revision"))+1);Changed->SetArrayField(TEXT("items"),{});ApplyInventory(Changed);Check(SelectedItemSlot==-1&&!bConfirmSale,TEXT("server update invalidates stale selection and sale confirmation"));
        bLocalAvailable=false;SendItemAction(TEXT("merchant_sell"),40);Check(Outgoing.IsEmpty(),TEXT("no actions after loss of local player"));
        Disconnect();ClearEntities();Check(!InventoryState.IsValid()&&!InventoryOverlay.IsValid()&&!bInventoryOpen,TEXT("session cleanup removes items and widgets"));Check(Socket==nullptr,TEXT("no connected socket used"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("checks"),Checks);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".native.json")));UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
