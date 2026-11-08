#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "ImageUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Kismet/KismetSystemLibrary.h"

extern bool VerifyDAoCClassicHoverWidget();
bool UDAoCBridgeSubsystem::TickHoverDetailsAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeHoverDetailsTest="),Path))return false;
 static bool Started=false,Done=false;static double Began=0;static TSharedPtr<SWidget> Preview,PreviewRoot;
 static TArray<TSharedPtr<FJsonValue>> Failures;static int32 Checks=0;
 if(Done)return true;if(!GetWorld()||!GetWorld()->GetGameViewport()||!GetWorld()->GetFirstPlayerController())return true;
 auto Check=[&](bool Value,const TCHAR* Label){++Checks;if(!Value)Failures.Add(MakeShared<FJsonValueString>(Label));};
 if(!Started){
  Started=true;Began=FPlatformTime::Seconds();Session=TEXT("isolated-hover-details");bLocalAvailable=true;bExiting=false;
  Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private hover command capture"),false);Outgoing.Empty();
  ClassicState=MakeShared<FJsonObject>();auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),TEXT("srv:40"));Entry->SetStringField(TEXT("token"),TEXT("item:original"));Entry->SetStringField(TEXT("name"),TEXT("Training sword"));Entry->SetStringField(TEXT("kind"),TEXT("item"));
  ClassicState->SetArrayField(TEXT("entries"),{MakeShared<FJsonValueObject>(Entry)});
  Entry->SetStringField(TEXT("item_token"),TEXT("held"));InventoryState=MakeShared<FJsonObject>();auto Held=MakeShared<FJsonObject>();Held->SetNumberField(TEXT("slot"),40);Held->SetStringField(TEXT("token"),TEXT("held"));InventoryState->SetArrayField(TEXT("items"),{MakeShared<FJsonValueObject>(Held)});
  Check(VerifyDAoCClassicHoverWidget(),TEXT("actual icon and label hover callbacks show live noninteractive text without clicks or inspection"));
  ClassicHover(TEXT("srv:40"),TEXT("stale"));Check(Outgoing.IsEmpty(),TEXT("stale item identity cannot request replacement details"));
  ClassicHover(TEXT("srv:missing"),TEXT("item:original"));Check(Outgoing.IsEmpty(),TEXT("unknown entry cannot request details"));
  bExiting=true;ClassicHover(TEXT("srv:40"),TEXT("item:original"));Check(Outgoing.IsEmpty(),TEXT("exiting session blocks new hover requests"));bExiting=false;
  Entry->SetStringField(TEXT("kind"),TEXT("petcmd"));ClassicHover(TEXT("srv:40"),TEXT("item:original"));Check(Outgoing.IsEmpty(),TEXT("pet commands cannot be treated as item detail requests"));Entry->SetStringField(TEXT("kind"),TEXT("item"));
  ClassicHover(TEXT("srv:40"),TEXT("item:original"));Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Request;
  const bool Parsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Request)&&Request.IsValid();Check(Parsed,TEXT("hover emits a structured command"));
  if(Parsed){Check(Request->GetStringField(TEXT("action"))==TEXT("ui_hover"),TEXT("hover uses metadata-only request rather than item use"));Check(Request->GetStringField(TEXT("entry_id"))==TEXT("srv:40")&&Request->GetStringField(TEXT("entry_token"))==TEXT("item:original"),TEXT("hover carries exact current entry identity"));Check(!Request->HasField(TEXT("slot"))&&!Request->HasField(TEXT("spell")),TEXT("hover cannot inject an item move or cast"));}
  Check(ClassicHoverText(TEXT("srv:40"),TEXT("item:original")).ToString()==TEXT("Training sword"),TEXT("missing response shows original name only"));
  auto Hover=MakeShared<FJsonObject>();Hover->SetStringField(TEXT("entry_id"),TEXT("srv:40"));Hover->SetStringField(TEXT("entry_token"),TEXT("item:original"));Hover->SetStringField(TEXT("caption"),TEXT("Training sword"));Hover->SetStringField(TEXT("status"),TEXT("pending"));Hover->SetArrayField(TEXT("lines"),{MakeShared<FJsonValueString>(TEXT("Condition: 81%")),MakeShared<FJsonValueString>(TEXT("Durability: 97%")),MakeShared<FJsonValueString>(TEXT("A description supplied by the original server. No local stats are invented."))});ClassicState->SetObjectField(TEXT("hover"),Hover);
  Check(ClassicHoverText(TEXT("srv:40"),TEXT("item:original")).ToString()==TEXT("Training sword"),TEXT("pending response cannot show unconfirmed properties"));Hover->SetStringField(TEXT("status"),TEXT("ready"));
  Check(ClassicHoverText(TEXT("srv:40"),TEXT("item:original")).ToString().Contains(TEXT("Condition: 81%\nDurability: 97%")),TEXT("ready response preserves original lines and English case"));
  Hover->SetStringField(TEXT("entry_token"),TEXT("old"));Check(ClassicHoverText(TEXT("srv:40"),TEXT("item:original")).ToString()==TEXT("Training sword"),TEXT("stale response cannot show properties of a previous item"));Hover->SetStringField(TEXT("entry_token"),TEXT("item:original"));
  Check(ClassicHoverText(TEXT("srv:40"),TEXT("old")).IsEmpty(),TEXT("stale widget cannot display a replacement item"));
  Held->SetStringField(TEXT("token"),TEXT("replacement"));ClassicHover(TEXT("srv:40"),TEXT("item:original"));Check(Outgoing.IsEmpty(),TEXT("inventory packet invalidates hover before the classic catalogue refreshes"));Check(ClassicHoverText(TEXT("srv:40"),TEXT("item:original")).IsEmpty(),TEXT("replacement inventory identity hides stale tooltip immediately"));Held->SetStringField(TEXT("token"),TEXT("held"));
  auto Label=MakeClassicHoverLabel(SNew(STextBlock).Text(FText::FromString(TEXT("Training sword"))),TEXT("srv:40"),TEXT("item:original"));
  Preview=Label->GetToolTip()->AsWidget();PreviewRoot=SNew(SBox).HAlign(HAlign_Left).VAlign(VAlign_Top)[Preview.ToSharedRef()];GetWorld()->GetGameViewport()->AddViewportWidgetContent(PreviewRoot.ToSharedRef(),75);
  Check(!ClassicDetailOverlay.IsValid(),TEXT("hover creates no information window"));Check(Outgoing.IsEmpty(),TEXT("tooltip text evaluation sends no additional requests"));
  return true;
 }
 if(FPlatformTime::Seconds()-Began<.7)return true;
 TArray<FColor> Pixels;FIntVector Size=FIntVector::ZeroValue;TArray<uint8> Bytes;bool Captured=Preview.IsValid()&&FSlateApplication::Get().TakeScreenshot(Preview.ToSharedRef(),Pixels,Size);
 if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("actual tooltip widget captured for visual review"));
 if(Preview.IsValid())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(PreviewRoot.ToSharedRef());Preview.Reset();PreviewRoot.Reset();ClassicState.Reset();InventoryState.Reset();Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();bLocalAvailable=false;
 auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*Path);Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
