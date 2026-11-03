#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SCanvas.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Widgets/Images/SImage.h"
#include "Misc/Paths.h"
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
#include "ContentStreaming.h"
#include "ShaderCompiler.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "Fonts/FontMeasure.h"
#include "UnrealClient.h"
#include "Kismet/KismetSystemLibrary.h"
#include "ImageUtils.h"
#include "Serialization/BufferArchive.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "StaticMeshResources.h"

namespace {
FString LobbyText(TSharedPtr<FJsonObject> O,const TCHAR* K){FString V;if(O)O->TryGetStringField(K,V);return V;}
bool LobbyFlag(TSharedPtr<FJsonObject> O,const TCHAR* K){bool V=false;if(O)O->TryGetBoolField(K,V);return V;}
int32 LobbyNumber(TSharedPtr<FJsonObject> O,const TCHAR* K){double V=0;if(O)O->TryGetNumberField(K,V);return int32(V);}
TArray<TSharedPtr<FJsonValue>> LobbyArray(TSharedPtr<FJsonObject> O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
TSharedPtr<FJsonObject> LobbyLore(){static TSharedPtr<FJsonObject> Lore;if(!Lore){FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/Pregame/lore.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Lore);}return Lore;}

}

void UDAoCBridgeSubsystem::RemoveCharacterLobby(){
    const bool WasOpen=CharacterLobbyOverlay.IsValid();
    if(CharacterLobbyOverlay&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef());
    if(WasOpen&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->bDisableWorldRendering=false;
    CharacterLobbyOverlay.Reset();CharacterLobbyPanel.Reset();CharacterLobbyState.Reset();CharacterLobbyRevision=-1;CharacterLobbyScreen=TEXT("select");ClearCharacterLobbyPreview();
    if(WasOpen&&GetWorld())if(auto* PC=GetWorld()->GetFirstPlayerController()){
        FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(false);Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC->SetInputMode(Mode);PC->bShowMouseCursor=true;
        if(auto* V=GetWorld()->GetGameViewport()){V->SetMouseCaptureMode(EMouseCaptureMode::CaptureDuringRightMouseDown);V->SetMouseLockMode(EMouseLockMode::DoNotLock);}
    }
}

void UDAoCBridgeSubsystem::ApplyCharacterLobby(TSharedPtr<FJsonObject> State,bool InGame){
    if(InGame||!LobbyFlag(State,TEXT("enabled"))){if(CharacterLobbyOverlay)RemoveCharacterLobby();return;}
    // The menu precedes the player pawn, which used to be the only cursor setup.
    // Restore a visible, unlocked pointer without stealing focus from typed names.
    if(auto* PC=GetWorld()->GetFirstPlayerController()){
        const bool ResetMouse=!CharacterLobbyOverlay.IsValid()||bMouseLook||!PC->bShowMouseCursor;
        bMouseLookToggle=false;SetMouseLook(false);
        if(ResetMouse){FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(false);Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC->SetInputMode(Mode);
            if(auto* V=GetWorld()->GetGameViewport()){V->SetMouseCaptureMode(EMouseCaptureMode::NoCapture);V->SetMouseLockMode(EMouseLockMode::DoNotLock);}}
        PC->bShowMouseCursor=true;PC->DefaultMouseCursor=EMouseCursor::Default;PC->CurrentMouseCursor=EMouseCursor::Default;
    }
    if(!CharacterLobbyOverlay){ClearEntities();}
    if(CharacterLobbyState&&LobbyFlag(CharacterLobbyState,TEXT("pending"))&&!LobbyFlag(State,TEXT("pending"))&&LobbyText(State,TEXT("feedback")).StartsWith(TEXT("Character created"))){CharacterLobbyScreen=TEXT("select");for(auto V:LobbyArray(State,TEXT("characters")))if(LobbyText(V->AsObject(),TEXT("name")).Equals(CharacterLobbyName,ESearchCase::IgnoreCase))CharacterLobbySlot=LobbyNumber(V->AsObject(),TEXT("slot"));}
    CharacterLobbyState=State;const int64 Revision=LobbyNumber(State,TEXT("revision"));
    FVector2D Size;GetWorld()->GetGameViewport()->GetViewportSize(Size);const bool Resized=!CharacterLobbyViewportSize.Equals(Size,.1);CharacterLobbyViewportSize=Size;
    if(CharacterLobbyOverlay&&CharacterLobbyRevision==Revision&&!Resized){if(CharacterLobbyCapture){IStreamingManager::Get().AddViewInformation(CharacterLobbyCapture->GetComponentLocation(),Size.X,Size.X/FMath::Tan(FMath::DegreesToRadians(CharacterLobbyCapture->FOVAngle*.5f)),1,false,.5f,CharacterLobbyPreviewActor.Get(),GetWorld());CharacterLobbyCapture->CaptureScene();}return;}
    if(Resized)CharacterLobbyPreviewSignature.Empty();
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
    FVector2D Pixels;Viewport->GetViewportSize(Pixels);const double Width=FMath::Max(1024.,768.*Pixels.X/FMath::Max(1.,Pixels.Y)),Shift=Width-1024;
    CharacterLobbyButtonStyles.Empty();auto Canvas=SNew(SCanvas);const FLinearColor Gold(1,.84,.45),Cream(.93,.89,.78),Dim(.55,.56,.51);
    auto Font=[](int32 Size){return FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"),FMath::Max(7,FMath::RoundToInt(Size*.75)));};
    auto At=[Canvas](double X,double Y,double W,double H,TSharedRef<SWidget> Widget){Canvas->AddSlot().Position(FVector2D(X,Y)).Size(FVector2D(W,H))[Widget];};
    auto Label=[&](const FString& Text,double X,double Y,double W,double H,int32 Size,FLinearColor Color,bool Center=false){At(X,Y,W,H,SNew(STextBlock).Text(FText::FromString(Text.ToUpper())).Font(Font(Size)).ColorAndOpacity(Color).Justification(Center?ETextJustify::Center:ETextJustify::Left).AutoWrapText(true).ShadowOffset(FVector2D(1,1)));};
    auto Button=[&](const FString& Text,double X,double Y,double W,double H,TFunction<void()> Action,bool Enabled=true,bool Selected=false,bool Stone=false){int32 ButtonSize=14;while(ButtonSize>8&&FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text.ToUpper(),Font(ButtonSize)).X>W-8)--ButtonSize;TSharedPtr<FButtonStyle> Style=MakeShared<FButtonStyle>(FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"));CharacterLobbyButtonStyles.Add(Style);if(Stone){for(int32 I=0;I<4;++I){auto Brush=*ClassicArt(TEXT("Pregame/misc_pieces_new"),FVector2D(0,(105.+I*22)/256.),FVector2D(102./256.,(127.+I*22)/256.));if(I==0)Style->SetNormal(Brush);if(I==1)Style->SetHovered(Brush);if(I==2)Style->SetPressed(Brush);if(I==3)Style->SetDisabled(Brush);}}At(X,Y,W,H,SNew(SButton).IsEnabled(Enabled).IsFocusable(false).ButtonStyle(Style.Get()).ContentPadding(0).OnClicked_Lambda([Action,Style](){Action();return FReply::Handled();})[SNew(STextBlock).Text(FText::FromString(Text.ToUpper())).Font(Font(ButtonSize)).ColorAndOpacity(Selected?Gold:Cream).Justification(ETextJustify::Center).AutoWrapText(false)]);};
    auto Art=[&](const FString& Name,double X,double Y,double W,double H,FVector2D Min=FVector2D::ZeroVector,FVector2D Max=FVector2D(1,1)){At(X,Y,W,H,SNew(SImage).Image(ClassicArt(TEXT("Pregame/")+Name,Min,Max)).Visibility(EVisibility::HitTestInvisible));};
    auto Medallion=[&](const FString& Caption,int32 Col,int32 Row,double X,double Y,TFunction<void()> Action,bool Enabled=true,double Size=50,int32 CaptionSize=13){
        TSharedPtr<FButtonStyle> Style=MakeShared<FButtonStyle>(FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"));CharacterLobbyButtonStyles.Add(Style);
        auto Normal=*ClassicArt(TEXT("Pregame/breadcrumbs"),FVector2D(Col*.25,Row*.25),FVector2D((Col+1)*.25,(Row+1)*.25));
        auto Hover=*ClassicArt(TEXT("Pregame/breadcrumbs"),FVector2D((Col+1)*.25,Row*.25),FVector2D((Col+2)*.25,(Row+1)*.25));
        Style->SetNormal(Normal);Style->SetHovered(Hover);Style->SetPressed(Hover);Style->SetDisabled(Normal);
        At(X-Size*.5,Y-Size*.5-6,Size,Size,SNew(SButton).IsEnabled(Enabled).IsFocusable(false).ToolTipText(FText::FromString(Enabled?Caption:Caption+TEXT(" - not yet available"))).ButtonStyle(Style.Get()).ContentPadding(0).OnClicked_Lambda([Action,Style](){Action();return FReply::Handled();}));
        Label(Caption,X-70,Y+Size*.5-8,140,CaptionSize+6,CaptionSize,Enabled?Cream:Dim,true);
    };
    const bool Ready=LobbyFlag(CharacterLobbyState,TEXT("ready")),Pending=LobbyFlag(CharacterLobbyState,TEXT("pending"));auto Characters=LobbyArray(CharacterLobbyState,TEXT("characters"));
    auto Quit=[this](){Send(TEXT("logout"));bExiting=true;};
    if(CharacterLobbyScreen==TEXT("realm")){
        ClearCharacterLobbyPreview();Art(TEXT("realm_selection_wide"),0,0,Width,768);
        const TArray<FString> Names={TEXT("Albion"),TEXT("Hibernia"),TEXT("Midgard")};const TArray<FString> Pictures={TEXT("albion_button"),TEXT("hibernia_button"),TEXT("midgard_button")};
        const TArray<double> AtlasWidths={256,512,256};const TArray<double> CellWidths={122,150,126};const TArray<double> CellHeights={206,214,218};
        for(int32 I=0;I<3;++I){const double X=Width*(170+I*342)/1024.;const bool Allowed=I==1;At(X-75,92,150,210,SNew(SButton).IsEnabled(Allowed).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).OnClicked_Lambda([this](){CharacterLobbyScreen=TEXT("select");RefreshCharacterLobby();return FReply::Handled();})[SNew(SImage).Image(ClassicArt(TEXT("Pregame/")+Pictures[I],FVector2D::ZeroVector,FVector2D(CellWidths[I]/AtlasWidths[I],CellHeights[I]/256)))]);Label(Names[I],X-150,320,300,36,22,Allowed?Gold:Dim,true);const TSharedPtr<FJsonObject>* RealmDescriptions=nullptr;FString LoreText;auto Metadata=LobbyLore();if(Metadata&&Metadata->TryGetObjectField(TEXT("realm_descriptions"),RealmDescriptions))(*RealmDescriptions)->TryGetStringField(Names[I].ToLower(),LoreText);Label(LoreText,X-145,370,290,240,13,Allowed?Cream:Dim,true);if(Allowed)Label(FString::Printf(TEXT("%d CHARACTERS"),Characters.Num()),X-145,610,290,30,15,Gold,true);}
        Label(TEXT("SELECT YOUR REALM"),160+(Width-1024)/2,660,704,36,26,Gold,true);Medallion(TEXT("QUIT"),2,3,44,726,Quit);
    }else{
        TSharedPtr<FJsonObject> Selected;for(auto V:Characters){auto C=V->AsObject();if(LobbyNumber(C,TEXT("slot"))==CharacterLobbySlot)Selected=C;}
        CharacterLobbySelected=Selected?LobbyText(Selected,TEXT("name")):TEXT("");
        TArray<TSharedPtr<FJsonObject>> Choices;for(auto V:LobbyArray(CharacterLobbyState,TEXT("choices"))){auto C=V->AsObject();if(LobbyText(C,TEXT("race"))==CharacterLobbyRace&&LobbyFlag(C,TEXT("female"))==bCharacterLobbyFemale)Choices.Add(C);}
        TSharedPtr<FJsonObject> Choice;for(auto C:Choices)if(LobbyText(C,TEXT("id"))==CharacterLobbyChoice)Choice=C;if(!Choice&&!Choices.IsEmpty()){Choice=Choices[0];CharacterLobbyChoice=LobbyText(Choice,TEXT("id"));}
        auto Preview=Selected?Selected:MakeShared<FJsonObject>();if(CharacterLobbyScreen==TEXT("create")){Preview=MakeShared<FJsonObject>();const TMap<FString,FString> Prefixes={{TEXT("Celt"),TEXT("cel")},{TEXT("Firbolg"),TEXT("fir")},{TEXT("Elf"),TEXT("elf")},{TEXT("Lurikeen"),TEXT("lur")},{TEXT("Sylvan"),TEXT("syl")}};Preview->SetStringField(TEXT("prefix"),Prefixes.FindRef(CharacterLobbyRace)+(bCharacterLobbyFemale?TEXT("_f"):TEXT("_m")));}
        RefreshCharacterLobbyPreview(Preview);if(CharacterLobbyPreviewBrush)At(0,0,Width,768,SNew(SImage).Image(CharacterLobbyPreviewBrush.Get()).Visibility(EVisibility::HitTestInvisible));
        const bool Creating=CharacterLobbyScreen==TEXT("create");const FString Frame=Creating?TEXT("character_creation"):TEXT("character_selection");const double Left=Creating?240:12,Right=Creating?238:268;
        Art(Frame,0,0,Left,768,FVector2D::ZeroVector,FVector2D(Left/1024,1));Art(Frame,Left,0,Width-Left-Right,768,FVector2D(Left/1024,0),FVector2D((1024-Right)/1024,1));Art(Frame,Width-Right,0,Right,768,FVector2D((1024-Right)/1024,0),FVector2D(1,1));
        if(!Creating){
            Label(TEXT("SELECT CHARACTER"),760+Shift,64,248,32,22,Gold,true);
            for(int32 I=0;I<10;++I){TSharedPtr<FJsonObject> C;for(auto V:Characters)if(LobbyNumber(V->AsObject(),TEXT("slot"))==I)C=V->AsObject();const double Y=109+I*45;Button(TEXT(""),764+Shift,Y+1,240,43,[this,I](){CharacterLobbySlot=I;RefreshCharacterLobby();},!Pending);const double Cell=I==CharacterLobbySlot?185:215;Art(TEXT("misc_pieces_new"),770+Shift,Y+11,20,20,FVector2D(Cell/256.,7./256),FVector2D((Cell+24)/256.,31./256));
                if(C){Label(LobbyText(C,TEXT("name"))+(LobbyText(C,TEXT("class_name")).IsEmpty()?TEXT(""):TEXT(" THE ")+LobbyText(C,TEXT("class_name"))),796+Shift,Y+3,206,22,14,I==CharacterLobbySlot?Gold:Cream);Label(FString::Printf(TEXT("LEVEL %d"),LobbyNumber(C,TEXT("level")))+TEXT(" IN ")+LobbyText(C,TEXT("location")),796+Shift,Y+23,208,20,11,Dim);}else Label(TEXT("EMPTY"),796+Shift,Y+11,208,22,16,Dim);
            }
            Medallion(Selected?TEXT("PLAY"):TEXT("CREATE"),0,2,884+Shift,600,[this,Selected](){if(Selected)SendCharacterAction(TEXT("character_enter"));else{CharacterLobbyScreen=TEXT("create");RefreshCharacterLobby();}},Ready&&!Pending,66,24);
            Label(TEXT("SELECT YOUR CHARACTER"),160+Shift/2,660,704,36,26,Gold,true);Medallion(TEXT("QUIT"),2,3,Width*.095,726,Quit);Medallion(TEXT("REALM"),0,0,Width*.2975,726,[this](){CharacterLobbyScreen=TEXT("realm");RefreshCharacterLobby();},!Pending);Medallion(TEXT("OPTIONS"),2,0,Width*.5,726,[](){},false);Medallion(TEXT("CUSTOMIZE"),2,2,Width*.7025,726,[](){},false);Medallion(TEXT("DELETE"),0,1,Width*.905,726,[](){},false);
        }else{
            Label(TEXT("DESCRIPTIONS"),16,62,220,30,22,Gold,true);Label(CharacterLobbyRace,24,96,210,26,20,Gold);Label(Choice?LobbyText(Choice,TEXT("class_name")):TEXT(""),24,124,210,26,16,Gold);
            auto Lore=LobbyLore();
            const TMap<FString,FString> RaceCodes={{TEXT("Celt"),TEXT("CELT")},{TEXT("Firbolg"),TEXT("FIRB")},{TEXT("Elf"),TEXT("ELF")},{TEXT("Lurikeen"),TEXT("LURI")},{TEXT("Sylvan"),TEXT("SYLV")}};
            const TMap<FString,FString> Paths={{TEXT("Blademaster"),TEXT("ARMS")},{TEXT("Champion"),TEXT("ARMS")},{TEXT("Hero"),TEXT("ARMS")},{TEXT("Bard"),TEXT("NATU")},{TEXT("Druid"),TEXT("NATU")},{TEXT("Warden"),TEXT("NATU")},{TEXT("Eldritch"),TEXT("MAGI")},{TEXT("Enchanter"),TEXT("MAGI")},{TEXT("Mentalist"),TEXT("MAGI")},{TEXT("Nightshade"),TEXT("STEA")},{TEXT("Ranger"),TEXT("STEA")},{TEXT("Animist"),TEXT("GROV")},{TEXT("Valewalker"),TEXT("GROV")}};
            FString Description;const TSharedPtr<FJsonObject>* Classes=nullptr;const TSharedPtr<FJsonObject>* Info=nullptr;if(Lore&&Lore->TryGetObjectField(TEXT("classes"),Classes)&&(*Classes)->TryGetObjectField(RaceCodes.FindRef(CharacterLobbyRace)+TEXT("-")+Paths.FindRef(Choice?LobbyText(Choice,TEXT("class_name")):TEXT("")),Info))Description=LobbyText(*Info,TEXT("text"));
            if(Choice&&LobbyNumber(Choice,TEXT("class_id"))==47)Description+=TEXT("\n\nThis server starts the Druid path as a Naturalist. Advance at a Druid trainer at level 5.");
            At(24,160,210,455,SNew(SScrollBox)+SScrollBox::Slot()[SNew(STextBlock).Text(FText::FromString(Description.ToUpper())).Font(Font(14)).ColorAndOpacity(Cream).AutoWrapText(true)]);
            Label(TEXT("NAME"),790+Shift,80,216,30,22,Gold,true);At(797+Shift,116,199,22,SNew(SEditableTextBox).Font(Font(16)).Text(FText::FromString(CharacterLobbyName)).HintText(FText::FromString(TEXT("NAME"))).OnTextChanged_Lambda([this](const FText& Text){CharacterLobbyName=Text.ToString().Left(23);}));
            const double RaceY=149+(122-3*30)*.5+2;Label(TEXT("RACE"),794+Shift,RaceY,102,27,20,Gold,true);const TArray<FString> Races={TEXT("Celt"),TEXT("Firbolg"),TEXT("Elf"),TEXT("Lurikeen"),TEXT("Sylvan")};for(int32 I=0;I<Races.Num();++I){const FString Race=Races[I];const int32 Cell=I+1;Button(Race,794+Shift+(Cell%2)*106,RaceY+(Cell/2)*30,102,27,[this,Race](){CharacterLobbyRace=Race;CharacterLobbyChoice.Empty();RefreshCharacterLobby();},!Pending,CharacterLobbyRace==Race,true);}
            Label(TEXT("GENDER"),790+Shift,275,216,24,20,Gold,true);for(int32 G=0;G<2;++G)Button(G?TEXT("FEMALE"):TEXT("MALE"),794+Shift+G*106,304,102,27,[this,G](){bCharacterLobbyFemale=G!=0;CharacterLobbyChoice.Empty();RefreshCharacterLobby();},!Pending,bCharacterLobbyFemale==(G!=0),true);
            const TMap<int32,FString> StartingClasses={{40,TEXT("MAGICIAN")},{41,TEXT("MAGICIAN")},{42,TEXT("MAGICIAN")},{43,TEXT("GUARDIAN")},{44,TEXT("GUARDIAN")},{45,TEXT("GUARDIAN")},{46,TEXT("NATURALIST")},{47,TEXT("NATURALIST")},{48,TEXT("NATURALIST")},{49,TEXT("STALKER")},{50,TEXT("STALKER")},{55,TEXT("FORESTER")},{56,TEXT("FORESTER")}};if(Choice&&StartingClasses.Contains(LobbyNumber(Choice,TEXT("class_id"))))Label(TEXT("STARTS AS ")+StartingClasses.FindRef(LobbyNumber(Choice,TEXT("class_id")))+TEXT("\nADVANCED TRAINING AT LEVEL 5"),794+Shift,570,208,44,12,Gold,true);Label(TEXT("CLASS"),790+Shift,346,216,24,20,Gold,true);for(int32 I=0;I<Choices.Num();++I){const FString Id=LobbyText(Choices[I],TEXT("id"));Button(LobbyText(Choices[I],TEXT("class_name")),794+Shift+(I%2)*106,376+(I/2)*30,102,27,[this,Id](){CharacterLobbyChoice=Id;RefreshCharacterLobby();},!Pending,CharacterLobbyChoice==Id,true);}
            Label(TEXT("SELECT YOUR RACE"),160+Shift/2,660,704,36,26,Gold,true);Medallion(TEXT("CANCEL"),2,3,Width*.095,726,[this](){CharacterLobbyScreen=TEXT("select");RefreshCharacterLobby();},!Pending);Medallion(TEXT("REALM"),0,0,Width*.2975,726,[this](){CharacterLobbyScreen=TEXT("realm");RefreshCharacterLobby();},!Pending);Medallion(TEXT("CREATE"),2,2,Width*.905,726,[this](){SendCharacterAction(TEXT("character_create"));},Ready&&!Pending&&Choice.IsValid()&&Characters.Num()<10);
        }
        Label(LobbyText(CharacterLobbyState,TEXT("feedback")),160+Shift/2,630,704,28,14,Gold,true);
    }
    CharacterLobbyPanel=SNew(SBox).WidthOverride(Width).HeightOverride(768)[Canvas];CharacterLobbyOverlay=SNew(SOverlay)+SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor::Black)]+SOverlay::Slot()[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[CharacterLobbyPanel.ToSharedRef()]];Viewport->bDisableWorldRendering=true;Viewport->AddViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef(),100);
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
            ApplyCharacterLobby(State,false);Check(CharacterLobbyOverlay.IsValid()&&CharacterLobbyPanel.IsValid(),TEXT("selection and creation screen opens before world entry"));Check(GetWorld()->GetGameViewport()->bDisableWorldRendering,TEXT("character screen does not render the gameplay map behind its original backdrop"));
            if(auto* PC=GetWorld()->GetFirstPlayerController()){
                Check(PC->bShowMouseCursor&&!bMouseLook,TEXT("character menu shows the cursor before a player pawn exists"));
                PC->bShowMouseCursor=false;ApplyCharacterLobby(State,false);
                Check(PC->bShowMouseCursor,TEXT("unchanged lobby revision restores a lost cursor"));
                Check(GetWorld()->GetGameViewport()->GetMouseCaptureMode()==EMouseCaptureMode::NoCapture,TEXT("character menu does not capture the pointer"));
            }
            const bool BeforeView=bFirstPerson;bLocalAvailable=true;ToggleFirstPerson();Check(bFirstPerson==BeforeView,TEXT("character menu blocks gameplay camera toggles"));bLocalAvailable=false;
            Check(ClassicArt(TEXT("Pregame/character_selection"))!=nullptr&&ClassicArt(TEXT("Pregame/character_creation"))!=nullptr&&ClassicArt(TEXT("Pregame/realm_selection_wide"))!=nullptr,TEXT("original realm selection and creation artwork is installed"));
            CharacterLobbyScreen=TEXT("create");RefreshCharacterLobby();
            TArray<TSharedPtr<SEditableTextBox>> Inputs;TFunction<void(TSharedRef<SWidget>)> Visit;Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SEditableTextBox"))Inputs.Add(StaticCastSharedRef<SEditableTextBox>(W));auto* Children=W->GetChildren();for(int32 I=0;Children&&I<Children->Num();++I)Visit(Children->GetChildAt(I));};
            if(CharacterLobbyPanel)Visit(CharacterLobbyPanel.ToSharedRef());Check(Inputs.Num()==1,TEXT("character name has an editable input"));if(!Inputs.IsEmpty())Inputs[0]->SetText(FText::FromString(TEXT("Previewhero")));
            Check(CharacterLobbyName==TEXT("Previewhero"),TEXT("typed character name survives UI state"));
            Check(!CharacterLobbySelected.IsEmpty()&&!CharacterLobbyChoice.IsEmpty(),TEXT("only supplied characters and class choices are selected"));
            Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Offline character menu acceptance"),false);Session=TEXT("character-menu-acceptance");
            auto ReadCommand=[&](const FString& Action){Outgoing.Add(0);const FString Data=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Value;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Data),Value)&&Value&&LobbyText(Value,TEXT("action"))==Action,TEXT("menu sends ")+Action);return Value;};
            SendCharacterAction(TEXT("character_create"));auto Create=ReadCommand(TEXT("character_create"));if(Create)Check(LobbyText(Create,TEXT("name"))==TEXT("Previewhero")&&LobbyText(Create,TEXT("choice_id"))==CharacterLobbyChoice&&LobbyNumber(Create,TEXT("lobby_revision"))==LobbyNumber(State,TEXT("revision")),TEXT("creation carries exact name choice and server revision"));
            CharacterLobbyScreen=TEXT("select");RefreshCharacterLobby();
            SendCharacterAction(TEXT("character_enter"));auto Enter=ReadCommand(TEXT("character_enter"));if(Enter)Check(LobbyText(Enter,TEXT("name"))==CharacterLobbySelected,TEXT("enter request uses selected server character"));
            ApplyCharacterLobby(State,true);Check(!CharacterLobbyOverlay.IsValid(),TEXT("menu closes when server confirms world entry"));Check(!GetWorld()->GetGameViewport()->bDisableWorldRendering,TEXT("entering the realm restores normal world rendering"));
            ApplyCharacterLobby(State,false);Check(CharacterLobbyOverlay.IsValid(),TEXT("menu can be restored after a session transition"));
            if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Session.Empty();
        }
    }
    if(Phase==1){FString Screen;if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCharacterLobbyScreen="),Screen)&&Screen!=CharacterLobbyScreen&&(Screen==TEXT("create")||Screen==TEXT("realm"))){CharacterLobbyScreen=Screen;RefreshCharacterLobby();}}
    if(!Capture.IsEmpty()){
        if(Phase==1){ApplyCharacterLobby(CharacterLobbyState,false);if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;if(FPlatformTime::Seconds()-Started<8)return true;FScreenshotRequest::RequestScreenshot(Capture,true,false);Phase=2;Started=FPlatformTime::Seconds();return true;}
        if(FPlatformTime::Seconds()-Started<1)return true;
        // Preserve the actual scene target separately from the desktop-scaled UI
        // screenshot. A small Slate window cannot establish full-resolution fidelity.
        if(CharacterLobbyCapture)CharacterLobbyCapture->CaptureScene();
        FlushRenderingCommands();FBufferArchive PreviewBytes;
        Check(CharacterLobbyTarget&&FImageUtils::ExportRenderTarget2DAsPNG(CharacterLobbyTarget,PreviewBytes)&&FFileHelper::SaveArrayToFile(PreviewBytes,*(Capture+TEXT(".scene.png"))),TEXT("full scene target exported"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("live_account"),false);
    if(CharacterLobbyTarget){Report->SetNumberField(TEXT("preview_width"),CharacterLobbyTarget->SizeX);Report->SetNumberField(TEXT("preview_height"),CharacterLobbyTarget->SizeY);}
    if(auto* Backdrop=Cast<AStaticMeshActor>(CharacterLobbyBackdropActor.Get()))if(UStaticMesh* Mesh=Backdrop->GetStaticMeshComponent()->GetStaticMesh())if(auto* Data=Mesh->GetRenderData()){
        TArray<TSharedPtr<FJsonValue>> Lods;for(const auto& Lod:Data->LODResources){auto Entry=MakeShared<FJsonObject>();Entry->SetNumberField(TEXT("triangles"),Lod.GetNumTriangles());Entry->SetNumberField(TEXT("uv_channels"),Lod.VertexBuffers.StaticMeshVertexBuffer.GetNumTexCoords());Lods.Add(MakeShared<FJsonValueObject>(Entry));}Report->SetArrayField(TEXT("backdrop_lods"),Lods);
    }
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));RemoveCharacterLobby();Phase=99;
    UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
