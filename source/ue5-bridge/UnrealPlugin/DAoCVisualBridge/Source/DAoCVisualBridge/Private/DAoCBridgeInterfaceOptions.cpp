#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Widgets/SWidget.h"

void UDAoCBridgeSubsystem::LoadInterfaceSettings(){
    if(InterfaceSettings)return;InterfaceSettings=MakeShared<FBridgeInterfaceSettings>();
    FString File=FPaths::ProjectSavedDir()/TEXT("DAoCBridgeInterface.ini");const bool Explicit=FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInterfaceSettings="),File);
    if(Explicit||(!FParse::Param(FCommandLine::Get(),TEXT("unattended"))&&!FParse::Param(FCommandLine::Get(),TEXT("RenderOffscreen"))))InterfaceSettings->Load(File);
    PendingInterfaceScale=InterfaceSettings->Scale;
}
void UDAoCBridgeSubsystem::PreviewInterfaceScale(float Value){
    if(!bOptionsOpen||!bInterfaceOptions||!FBridgeInterfaceSettings::Valid(Value))return;
    PendingInterfaceScale=FMath::Clamp(FMath::RoundToFloat(Value/.05f)*.05f,.6f,1.6f);
    if(!bInterfaceScaleDragging)CommitInterfaceScale();
}
void UDAoCBridgeSubsystem::CommitInterfaceScale(){
    if(!bOptionsOpen||!bInterfaceOptions)return;
    LoadInterfaceSettings();if(!FBridgeInterfaceSettings::Valid(PendingInterfaceScale))return;
    const float Previous=InterfaceSettings->Scale;InterfaceSettings->Scale=PendingInterfaceScale;
    if(!InterfaceSettings->Save()){InterfaceSettings->Scale=PendingInterfaceScale=Previous;InterfaceMessage=TEXT("Could not save the interface scale; previous size retained.");return;}
    InterfaceMessage=TEXT("Interface scale saved. Large windows fit the screen automatically.");UpdateUILayout();
    if(OptionsOverlay.IsValid())OptionsOverlay->Invalidate(EInvalidateWidgetReason::Layout);
}
