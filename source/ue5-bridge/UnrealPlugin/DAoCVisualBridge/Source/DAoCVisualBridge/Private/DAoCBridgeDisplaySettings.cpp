#include "DAoCBridgeDisplaySettings.h"
#include "Engine/Engine.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"

const TArray<int32>& FBridgeDisplaySettings::Caps(){static const TArray<int32> Values={0,30,60,75,90,120,144,165,240,-1};return Values;}
bool FBridgeDisplaySettings::Valid(FIntPoint Size,int32 WindowMode,int32 FrameCap){return Size.X>=640&&Size.Y>=480&&Size.X<=16384&&Size.Y<=16384&&WindowMode>=0&&WindowMode<=2&&Caps().Contains(FrameCap);}
TArray<FIntPoint> FBridgeDisplaySettings::Resolutions(FIntPoint Desktop,FIntPoint Current){
    TArray<FIntPoint> Result;for(FIntPoint Size:TArray<FIntPoint>{{1280,720},{1366,768},{1600,900},{1920,1080},{2560,1080},{2560,1440},{3440,1440},{3840,2160}})if(Size.X<=Desktop.X&&Size.Y<=Desktop.Y)Result.Add(Size);
    for(FIntPoint Size:{Desktop,Current})if(Valid(Size,2,0)&&Size.X<=Desktop.X&&Size.Y<=Desktop.Y)Result.AddUnique(Size);
    if(Result.IsEmpty())Result.Add(FIntPoint(640,480));return Result;
}
bool FBridgeDisplaySettings::Load(const FString& Path){
    File=FPaths::ConvertRelativePathToFull(Path);HasSaved=false;FConfigFile Config;if(!FPaths::FileExists(File))return false;Config.Read(File);
    int32 Version=0,X=0,Y=0,M=-1,C=-2;
    if(!Config.GetInt(TEXT("Display"),TEXT("Version"),Version)||Version!=1||!Config.GetInt(TEXT("Display"),TEXT("Width"),X)||!Config.GetInt(TEXT("Display"),TEXT("Height"),Y)||!Config.GetInt(TEXT("Display"),TEXT("Mode"),M)||!Config.GetInt(TEXT("Display"),TEXT("FrameCap"),C)||!Valid(FIntPoint(X,Y),M,C))return false;
    Resolution=FIntPoint(X,Y);Mode=M;Cap=C;HasSaved=true;return true;
}
bool FBridgeDisplaySettings::Save() const{
    if(File.IsEmpty()||!Valid(Resolution,Mode,Cap))return false;IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);
    FConfigFile Config;Config.Read(File);Config.SetString(TEXT("Display"),TEXT("Version"),*FString::FromInt(1));Config.SetString(TEXT("Display"),TEXT("Width"),*FString::FromInt(Resolution.X));Config.SetString(TEXT("Display"),TEXT("Height"),*FString::FromInt(Resolution.Y));Config.SetString(TEXT("Display"),TEXT("Mode"),*FString::FromInt(Mode));Config.SetString(TEXT("Display"),TEXT("FrameCap"),*FString::FromInt(Cap));return Config.Write(File);
}
void FBridgeDisplaySettings::Apply(bool Resize) const{
    if(!Valid(Resolution,Mode,Cap))return;
    if(Resize&&GEngine)if(auto* Settings=GEngine->GetGameUserSettings()){Settings->SetScreenResolution(Resolution);Settings->SetFullscreenMode(static_cast<EWindowMode::Type>(Mode));UGameUserSettings::RequestResolutionChange(Resolution.X,Resolution.Y,static_cast<EWindowMode::Type>(Mode),false);IConsoleManager::Get().CallAllConsoleVariableSinks();}
    if(auto* VSync=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VSync")))VSync->SetWithCurrentPriority(Cap>=0?1:0);
    if(auto* FPS=IConsoleManager::Get().FindConsoleVariable(TEXT("t.MaxFPS")))FPS->SetWithCurrentPriority(float(FMath::Max(0,Cap)));
}
