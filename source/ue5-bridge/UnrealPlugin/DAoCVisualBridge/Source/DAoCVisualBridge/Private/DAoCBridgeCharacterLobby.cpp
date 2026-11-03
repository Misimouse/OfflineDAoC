#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "UnrealClient.h"
#include "Kismet/KismetSystemLibrary.h"

namespace {
FString LobbyText(TSharedPtr<FJsonObject> O,const TCHAR* K){FString V;if(O)O->TryGetStringField(K,V);return V;}
bool LobbyFlag(TSharedPtr<FJsonObject> O,const TCHAR* K){bool V=false;if(O)O->TryGetBoolField(K,V);return V;}
int32 LobbyNumber(TSharedPtr<FJsonObject> O,const TCHAR* K){double V=0;if(O)O->TryGetNumberField(K,V);return int32(V);}
TArray<TSharedPtr<FJsonValue>> LobbyArray(TSharedPtr<FJsonObject> O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
TSharedRef<STextBlock> LobbyLabel(const FString& Text,int32 Size=14){return SNew(STextBlock).Text(FText::FromString(Text)).Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),Size)).AutoWrapText(true).ColorAndOpacity(FLinearColor(.94f,.89f,.77f));}
TSharedRef<SButton> LobbyButton(const FString& Text,TFunction<void()> Action){return SNew(SButton).OnClicked_Lambda([Action](){Action();return FReply::Handled();})[LobbyLabel(Text)];}
}

void UDAoCBridgeSubsystem::RemoveCharacterLobby(){
    if(CharacterLobbyOverlay&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef());
    CharacterLobbyOverlay.Reset();CharacterLobbyPanel.Reset();CharacterLobbyState.Reset();CharacterLobbyRevision=-1;
}

void UDAoCBridgeSubsystem::ApplyCharacterLobby(TSharedPtr<FJsonObject> State,bool InGame){
    if(InGame||!LobbyFlag(State,TEXT("enabled"))){if(CharacterLobbyOverlay)RemoveCharacterLobby();return;}
    if(!CharacterLobbyOverlay){RemoveClassicUI();RemoveInventoryUI();RemoveInteractionUI();RemovePlayerStatusUI();}
    CharacterLobbyState=State;const int64 Revision=LobbyNumber(State,TEXT("revision"));
    if(CharacterLobbyOverlay&&CharacterLobbyRevision==Revision)return;
    CharacterLobbyRevision=Revision;RefreshCharacterLobby();
}

void UDAoCBridgeSubsystem::SendCharacterAction(const FString& Action){
    if(!CharacterLobbyState||!CharacterLobbyOverlay)return;
    auto Values=MakeShared<FJsonObject>();Values->SetNumberField(TEXT("lobby_revision"),LobbyNumber(CharacterLobbyState,TEXT("revision")));
    if(Action==TEXT("character_enter"))Values->SetStringField(TEXT("name"),CharacterLobbySelected);
    if(Action==TEXT("character_create")){Values->SetStringField(TEXT("name"),CharacterLobbyName);Values->SetStringField(TEXT("choice_id"),CharacterLobbyChoice);}
    Send(Action,Values);
}

void UDAoCBridgeSubsystem::RefreshCharacterLobby(){
    if(!GetWorld()||!GetWorld()->GetGameViewport()||!CharacterLobbyState)return;auto* Viewport=GetWorld()->GetGameViewport();
    if(CharacterLobbyOverlay)Viewport->RemoveViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef());
    auto Content=SNew(SVerticalBox);Content->AddSlot().AutoHeight().Padding(0,0,0,18)[LobbyLabel(TEXT("Dark Age of Camelot - Hibernia"),24)];
    auto Columns=SNew(SHorizontalBox);auto Roster=SNew(SVerticalBox);auto Characters=LobbyArray(CharacterLobbyState,TEXT("characters"));
    bool SelectedExists=false;for(auto V:Characters)if(LobbyText(V->AsObject(),TEXT("name"))==CharacterLobbySelected)SelectedExists=true;
    if(!SelectedExists)CharacterLobbySelected=Characters.IsEmpty()?TEXT(""):LobbyText(Characters[0]->AsObject(),TEXT("name"));
    Roster->AddSlot().AutoHeight().Padding(0,0,0,10)[LobbyLabel(TEXT("Your characters"),18)];
    auto Rows=SNew(SVerticalBox);
    for(auto V:Characters){auto Row=V->AsObject();const FString Name=LobbyText(Row,TEXT("name"));const FString Caption=Name+FString::Printf(TEXT("  -  Level %d\n"),LobbyNumber(Row,TEXT("level")))+LobbyText(Row,TEXT("race"))+TEXT(" ")+LobbyText(Row,TEXT("class_name"));
        Rows->AddSlot().AutoHeight().Padding(0,3)[SNew(SBorder).BorderBackgroundColor(Name==CharacterLobbySelected?FLinearColor(.3f,.25f,.1f):FLinearColor(.03f,.03f,.03f)).Padding(2)[LobbyButton(Caption,[this,Name](){CharacterLobbySelected=Name;RefreshCharacterLobby();})]];
    }
    if(Characters.IsEmpty())Rows->AddSlot().AutoHeight()[LobbyLabel(TEXT("No characters in this realm yet."))];
    Roster->AddSlot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[Rows]];
    const bool Ready=LobbyFlag(CharacterLobbyState,TEXT("ready")),Pending=LobbyFlag(CharacterLobbyState,TEXT("pending"));
    Roster->AddSlot().AutoHeight().Padding(0,12)[SNew(SBox).IsEnabled(Ready&&!Pending&&!CharacterLobbySelected.IsEmpty())[LobbyButton(TEXT("ENTER REALM"),[this](){SendCharacterAction(TEXT("character_enter"));})]];
    Columns->AddSlot().FillWidth(1).Padding(0,0,20,0)[Roster];
    auto Create=SNew(SVerticalBox);Create->AddSlot().AutoHeight().Padding(0,0,0,10)[LobbyLabel(TEXT("Create a character"),18)];
    Create->AddSlot().AutoHeight().Padding(0,4)[LobbyLabel(TEXT("Name"))];
    Create->AddSlot().AutoHeight().Padding(0,4)[SNew(SEditableTextBox).Text(FText::FromString(CharacterLobbyName)).HintText(FText::FromString(TEXT("Start with a capital letter"))).OnTextChanged_Lambda([this](const FText& Text){CharacterLobbyName=Text.ToString().Left(24);})];
    auto RaceMenu=SNew(SVerticalBox);for(const FString Race:{TEXT("Celt"),TEXT("Firbolg"),TEXT("Elf"),TEXT("Lurikeen"),TEXT("Sylvan")})RaceMenu->AddSlot().AutoHeight()[LobbyButton(Race,[this,Race](){CharacterLobbyRace=Race;CharacterLobbyChoice.Empty();RefreshCharacterLobby();})];
    Create->AddSlot().AutoHeight().Padding(0,4)[LobbyLabel(TEXT("Race"))];Create->AddSlot().AutoHeight()[SNew(SComboButton).ButtonContent()[LobbyLabel(CharacterLobbyRace)].MenuContent()[RaceMenu]];
    auto Gender=SNew(SHorizontalBox);for(bool Female:{false,true})Gender->AddSlot().FillWidth(1).Padding(2)[LobbyButton(Female?TEXT("Female"):TEXT("Male"),[this,Female](){bCharacterLobbyFemale=Female;CharacterLobbyChoice.Empty();RefreshCharacterLobby();})];
    Create->AddSlot().AutoHeight().Padding(0,8)[LobbyLabel(bCharacterLobbyFemale?TEXT("Gender: Female"):TEXT("Gender: Male"))];Create->AddSlot().AutoHeight()[Gender];
    TArray<TSharedPtr<FJsonObject>> Choices;for(auto V:LobbyArray(CharacterLobbyState,TEXT("choices"))){auto C=V->AsObject();if(LobbyText(C,TEXT("race"))==CharacterLobbyRace&&LobbyFlag(C,TEXT("female"))==bCharacterLobbyFemale)Choices.Add(C);}
    TSharedPtr<FJsonObject> SelectedChoice;for(auto C:Choices)if(LobbyText(C,TEXT("id"))==CharacterLobbyChoice)SelectedChoice=C;
    if(!SelectedChoice&&!Choices.IsEmpty()){SelectedChoice=Choices[0];CharacterLobbyChoice=LobbyText(SelectedChoice,TEXT("id"));}
    auto Classes=SNew(SVerticalBox);for(auto C:Choices){const FString Id=LobbyText(C,TEXT("id"));Classes->AddSlot().AutoHeight()[LobbyButton(LobbyText(C,TEXT("class_name")),[this,Id](){CharacterLobbyChoice=Id;RefreshCharacterLobby();})];}
    Create->AddSlot().AutoHeight().Padding(0,8)[LobbyLabel(TEXT("Class"))];Create->AddSlot().AutoHeight()[SNew(SComboButton).ButtonContent()[LobbyLabel(SelectedChoice?LobbyText(SelectedChoice,TEXT("class_name")):TEXT("Loading classes..."))].MenuContent()[SNew(SBox).MaxDesiredHeight(300)[SNew(SScrollBox)+SScrollBox::Slot()[Classes]]]];
    Create->AddSlot().AutoHeight().Padding(0,12)[LobbyLabel(TEXT("Starting attributes follow your selected class. New characters use the default appearance."),11)];
    Create->AddSlot().AutoHeight()[SNew(SBox).IsEnabled(Ready&&!Pending&&SelectedChoice.IsValid()&&Characters.Num()<10)[LobbyButton(TEXT("CREATE CHARACTER"),[this](){SendCharacterAction(TEXT("character_create"));})]];
    Columns->AddSlot().FillWidth(1)[SNew(SBox).IsEnabled(!Pending)[Create]];Content->AddSlot().FillHeight(1)[Columns];
    Content->AddSlot().AutoHeight().Padding(0,14)[LobbyLabel(LobbyText(CharacterLobbyState,TEXT("feedback")))];
    auto Bottom=SNew(SHorizontalBox);Bottom->AddSlot().FillWidth(1)[SNew(SBox).IsEnabled(!Pending)[LobbyButton(TEXT("REFRESH LIST"),[this](){SendCharacterAction(TEXT("character_refresh"));})]];Bottom->AddSlot().FillWidth(1).Padding(10,0,0,0)[LobbyButton(TEXT("QUIT"),[this](){Send(TEXT("logout"));})];Content->AddSlot().AutoHeight()[Bottom];
    CharacterLobbyPanel=SNew(SBorder).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,1)).Padding(28)[SNew(SBox).WidthOverride(780).HeightOverride(590)[Content]];
    CharacterLobbyOverlay=SNew(SOverlay)+SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor(.005f,.008f,.005f,.99f))]+SOverlay::Slot().Padding(24)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)[CharacterLobbyPanel.ToSharedRef()]];
    Viewport->AddViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef(),100);
}

bool UDAoCBridgeSubsystem::TickCharacterLobbyAcceptance(){
    FString LiveProbe;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCharacterLobbyLiveProbe="),LiveProbe)){
        static double ReadyAt=0;static bool Captured=false,Finished=false;
        if(Finished)return true;
        if(!CharacterLobbyOverlay||!LobbyFlag(CharacterLobbyState,TEXT("ready")))return false;
        const double Now=FPlatformTime::Seconds();if(!ReadyAt)ReadyAt=Now;
        if(Now-ReadyAt>2&&!Captured){FScreenshotRequest::RequestScreenshot(LiveProbe+TEXT(".png"),true,false);Captured=true;}
        if(Now-ReadyAt>4){auto R=MakeShared<FJsonObject>();const auto Characters=LobbyArray(CharacterLobbyState,TEXT("characters")),Choices=LobbyArray(CharacterLobbyState,TEXT("choices"));R->SetBoolField(TEXT("passed"),CharacterLobbyPanel.IsValid()&&!Choices.IsEmpty()&&FPaths::FileExists(LiveProbe+TEXT(".png")));R->SetBoolField(TEXT("world_entered"),bHavePlayer);R->SetNumberField(TEXT("characters"),Characters.Num());R->SetNumberField(TEXT("choices"),Choices.Num());FString Result;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Result));FFileHelper::SaveStringToFile(Result,*LiveProbe);Finished=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;}
        return false;
    }
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCharacterLobbyTest="),Path))return false;
    static int32 Phase=0,Checks=0;static double Started=0;static TArray<TSharedPtr<FJsonValue>> Failures;
    if(Phase==99)return true;
    auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Capture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCharacterLobbyCapture="),Capture);
    if(Phase==0){
        Phase=1;Started=FPlatformTime::Seconds();FString Text;TSharedPtr<FJsonObject> Fixture;
        Check(FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("server lobby fixture loaded"));
        if(Fixture){
            auto State=Fixture->GetObjectField(TEXT("character_lobby"));Check(LobbyFlag(State,TEXT("ready")),TEXT("server supplied a complete character list"));
            ApplyCharacterLobby(State,false);Check(CharacterLobbyOverlay.IsValid()&&CharacterLobbyPanel.IsValid(),TEXT("selection and creation screen opens before world entry"));
            const bool BeforeView=bFirstPerson;bLocalAvailable=true;ToggleFirstPerson();Check(bFirstPerson==BeforeView,TEXT("character menu blocks gameplay camera toggles"));bLocalAvailable=false;
            TArray<TSharedPtr<SEditableTextBox>> Inputs;TFunction<void(TSharedRef<SWidget>)> Visit;Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SEditableTextBox"))Inputs.Add(StaticCastSharedRef<SEditableTextBox>(W));auto* Children=W->GetChildren();for(int32 I=0;Children&&I<Children->Num();++I)Visit(Children->GetChildAt(I));};
            if(CharacterLobbyPanel)Visit(CharacterLobbyPanel.ToSharedRef());Check(Inputs.Num()==1,TEXT("character name has an editable input"));if(!Inputs.IsEmpty())Inputs[0]->SetText(FText::FromString(TEXT("Previewhero")));
            Check(CharacterLobbyName==TEXT("Previewhero"),TEXT("typed character name survives UI state"));
            Check(!CharacterLobbySelected.IsEmpty()&&!CharacterLobbyChoice.IsEmpty(),TEXT("only supplied characters and class choices are selected"));
            Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Offline character menu acceptance"),false);Session=TEXT("character-menu-acceptance");
            auto ReadCommand=[&](const FString& Action){Outgoing.Add(0);const FString Data=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Value;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Data),Value)&&Value&&LobbyText(Value,TEXT("action"))==Action,TEXT("menu sends ")+Action);return Value;};
            SendCharacterAction(TEXT("character_create"));auto Create=ReadCommand(TEXT("character_create"));if(Create)Check(LobbyText(Create,TEXT("name"))==TEXT("Previewhero")&&LobbyText(Create,TEXT("choice_id"))==CharacterLobbyChoice&&LobbyNumber(Create,TEXT("lobby_revision"))==LobbyNumber(State,TEXT("revision")),TEXT("creation carries exact name choice and server revision"));
            SendCharacterAction(TEXT("character_enter"));auto Enter=ReadCommand(TEXT("character_enter"));if(Enter)Check(LobbyText(Enter,TEXT("name"))==CharacterLobbySelected,TEXT("enter request uses selected server character"));
            ApplyCharacterLobby(State,true);Check(!CharacterLobbyOverlay.IsValid(),TEXT("menu closes when server confirms world entry"));
            ApplyCharacterLobby(State,false);Check(CharacterLobbyOverlay.IsValid(),TEXT("menu can be restored after a session transition"));
            if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Session.Empty();
        }
    }
    if(!Capture.IsEmpty()){
        if(Phase==1){if(FPlatformTime::Seconds()-Started<4)return true;FScreenshotRequest::RequestScreenshot(Capture,true,false);Phase=2;Started=FPlatformTime::Seconds();return true;}
        if(FPlatformTime::Seconds()-Started<1)return true;
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("live_account"),false);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));RemoveCharacterLobby();Phase=99;
    UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
