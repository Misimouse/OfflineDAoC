#include "DAoCBridgeInterfaceSettings.h"
#include "HAL/FileManager.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/Paths.h"

bool FBridgeInterfaceSettings::Valid(float Value){return FMath::IsFinite(Value)&&Value>=.6f&&Value<=1.6f;}
float FBridgeInterfaceSettings::EffectiveScale(FVector2D Size,float Preference){
    if(!FMath::IsFinite(Size.X)||!FMath::IsFinite(Size.Y)||Size.X<=16||Size.Y<=16)return .4f;
    const float Base=FMath::Clamp(float(FMath::Min(Size.Y/600.,Size.X/800.)*.78),.4f,2.5f);
    // Keep the largest existing game window (exchange, 700 x 556) reachable.
    const float Fit=float(FMath::Min((Size.X-16)/700.,(Size.Y-16)/556.));
    return FMath::Max(.01f,FMath::Min(Base*(Valid(Preference)?Preference:1.f),Fit));
}
bool FBridgeInterfaceSettings::Load(const FString& Path){
    File=FPaths::ConvertRelativePathToFull(Path);Scale=1.f;FConfigFile Config;
    if(!FPaths::FileExists(File))return false;Config.Read(File);
    int32 Version=0;float Value=1;
    if(!Config.GetInt(TEXT("Interface"),TEXT("Version"),Version)||Version!=1||!Config.GetFloat(TEXT("Interface"),TEXT("UIScale"),Value)||!Valid(Value))return false;
    Scale=Value;return true;
}
bool FBridgeInterfaceSettings::Save()const{
    if(File.IsEmpty()||!Valid(Scale))return false;
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(File),true);FConfigFile Config;Config.Read(File);
    // Nine significant digits preserve every float slider step on reload.
    Config.SetString(TEXT("Interface"),TEXT("Version"),TEXT("1"));Config.SetString(TEXT("Interface"),TEXT("UIScale"),*FString::Printf(TEXT("%.9g"),double(Scale)));return Config.Write(File);
}
