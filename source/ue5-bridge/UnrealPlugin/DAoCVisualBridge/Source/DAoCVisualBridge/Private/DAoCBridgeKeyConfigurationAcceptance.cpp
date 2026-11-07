#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Application/IInputProcessor.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "ImageUtils.h"

bool UDAoCBridgeSubsystem::TickKeyConfigurationAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeKeyConfigurationTest="),Path))return false;
    static bool Done=false,Started=false;static double Began=0;static int32 Checks=0;static TArray<FString> Failures;
    if(Done)return true;auto Check=[&](bool V,const TCHAR* Name){++Checks;if(!V)Failures.Add(Name);};
    if(!Started){
        Started=true;Began=FPlatformTime::Seconds();LoadKeyConfiguration();FString Message;FBridgeKeyConfiguration K;FBridgeKeyConfiguration::FChord Chord;
        Check(K.Actions.Num()==10,TEXT("bounded ten actions match delivered movement and tracking"));
        for(const auto& A:K.Actions)Check(A.Bindings==A.Defaults&&FBridgeKeyConfiguration::Parse(A.Bindings[0],Chord),*FString::Printf(TEXT("valid unchanged default %s"),*A.Id));
        for(const FKey Key:{EKeys::Escape,EKeys::Tab,EKeys::Enter,EKeys::F11,EKeys::I,EKeys::C,EKeys::N,EKeys::One,EKeys::LeftMouseButton})Check(!K.Bind(TEXT("jump"),0,Key.GetFName().ToString(),Message),TEXT("fixed action cannot be shadowed"));
        Check(!K.Bind(TEXT("unknown"),0,TEXT("Q"),Message)&&!K.Bind(TEXT("jump"),2,TEXT("Q"),Message),TEXT("invalid action and slot rejected"));
        Check(!K.Bind(TEXT("jump"),0,TEXT("Ctrl+Ctrl+Q"),Message)&&!K.Bind(TEXT("jump"),0,TEXT("InventedKey"),Message),TEXT("malformed and unknown key rejected"));
        Check(K.Bind(TEXT("jump"),1,TEXT("Ctrl+Q"),Message)&&K.Text(TEXT("jump"),0)==TEXT("SpaceBar"),TEXT("second binding preserves first slot"));
        Check(K.Bind(TEXT("face"),0,TEXT("Ctrl+Q"),Message)&&K.Text(TEXT("jump"),1)==TEXT("-"),TEXT("exact conflicting chord moves from former action"));
        Check(!K.Bind(TEXT("move_forward"),0,TEXT("F"),Message),TEXT("held movement cannot overlap face or follow"));
        Check(K.Bind(TEXT("face"),0,TEXT(""),Message),TEXT("clear previous chord before assigning its held movement key"));
        Check(K.Bind(TEXT("move_forward"),0,TEXT("Q"),Message)&&K.Bind(TEXT("move_forward"),1,TEXT("ThumbMouseButton"),Message),TEXT("keyboard and gaming mouse movement bindings accepted"));
        Check(!K.Bind(TEXT("jump"),0,TEXT("Shift+Q"),Message),TEXT("held walking modifier cannot shadow another action"));
        FBridgeKeyConfiguration::Parse(TEXT("F"),Chord);Check(FBridgeKeyConfiguration::Matches(Chord,EKeys::F,false,false,false,false)&&!FBridgeKeyConfiguration::Matches(Chord,EKeys::F,true,false,false,false),TEXT("face and Shift follow press modifiers remain exact"));
        FBridgeKeyConfiguration::Parse(TEXT("Q"),Chord);Check(FBridgeKeyConfiguration::Matches(Chord,EKeys::Q,true,false,false,true)&&!FBridgeKeyConfiguration::Matches(Chord,EKeys::Q,false,true,false,true),TEXT("held Shift walks while Ctrl does not activate bare movement"));
        K.Path=KeyConfiguration->Path+TEXT(".roundtrip.ini");Check(K.Save(),TEXT("private changed configuration saves"));FBridgeKeyConfiguration Loaded;Loaded.Load(K.Path);Check(Loaded.Text(TEXT("move_forward"),0)==TEXT("Q")&&Loaded.Text(TEXT("move_forward"),1)==TEXT("ThumbMouseButton")&&Loaded.Text(TEXT("jump"),1)==TEXT("-"),TEXT("two slots and cleared slot survive reload"));
        FFileHelper::SaveStringToFile(TEXT("[Bindings]\nmove_forward0=Escape\n"),*(K.Path+TEXT(".invalid")));Loaded.Load(K.Path+TEXT(".invalid"));Check(Loaded.Text(TEXT("move_forward"),0)==TEXT("W"),TEXT("invalid saved map falls back as a whole"));
        FFileHelper::SaveStringToFile(TEXT("[Bindings]\nmove_forward0=F\n"),*(K.Path+TEXT(".conflict")));Loaded.Load(K.Path+TEXT(".conflict"));Check(Loaded.Text(TEXT("move_forward"),0)==TEXT("W"),TEXT("ambiguous saved held binding cannot bypass conflict gate"));
        FFileHelper::SaveStringToFile(TEXT("[Bindings]\nmove_forward0=S\nmove_back0=W\n"),*(K.Path+TEXT(".swap")));Loaded.Load(K.Path+TEXT(".swap"));Check(Loaded.Text(TEXT("move_forward"),0)==TEXT("S")&&Loaded.Text(TEXT("move_back"),0)==TEXT("W"),TEXT("valid complete movement swap reloads independently of defaults"));
        auto* PC=GetWorld()->GetFirstPlayerController();
        PC->InputKey(FInputKeyEventArgs(nullptr,FInputDeviceId::CreateFromInternalId(0),EKeys::Q,IE_Pressed,FPlatformTime::Cycles64()));PC->PlayerInput->ProcessInputStack({},1.f/60,false);Check(K.Pressed(PC,TEXT("move_forward"))&&K.Held(PC,TEXT("move_forward")),TEXT("actual player input uses remapped forward key"));PC->InputKey(FInputKeyEventArgs(nullptr,FInputDeviceId::CreateFromInternalId(0),EKeys::Q,IE_Released,FPlatformTime::Cycles64()));PC->PlayerInput->ProcessInputStack({},1.f/60,false);Check(!K.Held(PC,TEXT("move_forward")),TEXT("actual release stops remapped held action"));
        Check(!K.Held(nullptr,TEXT("move_forward"))&&!K.Pressed(nullptr,TEXT("jump")),TEXT("missing controller produces no action"));
        bControlsOptions=true;const int32 Before=Outgoing.Num();OpenOptions();Check(bOptionsOpen&&OptionsOverlay&&ClassicArt(TEXT("options")),TEXT("controls page reuses actual original options artwork"));
        Check(WorldPointerBlocked(FVector2D(10,10))&&!bMouseLook&&!bLeftPointerHeld&&!bRightPointerHeld,TEXT("options disables world gesture and movement input"));
        BindingCaptureAction=TEXT("jump");BindingCaptureSlot=0;
        FKeyEvent Escape(EKeys::Escape,FModifierKeysState(),0,false,0,0);Check(WorldPointerInput->HandleKeyDownEvent(FSlateApplication::Get(),Escape)&&BindingCaptureAction.IsEmpty()&&bOptionsOpen,TEXT("actual input preprocessor Esc cancels capture without closing options"));
        BindingCaptureAction=TEXT("jump");BindingCaptureSlot=0;FKeyEvent Q(EKeys::Q,FModifierKeysState(),0,false,0,0);Check(WorldPointerInput->HandleKeyDownEvent(FSlateApplication::Get(),Q)&&BindingCaptureAction.IsEmpty()&&KeyConfiguration->Text(TEXT("jump"),0)==TEXT("Q"),TEXT("actual input preprocessor captures and saves a new chord"));
        FBridgeKeyConfiguration Reloaded;Reloaded.Load(KeyConfiguration->Path);Check(Reloaded.Text(TEXT("jump"),0)==TEXT("Q"),TEXT("actual UI capture persists to its private file"));
        BindingCaptureAction=TEXT("jump");BindingCaptureSlot=0;Check(CaptureControlKey(EKeys::LeftShift,true,false,false)&&BindingCaptureAction==TEXT("jump"),TEXT("standalone modifier waits for the main key"));
        Check(CaptureControlKey(EKeys::F11,false,false,false)&&BindingCaptureAction==TEXT("jump"),TEXT("reserved camera key is consumed without changing view"));
        Check(CaptureControlKey(EKeys::RightMouseButton,false,false,false)&&KeyConfiguration->Text(TEXT("jump"),0)==TEXT("-"),TEXT("right click clears selected slot without world interaction"));
        KeyConfiguration->Reset();KeyConfiguration->Save();Check(KeyConfiguration->Text(TEXT("jump"),0)==TEXT("SpaceBar"),TEXT("restore returns delivered jump and dismount key"));
        const bool PreviousInvert=bInvertMouse;const float PreviousSensitivity=MouseSensitivity;bInvertMouse=true;MouseSensitivity=.6f;SaveControls();FString Saved;Check(FFileHelper::LoadFileToString(Saved,*ControlsFile)&&Saved.Contains(TEXT("invert_mouse"))&&Saved.Contains(TEXT("preserved_test_field")),TEXT("camera preferences save without discarding pre-existing settings fields"));bInvertMouse=PreviousInvert;MouseSensitivity=PreviousSensitivity;SaveControls();
        Check(Outgoing.Num()==Before,TEXT("configuration and capture send no gameplay or logout requests"));
    }
    if(FPlatformTime::Seconds()-Began<1)return true;
    TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size;bool Shot=OptionsOverlay&&FSlateApplication::Get().TakeScreenshot(OptionsOverlay.ToSharedRef(),Pixels,Size);if(Shot){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Shot=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Shot,TEXT("actual controls page screenshot captured"));
    Check(CloseOptions()&&!OptionsOverlay&&BindingCaptureAction.IsEmpty(),TEXT("closing removes page and pending capture"));
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);TArray<TSharedPtr<FJsonValue>> Rows;for(const auto& F:Failures)Rows.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Rows);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);
    Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
