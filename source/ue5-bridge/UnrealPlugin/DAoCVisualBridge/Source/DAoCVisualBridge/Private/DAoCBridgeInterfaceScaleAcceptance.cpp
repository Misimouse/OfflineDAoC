#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Input/SSlider.h"
#include <limits>

bool UDAoCBridgeSubsystem::TickInterfaceScaleAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInterfaceScaleTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0,Before=0;double Began=0;float InitialWidth=0;TArray<FString> Failures;TSharedPtr<SSlider> Slider;};static FRun Run;
    auto Check=[&](bool V,const TCHAR* Name){++Run.Checks;if(!V)Run.Failures.Add(Name);};
    auto Capture=[&](const FString& Suffix){TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size;bool OK=OptionsOverlay.IsValid()&&FSlateApplication::Get().TakeScreenshot(OptionsOverlay.ToSharedRef(),Pixels,Size);if(OK){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);OK=FFileHelper::SaveArrayToFile(Bytes,*(Path+Suffix));}Check(OK,TEXT("actual interface page screenshot captured"));};
    if(Run.Phase==0){
        LoadInterfaceSettings();float Expected=1;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeExpectedInterfaceScale="),Expected);
        Check(FMath::IsNearlyEqual(InterfaceSettings->Scale,Expected),TEXT("new process loads the saved interface preference"));Run.Before=Outgoing.Num();
        for(float V:{.59f,1.61f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()})Check(!FBridgeInterfaceSettings::Valid(V),TEXT("invalid scale preferences are rejected"));
        const FString File=InterfaceSettings->File;
        for(int32 Step=12;Step<=32;++Step){
            const float Preference=Step*.05f;FBridgeInterfaceSettings Settings;Settings.File=File+TEXT(".roundtrip");Settings.Scale=Preference;
            Check(Settings.Save(),TEXT("each original slider step saves"));FBridgeInterfaceSettings Loaded;Check(Loaded.Load(Settings.File)&&FMath::IsNearlyEqual(Loaded.Scale,Preference),TEXT("each slider step reloads without changing its value"));
            for(FVector2D Size:TArray<FVector2D>{{640,480},{800,600},{1280,720},{1920,1080},{2560,1080},{3440,1440},{3840,2160}}){
                const float Scale=FBridgeInterfaceSettings::EffectiveScale(Size,Preference);
                Check(FMath::IsFinite(Scale)&&Scale>0&&700*Scale<=Size.X-15.9&&556*Scale<=Size.Y-15.9,TEXT("largest existing window fits at every original scale and tested viewport"));
            }
        }
        for(const TCHAR* Value:{TEXT("0"),TEXT("2"),TEXT("nan"),TEXT("missing")}){
            const FString Bad=File+TEXT(".invalid");FFileHelper::SaveStringToFile(FString::Printf(TEXT("[Interface]\nVersion=1\nUIScale=%s\n"),Value),*Bad);FBridgeInterfaceSettings Loaded;
            Check(!Loaded.Load(Bad)&&Loaded.Scale==1,TEXT("malformed saved preference falls back to default size"));
        }
        FFileHelper::SaveStringToFile(TEXT("[Interface]\nVersion=99\nUIScale=1.2\n"),*(File+TEXT(".version")));FBridgeInterfaceSettings Version;
        Check(!Version.Load(File+TEXT(".version"))&&Version.Scale==1,TEXT("unknown settings version cannot change scale"));
        for(FVector2D Size:TArray<FVector2D>{{1280,720},{1920,1080},{3440,1440}}){const float Prior=FMath::Clamp(float(FMath::Min(Size.Y/600.,Size.X/800.)*.78),.4f,2.5f);Check(FMath::IsNearlyEqual(FBridgeInterfaceSettings::EffectiveScale(Size,1),Prior),TEXT("default scale preserves the established native interface size"));}
        FString FixtureFile,Text;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeUIScaleFixture="),FixtureFile);
        const bool Loaded=FFileHelper::LoadFileToString(Text,*FixtureFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture)&&Fixture.IsValid();Check(Loaded,TEXT("original game UI fixture loads"));
        if(Loaded){Fixture->GetObjectField(TEXT("classic_ui"))->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedUIScale%lld"),FDateTime::UtcNow().GetTicks()));ApplyInventory(Fixture->GetObjectField(TEXT("inventory")));ApplyClassicUI(Fixture->GetObjectField(TEXT("classic_ui")));}
        bControlsOptions=bDisplayOptions=false;bInterfaceOptions=true;OpenOptions();Check(bOptionsOpen&&OptionsOverlay.IsValid()&&ClassicArt(TEXT("options")),TEXT("interface page uses original options artwork"));
        PreviewInterfaceScale(1);Run.Phase=1;Run.Began=FPlatformTime::Seconds();return true;
    }
    if(FPlatformTime::Seconds()-Run.Began<.8)return true;
    if(Run.Phase==1){
        TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SSlider"))Run.Slider=StaticCastSharedRef<SSlider>(W);auto* Children=W->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(OptionsOverlay.ToSharedRef());
        Check(Run.Slider.IsValid(),TEXT("actual interface page has its scale slider"));Capture(TEXT(".default.png"));
        if(Run.Slider){const auto Geometry=Run.Slider->GetCachedGeometry();Run.InitialWidth=float(Geometry.GetAbsoluteSize().X);const FVector2D Point=Geometry.LocalToAbsolute(FVector2D(Geometry.GetLocalSize().X-1,Geometry.GetLocalSize().Y*.5));
            const FPointerEvent Mouse(0,Point,Point,TSet<FKey>{EKeys::LeftMouseButton},EKeys::LeftMouseButton,0,FModifierKeysState());Run.Slider->OnMouseButtonDown(Geometry,Mouse);
            Check(bInterfaceScaleDragging&&PendingInterfaceScale>1.5f&&FMath::IsNearlyEqual(InterfaceSettings->Scale,1.f),TEXT("actual slider drag previews without moving the interface under the pointer"));
            Run.Slider->OnMouseCaptureLost(FCaptureLostEvent());Check(!bInterfaceScaleDragging&&InterfaceSettings->Scale>1.5f,TEXT("ending slider capture applies the selected interface size"));
        }
        Check(WorldPointerBlocked(FVector2D(10,10)),TEXT("interface options block world clicks"));Run.Phase=2;Run.Began=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==2){
        if(Run.Slider)Check(Run.Slider->GetCachedGeometry().GetAbsoluteSize().X>Run.InitialWidth,TEXT("same actual slider is larger after release without rebuilding the window"));
        Check(UILayoutUnits.Equals(UIViewportSize()/ClassicScale(),.5),TEXT("game windows reflow using the new scale"));Capture(TEXT(".large.png"));
        const float Before=InterfaceSettings->Scale;PreviewInterfaceScale(std::numeric_limits<float>::quiet_NaN());Check(InterfaceSettings->Scale==Before,TEXT("invalid live slider value leaves size unchanged"));
        bInterfaceScaleDragging=true;PreviewInterfaceScale(.7f);CloseOptions();Check(!bInterfaceScaleDragging&&InterfaceSettings->Scale==Before&&PendingInterfaceScale==Before,TEXT("closing during preview cancels unapplied movement"));
        bInterfaceOptions=true;OpenOptions();const FString SavedFile=InterfaceSettings->File;InterfaceSettings->File.Empty();PreviewInterfaceScale(.8f);Check(InterfaceSettings->Scale==Before&&PendingInterfaceScale==Before&&InterfaceMessage.Contains(TEXT("Could not save")),TEXT("save failure retains the previous applied size"));InterfaceSettings->File=SavedFile;
        PreviewInterfaceScale(1);Check(InterfaceSettings->Scale==1,TEXT("default size can be restored"));PreviewInterfaceScale(1.35f);
        FBridgeInterfaceSettings Reloaded;Check(Reloaded.Load(SavedFile)&&FMath::IsNearlyEqual(Reloaded.Scale,1.35f),TEXT("applied size persists in a fresh settings object"));
        Check(Outgoing.Num()==Run.Before,TEXT("interface scaling sends no gameplay or inventory requests"));CloseOptions();
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Failure:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Failure));Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=3;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
