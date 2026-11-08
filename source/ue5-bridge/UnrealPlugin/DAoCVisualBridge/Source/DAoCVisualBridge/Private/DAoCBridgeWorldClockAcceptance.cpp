#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBox.h"

bool UDAoCBridgeSubsystem::TickWorldClockAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWorldClockTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Name){++Run.Checks;if(!Good)Run.Failures.Add(Name);};
    auto SetHour=[&](double Hour){auto Value=MakeShared<FJsonObject>();Value->SetBoolField(TEXT("ready"),true);Value->SetNumberField(TEXT("hour"),Hour);ApplyWorldClock(Value);if(ClassicTimeBox)ClassicTimeBox->UpdateAllAttributes();};
    if(Run.Phase==0){
        FString File,Text,Art;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeClockFixture="),File);FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeClockArt="),Art);
        Check(FFileHelper::LoadFileToString(Text,*File)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("original interface fixture loads"));
        if(Fixture){auto State=Fixture->GetObjectField(TEXT("classic_ui"));State->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedClock%lld"),FDateTime::UtcNow().GetTicks()));bLocalAvailable=true;ApplyWorldClock(nullptr);ApplyClassicUI(State);
            auto LoadArt=[&](){if(!Art.IsEmpty()){auto* Texture=FImageUtils::ImportFileAsTexture2D(Art);if(Texture){Texture->SRGB=true;Texture->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("timedisp"),Texture);}}RefreshWorldClock();};LoadArt();
            Check(ClassicArt(TEXT("timedisp"))!=nullptr,TEXT("original Time frame is available"));
            if(ClassicTimeBox)ClassicTimeBox->UpdateAllAttributes();
            Check(ClassicTimeBox&&ClassicTimeBox->GetVisibility()==EVisibility::Collapsed&&WorldClockText().IsEmpty(),TEXT("no invented time before original server clock"));
            const double Hours[]={0.,5.5,6.,12.,18.,23.99};const TCHAR* Labels[]={TEXT("00:00"),TEXT("05:30"),TEXT("06:00"),TEXT("12:00"),TEXT("18:00"),TEXT("23:59")};
            for(int32 I=0;I<6;++I){SetHour(Hours[I]);Check(WorldClockText()==Labels[I]&&ClassicTimeBox->GetVisibility()==EVisibility::Visible,TEXT("original 24 hour minute formatting"));}
            for(double Hour:{-1.,24.,1000.}){SetHour(Hour);Check(WorldClockText().IsEmpty()&&ClassicTimeBox->GetVisibility()==EVisibility::Collapsed,TEXT("invalid time clears stale display"));}
            auto Malformed=MakeShared<FJsonObject>();Malformed->SetStringField(TEXT("ready"),TEXT("true"));Malformed->SetNumberField(TEXT("hour"),12);ApplyWorldClock(Malformed);Check(WorldClockHour<0,TEXT("string readiness is not a server clock"));
            Malformed->SetBoolField(TEXT("ready"),true);Malformed->SetStringField(TEXT("hour"),TEXT("12:00"));ApplyWorldClock(Malformed);Check(WorldClockHour<0,TEXT("non numeric hour is rejected"));
            SetHour(12.);CameraYaw=113;Check(WorldClockText()==TEXT("12:00"),TEXT("camera orbit cannot alter world time"));
            ToggleRecoverableWindow(TEXT("time"));ClassicTimeBox->UpdateAllAttributes();Check(!bClassicTimeOpen&&ClassicTimeBox->GetVisibility()==EVisibility::Collapsed,TEXT("Windows page can hide Time"));
            ToggleRecoverableWindow(TEXT("time"));Check(RecoverableWindowOpen(TEXT("time")),TEXT("Windows page recovers Time"));
            ClassicTimePosition={300,180};bClassicTimeOpen=false;SaveClassicLayout();RemoveClassicUI();ClassicLayoutCharacter.Empty();ApplyClassicUI(State);LoadArt();
            Check(!bClassicTimeOpen&&ClassicTimePosition.Equals(FVector2D(300,180),.01),TEXT("Time position and visibility persist per character"));
            ResetWindowLayout();Check(bClassicTimeOpen&&ClassicTimePosition.Equals(FVector2D(127,0),.01),TEXT("layout reset restores original Time placement"));
            bLocalAvailable=false;ClassicTimeBox->UpdateAllAttributes();Check(ClassicTimeBox->GetVisibility()==EVisibility::Collapsed,TEXT("lobby cannot show last character's clock"));bLocalAvailable=true;SetHour(12.5);
        }
        Run.At=FPlatformTime::Seconds();Run.Phase=1;return true;
    }
    if(FPlatformTime::Seconds()-Run.At<1)return true;
    if(ClassicTimeBox){const auto Geometry=ClassicTimeBox->GetCachedGeometry();Check(Geometry.GetLocalSize().Equals(FVector2D(100,32),.1),TEXT("original Time logical dimensions"));Check(WorldPointerBlocked(Geometry.LocalToAbsolute(FVector2D(50,16))),TEXT("Time blocks world selection"));
        auto Widget=ClassicTimeBox->GetChildren()->GetChildAt(0);const auto Point=Geometry.LocalToAbsolute(FVector2D(3,3));TSet<FKey> Buttons{EKeys::LeftMouseButton};FPointerEvent Down(0,Point,Point,Buttons,EKeys::LeftMouseButton,0,FModifierKeysState());auto Reply=Widget->OnMouseButtonDown(Geometry,Down);Check(Reply.IsEventHandled()&&Reply.GetMouseCaptor().IsValid(),TEXT("original move handle requests drag capture"));Widget->OnMouseButtonUp(Geometry,Down);
        TSharedPtr<SButton> Close;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SButton"))Close=StaticCastSharedRef<SButton>(W);auto* Children=W->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(ClassicTimeBox.ToSharedRef());Check(Close.IsValid(),TEXT("original painted close cross has a real button"));if(Close){Close->SimulateClick();Check(!bClassicTimeOpen,TEXT("actual close button hides Time"));ToggleRecoverableWindow(TEXT("time"));}
        TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool Captured=FSlateApplication::Get().TakeScreenshot(ClassicTimeBox.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("actual original Time window captured"));
    }
    ApplyWorldClock(nullptr);Check(WorldClockText().IsEmpty(),TEXT("missing clock metadata clears previous session time"));
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
