#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Input/SButton.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Widgets/Text/STextBlock.h"

bool UDAoCBridgeSubsystem::TickWindowRecoveryAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWindowRecoveryTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double Began=0;TArray<FString> Failures;TSharedPtr<FJsonObject> Fixture;FString Original;FVector2D Defaults[5],Chats[2];TArray<FString> Types[2];float Scale=1;};static FRun Run;
    auto Check=[&](bool Good,const TCHAR* Name){++Run.Checks;if(!Good)Run.Failures.Add(Name);};
    auto Button=[&](const FString& Name){TSharedPtr<SButton> Found;TFunction<bool(TSharedRef<SWidget>)> HasText=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("STextBlock"))return StaticCastSharedRef<STextBlock>(W)->GetText().ToString()==Name;auto* C=W->GetChildren();for(int32 I=0;I<C->Num();++I)if(HasText(C->GetChildAt(I)))return true;return false;};TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SButton")&&HasText(W))Found=StaticCastSharedRef<SButton>(W);auto* C=W->GetChildren();for(int32 I=0;I<C->Num();++I)Visit(C->GetChildAt(I));};if(OptionsOverlay)Visit(OptionsOverlay.ToSharedRef());return Found;};
    auto Click=[&](const TCHAR* Name){auto W=Button(Name);Check(W.IsValid()&&W->IsEnabled(),TEXT("original window page button exists and is enabled"));if(W)W->SimulateClick();};
    if(Run.Phase==0){
        FString FixtureFile,Text;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWindowFixture="),FixtureFile);
        Check(FFileHelper::LoadFileToString(Text,*FixtureFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Run.Fixture)&&Run.Fixture.IsValid(),TEXT("original game fixture loads"));
        if(!Run.Fixture){Run.Phase=2;Run.Began=0;return true;}
        auto State=Run.Fixture->GetObjectField(TEXT("classic_ui"));State->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedWindows%lld"),FDateTime::UtcNow().GetTicks()));
        ApplyInventory(Run.Fixture->GetObjectField(TEXT("inventory")));ApplyClassicUI(State);ApplyChat(Run.Fixture);SetChatChannel(0,TEXT("guild"),false);SetChatChannel(1,TEXT("guild"),true);
        FJsonSerializer::Serialize(State,TJsonWriterFactory<>::Create(&Run.Original));Run.Scale=InterfaceSettings->Scale;
        for(int32 I=0;I<5;++I)Run.Defaults[I]=ClassicPositions[I];for(int32 I=0;I<2;++I){Run.Chats[I]=ChatPositions[I];Run.Types[I]=ChatTypes[I];}
        bControlsOptions=bDisplayOptions=bInterfaceOptions=false;bWindowOptions=true;OpenOptions();
        Run.Phase=1;Run.Began=FPlatformTime::Seconds();return true;
    }
    if(FPlatformTime::Seconds()-Run.Began<1)return true;
    if(Run.Phase==1){
        // Unreal may finish applying its display mode after the first game tick.
        // Ask the existing chat initializer for defaults at the actual viewport,
        // rather than comparing margins measured at two different resolutions.
        bChatLayoutReady=false;EnsureChatLayout();SetChatChannel(0,TEXT("guild"),false);SetChatChannel(1,TEXT("guild"),true);
        for(int32 I=0;I<2;++I){Run.Chats[I]=ChatPositions[I];Run.Types[I]=ChatTypes[I];}
        Check(bOptionsOpen&&bWindowOptions&&ClassicArt(TEXT("options")),TEXT("window recovery uses original options frame"));
        for(const TCHAR* Name:{TEXT("SOUND"),TEXT("CONTROLS"),TEXT("DISPLAY"),TEXT("INTERFACE"),TEXT("WINDOWS")})Check(Button(Name).IsValid(),TEXT("all options pages remain accessible"));
        ClassicPositions[0]={30,90};const auto PanelPosition=ClassicPositions[0];Click(TEXT("CHARACTER PANEL"));Check(!bClassicOpen,TEXT("actual panel button closes the existing panel"));Click(TEXT("CHARACTER PANEL"));Check(bClassicOpen&&ClassicPositions[0]==PanelPosition,TEXT("panel reopens at its retained position"));
        ChatPositions[1]={90,180};const auto ChatPosition=ChatPositions[1];Click(TEXT("COMBAT CHAT"));Check(!bChatCombatOpen&&ChatPanels[1]->GetVisibility()==EVisibility::Collapsed,TEXT("combat chat closes independently"));Click(TEXT("COMBAT CHAT"));Check(bChatCombatOpen&&ChatPositions[1]==ChatPosition&&ChatPanels[1]->GetVisibility()==EVisibility::Visible,TEXT("combat chat returns at its retained position"));
        Click(TEXT("GROUP"));Check(bClassicMiniGroupOpen,TEXT("group button opens the existing mini group"));Click(TEXT("GROUP"));Check(!bClassicMiniGroupOpen,TEXT("group button closes the existing mini group"));
        ClassicJournalPosition={40,120};Click(TEXT("QUEST JOURNAL"));Check(bClassicJournalOpen&&ClassicJournalOverlay.IsValid(),TEXT("journal recovery opens the original journal"));Click(TEXT("QUEST JOURNAL"));Check(!bClassicJournalOpen&&ClassicJournalPosition==FVector2D(40,120),TEXT("journal close retains its location"));
        ZoneMapPosition={30,50};Click(TEXT("MAP"));Check(bZoneMapOpen&&ZoneMapOverlay.IsValid(),TEXT("map recovery opens the existing map"));Click(TEXT("MAP"));Check(!bZoneMapOpen&&ZoneMapPosition==FVector2D(30,50),TEXT("map close retains its location"));
        Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private window recovery capture"),false);const auto BeforeGuild=Outgoing.Num();Session=TEXT("isolated-window-recovery");Click(TEXT("GUILD"));Check(Outgoing.Num()>BeforeGuild&&!GuildOverlay.IsValid(),TEXT("guild opening requests original server data instead of fabricating a roster"));Outgoing.Reset();Session.Empty();Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;
        const bool BeforePanel=bClassicOpen;ToggleRecoverableWindow(TEXT("not-a-window"));Check(bClassicOpen==BeforePanel&&Outgoing.IsEmpty(),TEXT("unknown window cannot execute gameplay actions"));
        for(auto& P:ClassicPositions)P={-10000,10000};ClassicVertical[0]=ClassicVertical[1]=true;ClassicVertical[2]=false;ChatSizes[0]={800,400};ChatSizes[1]={700,300};bClassicMiniGroupOpen=true;
        Click(TEXT("RESET WINDOW LAYOUT"));
        for(int32 I=0;I<5;++I)Check(ClassicPositions[I].Equals(Run.Defaults[I],.1),TEXT("reset restores default native window position"));
        for(int32 I=0;I<2;++I){Check(ChatPositions[I].Equals(Run.Chats[I],.1),*FString::Printf(TEXT("reset restores default chat position: before %s after %s"),*Run.Chats[I].ToString(),*ChatPositions[I].ToString()));Check(ChatTypes[I]==Run.Types[I],TEXT("reset preserves the selected chat filters"));}
        Check(ChatSizes[0]==FVector2D(400,112)&&ChatSizes[1]==FVector2D(400,88),TEXT("reset restores existing chat sizes"));
        Check(!ClassicVertical[0]&&!ClassicVertical[1]&&ClassicVertical[2],TEXT("reset restores default quickbar orientations"));
        Check(bClassicOpen&&bChatCombatOpen&&!bClassicMiniGroupOpen&&!bClassicJournalOpen&&!bZoneMapOpen,TEXT("reset restores native default visibility"));
        Check(InterfaceSettings->Scale==Run.Scale,TEXT("window reset preserves the interface scale preference"));
        FString State;FJsonSerializer::Serialize(ClassicState.ToSharedRef(),TJsonWriterFactory<>::Create(&State));Check(State==Run.Original,TEXT("recovery preserves all inventory quickbar and character data"));Check(Outgoing.IsEmpty(),TEXT("local layout recovery sends no inventory or gameplay requests"));
        SaveClassicLayout();RemoveClassicUI();ClassicLayoutCharacter.Empty();ApplyClassicUI(Run.Fixture->GetObjectField(TEXT("classic_ui")));ApplyChat(Run.Fixture);
        for(int32 I=0;I<5;++I)Check(ClassicPositions[I].Equals(Run.Defaults[I],.1),TEXT("reset position survives interface reconstruction"));
        Run.Phase=2;Run.Began=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==2){
        TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size;bool Captured=OptionsOverlay&&FSlateApplication::Get().TakeScreenshot(OptionsOverlay.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("actual Windows options page captured"));
        Check(WorldPointerBlocked(FVector2D(10,10)),TEXT("window options block world input"));CloseOptions();
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=3;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
