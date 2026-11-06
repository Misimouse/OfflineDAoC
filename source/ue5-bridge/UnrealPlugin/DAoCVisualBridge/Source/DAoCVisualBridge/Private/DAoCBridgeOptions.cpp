#include "DAoCBridgeSubsystem.h"
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
    LoadAudioSettings();
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
    auto Button=[&](const FString& Text,float X,float Y,float W,TFunction<void()> Click){At(X,Y,W,22,SNew(SButton).IsFocusable(false).ContentPadding(FMargin(2,0)).OnClicked_Lambda([Click](){Click();return FReply::Handled();})[Label(Text,Text==TEXT("CHARACTER SELECT")?8:10)]);};
    At(0,0,384,420,SNew(SImage).Image(ClassicArt(TEXT("options"))));
    At(15,5,330,19,Label(TEXT("OPTIONS"),13));
    At(18,34,330,22,Label(TEXT("SOUND"),14));
    for(int32 I=0;I<2;++I){const bool Master=I==0;const float Y=85+I*80;
        At(20,Y,300,22,Label(Master?TEXT("MASTER VOLUME"):TEXT("SOUND EFFECTS")));
        At(20,Y+28,275,20,SNew(SSlider).Value_Lambda([this,Master](){return Master?AudioMasterVolume:AudioEffectsVolume;}).OnValueChanged_Lambda([this,Master](float Value){SetAudioVolume(Master,Value);}));
        At(305,Y+26,55,22,SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",12)).Text_Lambda([this,Master](){return FText::FromString(FString::Printf(TEXT("%d%%"),FMath::RoundToInt((Master?AudioMasterVolume:AudioEffectsVolume)*100)));}));
    }
    At(20,285,330,55,Label(TEXT("Changes are saved automatically."),11));
    Button(TEXT("CHARACTER SELECT"),10,394,114,[this](){CloseOptions();auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("text"),TEXT("/quit"));Send(TEXT("chat"),Value);});
    Button(TEXT("QUIT"),135,394,114,[this](){CloseOptions();Send(TEXT("logout"));bExiting=true;Status=TEXT("Saving and logging out...");});
    Button(TEXT("CLOSE"),256,394,114,[this](){CloseOptions();});
    const float Scale=ClassicScale();auto Overlay=SNew(SOverlay);Overlay->AddSlot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SBox).WidthOverride(384*Scale).HeightOverride(420*Scale)[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)[SNew(SBox).WidthOverride(384).HeightOverride(420)[Canvas]]]];
    OptionsOverlay=Overlay;GetWorld()->GetGameViewport()->AddViewportWidgetContent(Overlay,90);
}
bool UDAoCBridgeSubsystem::CloseOptions(){
    const bool WasOpen=bOptionsOpen;bOptionsOpen=false;
    if(OptionsOverlay&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(OptionsOverlay.ToSharedRef());
    OptionsOverlay.Reset();return WasOpen;
}
