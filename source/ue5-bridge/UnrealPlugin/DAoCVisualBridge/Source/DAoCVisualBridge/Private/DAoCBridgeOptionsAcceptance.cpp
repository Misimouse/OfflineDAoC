#include "DAoCBridgeSubsystem.h"
#include "Camera/CameraActor.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickOptionsAudioAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeOptionsAudioTest="),Path))return false;
    struct FRun{bool Started=false,Done=false;double Began=0;int32 Checks=0;TArray<FString> Failures;};static FRun Run;
    if(Run.Done)return true;
    auto Check=[&](bool Value,const TCHAR* Name){++Run.Checks;if(!Value)Run.Failures.Add(Name);};
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;const int32 Before=Outgoing.Num();
        LoadAudioSettings();float ExpectedMaster=1,ExpectedEffects=1;
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeExpectedMaster="),ExpectedMaster);FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeExpectedEffects="),ExpectedEffects);
        Check(FMath::IsNearlyEqual(AudioMasterVolume,ExpectedMaster)&&FMath::IsNearlyEqual(AudioEffectsVolume,ExpectedEffects),TEXT("new process loads the previously saved volume preferences"));
        SetAudioVolume(true,1);SetAudioVolume(false,1);OpenOptions();
        Check(bOptionsOpen&&OptionsOverlay.IsValid(),TEXT("original options window opens without a world login"));
        Check(ClassicArt(TEXT("options"))!=nullptr,TEXT("original options artwork loads"));
        Check(WorldPointerBlocked(FVector2D(10,10)),TEXT("options blocks world pointer input even outside its panel"));
        Check(!bMouseLook&&!bLeftPointerHeld&&!bRightPointerHeld,TEXT("options releases captured camera and movement buttons"));
        Check(Outgoing.Num()==Before,TEXT("opening options cannot send logout or gameplay requests"));
        SetAudioVolume(true,.4);SetAudioVolume(false,.5);bAudioSettingsLoaded=false;AudioMasterVolume=AudioEffectsVolume=1;LoadAudioSettings();
        Check(FMath::IsNearlyEqual(AudioMasterVolume,.4f)&&FMath::IsNearlyEqual(AudioEffectsVolume,.5f),TEXT("both volume preferences persist and reload"));
        FString Saved;Check(FFileHelper::LoadFileToString(Saved,*AudioSettingsPath)&&Saved.Contains(TEXT("Master="))&&Saved.Contains(TEXT("Effects=")),TEXT("volume preferences are written to the private settings file"));
        SetAudioVolume(true,2);SetAudioVolume(false,-1);
        Check(AudioMasterVolume==1&&AudioEffectsVolume==0,TEXT("volumes clamp to the valid range"));
        SetAudioVolume(true,1);SetAudioVolume(false,1);
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();if(auto* PC=GetWorld()->GetFirstPlayerController())PC->SetViewTarget(Camera);
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),TEXT("private-options-audio"));auto E=MakeShared<FJsonObject>();
        E->SetNumberField(TEXT("seq"),1);E->SetNumberField(TEXT("age_ms"),0);E->SetStringField(TEXT("owner"),TEXT("qa:audio"));E->SetStringField(TEXT("sheet"),TEXT("weapons"));E->SetNumberField(TEXT("set"),25);E->SetStringField(TEXT("event"),TEXT("use"));
        E->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(1364),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});Snapshot->SetArrayField(TEXT("combat_audio"),{MakeShared<FJsonValueObject>(E)});
        ApplySpellAudio(Snapshot);TickSpellAudio();const double Base=SpellAudioReport()->GetNumberField(TEXT("max_voice_volume"));
        Check(Base>0&&SpellAudioReport()->GetNumberField(TEXT("played_clips"))==1,TEXT("original audio produces an actual voice before volume adjustments"));
        SetAudioVolume(true,0);TickSpellAudio();Check(SpellAudioReport()->GetNumberField(TEXT("max_voice_volume"))==0,TEXT("master zero mutes an already playing voice"));
        SetAudioVolume(true,.5);SetAudioVolume(false,.5);TickSpellAudio();
        Check(FMath::IsNearlyEqual(SpellAudioReport()->GetNumberField(TEXT("max_voice_volume")),Base*.25,1e-5),TEXT("master and effects multiply the live source gain"));
        SetAudioVolume(true,1);SetAudioVolume(false,1);
    }
    TickSpellAudio();
    if(Now-Run.Began>1){
        Check(SpellAudioReport()->GetNumberField(TEXT("pcm_consumed_bytes"))>0,TEXT("audio engine consumes original PCM with preferences applied"));
        TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size;
        bool Captured=OptionsOverlay&&FSlateApplication::Get().TakeScreenshot(OptionsOverlay.ToSharedRef(),Pixels,Size);
        int32 VisiblePixels=0;for(const auto& Pixel:Pixels)VisiblePixels+=FMath::Max3(Pixel.R,Pixel.G,Pixel.B)>20;
        Captured=Captured&&VisiblePixels>1000;if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}
        Check(Captured,TEXT("options screenshot captured from the actual viewport"));
        const int32 Before=Outgoing.Num();Check(CloseOptions()&&!bOptionsOpen&&!OptionsOverlay,TEXT("close resumes the world without exiting"));
        Check(Outgoing.Num()==Before,TEXT("closing options does not send logout"));ClearSpellAudio();
        Check(SpellAudioReport()->GetNumberField(TEXT("active_voices"))==0,TEXT("normal audio cleanup remains effective"));
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);
        TArray<TSharedPtr<FJsonValue>> Failures;for(auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("server_started"),false);Report->SetNumberField(TEXT("pcm_consumed_bytes"),SpellAudioReport()->GetNumberField(TEXT("pcm_consumed_bytes")));
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);
        Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
