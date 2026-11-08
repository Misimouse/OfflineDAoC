#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Widgets/Layout/SBox.h"
#include "Framework/Application/SlateApplication.h"
#include "UnrealClient.h"

bool UDAoCBridgeSubsystem::TickCompassAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCompassTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;TSharedPtr<FJsonObject> State;FVector2D Position;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Name){++Run.Checks;if(!Good)Run.Failures.Add(Name);};
    if(Run.Phase==0){
        FString File,Text;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCompassFixture="),File);
        Check(FFileHelper::LoadFileToString(Text,*File)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("original interface fixture loads"));
        if(Fixture){Run.State=Fixture->GetObjectField(TEXT("classic_ui"));Run.State->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedCompass%lld"),FDateTime::UtcNow().GetTicks()));bLocalAvailable=true;ApplyClassicUI(Run.State);
            FString Art;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCompassArt="),Art);
            if(!Art.IsEmpty()){auto* Texture=FImageUtils::ImportFileAsTexture2D(Art);if(Texture){Texture->SRGB=true;Texture->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("compass_bar"),Texture);}}RefreshCompass();
            Check(ClassicArt(TEXT("compass_bar"))!=nullptr,TEXT("original letter-strip artwork is available"));
            Check(ClassicCompassBox&&ClassicCompassBox->GetVisibility()==EVisibility::Visible,TEXT("compass defaults visible in world"));
            PlayerPawn=GetWorld()->SpawnActor<ADAoCBridgeCharacter>(FVector::ZeroVector,FRotator::ZeroRotator);
            Check(IsValid(PlayerPawn),TEXT("heading uses actual native character"));
            if(PlayerPawn){for(int32 I=0;I<8;++I){PlayerPawn->SetActorRotation(FRotator(0,I*45.-90,0));Check(FMath::IsNearlyEqual(CompassDegrees(),I*45.,.001),TEXT("all original compass directions follow character facing"));}
                PlayerPawn->SetActorRotation(FRotator(0,-90.01,0));Check(FMath::IsNearlyEqual(CompassDegrees(),359.99,.01),TEXT("north wrap has no reversed jump"));
                PlayerPawn->SetActorRotation(FRotator(0,-90,0));CameraYaw=135;Check(FMath::IsNearlyZero(CompassDegrees(),.001),TEXT("orbiting camera leaves character compass north"));}
            FBridgeKeyConfiguration Keys;auto* Key=Keys.Find(TEXT("show_compass"));Check(Key&&Key->Defaults[0]==TEXT("Ctrl+C"),TEXT("original Ctrl C shortcut remains editable"));
            Run.Position=ClassicCompassPosition;ToggleCompass();ClassicCompassBox->UpdateAllAttributes();Check(!bClassicCompassOpen&&ClassicCompassBox->GetVisibility()==EVisibility::Collapsed,TEXT("local toggle hides compass"));
            ToggleRecoverableWindow(TEXT("compass"));Check(RecoverableWindowOpen(TEXT("compass"))&&ClassicCompassPosition.Equals(Run.Position),TEXT("Windows recovery reopens retained compass position"));
            ClassicCompassPosition={140,180};bClassicCompassOpen=false;SaveClassicLayout();RemoveClassicUI();ClassicLayoutCharacter.Empty();ApplyClassicUI(Run.State);
            Check(!bClassicCompassOpen&&ClassicCompassPosition.Equals({140,180},.01),TEXT("visibility and position survive interface reconstruction"));
            ResetWindowLayout();const auto Extent=UIViewportSize()/ClassicScale();Check(bClassicCompassOpen&&ClassicCompassPosition.Equals({Extent.X*.5-56,Extent.Y-107},.01),TEXT("Reset Window Layout restores compass defaults"));
            bLocalAvailable=false;ClassicCompassBox->UpdateAllAttributes();Check(ClassicCompassBox->GetVisibility()==EVisibility::Collapsed,TEXT("lobby or absent player never displays a stale compass"));bLocalAvailable=true;
            // Private texture injection is lost on reconstruction; reload only in this isolated test.
            if(!Art.IsEmpty()){auto* Texture=FImageUtils::ImportFileAsTexture2D(Art);if(Texture){Texture->SRGB=true;Texture->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("compass_bar"),Texture);}}RefreshCompass();
        }
        Run.At=FPlatformTime::Seconds();Run.Phase=1;return true;
    }
    if(FPlatformTime::Seconds()-Run.At<1)return true;
    if(ClassicCompassBox){const auto Geometry=ClassicCompassBox->GetCachedGeometry();Check(Geometry.GetLocalSize().Equals(FVector2D(112,22),.1),TEXT("original compass logical dimensions retained"));const auto Point=Geometry.LocalToAbsolute(FVector2D(56,10));Check(WorldPointerBlocked(Point),TEXT("compass intercepts clicks instead of selecting world objects"));
        auto Widget=ClassicCompassBox->GetChildren()->GetChildAt(0);TSet<FKey> Buttons{EKeys::LeftMouseButton};FPointerEvent Down(0,Point,Point,Buttons,EKeys::LeftMouseButton,0,FModifierKeysState());auto Reply=Widget->OnMouseButtonDown(Geometry,Down);Check(Reply.IsEventHandled()&&Reply.GetMouseCaptor().IsValid(),TEXT("entire compass requests drag capture"));Widget->OnMouseButtonUp(Geometry,Down);
        TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool Captured=FSlateApplication::Get().TakeScreenshot(ClassicCompassBox.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("actual original compass widget captured"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
