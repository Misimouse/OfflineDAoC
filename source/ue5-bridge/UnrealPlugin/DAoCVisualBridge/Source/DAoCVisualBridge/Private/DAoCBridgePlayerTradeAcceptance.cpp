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
extern bool VerifyDAoCPlayerTradeDrop();
bool UDAoCBridgeSubsystem::TickPlayerTradeAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePlayerTradeTest="),Path))return false;
 static int32 Phase=0,Checks=0;static double Started=0;static TSharedPtr<FJsonObject> Fixture;static TArray<TSharedPtr<FJsonValue>> Failures;
 auto Check=[&](bool OK,const FString& Name){++Checks;if(!OK)Failures.Add(MakeShared<FJsonValueString>(Name));UE_LOG(LogTemp,Display,TEXT("Player trade acceptance %d: %s %s"),Checks,OK?TEXT("PASS"):TEXT("FAIL"),*Name);};
 TFunction<void(TSharedRef<SWidget>,const FString&,TArray<TSharedPtr<SWidget>>&)> Collect;
 Collect=[&](TSharedRef<SWidget> W,const FString& Type,TArray<TSharedPtr<SWidget>>& Found){if(W->GetTypeAsString()==Type)Found.Add(W);auto Children=W->GetChildren();for(int32 I=0;Children&&I<Children->Num();++I)Collect(Children->GetChildAt(I),Type,Found);};
 auto Button=[&](const FString& Label)->TSharedPtr<SButton>{TArray<TSharedPtr<SWidget>> Buttons;if(PlayerTradePanel)Collect(PlayerTradePanel.ToSharedRef(),TEXT("SButton"),Buttons);for(auto W:Buttons){TArray<TSharedPtr<SWidget>> Texts;Collect(W.ToSharedRef(),TEXT("STextBlock"),Texts);for(auto T:Texts)if(StaticCastSharedPtr<STextBlock>(T)->GetText().ToString()==Label)return StaticCastSharedPtr<SButton>(W);}return nullptr;};
 auto Capture=[&](const FString& Action){Outgoing.Add(0);FString Raw=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> V;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),V)&&V&&V->GetStringField(TEXT("action"))==Action,TEXT("native trade command: ")+Action);return V;};
 if(Phase==0){FString Text;FFileHelper::LoadFileToString(Text,*Path);if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture)||!Fixture){Check(false,TEXT("fixture loads"));Phase=3;return true;}
  Session=TEXT("player-trade-native-isolated");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Player trade acceptance"),false);InventoryState=Fixture->GetObjectField(TEXT("inventory"));ApplyPlayerTrade(Fixture->GetObjectField(TEXT("trade")));Started=FPlatformTime::Seconds();Phase=1;return true;}
 if(Phase==1&&FPlatformTime::Seconds()-Started>.5){
  Check(VerifyDAoCPlayerTradeDrop(),TEXT("actual drag accepts only own backpack offer area"));
  Check(PlayerTradeOverlay&&PlayerTradePanel,TEXT("original trade panel opens"));Check(ClassicArt(TEXT("trade"))&&ClassicIcon(912),TEXT("original trade atlas and existing item icon load"));
  auto G=PlayerTradePanel->GetCachedGeometry();Check(G.GetLocalSize().Equals(FVector2D(384,256),.1),TEXT("original trade dimensions preserved"));Check(WorldPointerBlocked(G.LocalToAbsolute(FVector2D(30,100))),TEXT("own offer blocks world clicks"));Check(WorldPointerBlocked(G.LocalToAbsolute(FVector2D(300,100))),TEXT("partner offer blocks world clicks"));
  TArray<TSharedPtr<SWidget>> Labels;Collect(PlayerTradePanel.ToSharedRef(),TEXT("STextBlock"),Labels);bool HasCount=false;for(auto W:Labels)HasCount|=StaticCastSharedPtr<STextBlock>(W)->GetText().ToString()==TEXT("12 TRAINING SHIELD");Check(HasCount,TEXT("own offered stack count remains visible"));
  TArray<TSharedPtr<SWidget>> Edits;Collect(PlayerTradePanel.ToSharedRef(),TEXT("SEditableTextBox"),Edits);Check(Edits.Num()==5,TEXT("five original money denominations"));
  if(Edits.Num()==5){FSlateApplication::Get().SetKeyboardFocus(Edits[0],EFocusCause::SetDirectly);Check(ExchangeTyping(),TEXT("money typing captures gameplay input"));FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);}
  auto Accept=Button(TEXT("OK"));Check(Accept.IsValid(),TEXT("accept control exists"));if(Accept){Accept->SimulateClick();auto V=Capture(TEXT("player_trade_accept"));if(V)Check(V->GetStringField(TEXT("trade_token"))==TEXT("offer-one"),TEXT("accept carries displayed offer identity"));}
  Check(PlayerTradeState->GetStringField(TEXT("token"))==TEXT("offer-one")&&!PlayerTradeState->HasField(TEXT("accepted")),TEXT("local click does not predict acceptance or ownership"));
  auto Next=Fixture->GetObjectField(TEXT("trade"));Next->SetStringField(TEXT("token"),TEXT("offer-two"));ApplyPlayerTrade(Next);if(Accept)Accept->SimulateClick();Check(Outgoing.IsEmpty(),TEXT("old button cannot accept changed offer"));
  PlayerTradeMoney={TEXT("0"),TEXT("0"),TEXT("0"),TEXT("1"),TEXT("25")};auto V=MakeShared<FJsonObject>();V->SetArrayField(TEXT("slots"),Next->GetObjectField(TEXT("offer"))->GetArrayField(TEXT("own_slots")));PlayerTradeRequest(TEXT("player_trade_update"),TEXT("offer-two"),7,V);auto Update=Capture(TEXT("player_trade_update"));if(Update){Check(Update->GetNumberField(TEXT("inventory_revision"))==7,TEXT("update retains displayed inventory revision"));Check(Update->GetObjectField(TEXT("item_tokens"))->GetStringField(TEXT("40"))==TEXT("own-cloak"),TEXT("offered item retains inventory identity"));Check(Update->GetArrayField(TEXT("money"))[3]->AsNumber()==1&&Update->GetArrayField(TEXT("money"))[4]->AsNumber()==25,TEXT("money denomination order preserved"));}
  PlayerTradeMoney[4]=TEXT("1.5");PlayerTradeRequest(TEXT("player_trade_update"),TEXT("offer-two"),7,V);Check(Outgoing.IsEmpty(),TEXT("fractional monetary input refused"));PlayerTradeMoney[4]=TEXT("25");PlayerTradeRequest(TEXT("player_trade_update"),TEXT("offer-two"),6,V);Check(Outgoing.IsEmpty(),TEXT("stale inventory update refused"));
  Next->SetBoolField(TEXT("pending"),true);ApplyPlayerTrade(Next);Accept=Button(TEXT("OK"));Check(Accept&&!Accept->IsEnabled(),TEXT("pending offer disables acceptance"));auto Cancel=Button(TEXT("X"));Check(Cancel&&Cancel->IsEnabled(),TEXT("pending offer keeps cancel available"));if(Cancel){Cancel->SimulateClick();Capture(TEXT("player_trade_cancel"));}
  Next->SetBoolField(TEXT("visible"),false);ApplyPlayerTrade(Next);Check(!PlayerTradeOverlay&&!PlayerTradePanel,TEXT("server close removes native trade"));PlayerTradeRequest(TEXT("player_trade_accept"),TEXT("offer-two"),7);Check(Outgoing.IsEmpty(),TEXT("closed state cannot send acceptance"));
  Next->SetBoolField(TEXT("visible"),true);Next->SetBoolField(TEXT("pending"),false);ApplyPlayerTrade(Next);Check(CloseClassicPanel(),TEXT("escape closes trade first"));Capture(TEXT("player_trade_cancel"));ApplyPlayerTrade(Next);Started=FPlatformTime::Seconds();Phase=2;return true;
 }
 if(Phase==2&&FPlatformTime::Seconds()-Started>.5){FScreenshotRequest::RequestScreenshot(Path+TEXT(".png"),true,false);Started=FPlatformTime::Seconds();Phase=3;return true;}
 if(Phase==3&&FPlatformTime::Seconds()-Started>.5){auto Result=MakeShared<FJsonObject>();Result->SetBoolField(TEXT("passed"),Failures.IsEmpty());Result->SetNumberField(TEXT("checks"),Checks);Result->SetArrayField(TEXT("failures"),Failures);Result->SetBoolField(TEXT("real_server"),false);FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);}
 return true;
}
