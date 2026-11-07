#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeDisplaySettings.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/GameUserSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#include "HAL/IConsoleManager.h"

void UDAoCBridgeSubsystem::TickDisplaySettings(){
    if(DisplayConfirmUntil>0&&FPlatformTime::Seconds()>=DisplayConfirmUntil)ConfirmDisplayChange(false);
    if(DisplaySettings||!GEngine||!GetWorld()||!GetWorld()->GetGameViewport()||!GetWorld()->GetGameViewport()->Viewport)return;
    FString File=FPaths::ProjectSavedDir()/TEXT("DAoCBridgeDisplay.ini");const bool Explicit=FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDisplaySettings="),File);
    // Automated fixtures keep their own requested window unless they explicitly exercise display preferences.
    if(!Explicit&&(FParse::Param(FCommandLine::Get(),TEXT("unattended"))||FParse::Param(FCommandLine::Get(),TEXT("RenderOffscreen"))))return;
    auto* User=GEngine->GetGameUserSettings();if(!User)return;
    DisplaySettings=MakeShared<FBridgeDisplaySettings>();DisplaySettings->Resolution=GetWorld()->GetGameViewport()->Viewport->GetSizeXY();DisplaySettings->Mode=int32(GetWorld()->GetGameViewport()->Viewport->GetWindowMode());
    const bool Saved=DisplaySettings->Load(File);
    if(Explicit)UE_LOG(LogTemp,Display,TEXT("DAoC private display settings loaded=%d size=%dx%d mode=%d cap=%d"),Saved,DisplaySettings->Resolution.X,DisplaySettings->Resolution.Y,DisplaySettings->Mode,DisplaySettings->Cap);
    if(Saved){FIntPoint Desktop=User->GetDesktopResolution();if(Desktop.X>0&&Desktop.Y>0)DisplaySettings->Resolution=DisplaySettings->Resolution.ComponentMin(Desktop);DisplaySettings->Apply();}
    else {const auto* Sync=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync"));const auto* FPS=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));int32 Cap=FPS?FMath::RoundToInt(FPS->GetFloat()):0;DisplaySettings->Cap=FBridgeDisplaySettings::Caps().Contains(Cap)&&Cap>0?Cap:Sync&&Sync->GetInt()!=0?0:-1;}
    PendingDisplayResolution=DisplaySettings->Resolution;PendingDisplayMode=DisplaySettings->Mode;PendingDisplayCap=DisplaySettings->Cap;
}
void UDAoCBridgeSubsystem::BeginDisplayChange(){
    if(!DisplaySettings||DisplayConfirmUntil>0||!FBridgeDisplaySettings::Valid(PendingDisplayResolution,PendingDisplayMode,PendingDisplayCap))return;
    DisplayBefore=MakeShared<FBridgeDisplaySettings>(*DisplaySettings);
    DisplaySettings->Resolution=PendingDisplayResolution;DisplaySettings->Mode=PendingDisplayMode;DisplaySettings->Cap=PendingDisplayCap;
    DisplayConfirmUntil=FPlatformTime::Seconds()+15;DisplayMessage=TEXT("Keep these settings? Reverting in 15 seconds.");DisplaySettings->Apply();
}
void UDAoCBridgeSubsystem::ConfirmDisplayChange(bool Keep){
    if(!DisplayBefore||!DisplaySettings)return;
    if(Keep){if(DisplaySettings->Save()){DisplaySettings->HasSaved=true;DisplayMessage=TEXT("Display settings saved.");}else{*DisplaySettings=*DisplayBefore;DisplaySettings->Apply();DisplayMessage=TEXT("Could not save display settings; previous display restored.");}}
    else{*DisplaySettings=*DisplayBefore;DisplaySettings->Apply();DisplayMessage=TEXT("Previous display restored.");}
    PendingDisplayResolution=DisplaySettings->Resolution;PendingDisplayMode=DisplaySettings->Mode;PendingDisplayCap=DisplaySettings->Cap;DisplayBefore.Reset();DisplayConfirmUntil=0;
}
