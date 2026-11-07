#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "ImageUtils.h"
#include "InputCoreTypes.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickGuildAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGuildTest="),Path))return false;
 static bool Started=false,Done=false;static double Began=0;static int32 Checks=0;static TArray<FString> Failures;
 if(Done)return true;auto Check=[&](bool Value,const TCHAR* Label){++Checks;if(!Value)Failures.Add(Label);};
 if(!GetWorld()||!GetWorld()->GetGameViewport())return true;
 auto Capture=[&](const TCHAR* Action){Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Value;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Value)&&Value&&Value->GetStringField(TEXT("action"))==Action,TEXT("exactly one original guild command dispatched"));return Value;};
 auto Flag=[](TSharedPtr<FJsonObject> Obj,const TCHAR* Name){bool V=false;if(Obj)Obj->TryGetBoolField(Name,V);return V;};
 auto Gather=[&](TSharedRef<SWidget> Root){TSet<FString> Labels;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetType()==TEXT("STextBlock"))Labels.Add(StaticCastSharedRef<STextBlock>(W)->GetText().ToString());auto* Children=W->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(Root);return Labels;};
 if(!Started){Started=true;Began=FPlatformTime::Seconds();Session=TEXT("isolated-guild-window");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private guild command capture"),false);Outgoing.Empty();
  ClassicLayoutCharacter=TEXT("PRIVATE-GUILD-QA");ClassicLayoutFile=Path+TEXT(".layout.json");ClassicState=MakeShared<FJsonObject>();LoadKeyConfiguration();
  Check(KeyConfiguration->Text(TEXT("show_guild"),0)==TEXT("Shift+G"),TEXT("original Shift+G guild shortcut is available"));
  FString Bindings=Path+TEXT(".migration.ini");FFileHelper::SaveStringToFile(TEXT("[Bindings]\nshow_inventory0=Shift+G\n"),*Bindings);FBridgeKeyConfiguration Migration;Migration.Load(Bindings);
  Check(Migration.Text(TEXT("show_inventory"),0)==TEXT("Shift+G")&&Migration.Text(TEXT("show_guild"),0)==TEXT("-"),TEXT("new guild default cannot replace an existing user shortcut"));
  Check(Migration.Text(TEXT("jump"),0)==TEXT("SpaceBar"),TEXT("shortcut migration retains unrelated controls"));
  auto* PC=GetWorld()->GetFirstPlayerController();Check(PC&&PC->PlayerInput,TEXT("actual native input is available"));
  if(PC&&PC->PlayerInput){PC->PlayerInput->FlushPressedKeys();PC->PlayerInput->ProcessInputStack({},1.f/60,false);for(FKey K:{EKeys::LeftShift,EKeys::G})PC->InputKey(FInputKeyEventArgs(nullptr,FInputDeviceId::CreateFromInternalId(0),K,IE_Pressed,FPlatformTime::Cycles64()));PC->PlayerInput->ProcessInputStack({},1.f/60,false);const FString OldTab=ClassicTab;UpdateClassicInput();auto Open=Capture(TEXT("guild_open"));Check(Flag(Open,TEXT("open"))&&ClassicTab==OldTab,TEXT("Shift+G opens guild without activating plain G group window"));PC->PlayerInput->FlushPressedKeys();PC->PlayerInput->ProcessInputStack({},1.f/60,false);}
  auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("visible"),true);State->SetStringField(TEXT("token"),TEXT("qa:guild:1"));State->SetStringField(TEXT("guild"),TEXT("QA Guild"));State->SetStringField(TEXT("tab"),TEXT("guild"));State->SetNumberField(TEXT("sort"),1);State->SetNumberField(TEXT("page"),1);State->SetNumberField(TEXT("total"),2);State->SetNumberField(TEXT("revision"),1);
  State->SetBoolField(TEXT("pending"),false);State->SetBoolField(TEXT("stale"),false);State->SetBoolField(TEXT("show_offline"),true);
  TArray<TSharedPtr<FJsonValue>> Members;for(int32 I=0;I<2;++I){auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("token"),I?TEXT("qa:birch"):TEXT("qa:oak"));Row->SetStringField(TEXT("name"),I?TEXT("QaBirch"):TEXT("QaOak"));Row->SetNumberField(TEXT("level"),I?12:10);Row->SetStringField(TEXT("class_name"),I?TEXT("Druid"):TEXT("Hero"));Row->SetNumberField(TEXT("rank"),I?5:2);Row->SetNumberField(TEXT("group"),I?0:1);Row->SetBoolField(TEXT("online"),I==0);Row->SetStringField(TEXT("zone"),I?TEXT("2 days ago"):TEXT("Connacht"));Row->SetStringField(TEXT("note"),I?TEXT("Offline member"):TEXT("Guard, west gate"));Members.Add(MakeShared<FJsonValueObject>(Row));}State->SetArrayField(TEXT("members"),Members);
  ApplyGuild(State);Check(GuildOverlay&&GuildPanel,TEXT("original guild roster window builds"));Check(ClassicArt(TEXT("chatext"))!=nullptr,TEXT("existing original frame atlas loads"));Check(ClassicTextures.Contains(TEXT("guild_radio")),TEXT("original blue radio-button artwork loads"));
  const auto Labels=Gather(GuildOverlay.ToSharedRef());Check(Labels.Contains(TEXT("RANK"))&&Labels.Contains(TEXT("NOTE"))&&Labels.Contains(TEXT("QAOAK"))&&Labels.Contains(TEXT("GUARD, WEST GATE")),TEXT("guild columns and quoted note display actual roster data"));
  GuildSelectedToken=TEXT("qa:oak");GuildSelectedName=TEXT("QaOak");GuildMemberAction(TEXT("promote"));auto Promote=Capture(TEXT("guild_member"));Check(Promote&&Promote->GetStringField(TEXT("member_token"))==TEXT("qa:oak")&&Promote->GetStringField(TEXT("verb"))==TEXT("promote"),TEXT("member request carries exact selected roster identity"));Check(Members[0]->AsObject()->GetIntegerField(TEXT("rank"))==2,TEXT("rank remains unchanged until server response"));
  GuildMemberAction(TEXT("remove"));Check(GuildConfirm&&Outgoing.IsEmpty(),TEXT("removal opens confirmation without sending a command"));CompleteGuildConfirmation(false);Check(!GuildConfirm&&Outgoing.IsEmpty(),TEXT("cancel sends no destructive guild command"));GuildMemberAction(TEXT("remove"));CompleteGuildConfirmation(true);auto Remove=Capture(TEXT("guild_member"));Check(Flag(Remove,TEXT("confirmed")),TEXT("only explicit confirmation sends member removal request"));
  GuildMemberAction(TEXT("send"));Check(bChatOpen&&ChatInput&&ChatInput->GetText().ToString()==TEXT("/send QaOak ")&&Outgoing.IsEmpty(),TEXT("Send prepares chat draft without sending a private message"));CloseChat();
  State->SetBoolField(TEXT("pending"),true);ApplyGuild(State);GuildMemberAction(TEXT("demote"));Check(Outgoing.IsEmpty(),TEXT("loading roster disables member actions"));State->SetBoolField(TEXT("pending"),false);State->SetBoolField(TEXT("stale"),true);ApplyGuild(State);GuildMemberAction(TEXT("demote"));Check(Outgoing.IsEmpty(),TEXT("stale roster disables member actions"));State->SetBoolField(TEXT("stale"),false);
  State->SetStringField(TEXT("tab"),TEXT("alliance"));for(auto Value:Members)Value->AsObject()->SetStringField(TEXT("guild"),TEXT("QA Second Guild"));ApplyGuild(State);const auto AllianceLabels=Gather(GuildOverlay.ToSharedRef());Check(AllianceLabels.Contains(TEXT("GUILD"))&&!AllianceLabels.Contains(TEXT("RANK"))&&!AllianceLabels.Contains(TEXT("NOTE")),TEXT("alliance uses original guild column and omits rank/note"));GuildSelectedToken=TEXT("qa:oak");GuildMemberAction(TEXT("promote"));Check(Outgoing.IsEmpty(),TEXT("alliance cannot dispatch guild rank commands"));
  State->SetStringField(TEXT("tab"),TEXT("guild"));ApplyGuild(State);GuildSelectedToken=TEXT("qa:oak");GuildMemberAction(TEXT("remove"));Check(CloseClassicPanel()&&!GuildConfirm&&GuildOverlay,TEXT("Escape-style panel close cancels confirmation before closing roster"));
  Check(CloseGuild()&&!GuildOverlay,TEXT("close removes guild overlay"));auto Closed=Capture(TEXT("guild_open"));Check(Closed&&!Flag(Closed,TEXT("open")),TEXT("close informs original backend state"));ApplyGuild(State);Check(!GuildOverlay,TEXT("late visible snapshot cannot reopen dismissed guild window"));
  ToggleGuild();Capture(TEXT("guild_open"));ApplyGuild(State);Check(GuildOverlay.IsValid(),TEXT("explicit reopen clears local dismissal"));
  GuildSelectedToken=TEXT("qa:oak");GuildSelectedName=TEXT("QaOak");GuildMemberAction(TEXT("remove"));State->SetStringField(TEXT("token"),TEXT("qa:guild:2"));ApplyGuild(State);Check(!GuildConfirm&&GuildSelectedToken.IsEmpty()&&GuildSelectedName.IsEmpty(),TEXT("new membership invalidates selection and pending confirmation"));
  GuildPosition=FVector2D(-1,80);Outgoing.Empty();
 }
 if(FPlatformTime::Seconds()-Began<1)return true;
 Check(GuildPanel&&WorldPointerBlocked(GuildPanel->GetCachedGeometry().GetAbsolutePosition()+FVector2D(12,12)),TEXT("actual guild window intercepts world clicks"));
 TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool Captured=GuildOverlay&&FSlateApplication::Get().TakeScreenshot(GuildOverlay.ToSharedRef(),Pixels,Size);int32 Visible=0;for(auto Pixel:Pixels)Visible+=FMath::Max3(Pixel.R,Pixel.G,Pixel.B)>20;
 if(Captured&&Visible>1000){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}else Captured=false;Check(Captured,TEXT("original guild window captured from actual viewport"));
 CloseGuild(false);RemoveChat();ClassicState.Reset();Check(!GuildOverlay&&!GuildPanel&&!GuildConfirm,TEXT("guild UI cleanup removes panels and confirmation"));Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();bLocalAvailable=false;
 auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);TArray<TSharedPtr<FJsonValue>> Values;for(auto Failure:Failures)Values.Add(MakeShared<FJsonValueString>(Failure));Report->SetArrayField(TEXT("failures"),Values);Report->SetBoolField(TEXT("server_started"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
