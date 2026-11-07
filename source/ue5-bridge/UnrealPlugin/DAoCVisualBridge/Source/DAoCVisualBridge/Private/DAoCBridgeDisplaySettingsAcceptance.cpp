#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeDisplaySettings.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"
#include "GameFramework/PlayerController.h"
#include "Serialization/JsonSerializer.h"
#include "Framework/Application/SlateApplication.h"
#include "ImageUtils.h"
bool UDAoCBridgeSubsystem::TickDisplaySettingsAcceptance(){
    FString Report;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDisplaySettingsTest="),Report))return false;
    static bool Done=false;if(Done)return true;FString File;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDisplaySettings="),File);
    static int32 Checks=0;static TArray<FString> Failures;static bool Started=false;static double Began=0;auto Check=[&](bool Value,const TCHAR* Name){++Checks;if(!Value)Failures.Add(Name);};
    if(!GetWorld()||!GetWorld()->GetGameViewport())return true;
    TickDisplaySettings();if(!DisplaySettings)return true;
    if(!Started){Started=true;Began=FPlatformTime::Seconds();
    IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"))->Set(60.f,ECVF_SetBySystemSettingsIni);
    IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync"))->Set(0,ECVF_SetBySystemSettingsIni);
    const int32 Before=Outgoing.Num();auto* User=GEngine->GetGameUserSettings();const auto Original=User->ScalabilityQuality;
    Check(!DisplaySettings->HasSaved,TEXT("first run preserves command-line window and does not create preferences"));
    Check(DisplaySettings->Resolution==FIntPoint(1280,720),TEXT("first run reads actual viewport dimensions"));
    Check(DisplaySettings->Mode==int32(GetWorld()->GetGameViewport()->Viewport->GetWindowMode()),TEXT("first run reflects the actual window mode instead of an unused engine default"));
    Check(!FPaths::FileExists(File),TEXT("opening a display page cannot persist an implicit default"));
    auto Sizes=FBridgeDisplaySettings::Resolutions(FIntPoint(1920,1080),FIntPoint(1500,800));
    Check(Sizes.Contains(FIntPoint(1500,800))&&Sizes.Contains(FIntPoint(1920,1080)),TEXT("resolution list includes current and monitor sizes"));
    Check(!Sizes.Contains(FIntPoint(3840,2160)),TEXT("resolution list excludes values beyond the monitor"));
    for(int32 Cap:FBridgeDisplaySettings::Caps()){FBridgeDisplaySettings Test;Test.File=File;Test.Resolution=FIntPoint(1280,720);Test.Mode=2;Test.Cap=Cap;Check(Test.Save(),TEXT("each original frame cap persists"));FBridgeDisplaySettings Loaded;Check(Loaded.Load(File)&&Loaded.Cap==Cap&&Loaded.Mode==2&&Loaded.Resolution==Test.Resolution,TEXT("each frame cap reloads in a fresh settings object"));Test.Apply(false);auto* V=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync"));auto* F=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS"));Check(V&&V->GetInt()==(Cap>=0)&&F&&FMath::IsNearlyEqual(F->GetFloat(),float(FMath::Max(0,Cap))),TEXT("actual engine VSync and frame cap match original semantics"));}
    Check(!FBridgeDisplaySettings::Valid(FIntPoint(0,720),2,60)&&!FBridgeDisplaySettings::Valid(FIntPoint(1280,720),3,60)&&!FBridgeDisplaySettings::Valid(FIntPoint(1280,720),2,999),TEXT("invalid dimensions, modes and caps are rejected"));
    FFileHelper::SaveStringToFile(TEXT("[Display]\nVersion=1\nWidth=0\nHeight=720\nMode=2\nFrameCap=60\n"),*File);FBridgeDisplaySettings Bad;Check(!Bad.Load(File)&&!Bad.HasSaved,TEXT("malformed preferences leave live defaults intact"));
    *DisplaySettings=FBridgeDisplaySettings();DisplaySettings->File=File;DisplaySettings->Resolution=FIntPoint(1280,720);DisplaySettings->Mode=2;DisplaySettings->Cap=-1;DisplaySettings->Apply(false);
    bDisplayOptions=true;OpenOptions();Check(bOptionsOpen&&OptionsOverlay.IsValid()&&WorldPointerBlocked(FVector2D(10,10)),TEXT("actual original options display page opens and blocks gameplay input"));
    PendingDisplayResolution=FIntPoint(1366,768);PendingDisplayMode=2;PendingDisplayCap=60;BeginDisplayChange();Check(DisplayConfirmUntil>FPlatformTime::Seconds()&&User->GetScreenResolution()==FIntPoint(1366,768),TEXT("apply changes actual engine requested resolution with countdown"));
    ConfirmDisplayChange(false);Check(DisplaySettings->Resolution==FIntPoint(1280,720)&&DisplaySettings->Cap==-1&&DisplayConfirmUntil==0,TEXT("revert restores resolution and frame cap"));
    PendingDisplayCap=30;BeginDisplayChange();DisplayConfirmUntil=FPlatformTime::Seconds()-1;TickDisplaySettings();Check(DisplaySettings->Cap==-1&&!DisplayBefore,TEXT("timeout automatically restores previous display"));
    PendingDisplayCap=75;BeginDisplayChange();ConfirmDisplayChange(true);FBridgeDisplaySettings Saved;Check(Saved.Load(File)&&Saved.Cap==75,TEXT("keep saves only confirmed display settings"));
    PendingDisplayCap=144;BeginDisplayChange();CloseOptions();Check(DisplaySettings->Cap==75&&DisplayConfirmUntil==0,TEXT("closing options reverts an unconfirmed change"));
    bDisplayOptions=true;OpenOptions();
    Check(User->ScalabilityQuality==Original,TEXT("display operations preserve all scalability quality settings"));Check(Outgoing.Num()==Before,TEXT("display operations send no gameplay or server requests"));
    }
    if(FPlatformTime::Seconds()-Began<1)return true;
    TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size;bool Captured=FSlateApplication::Get().TakeScreenshot(OptionsOverlay.ToSharedRef(),Pixels,Size);int32 Visible=0;for(auto P:Pixels)Visible+=FMath::Max3(P.R,P.G,P.B)>20;
    if(Captured&&Visible>1000){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Report+TEXT(".png")));}else Captured=false;Check(Captured,TEXT("actual display page screenshot captured"));CloseOptions();
    auto Json=MakeShared<FJsonObject>();Json->SetBoolField(TEXT("passed"),Failures.IsEmpty());Json->SetNumberField(TEXT("checks"),Checks);TArray<TSharedPtr<FJsonValue>> Values;for(auto Failure:Failures)Values.Add(MakeShared<FJsonValueString>(Failure));Json->SetArrayField(TEXT("failures"),Values);Json->SetBoolField(TEXT("server_started"),false);FString Text;FJsonSerializer::Serialize(Json,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Report);Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
