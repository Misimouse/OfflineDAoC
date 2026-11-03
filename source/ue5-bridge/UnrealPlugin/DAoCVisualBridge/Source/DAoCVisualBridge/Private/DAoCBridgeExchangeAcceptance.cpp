#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Framework/Application/SlateApplication.h"
#include "UnrealClient.h"
#include "Kismet/KismetSystemLibrary.h"
#include "InputCoreTypes.h"

bool UDAoCBridgeSubsystem::TickExchangeAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeExchangeTest="),Path))return false;
 static int Phase=0,Checks=0;static double At=0;static TSharedPtr<FJsonObject> Fixture;static TArray<TSharedPtr<FJsonValue>> Failures;
 auto Check=[&](bool OK,const FString& Name){++Checks;if(!OK)Failures.Add(MakeShared<FJsonValueString>(Name));UE_LOG(LogTemp,Display,TEXT("Exchange acceptance %d phase %d: %s %s"),Checks,Phase,OK?TEXT("PASS"):TEXT("FAIL"),*Name);};
 auto Capture=[&](const FString& Action){Outgoing.Add(0);FString Raw=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> V;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),V)&&V&&V->GetStringField(TEXT("action"))==Action,TEXT("native exchange command: ")+Action);return V;};
 TFunction<void(TSharedRef<SWidget>,const FString&,TArray<TSharedPtr<SWidget>>&)> Collect;
 Collect=[&](TSharedRef<SWidget> W,const FString& Type,TArray<TSharedPtr<SWidget>>& Found){if(W->GetTypeAsString()==Type)Found.Add(W);auto Children=W->GetChildren();for(int I=0;Children&&I<Children->Num();++I)Collect(Children->GetChildAt(I),Type,Found);};
 auto Button=[&](const FString& Label)->TSharedPtr<SButton>{TArray<TSharedPtr<SWidget>> Buttons;if(ExchangePanel)Collect(ExchangePanel.ToSharedRef(),TEXT("SButton"),Buttons);for(auto W:Buttons){TArray<TSharedPtr<SWidget>> Texts;Collect(W.ToSharedRef(),TEXT("STextBlock"),Texts);for(auto T:Texts)if(StaticCastSharedPtr<STextBlock>(T)->GetText().ToString()==Label)return StaticCastSharedPtr<SButton>(W);}return nullptr;};
 if(Phase==0){FString Text;FFileHelper::LoadFileToString(Text,*Path);if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture)||!Fixture){Check(false,TEXT("exchange fixture loads"));Phase=3;return true;}
  Session=TEXT("exchange-native-isolated");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Exchange acceptance"),false);
  ApplyInventory(Fixture->GetObjectField(TEXT("inventory")));ApplyPlayerStatus(Fixture->GetObjectField(TEXT("player_status")));ApplyClassicUI(Fixture->GetObjectField(TEXT("classic_ui")));SetClassicTab(TEXT("inventory"));ApplyExchange(Fixture->GetObjectField(TEXT("exchange")));At=FPlatformTime::Seconds();Phase=1;return true;}
 if(Phase==1&&FPlatformTime::Seconds()-At>.5){
  Check(ExchangeOverlay.IsValid()&&ExchangePanel.IsValid(),TEXT("original exchange window opens from broker state"));Check(ClassicArt(TEXT("chatext"))&&ClassicIcon(912),TEXT("original granite and real item icon loaded"));
  auto G=ExchangePanel->GetCachedGeometry();Check(G.GetLocalSize().Equals(FVector2D(700,556),.1),TEXT("original 700 by 556 layout"));Check(WorldPointerBlocked(G.LocalToAbsolute(FVector2D(40,120))),TEXT("exchange filters block world clicks"));Check(WorldPointerBlocked(G.LocalToAbsolute(FVector2D(680,480))),TEXT("exchange list and footer block world clicks"));
  TArray<TSharedPtr<SWidget>> Icons;Collect(ExchangePanel.ToSharedRef(),TEXT("SClassicAction"),Icons);Check(Icons.Num()==1,TEXT("one real market result icon"));
  TSet<FKey> Buttons;Buttons.Add(EKeys::LeftMouseButton);FPointerEvent Mouse(0,FVector2D(1,1),FVector2D(1,1),Buttons,EKeys::LeftMouseButton,0,FModifierKeysState());
  if(Icons.Num()==1){Icons[0]->OnMouseButtonDown(G,Mouse);Icons[0]->OnMouseButtonUp(G,Mouse);Check(ExchangeSelected==5&&Outgoing.IsEmpty(),TEXT("single click selects exact server result without buying"));Icons.Empty();Collect(ExchangePanel.ToSharedRef(),TEXT("SClassicAction"),Icons);Icons[0]->OnMouseButtonDoubleClick(G,Mouse);Check(ExchangeConfirm.IsValid()&&Outgoing.IsEmpty(),TEXT("double click asks before spending coins"));auto Confirm=Button(TEXT("CONFIRM PURCHASE"));Check(Confirm.IsValid(),TEXT("purchase confirmation is visible"));if(Confirm){Confirm->SimulateClick();auto V=Capture(TEXT("exchange_buy"));if(V)Check(V->GetIntegerField(TEXT("index"))==5&&V->GetStringField(TEXT("exchange_item_token"))==TEXT("market-item-5")&&V->GetStringField(TEXT("exchange_token"))==TEXT("exchange-native-window"),TEXT("confirmed purchase preserves exact item and window identity"));}}
  ExchangeSelect(5,true);ExchangeState->SetNumberField(TEXT("catalog_revision"),8);auto Confirm=Button(TEXT("CONFIRM PURCHASE"));if(Confirm)Confirm->SimulateClick();Check(Outgoing.IsEmpty()&&!ExchangeConfirm,TEXT("price or catalogue changes invalidate captured confirmation"));
  ExchangeState->SetBoolField(TEXT("pending"),true);ExchangeRequest(TEXT("exchange_claim"));Check(Outgoing.IsEmpty(),TEXT("pending operation blocks another frontend request"));ExchangeState->SetBoolField(TEXT("pending"),false);
  ExchangeSignature.Empty();RefreshExchange();TArray<TSharedPtr<SWidget>> Edits;Collect(ExchangePanel.ToSharedRef(),TEXT("SEditableTextBox"),Edits);Check(Edits.Num()==6,TEXT("six name level quality price and bonus fields available"));
  if(!Edits.IsEmpty()){FSlateApplication::Get().SetKeyboardFocus(Edits[0],EFocusCause::SetDirectly);Check(ExchangeTyping(),TEXT("typing in exchange fields captures gameplay keyboard"));FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);}
  ExchangeFields.Add(TEXT("name"),TEXT("club"));auto Search=Button(TEXT("SEARCH"));if(Search){Search->SimulateClick();auto V=Capture(TEXT("exchange_search"));if(V)Check(V->GetObjectField(TEXT("filters"))->GetStringField(TEXT("name"))==TEXT("club"),TEXT("search sends current original filter names"));}
  auto State=Fixture->GetObjectField(TEXT("listings"));ApplyExchange(State);Check(ExchangePanel.IsValid()&&ExchangeSelected==-1,TEXT("own chest resets selection on window change"));
  ExchangeListingPage=1;ExchangeSignature.Empty();RefreshExchange();Icons.Empty();Collect(ExchangePanel.ToSharedRef(),TEXT("SClassicAction"),Icons);Check(Icons.Num()==1,TEXT("second chest display page shows actual slot 170"));
  ExchangeSelect(170);ExchangeFields.Add(TEXT("price"),TEXT("1234"));auto SetPrice=Button(TEXT("SET PRICE"));if(SetPrice){SetPrice->SimulateClick();auto V=Capture(TEXT("exchange_price"));if(V)Check(V->GetIntegerField(TEXT("index"))==170&&V->GetIntegerField(TEXT("copper"))==1234,TEXT("listing price keeps server slot and copper units"));}
  auto Take=Button(TEXT("TAKE BACK"));if(Take){Take->SimulateClick();auto V=Capture(TEXT("exchange_take"));if(V)Check(V->GetIntegerField(TEXT("index"))==170,TEXT("withdrawal preserves chest slot after client pagination"));}
  auto Claim=Button(TEXT("CLAIM"));if(Claim){Claim->SimulateClick();Capture(TEXT("exchange_claim"));}
  auto Item=InventoryItem(40);Check(Item.IsValid(),TEXT("real backpack item exists for listing"));if(Item){ExchangeListItem(40,Item->GetStringField(TEXT("token")));auto V=Capture(TEXT("exchange_list"));if(V)Check(V->GetIntegerField(TEXT("slot"))==40&&V->GetStringField(TEXT("item_token"))==Item->GetStringField(TEXT("token")),TEXT("listing command carries exact backpack token"));ExchangeListItem(40,TEXT("stale"));Check(Outgoing.IsEmpty(),TEXT("stale backpack drag cannot list an item"));}
  Check(!ExchangeDropToBackpack(TEXT("srvc:170"),TEXT("owner-item-170"),TEXT("old-window"),9)&&Outgoing.IsEmpty(),TEXT("old window drag cannot withdraw"));Check(ExchangeDropToBackpack(TEXT("srvc:170"),TEXT("owner-item-170"),TEXT("exchange-native-owner"),9),TEXT("current listing drag accepts backpack destination"));Capture(TEXT("exchange_take"));
  Check(CloseClassicPanel()&&!ExchangeOverlay,TEXT("escape closes market before character sheet"));auto Closed=Capture(TEXT("exchange_close"));if(Closed)Check(Closed->GetStringField(TEXT("exchange_token"))==TEXT("exchange-native-owner"),TEXT("close carries correct broker window token"));
  auto Browse=Fixture->GetObjectField(TEXT("exchange"));Browse->SetNumberField(TEXT("catalog_revision"),7);ApplyExchange(Browse);ExchangeSelect(5);At=FPlatformTime::Seconds();Phase=2;return true;
 }
 if(Phase==2&&FPlatformTime::Seconds()-At>.5){FScreenshotRequest::RequestScreenshot(Path+TEXT(".png"),true,false);At=FPlatformTime::Seconds();Phase=3;return true;}
 if(Phase==3&&FPlatformTime::Seconds()-At>.5){auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),Failures.IsEmpty());Result->SetNumberField(TEXT("checks"),Checks);Result->SetArrayField(TEXT("failures"),Failures);Result->SetBoolField(TEXT("real_server"),false);FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);}
 return true;
}
