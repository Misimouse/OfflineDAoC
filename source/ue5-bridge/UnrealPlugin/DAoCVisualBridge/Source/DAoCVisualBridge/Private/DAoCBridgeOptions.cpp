#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "DAoCBridgeDisplaySettings.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "Widgets/Input/SComboBox.h"
#include "DAoCBridgeMovementKeys.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Engine/Texture2D.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Styling/CoreStyle.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SCanvas.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSlider.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"

void UDAoCBridgeSubsystem::LoadKeyConfiguration(){
    if(KeyConfiguration)return;
    KeyConfiguration=MakeShared<FBridgeKeyConfiguration>();FString Path=FPaths::ProjectSavedDir()/TEXT("DAoCKeyConfiguration.ini");
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeKeyConfiguration="),Path);KeyConfiguration->Load(Path);
}
bool UDAoCBridgeSubsystem::CaptureControlKey(FKey Key,bool Shift,bool Ctrl,bool Alt,bool Repeat){
    if(!bOptionsOpen||BindingCaptureAction.IsEmpty())return false;
    if(Repeat)return true;
    if(Key==EKeys::Escape){BindingCaptureAction.Empty();BindingCaptureSlot=-1;BindingMessage=TEXT("Binding cancelled.");return true;}
    if(Key==EKeys::LeftShift||Key==EKeys::RightShift||Key==EKeys::LeftControl||Key==EKeys::RightControl||Key==EKeys::LeftAlt||Key==EKeys::RightAlt)return true;
    const FString Value=Key==EKeys::RightMouseButton?FString():FBridgeKeyConfiguration::Describe(Key,Shift,Ctrl,Alt);
    if(KeyConfiguration->Bind(BindingCaptureAction,BindingCaptureSlot,Value,BindingMessage)){
        if(!KeyConfiguration->Save())BindingMessage=TEXT("Could not save the key configuration.");
        BindingCaptureAction.Empty();BindingCaptureSlot=-1;
    }
    return true;
}

void UDAoCBridgeSubsystem::LoadAudioSettings(){
    if(bAudioSettingsLoaded)return;bAudioSettingsLoaded=true;
    AudioSettingsPath=FPaths::ProjectSavedDir()/TEXT("DAoCBridgeAudio.ini");
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeAudioSettings="),AudioSettingsPath);
    AudioSettingsPath=FPaths::ConvertRelativePathToFull(AudioSettingsPath);
    GConfig->GetFloat(TEXT("Audio"),TEXT("Master"),AudioMasterVolume,AudioSettingsPath);
    GConfig->GetFloat(TEXT("Audio"),TEXT("Effects"),AudioEffectsVolume,AudioSettingsPath);
    AudioMasterVolume=FMath::IsFinite(AudioMasterVolume)?FMath::Clamp(AudioMasterVolume,0.f,1.f):1.f;
    AudioEffectsVolume=FMath::IsFinite(AudioEffectsVolume)?FMath::Clamp(AudioEffectsVolume,0.f,1.f):1.f;
}
void UDAoCBridgeSubsystem::SetAudioVolume(bool Master,float Value){
    LoadAudioSettings();if(!FMath::IsFinite(Value))return;
    (Master?AudioMasterVolume:AudioEffectsVolume)=FMath::Clamp(Value,0.f,1.f);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(AudioSettingsPath),true);
    GConfig->SetFloat(TEXT("Audio"),TEXT("Master"),AudioMasterVolume,AudioSettingsPath);
    GConfig->SetFloat(TEXT("Audio"),TEXT("Effects"),AudioEffectsVolume,AudioSettingsPath);
    GConfig->Flush(false,AudioSettingsPath);
}
void UDAoCBridgeSubsystem::OpenOptions(){
    if(bOptionsOpen||!GetWorld()||!GetWorld()->GetGameViewport())return;
    LoadAudioSettings();LoadKeyConfiguration();LoadInterfaceSettings();TickDisplaySettings();
    FString Art=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/options.png");
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeOptionsArt="),Art);
    if(!ClassicTextures.Contains(TEXT("options"))){
        auto* Texture=FImageUtils::ImportFileAsTexture2D(Art);if(!Texture){Status=TEXT("Options artwork could not be loaded.");return;}
        Texture->SRGB=true;Texture->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("options"),Texture);
    }
    bOptionsOpen=true;bMouseLookToggle=false;bLeftPointerHeld=bRightPointerHeld=bRightPointerDragged=false;SetMouseLook(false);
    if(auto* PC=GetWorld()->GetFirstPlayerController())PC->bShowMouseCursor=true;
    auto Canvas=SNew(SCanvas);
    auto At=[&](float X,float Y,float W,float H,TSharedRef<SWidget> Widget){Canvas->AddSlot().Position(FVector2D(X,Y)).Size(FVector2D(W,H))[Widget];};
    auto Label=[&](const FString& Text,int32 Size=12){return SNew(STextBlock).Text(FText::FromString(Text)).Font(FCoreStyle::GetDefaultFontStyle("Regular",Size)).ColorAndOpacity(FLinearColor(.94,.91,.78));};
    auto Button=[&](const FString& Text,float X,float Y,float W,TFunction<void()> Click){At(X,Y,W,22,SNew(SButton).IsFocusable(false).ContentPadding(FMargin(2,0)).OnClicked_Lambda([Click](){Click();return FReply::Handled();})[Label(Text,(Y==34||Text==TEXT("CHARACTER SELECT"))?8:10)]);};
    At(0,0,384,420,SNew(SImage).Image(ClassicArt(TEXT("options"))));
    At(15,5,330,19,Label(TEXT("OPTIONS"),13));
    Button(TEXT("SOUND"),15,34,83,[this](){CloseOptions();bControlsOptions=false;bDisplayOptions=bInterfaceOptions=false;OpenOptions();});
    Button(TEXT("CONTROLS"),105,34,83,[this](){CloseOptions();bControlsOptions=true;bDisplayOptions=bInterfaceOptions=false;OpenOptions();});
    Button(TEXT("DISPLAY"),195,34,83,[this](){CloseOptions();bControlsOptions=false;bDisplayOptions=true;bInterfaceOptions=false;OpenOptions();});
    Button(TEXT("INTERFACE"),285,34,83,[this](){CloseOptions();bControlsOptions=bDisplayOptions=false;bInterfaceOptions=true;OpenOptions();});
    if(bInterfaceOptions){
        At(20,85,300,22,Label(TEXT("UI SCALE")));
        At(20,118,275,20,SNew(SSlider).MinValue(.6f).MaxValue(1.6f).StepSize(.05f).MouseUsesStep(true)
            .Value_Lambda([this](){return PendingInterfaceScale;})
            .OnMouseCaptureBegin_Lambda([this](){bInterfaceScaleDragging=true;})
            .OnValueChanged_Lambda([this](float V){PreviewInterfaceScale(V);})
            .OnMouseCaptureEnd_Lambda([this](){const bool Dragging=bInterfaceScaleDragging;bInterfaceScaleDragging=false;if(Dragging&&bOptionsOpen)CommitInterfaceScale();}));
        At(305,116,55,22,SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",12)).Text_Lambda([this](){return FText::FromString(FString::Printf(TEXT("%d%%"),FMath::RoundToInt(PendingInterfaceScale*100)));}));
        At(20,164,340,75,SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",10)).Text(FText::FromString(TEXT("Make the interface bigger or smaller. Release the slider to apply. Large windows fit the screen automatically."))));
        Button(TEXT("RESTORE DEFAULT SIZE"),70,255,244,[this](){bInterfaceScaleDragging=false;PendingInterfaceScale=1.f;CommitInterfaceScale();});
        At(20,310,340,68,SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",10)).Text_Lambda([this](){return FText::FromString(InterfaceMessage.IsEmpty()?TEXT("Changes are saved automatically. Window positions follow their screen edges."):InterfaceMessage);}));
    }else if(bDisplayOptions){
        if(DisplaySettings){
            auto Choice=[&](float Y,const FString& Name,const TArray<FString>& Values,TFunction<int32()> Selected,TFunction<void(int32)> Change,TFunction<bool()> Enabled){
                At(20,Y,340,20,Label(Name,11));
                auto Items=MakeShared<TArray<TSharedPtr<FString>>>();for(const auto& Value:Values)Items->Add(MakeShared<FString>(Value));
                auto Current=MakeShared<int32>(FMath::Clamp(Selected(),0,Items->Num()-1));
                At(20,Y+24,340,24,SNew(SComboBox<TSharedPtr<FString>>).OptionsSource(&Items.Get()).InitiallySelectedItem((*Items)[*Current]).IsEnabled_Lambda([Enabled](){return Enabled();})
                    .OnGenerateWidget_Lambda([Items](TSharedPtr<FString> Item){return SNew(STextBlock).Text(FText::FromString(*Item)).Font(FCoreStyle::GetDefaultFontStyle("Regular",10));})
                    .OnSelectionChanged_Lambda([Items,Current,Change](TSharedPtr<FString> Item,ESelectInfo::Type){int32 Index=Items->IndexOfByKey(Item);if(Index!=INDEX_NONE){*Current=Index;Change(Index);}})
                    [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",10)).Text_Lambda([Items,Selected](){return FText::FromString(*(*Items)[FMath::Clamp(Selected(),0,Items->Num()-1)]);})]);
            };
            FIntPoint Desktop=GEngine->GetGameUserSettings()->GetDesktopResolution();auto Sizes=FBridgeDisplaySettings::Resolutions(Desktop,PendingDisplayResolution);TArray<FString> Names;
            for(auto Size:Sizes)Names.Add(FString::Printf(TEXT("%d X %d"),Size.X,Size.Y));
            Choice(75,TEXT("RESOLUTION"),Names,[this,Sizes](){return Sizes.IndexOfByKey(PendingDisplayResolution);},[this,Sizes](int32 I){PendingDisplayResolution=Sizes[I];},[this](){return DisplayConfirmUntil==0&&PendingDisplayMode!=1;});
            Choice(140,TEXT("WINDOW MODE"),{TEXT("FULLSCREEN"),TEXT("BORDERLESS (DESKTOP)"),TEXT("WINDOWED")},[this](){return PendingDisplayMode;},[this](int32 I){PendingDisplayMode=I;},[this](){return DisplayConfirmUntil==0;});
            Names.Reset();for(int32 Cap:FBridgeDisplaySettings::Caps())Names.Add(Cap==0?TEXT("MONITOR REFRESH (VSYNC)"):Cap<0?TEXT("UNLIMITED (NO VSYNC)"):FString::Printf(TEXT("%d FPS"),Cap));
            Choice(205,TEXT("FRAME RATE CAP"),Names,[this](){return FBridgeDisplaySettings::Caps().IndexOfByKey(PendingDisplayCap);},[this](int32 I){PendingDisplayCap=FBridgeDisplaySettings::Caps()[I];},[this](){return DisplayConfirmUntil==0;});
            At(20,271,340,35,SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",9)).Text(FText::FromString(TEXT("Positive limits use VSync. Borderless fills the desktop. F11 remains first-person view."))));
            Button(TEXT("APPLY"),20,310,100,[this](){BeginDisplayChange();});Button(TEXT("KEEP"),140,310,100,[this](){ConfirmDisplayChange(true);});Button(TEXT("REVERT"),260,310,100,[this](){ConfirmDisplayChange(false);CloseOptions();bDisplayOptions=true;OpenOptions();});
            At(20,345,340,42,SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",10)).Text_Lambda([this](){return FText::FromString(DisplayConfirmUntil>0?FString::Printf(TEXT("Keep these settings? Reverting in %d seconds."),FMath::Max(0,FMath::CeilToInt(DisplayConfirmUntil-FPlatformTime::Seconds()))):DisplayMessage.IsEmpty()?TEXT("Apply, then Keep to save your display settings."):DisplayMessage);}));
        }else At(20,85,340,55,Label(TEXT("Display settings are unavailable in this test."),10));
    }else if(!bControlsOptions){
    for(int32 I=0;I<2;++I){const bool Master=I==0;const float Y=85+I*80;
        At(20,Y,300,22,Label(Master?TEXT("MASTER VOLUME"):TEXT("SOUND EFFECTS")));
        At(20,Y+28,275,20,SNew(SSlider).Value_Lambda([this,Master](){return Master?AudioMasterVolume:AudioEffectsVolume;}).OnValueChanged_Lambda([this,Master](float Value){SetAudioVolume(Master,Value);}));
        At(305,Y+26,55,22,SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",12)).Text_Lambda([this,Master](){return FText::FromString(FString::Printf(TEXT("%d%%"),FMath::RoundToInt((Master?AudioMasterVolume:AudioEffectsVolume)*100)));}));
    }
    At(20,285,330,55,Label(TEXT("Changes are saved automatically."),11));
    }else{
        auto List=SNew(SVerticalBox);
        List->AddSlot().AutoHeight().Padding(0,4)[Label(TEXT("MOVEMENT"),12)];
        List->AddSlot().AutoHeight()[Label(TEXT("MOUSE SENSITIVITY"),10)];
        List->AddSlot().AutoHeight().Padding(0,4)[SNew(SSlider).MinValue(.05f).MaxValue(1.5f).Value_Lambda([this](){return MouseSensitivity;}).OnValueChanged_Lambda([this](float V){if(FMath::IsFinite(V)){MouseSensitivity=FMath::Clamp(V,.05f,1.5f);SaveControls();}})];
        List->AddSlot().AutoHeight().Padding(0,4)[SNew(SCheckBox).IsChecked_Lambda([this](){return bInvertMouse?ECheckBoxState::Checked:ECheckBoxState::Unchecked;}).OnCheckStateChanged_Lambda([this](ECheckBoxState V){bInvertMouse=V==ECheckBoxState::Checked;SaveControls();})[Label(TEXT("INVERT MOUSE"),10)]];
        List->AddSlot().AutoHeight().Padding(0,6)[Label(TEXT("KEY CONFIGURATION"),12)];
        FString Category;
        for(const auto& Action:KeyConfiguration->Actions){
            if(Category!=Action.Category){Category=Action.Category;List->AddSlot().AutoHeight().Padding(0,5)[Label(Category.ToUpper(),11)];}
            const FString Id=Action.Id;auto Row=SNew(SHorizontalBox);Row->AddSlot().FillWidth(1).VAlign(VAlign_Center)[Label(Action.Label,10)];
            for(int32 Slot=0;Slot<2;++Slot)Row->AddSlot().AutoWidth().Padding(2,1)[SNew(SBox).WidthOverride(83).HeightOverride(23)[SNew(SButton).IsFocusable(false).ContentPadding(FMargin(1)).OnClicked_Lambda([this,Id,Slot](){BindingCaptureAction=Id;BindingCaptureSlot=Slot;BindingMessage=TEXT("Press a key. Esc cancels; right-click clears.");return FReply::Handled();})[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",9)).Text_Lambda([this,Id,Slot](){return FText::FromString(BindingCaptureAction==Id&&BindingCaptureSlot==Slot?TEXT("PRESS A KEY"):KeyConfiguration->Text(Id,Slot));})]]];
            List->AddSlot().AutoHeight()[Row];
        }
        List->AddSlot().AutoHeight().Padding(0,7)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([this](){KeyConfiguration->Reset();BindingCaptureAction.Empty();BindingCaptureSlot=-1;BindingMessage=KeyConfiguration->Save()?TEXT("Default keys restored."):TEXT("Could not save the key configuration.");return FReply::Handled();})[Label(TEXT("RESTORE DEFAULTS"),10)]];
        List->AddSlot().AutoHeight().Padding(0,5)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",9)).Text(FText::FromString(TEXT("Shift: walk while held. Chat, menu, camera and GM keys remain reserved. Click a key to change it; Mouse 4 / 5 also work.")))];
        At(15,66,354,277,SNew(SScrollBox)+SScrollBox::Slot()[List]);
        At(18,348,345,40,SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",10)).Text_Lambda([this](){return FText::FromString(BindingMessage.IsEmpty()?TEXT("Changes are saved automatically."):BindingMessage);}));
    }
    Button(TEXT("CHARACTER SELECT"),10,394,114,[this](){CloseOptions();auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("text"),TEXT("/quit"));Send(TEXT("chat"),Value);});
    Button(TEXT("QUIT"),135,394,114,[this](){CloseOptions();Send(TEXT("logout"));bExiting=true;Status=TEXT("Saving and logging out...");});
    Button(TEXT("CLOSE"),256,394,114,[this](){CloseOptions();});
    auto Overlay=SNew(SOverlay);Overlay->AddSlot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SBox).WidthOverride_Lambda([this](){return 384*ClassicScale();}).HeightOverride_Lambda([this](){return 420*ClassicScale();})[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SBox).WidthOverride(384).HeightOverride(420)[Canvas]]]];
    OptionsOverlay=Overlay;GetWorld()->GetGameViewport()->AddViewportWidgetContent(Overlay,90);
}
bool UDAoCBridgeSubsystem::CloseOptions(){
    if(DisplayConfirmUntil>0)ConfirmDisplayChange(false);
    const bool WasOpen=bOptionsOpen;bOptionsOpen=false;bInterfaceScaleDragging=false;if(InterfaceSettings)PendingInterfaceScale=InterfaceSettings->Scale;
    BindingCaptureAction.Empty();BindingCaptureSlot=-1;if(WasOpen){ChatClosedAt=FPlatformTime::Seconds();if(MovementKeys)MovementKeys->RunLock=false;}
    if(OptionsOverlay&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(OptionsOverlay.ToSharedRef());
    OptionsOverlay.Reset();return WasOpen;
}
