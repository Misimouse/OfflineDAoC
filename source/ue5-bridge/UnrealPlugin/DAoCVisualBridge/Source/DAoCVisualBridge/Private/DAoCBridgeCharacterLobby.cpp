#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeLobbyMotion.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
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
#include "Components/SkeletalMeshComponent.h"
#include "StaticMeshResources.h"
#include "SkeletalRenderPublic.h"

namespace {
FString LobbyText(TSharedPtr<FJsonObject> O,const TCHAR* K){FString V;if(O)O->TryGetStringField(K,V);return V;}
bool LobbyFlag(TSharedPtr<FJsonObject> O,const TCHAR* K){bool V=false;if(O)O->TryGetBoolField(K,V);return V;}
int32 LobbyNumber(TSharedPtr<FJsonObject> O,const TCHAR* K){double V=0;if(O)O->TryGetNumberField(K,V);return int32(V);}
TArray<TSharedPtr<FJsonValue>> LobbyArray(TSharedPtr<FJsonObject> O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
TSharedPtr<FJsonObject> LobbyLore(){static TSharedPtr<FJsonObject> Lore;if(!Lore){FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/Pregame/lore.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Lore);}return Lore;}
TSharedPtr<SWidget> LobbyFindButton(TSharedRef<SWidget> Root,const FString& Caption){
    if(Root->GetTypeAsString()==TEXT("SButton")){auto* Children=Root->GetChildren();if(Children->Num()==1){auto Child=Children->GetChildAt(0);if(Child->GetTypeAsString()==TEXT("STextBlock")&&StaticCastSharedRef<STextBlock>(Child)->GetText().ToString()==Caption)return Root;}}
    auto* Children=Root->GetChildren();for(int32 I=0;I<Children->Num();++I)if(auto Found=LobbyFindButton(Children->GetChildAt(I),Caption))return Found;return nullptr;
}

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
    // A saved-appearance message remains in snapshots until the next action.
    // Consume it only on a new server revision, never while opening another draft.
    if(LobbyNumber(State,TEXT("revision"))!=CharacterLobbyRevision&&CharacterLobbyScreen==TEXT("customize")&&bCharacterLobbyEditing&&LobbyText(State,TEXT("feedback"))==TEXT("Character appearance saved."))CharacterLobbyScreen=TEXT("select");
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
    if(Action==TEXT("character_create")){Values->SetStringField(TEXT("name"),CharacterLobbyName);Values->SetStringField(TEXT("choice_id"),CharacterLobbyChoice);Values->SetObjectField(TEXT("look"),CharacterLobbyLook?CharacterLobbyLook:MakeShared<FJsonObject>());}
    if(Action==TEXT("character_customize")){Values->SetStringField(TEXT("name"),CharacterLobbySelected);Values->SetObjectField(TEXT("look"),CharacterLobbyLook?CharacterLobbyLook:MakeShared<FJsonObject>());}
    Send(Action,Values);
}

void UDAoCBridgeSubsystem::RefreshCharacterLobby(){
    if(!GetWorld()||!GetWorld()->GetGameViewport()||!CharacterLobbyState)return;auto* Viewport=GetWorld()->GetGameViewport();
    if(CharacterLobbyOverlay)Viewport->RemoveViewportWidgetContent(CharacterLobbyOverlay.ToSharedRef());
    FVector2D Pixels;Viewport->GetViewportSize(Pixels);const double Width=FMath::Max(1024.,768.*Pixels.X/FMath::Max(1.,Pixels.Y)),Shift=Width-1024;
    CharacterLobbyButtonStyles.Empty();auto Canvas=SNew(SCanvas).Visibility(EVisibility::SelfHitTestInvisible);const FLinearColor Gold(1,.84,.45),Cream(.93,.89,.78),Dim(.55,.56,.51);
    auto Font=[](int32 Size){return FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"),FMath::Max(7,FMath::RoundToInt(Size*.75)));};
    auto At=[Canvas](double X,double Y,double W,double H,TSharedRef<SWidget> Widget){Canvas->AddSlot().Position(FVector2D(X,Y)).Size(FVector2D(W,H))[Widget];};
    auto Label=[&](const FString& Text,double X,double Y,double W,double H,int32 Size,FLinearColor Color,bool Center=false){At(X,Y,W,H,SNew(STextBlock).Text(FText::FromString(Text.ToUpper())).Font(Font(Size)).ColorAndOpacity(Color).Justification(Center?ETextJustify::Center:ETextJustify::Left).AutoWrapText(true).ShadowOffset(FVector2D(1,1)));};
    auto Button=[&](const FString& Text,double X,double Y,double W,double H,TFunction<void()> Action,bool Enabled=true,bool Selected=false,bool Stone=false){int32 ButtonSize=14;while(ButtonSize>8&&FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text.ToUpper(),Font(ButtonSize)).X>W-8)--ButtonSize;TSharedPtr<FButtonStyle> Style=MakeShared<FButtonStyle>(FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"));CharacterLobbyButtonStyles.Add(Style);if(Stone){for(int32 I=0;I<4;++I){auto Brush=*ClassicArt(TEXT("Pregame/misc_pieces_new"),FVector2D(0,(105.+I*22)/256.),FVector2D(102./256.,(127.+I*22)/256.));if(I==0)Style->SetNormal(Brush);if(I==1)Style->SetHovered(Brush);if(I==2)Style->SetPressed(Brush);if(I==3)Style->SetDisabled(Brush);}}At(X,Y,W,H,SNew(SButton).IsEnabled(Enabled).IsFocusable(false).ButtonStyle(Style.Get()).ContentPadding(0).OnClicked_Lambda([Action,Style](){Action();return FReply::Handled();})[SNew(STextBlock).Text(FText::FromString(Text.ToUpper())).Font(Font(ButtonSize)).ColorAndOpacity(!Enabled?FLinearColor(.4,.38,.35):Selected?FLinearColor(1,.8,.2):Cream).Justification(ETextJustify::Center).AutoWrapText(false)]);};
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
        auto Preview=Selected?Selected:MakeShared<FJsonObject>();const bool Customizing=CharacterLobbyScreen==TEXT("customize");
        if(CharacterLobbyScreen==TEXT("create")||(Customizing&&!bCharacterLobbyEditing)){Preview=MakeShared<FJsonObject>();const TMap<FString,FString> Prefixes={{TEXT("Celt"),TEXT("cel")},{TEXT("Firbolg"),TEXT("fir")},{TEXT("Elf"),TEXT("elf")},{TEXT("Lurikeen"),TEXT("lur")},{TEXT("Sylvan"),TEXT("syl")}};Preview->SetStringField(TEXT("prefix"),Prefixes.FindRef(CharacterLobbyRace)+(bCharacterLobbyFemale?TEXT("_f"):TEXT("_m")));}
        if(CharacterLobbyScreen==TEXT("create")&&CharacterLobbyLook)Preview->SetObjectField(TEXT("look"),CharacterLobbyLook);
        if(Customizing){FString Copy;FJsonSerializer::Serialize(Preview.ToSharedRef(),TJsonWriterFactory<>::Create(&Copy));FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Copy),Preview);Preview->SetObjectField(TEXT("look"),CharacterLobbyLook?CharacterLobbyLook:MakeShared<FJsonObject>());const TSharedPtr<FJsonObject>* Overview=nullptr;if(Preview->TryGetObjectField(TEXT("overview"),Overview)){const TSharedPtr<FJsonObject>* Models=nullptr;if((*Overview)->TryGetObjectField(TEXT("models"),Models))(*Models)->SetNumberField(TEXT("helmet"),0);}}
        FString AppearancePath=DAoCAppearancePath(),AppearanceText;TSharedPtr<FJsonObject> Appearance;const bool AppearanceAvailable=!AppearancePath.IsEmpty()&&FFileHelper::LoadFileToString(AppearanceText,*AppearancePath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(AppearanceText),Appearance)&&Appearance.IsValid()&&AppearanceText.Contains(TEXT("swatches"));
        RefreshCharacterLobbyPreview(Preview);if(CharacterLobbyPreviewBrush)At(0,0,Width,768,SAssignNew(CharacterLobbySceneInput,SBorder).Visibility(EVisibility::Visible).Padding(0).BorderImage(FCoreStyle::Get().GetBrush(TEXT("NoBrush")))[SNew(SImage).Image(CharacterLobbyPreviewBrush.Get()).Visibility(EVisibility::HitTestInvisible)]);
        const bool Creating=CharacterLobbyScreen==TEXT("create");const FString Frame=Customizing?TEXT("character_customize"):Creating?TEXT("character_creation"):TEXT("character_selection");const double Left=Creating?240:12,Right=Creating?238:268;
        Art(Frame,0,0,Left,768,FVector2D::ZeroVector,FVector2D(Left/1024,1));Art(Frame,Left,0,Width-Left-Right,768,FVector2D(Left/1024,0),FVector2D((1024-Right)/1024,1));Art(Frame,Width-Right,0,Right,768,FVector2D((1024-Right)/1024,0),FVector2D(1,1));
        if(Customizing){
            At(0,0,Width,768,BuildCharacterCustomization(Width));Label(TEXT("CUSTOMIZE YOUR CHARACTER"),160+Shift/2,660,704,36,26,Gold,true);
            Medallion(TEXT("CANCEL"),2,3,Width*.095,726,[this](){CharacterLobbyScreen=bCharacterLobbyEditing?TEXT("select"):TEXT("create");RefreshCharacterLobby();},!Pending);
            Medallion(TEXT("REALM"),0,0,Width*.2975,726,[this](){CharacterLobbyScreen=TEXT("realm");RefreshCharacterLobby();},!Pending);
            if(!bCharacterLobbyEditing)Medallion(TEXT("RACE / CLASS"),2,2,Width*.7025,726,[this](){CharacterLobbyScreen=TEXT("create");RefreshCharacterLobby();},!Pending);
            Medallion(bCharacterLobbyEditing?TEXT("SAVE"):TEXT("CONTINUE"),0,2,Width*.905,726,[this](){SendCharacterAction(bCharacterLobbyEditing?TEXT("character_customize"):TEXT("character_create"));},Ready&&!Pending);
        }else if(!Creating){
            Label(TEXT("SELECT CHARACTER"),760+Shift,64,248,32,22,Gold,true);
            for(int32 I=0;I<10;++I){TSharedPtr<FJsonObject> C;for(auto V:Characters)if(LobbyNumber(V->AsObject(),TEXT("slot"))==I)C=V->AsObject();const double Y=109+I*45;Button(TEXT(""),764+Shift,Y+1,240,43,[this,I](){CharacterLobbySlot=I;RefreshCharacterLobby();},!Pending);const double Cell=I==CharacterLobbySlot?185:215;Art(TEXT("misc_pieces_new"),770+Shift,Y+11,20,20,FVector2D(Cell/256.,7./256),FVector2D((Cell+24)/256.,31./256));
                if(C){Label(LobbyText(C,TEXT("name"))+(LobbyText(C,TEXT("class_name")).IsEmpty()?TEXT(""):TEXT(" THE ")+LobbyText(C,TEXT("class_name"))),796+Shift,Y+3,206,22,14,I==CharacterLobbySlot?Gold:Cream);Label(FString::Printf(TEXT("LEVEL %d"),LobbyNumber(C,TEXT("level")))+TEXT(" IN ")+LobbyText(C,TEXT("location")),796+Shift,Y+23,208,20,11,Dim);}else Label(TEXT("EMPTY"),796+Shift,Y+11,208,22,16,Dim);
            }
            Medallion(Selected?TEXT("PLAY"):TEXT("CREATE"),0,2,884+Shift,600,[this,Selected](){if(Selected)SendCharacterAction(TEXT("character_enter"));else{CharacterLobbyLook=MakeShared<FJsonObject>();CharacterLobbyScreen=TEXT("create");RefreshCharacterLobby();}},Ready&&!Pending,66,24);
            Label(TEXT("SELECT YOUR CHARACTER"),160+Shift/2,660,704,36,26,Gold,true);Medallion(TEXT("QUIT"),2,3,Width*.095,726,Quit);Medallion(TEXT("REALM"),0,0,Width*.2975,726,[this](){CharacterLobbyScreen=TEXT("realm");RefreshCharacterLobby();},!Pending);Medallion(TEXT("OPTIONS"),2,0,Width*.5,726,[](){},false);Medallion(TEXT("CUSTOMIZE"),2,2,Width*.7025,726,[this,Selected](){CharacterLobbyLook=MakeShared<FJsonObject>();const TSharedPtr<FJsonObject>* Look=nullptr;if(Selected&&Selected->TryGetObjectField(TEXT("look"),Look)){FString Copy;FJsonSerializer::Serialize((*Look).ToSharedRef(),TJsonWriterFactory<>::Create(&Copy));FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Copy),CharacterLobbyLook);}bCharacterLobbyEditing=true;CharacterLobbyScreen=TEXT("customize");RefreshCharacterLobby();},AppearanceAvailable&&Selected.IsValid()&&!Pending);Medallion(TEXT("DELETE"),0,1,Width*.905,726,[](){},false);
        }else{
            Label(TEXT("DESCRIPTIONS"),16,62,220,30,22,Gold,true);Label(CharacterLobbyRace,24,96,210,26,20,Gold);Label(Choice?LobbyText(Choice,TEXT("class_name")):TEXT(""),24,124,210,26,16,Gold);
            auto Lore=LobbyLore();
            const TMap<FString,FString> RaceCodes={{TEXT("Celt"),TEXT("CELT")},{TEXT("Firbolg"),TEXT("FIRB")},{TEXT("Elf"),TEXT("ELF")},{TEXT("Lurikeen"),TEXT("LURI")},{TEXT("Sylvan"),TEXT("SYLV")}};
            const TMap<FString,FString> Paths={{TEXT("Blademaster"),TEXT("ARMS")},{TEXT("Champion"),TEXT("ARMS")},{TEXT("Hero"),TEXT("ARMS")},{TEXT("Bard"),TEXT("NATU")},{TEXT("Druid"),TEXT("NATU")},{TEXT("Warden"),TEXT("NATU")},{TEXT("Eldritch"),TEXT("MAGI")},{TEXT("Enchanter"),TEXT("MAGI")},{TEXT("Mentalist"),TEXT("MAGI")},{TEXT("Nightshade"),TEXT("STEA")},{TEXT("Ranger"),TEXT("STEA")},{TEXT("Animist"),TEXT("GROV")},{TEXT("Valewalker"),TEXT("GROV")}};
            FString Description;const TSharedPtr<FJsonObject>* Classes=nullptr;const TSharedPtr<FJsonObject>* Info=nullptr;if(Lore&&Lore->TryGetObjectField(TEXT("classes"),Classes)&&(*Classes)->TryGetObjectField(RaceCodes.FindRef(CharacterLobbyRace)+TEXT("-")+Paths.FindRef(Choice?LobbyText(Choice,TEXT("class_name")):TEXT("")),Info))Description=LobbyText(*Info,TEXT("text"));
            if(Choice&&LobbyNumber(Choice,TEXT("class_id"))==47)Description+=TEXT("\n\nThis server starts the Druid path as a Naturalist. Advance at a Druid trainer at level 5.");
            At(24,160,210,455,SNew(SScrollBox)+SScrollBox::Slot()[SNew(STextBlock).Text(FText::FromString(Description.ToUpper())).Font(Font(14)).ColorAndOpacity(Cream).AutoWrapText(true)]);
            Label(TEXT("NAME"),790+Shift,80,216,30,22,Gold,true);At(797+Shift,116,199,22,SNew(SEditableTextBox).Font(Font(16)).Text(FText::FromString(CharacterLobbyName)).HintText(FText::FromString(TEXT("NAME"))).OnTextChanged_Lambda([this](const FText& Text){CharacterLobbyName=Text.ToString().Left(23);}));
            const double RaceY=149+(122-3*30)*.5+2;Label(TEXT("RACE"),794+Shift,RaceY,102,27,20,Gold,true);const TArray<FString> Races={TEXT("Celt"),TEXT("Firbolg"),TEXT("Elf"),TEXT("Lurikeen"),TEXT("Sylvan")};for(int32 I=0;I<Races.Num();++I){const FString Race=Races[I];const int32 Cell=I+1;Button(Race,794+Shift+(Cell%2)*106,RaceY+(Cell/2)*30,102,27,[this,Race](){CharacterLobbyRace=Race;CharacterLobbyLook=MakeShared<FJsonObject>();CharacterLobbyChoice.Empty();RefreshCharacterLobby();},!Pending,CharacterLobbyRace==Race,true);}
            Label(TEXT("GENDER"),790+Shift,275,216,24,20,Gold,true);for(int32 G=0;G<2;++G)Button(G?TEXT("FEMALE"):TEXT("MALE"),794+Shift+G*106,304,102,27,[this,G](){bCharacterLobbyFemale=G!=0;CharacterLobbyLook=MakeShared<FJsonObject>();CharacterLobbyChoice.Empty();RefreshCharacterLobby();},!Pending,bCharacterLobbyFemale==(G!=0),true);
            const TMap<int32,FString> StartingClasses={{40,TEXT("MAGICIAN")},{41,TEXT("MAGICIAN")},{42,TEXT("MAGICIAN")},{43,TEXT("GUARDIAN")},{44,TEXT("GUARDIAN")},{45,TEXT("GUARDIAN")},{46,TEXT("NATURALIST")},{47,TEXT("NATURALIST")},{48,TEXT("NATURALIST")},{49,TEXT("STALKER")},{50,TEXT("STALKER")},{55,TEXT("FORESTER")},{56,TEXT("FORESTER")}};if(Choice&&StartingClasses.Contains(LobbyNumber(Choice,TEXT("class_id"))))Label(TEXT("STARTS AS ")+StartingClasses.FindRef(LobbyNumber(Choice,TEXT("class_id")))+TEXT("\nADVANCED TRAINING AT LEVEL 5"),794+Shift,570,208,44,12,Gold,true);Label(TEXT("CLASS"),790+Shift,346,216,24,20,Gold,true);TMap<int32,FString> ClassNames;for(auto V:LobbyArray(CharacterLobbyState,TEXT("choices"))){auto C=V->AsObject();ClassNames.Add(LobbyNumber(C,TEXT("class_id")),LobbyText(C,TEXT("class_name")));}for(auto C:Choices)ClassNames.Add(LobbyNumber(C,TEXT("class_id")),LobbyText(C,TEXT("class_name")));TArray<int32> ClassIds;ClassNames.GetKeys(ClassIds);ClassIds.Sort();
            for(int32 I=0;I<ClassIds.Num();++I){const int32 ClassId=ClassIds[I];FString Id;for(auto C:Choices)if(LobbyNumber(C,TEXT("class_id"))==ClassId)Id=LobbyText(C,TEXT("id"));Button(ClassNames[ClassId],794+Shift+(I%2)*106,376+(I/2)*27,102,27,[this,Id](){if(!Id.IsEmpty()){CharacterLobbyChoice=Id;RefreshCharacterLobby();}},!Pending&&!Id.IsEmpty(),!Id.IsEmpty()&&CharacterLobbyChoice==Id,true);}
            Label(TEXT("SELECT YOUR RACE"),160+Shift/2,660,704,36,26,Gold,true);Medallion(TEXT("CANCEL"),2,3,Width*.095,726,[this](){CharacterLobbyScreen=TEXT("select");RefreshCharacterLobby();},!Pending);Medallion(TEXT("REALM"),0,0,Width*.2975,726,[this](){CharacterLobbyScreen=TEXT("realm");RefreshCharacterLobby();},!Pending);Medallion(AppearanceAvailable?TEXT("CONTINUE"):TEXT("CREATE"),2,2,Width*.905,726,[this,AppearanceAvailable](){if(AppearanceAvailable){if(!CharacterLobbyLook)CharacterLobbyLook=MakeShared<FJsonObject>();bCharacterLobbyEditing=false;CharacterLobbyScreen=TEXT("customize");RefreshCharacterLobby();}else SendCharacterAction(TEXT("character_create"));},Ready&&!Pending&&Choice.IsValid()&&Characters.Num()<10);
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
    static int32 Phase=0,Checks=0;static double Started=0;static TArray<TSharedPtr<FJsonValue>> Failures;static bool MotionShot=false;
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
            auto SavedLook=CharacterLobbyLook;CharacterLobbyLook=MakeShared<FJsonObject>();CharacterLobbyLook->SetNumberField(TEXT("face"),1);CharacterLobbyLook->SetNumberField(TEXT("skin"),2);
            SendCharacterAction(TEXT("character_create"));auto Create=ReadCommand(TEXT("character_create"));if(Create){Check(LobbyText(Create,TEXT("name"))==TEXT("Previewhero")&&LobbyText(Create,TEXT("choice_id"))==CharacterLobbyChoice&&LobbyNumber(Create,TEXT("lobby_revision"))==LobbyNumber(State,TEXT("revision")),TEXT("creation carries exact name choice and server revision"));const TSharedPtr<FJsonObject>* Look=nullptr;Check(Create->TryGetObjectField(TEXT("look"),Look)&&LobbyNumber(*Look,TEXT("face"))==1&&LobbyNumber(*Look,TEXT("skin"))==2,TEXT("creation carries chosen appearance to the original creation API"));}
            SendCharacterAction(TEXT("character_customize"));auto Customize=ReadCommand(TEXT("character_customize"));if(Customize){const TSharedPtr<FJsonObject>* Look=nullptr;Check(LobbyText(Customize,TEXT("name"))==CharacterLobbySelected&&Customize->TryGetObjectField(TEXT("look"),Look)&&LobbyNumber(*Look,TEXT("face"))==1,TEXT("customization carries exact selected character and appearance"));}CharacterLobbyLook=SavedLook;
            const FString SavedRace=CharacterLobbyRace;CharacterLobbyRace=TEXT("Lurikeen");CharacterLobbyChoice.Empty();RefreshCharacterLobby();
            auto Warden=LobbyFindButton(CharacterLobbyPanel.ToSharedRef(),TEXT("WARDEN"));auto Eldritch=LobbyFindButton(CharacterLobbyPanel.ToSharedRef(),TEXT("ELDRITCH"));
            Check(Warden.IsValid()&&!Warden->IsEnabled(),TEXT("race-ineligible Warden remains visible and disabled"));Check(Eldritch.IsValid()&&Eldritch->IsEnabled(),TEXT("eligible Eldritch remains selectable for Lurikeen"));CharacterLobbyRace=SavedRace;CharacterLobbyChoice.Empty();
            auto SavedMessage=MakeShared<FJsonObject>(*State);SavedMessage->SetNumberField(TEXT("revision"),LobbyNumber(State,TEXT("revision"))+1);SavedMessage->SetStringField(TEXT("feedback"),TEXT("Character appearance saved."));bCharacterLobbyEditing=true;CharacterLobbyScreen=TEXT("customize");ApplyCharacterLobby(SavedMessage,false);Check(CharacterLobbyScreen==TEXT("select"),TEXT("fresh customization save returns to selection"));
            CharacterLobbyScreen=TEXT("create");RefreshCharacterLobby();ApplyCharacterLobby(SavedMessage,false);Check(CharacterLobbyScreen==TEXT("create"),TEXT("stale saved feedback cannot close a new creation draft"));
            CharacterLobbyScreen=TEXT("customize");bCharacterLobbyEditing=false;RefreshCharacterLobby();ApplyCharacterLobby(SavedMessage,false);Check(CharacterLobbyScreen==TEXT("customize"),TEXT("stale saved feedback cannot close new-character customization"));ApplyCharacterLobby(State,false);
            CharacterLobbyScreen=TEXT("select");RefreshCharacterLobby();
            SendCharacterAction(TEXT("character_enter"));auto Enter=ReadCommand(TEXT("character_enter"));if(Enter)Check(LobbyText(Enter,TEXT("name"))==CharacterLobbySelected,TEXT("enter request uses selected server character"));
            ApplyCharacterLobby(State,true);Check(!CharacterLobbyOverlay.IsValid(),TEXT("menu closes when server confirms world entry"));Check(!GetWorld()->GetGameViewport()->bDisableWorldRendering,TEXT("entering the realm restores normal world rendering"));
            ApplyCharacterLobby(State,false);Check(CharacterLobbyOverlay.IsValid(),TEXT("menu can be restored after a session transition"));
            if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Session.Empty();
        }
    }
    if(Phase==1){FString Screen;if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCharacterLobbyScreen="),Screen)&&Screen!=CharacterLobbyScreen&&(Screen==TEXT("create")||Screen==TEXT("realm")||Screen==TEXT("customize"))){CharacterLobbyScreen=Screen;RefreshCharacterLobby();}}
    if(!Capture.IsEmpty()){
        // Exercise the actual Slate hit paths, rather than invoking callbacks.
        // These events stay inside this disposable native test; no OS cursor move.
        if(Phase==1&&CharacterLobbyScreen==TEXT("customize")){
            static int32 Step=0;static double LastStep=0;static TWeakObjectPtr<AActor> Scene;static TSharedPtr<FDAoCLobbyMotion> Animation;static TArray<FVector3f> Neutral;
            if(FPlatformTime::Seconds()-Started<3||FPlatformTime::Seconds()-LastStep<.3)return true;
            auto Click=[this](FVector2D Point){auto& Slate=FSlateApplication::Get();const FVector2D Absolute=CharacterLobbyPanel->GetCachedGeometry().LocalToAbsolute(Point);TSet<FKey> Pressed;Pressed.Add(EKeys::LeftMouseButton);Slate.ProcessMouseMoveEvent(FPointerEvent(0,Absolute,Absolute,{},FKey(),0,FModifierKeysState()));Slate.ProcessMouseButtonDownEvent(nullptr,FPointerEvent(0,Absolute,Absolute,Pressed,EKeys::LeftMouseButton,0,FModifierKeysState()));Slate.ProcessMouseButtonUpEvent(FPointerEvent(0,Absolute,Absolute,{},EKeys::LeftMouseButton,0,FModifierKeysState()));};
            auto HeadVertices=[this](){TArray<FVector3f> Positions;TArray<USkeletalMeshComponent*> Parts;CharacterLobbyPreviewActor->GetComponents(Parts);for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHead"))){TArray<FFinalSkinVertex> Vertices;Part->GetCPUSkinnedVertices(Vertices,0);for(const auto& V:Vertices)Positions.Add(V.Position);}return Positions;};
            const double Width=CharacterLobbyPanel->GetCachedGeometry().GetLocalSize().X,Shift=Width-1024;
            if(Step==0){Scene=CharacterLobbyBackdropActor;Animation=CharacterLobbyMotion;Click(FVector2D(500,300));}
            if(Step==1){Check(LobbySceneHit(CharacterLobbyPanel->GetCachedGeometry().LocalToAbsolute(FVector2D(500,300))),TEXT("customization leaves the 3D scene available to mouse orbit"));Click(FVector2D(978+Shift,112));}
            if(Step==2){Check(LobbyNumber(CharacterLobbyLook,TEXT("face"))==1,TEXT("clicking original face arrow updates appearance"));Check(Scene==CharacterLobbyBackdropActor&&Animation==CharacterLobbyMotion,TEXT("changing a feature preserves the live backdrop and animation timeline"));Neutral=HeadVertices();Click(FVector2D(978+Shift,139));}
            if(Step==3){const auto A=LobbyArray(CharacterLobbyLook,TEXT("sliders"));Check(A.Num()==4&&A[0]->AsNumber()>4,TEXT("drag control receives pointer input and applies a face morph"));const auto Changed=HeadVertices();double Distance=0;if(Changed.Num()==Neutral.Num())for(int32 I=0;I<Changed.Num();++I)Distance=FMath::Max(Distance,double((Changed[I]-Neutral[I]).Size()));Check(!Neutral.IsEmpty()&&Changed.Num()==Neutral.Num()&&Distance>.001,TEXT("face slider changes skinned vertex positions, not only stored values"));Click(FVector2D(811+Shift,271));}
            if(Step==4){Check(LobbyNumber(CharacterLobbyLook,TEXT("eyes"))==1,TEXT("clicking original colour swatch changes eye colour"));Click(FVector2D(946+Shift,620));}
            if(Step==5){Check(CharacterLobbyLook&&CharacterLobbyLook->Values.IsEmpty(),TEXT("original DEFAULT button restores neutral appearance"));TArray<USkeletalMeshComponent*> Parts;CharacterLobbyPreviewActor->GetComponents(Parts);int32 Heads=0;for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHead")))++Heads;Check(Heads==1,TEXT("repeated appearance edits replace components without duplicates"));}
            if(Step<6){++Step;LastStep=FPlatformTime::Seconds();return true;}
        }
        static bool CameraChecked=false;
        if(Phase==1&&!CameraChecked&&CharacterLobbyCapture&&CharacterLobbyPreviewActor&&CharacterLobbyPanel->GetCachedGeometry().GetLocalSize().X>100&&FPlatformTime::Seconds()-Started>.5){
            CameraChecked=true;const FVector BodyPosition=CharacterLobbyPreviewActor->GetActorLocation(),Eye=CharacterLobbyCapture->GetComponentLocation();
            FString AppearancePath;
            if(CharacterLobbyScreen==TEXT("create")&&!DAoCAppearancePath().IsEmpty()){
                TArray<USkeletalMeshComponent*> Parts;CharacterLobbyPreviewActor->GetComponents(Parts);int32 Heads=0;
                for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHead"))){++Heads;Check(Part->GetSkeletalMeshAsset()!=nullptr&&Part->GetMaterial(0)!=nullptr,TEXT("original appearance head has its mesh and texture material"));}
                Check(Heads==1,TEXT("original appearance replaces the head exactly once"));
            }
            const float SavedFigure=LobbyFigureYaw,SavedYaw=LobbyOrbitYaw,SavedPitch=LobbyOrbitPitch,SavedZoom=LobbyZoom;
            bLobbyRightHeld=true;LobbyLastPointer=FVector2D(100,100);HandleLobbyPointer(FKey(),false,FVector2D(250,120),true);bLobbyRightHeld=false;
            Check(CharacterLobbyCapture->GetComponentLocation().Equals(Eye,.1)!=(CharacterLobbyScreen==TEXT("customize")),TEXT("camera orbit is available only during appearance customization"));Check(CharacterLobbyPreviewActor->GetActorLocation().Equals(BodyPosition,.01),TEXT("orbiting does not move the figure"));
            const FRotator Before=CharacterLobbyPreviewActor->GetActorRotation();bLobbyLeftHeld=true;LobbyLastPointer=FVector2D(100,100);HandleLobbyPointer(FKey(),false,FVector2D(150,100),true);bLobbyLeftHeld=false;
            Check(CharacterLobbyPreviewActor->GetActorRotation().Equals(Before,.1)!=(CharacterLobbyScreen==TEXT("customize")),TEXT("figure rotation is available only during appearance customization"));
            LobbyOrbitYaw=SavedYaw;LobbyOrbitPitch=SavedPitch;LobbyZoom=.6f;UpdateLobbyCamera();Check(!CharacterLobbyCapture->GetComponentLocation().Equals(Eye,.1),TEXT("lobby zoom changes the camera position"));
            LobbyOrbitYaw=SavedYaw;LobbyOrbitPitch=SavedPitch;LobbyZoom=SavedZoom;UpdateLobbyCamera();
            const FVector2D ScenePoint=CharacterLobbyPanel->GetCachedGeometry().LocalToAbsolute(FVector2D(500,300));
            const bool WheelAccepted=HandleLobbyWheel(-1,ScenePoint);
            Check(WheelAccepted==(CharacterLobbyScreen!=TEXT("create")),TEXT("real wheel input zooms selection/customization and leaves race/class fixed"));
            Check(CharacterLobbyPreviewActor->GetActorLocation().Equals(BodyPosition,.01),TEXT("wheel never moves the character"));
            LobbyFigureYaw=SavedFigure;LobbyOrbitYaw=SavedYaw;LobbyOrbitPitch=SavedPitch;LobbyZoom=SavedZoom;CharacterLobbyPreviewActor->SetActorRotation(Before);UpdateLobbyCamera();
            Check(CharacterLobbyCapture->GetComponentLocation().Equals(Eye,.01),TEXT("lobby camera returns to its original position"));
        }
        float TestZoom=0;if(Phase==1&&FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestZoom="),TestZoom)){LobbyZoom=FMath::Clamp(TestZoom,.25f,5.f);UpdateLobbyCamera();}
        FString TestSliders;if(Phase==1&&CharacterLobbyLook&&FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestSliders="),TestSliders,false)){
            TArray<FString> Tokens;TestSliders.ParseIntoArray(Tokens,TEXT(","));TArray<TSharedPtr<FJsonValue>> V;for(const FString& Token:Tokens)V.Add(MakeShared<FJsonValueNumber>(FMath::Clamp(FCString::Atof(*Token),0.f,8.f)));CharacterLobbyLook->SetArrayField(TEXT("sliders"),V);UpdateCharacterLobbyAppearance(CharacterLobbyLook);
        }
        int32 TestSkin=-1;if(Phase==1&&FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestSkin="),TestSkin)&&CharacterLobbyLook&&CharacterLobbyScreen==TEXT("customize")){CharacterLobbyLook->SetNumberField(TEXT("skin"),FMath::Clamp(TestSkin,0,7));UpdateCharacterLobbyAppearance(CharacterLobbyLook);}
        if(Phase==1&&CharacterLobbyMotion){
            if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;
            static double MotionReadyAt=0;const double Now=FPlatformTime::Seconds();if(MotionReadyAt==0)MotionReadyAt=Now;
            ApplyCharacterLobby(CharacterLobbyState,false);
            if(!MotionShot&&Now-MotionReadyAt>2){FScreenshotRequest::RequestScreenshot(Capture+TEXT(".motion-mid.png"),true,false);MotionShot=true;}
            if(Now-MotionReadyAt<6)return true;
        }
        if(Phase==1){ApplyCharacterLobby(CharacterLobbyState,false);if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;if(FPlatformTime::Seconds()-Started<8)return true;FScreenshotRequest::RequestScreenshot(Capture,true,false);Phase=2;Started=FPlatformTime::Seconds();return true;}
        if(FPlatformTime::Seconds()-Started<1)return true;
        if(Phase==2&&CharacterLobbyMotion){int32 Orbit=90;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestOrbit="),Orbit);LobbyOrbitYaw=Orbit;int32 Pitch=0;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyTestPitch="),Pitch);LobbyOrbitPitch=FMath::Clamp(Pitch,-65,65);UpdateLobbyCamera();FScreenshotRequest::RequestScreenshot(Capture+TEXT(".orbit.png"),true,false);Phase=3;Started=FPlatformTime::Seconds();return true;}
        if(Phase==3){LobbyOrbitYaw=LobbyOrbitPitch=0;UpdateLobbyCamera();Phase=4;Started=FPlatformTime::Seconds();return true;}
        // Preserve the actual scene target separately from the desktop-scaled UI
        // screenshot. A small Slate window cannot establish full-resolution fidelity.
        if(CharacterLobbyCapture)CharacterLobbyCapture->CaptureScene();
        FlushRenderingCommands();FBufferArchive PreviewBytes;
        Check(CharacterLobbyTarget&&FImageUtils::ExportRenderTarget2DAsPNG(CharacterLobbyTarget,PreviewBytes)&&FFileHelper::SaveArrayToFile(PreviewBytes,*(Capture+TEXT(".scene.png"))),TEXT("full scene target exported"));
    }
    TArray<TSharedPtr<FJsonValue>> GalleryImages;FString Gallery;
    if(CharacterLobbyScreen==TEXT("customize")&&CharacterLobbyLook&&FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyAppearanceGallery="),Gallery)){
        FString Saved;FJsonSerializer::Serialize(CharacterLobbyLook.ToSharedRef(),TJsonWriterFactory<>::Create(&Saved));
        auto SaveScene=[&](const FString& Tag){
            UpdateCharacterLobbyAppearance(CharacterLobbyLook);
            TArray<USkeletalMeshComponent*> Parts;CharacterLobbyPreviewActor->GetComponents(Parts);
            for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHead"))||Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHair")))for(const auto& Curve:Part->GetMorphTargetCurves())if(Curve.Value>.001f){
                const auto* Target=Part->GetSkeletalMeshAsset()->FindMorphTarget(Curve.Key);const int32* Index=Part->ActiveMorphTargets.Find(Target);
                Check(Index&&Part->MorphTargetWeights.IsValidIndex(*Index)&&FMath::IsNearlyEqual(Part->MorphTargetWeights[*Index],Curve.Value),TEXT("render buffer receives facial morph ")+Curve.Key.ToString());
            }
            GetWorld()->SendAllEndOfFrameUpdates();CharacterLobbyCapture->CaptureScene();FlushRenderingCommands();FBufferArchive Bytes;
            // These are display previews, unlike the separately retained linear
            // scene target. Encode sRGB once, as Slate does on the real menu.
            TArray<FLinearColor> LinearPixels;TArray<FColor> Pixels;
            const bool Read=CharacterLobbyTarget->GameThread_GetRenderTargetResource()->ReadLinearColorPixels(LinearPixels);
            Pixels.Reserve(LinearPixels.Num());for(const auto& Pixel:LinearPixels)Pixels.Add(Pixel.ToFColor(true));
            if(Read)FImageUtils::CompressImageArray(CharacterLobbyTarget->SizeX,CharacterLobbyTarget->SizeY,Pixels,Bytes);
            const FString File=Gallery+TEXT("_")+Tag+TEXT(".png");const bool Ok=Read&&!Bytes.IsEmpty()&&FFileHelper::SaveArrayToFile(Bytes,*File);Check(Ok,TEXT("appearance gallery captures ")+Tag);if(Ok)GalleryImages.Add(MakeShared<FJsonValueString>(File));
        };
        for(int32 Skin=0;Skin<8;++Skin){CharacterLobbyLook->SetNumberField(TEXT("skin"),Skin);SaveScene(FString::Printf(TEXT("skin_%d"),Skin));}
        CharacterLobbyLook->SetNumberField(TEXT("skin"),1);
        for(int32 Lips:{0,8})for(int32 Jaw:{0,8}){TArray<TSharedPtr<FJsonValue>> V;for(int32 N:{4,4,Lips,Jaw})V.Add(MakeShared<FJsonValueNumber>(N));CharacterLobbyLook->SetArrayField(TEXT("sliders"),V);SaveScene(FString::Printf(TEXT("lips_%d_jaw_%d"),Lips,Jaw));}
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Saved),CharacterLobbyLook);UpdateCharacterLobbyAppearance(CharacterLobbyLook);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeLobbyAmbientTest")))Check(CharacterLobbyMotion&&CharacterLobbyMotion->CheckAmbientMotion(),TEXT("original ambient particles move, face orbit camera and preserve source diameter"));
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetArrayField(TEXT("appearance_gallery"),GalleryImages);Report->SetStringField(TEXT("gallery_color_space"),TEXT("display_srgb"));Report->SetBoolField(TEXT("live_account"),false);if(CharacterLobbyLook)Report->SetObjectField(TEXT("rendered_look"),CharacterLobbyLook);Report->SetNumberField(TEXT("rendered_zoom"),LobbyZoom);
    if(CharacterLobbyTarget){Report->SetNumberField(TEXT("preview_width"),CharacterLobbyTarget->SizeX);Report->SetNumberField(TEXT("preview_height"),CharacterLobbyTarget->SizeY);}
    Report->SetNumberField(TEXT("moving_surfaces"),CharacterLobbyMotion?CharacterLobbyMotion->MovingSurfaces():0);
    Report->SetNumberField(TEXT("ambient_emitters"),CharacterLobbyMotion?CharacterLobbyMotion->AmbientEmitters():0);Report->SetNumberField(TEXT("ambient_particles"),CharacterLobbyMotion?CharacterLobbyMotion->AmbientParticles():0);
    if(auto* Backdrop=Cast<AStaticMeshActor>(CharacterLobbyBackdropActor.Get()))if(UStaticMesh* Mesh=Backdrop->GetStaticMeshComponent()->GetStaticMesh())if(auto* Data=Mesh->GetRenderData()){
        TArray<TSharedPtr<FJsonValue>> Lods;for(const auto& Lod:Data->LODResources){auto Entry=MakeShared<FJsonObject>();Entry->SetNumberField(TEXT("triangles"),Lod.GetNumTriangles());Entry->SetNumberField(TEXT("uv_channels"),Lod.VertexBuffers.StaticMeshVertexBuffer.GetNumTexCoords());Lods.Add(MakeShared<FJsonValueObject>(Entry));}Report->SetArrayField(TEXT("backdrop_lods"),Lods);
    }
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));RemoveCharacterLobby();Phase=99;
    UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
