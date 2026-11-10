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
#include "SocketSubsystem.h"
#include "Sockets.h"

bool UDAoCBridgeSubsystem::TickKeyConfigurationAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeKeyConfigurationTest="),Path))return false;
    static bool Done=false,Started=false;static double Began=0;static int32 Checks=0;static TArray<FString> Failures;
    if(Done)return true;auto Check=[&](bool V,const TCHAR* Name){++Checks;if(!V)Failures.Add(Name);};
    if(!Started){
        Started=true;Began=FPlatformTime::Seconds();LoadKeyConfiguration();FString Message;FBridgeKeyConfiguration K;FBridgeKeyConfiguration::FChord Chord;
        if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeMovementBindingsMigrationTest"))){
            Check(KeyConfiguration->Text(TEXT("move_forward"),0)==TEXT("Q")&&KeyConfiguration->Text(TEXT("jump"),0)==TEXT("SpaceBar"),TEXT("earlier movement-only binding file preserves custom and default movement"));
            Check(KeyConfiguration->Text(TEXT("show_inventory"),0)==TEXT("I")&&KeyConfiguration->Text(TEXT("qb3_10"),0)==TEXT("Ctrl+Zero"),TEXT("new actions receive defaults without discarding saved movement"));
            KeyConfiguration->Reset();
        }
        Check(K.Actions.Num()==73,TEXT("73 supported actions include server-authorized sprint and weapon selection"));
        for(const auto& A:K.Actions)Check(A.Bindings==A.Defaults&&(A.Bindings[0].IsEmpty()||FBridgeKeyConfiguration::Parse(A.Bindings[0],Chord)),*FString::Printf(TEXT("valid unchanged default %s"),*A.Id));
        for(const FKey Key:{EKeys::Escape,EKeys::Enter,EKeys::F11,EKeys::F1,EKeys::F2,EKeys::F3,EKeys::F4,EKeys::F5,EKeys::LeftMouseButton})Check(!K.Bind(TEXT("jump"),0,Key.GetFName().ToString(),Message),TEXT("fixed action cannot be shadowed"));
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
        FString FixturePath;
        if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInterfaceKeysFixture="),FixturePath)){
            FString FixtureText;TSharedPtr<FJsonObject> Fixture;
            Check(FFileHelper::LoadFileToString(FixtureText,*FixturePath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(FixtureText),Fixture)&&Fixture.IsValid(),TEXT("private original UI fixture loads"));
            if(Fixture.IsValid()){
                Fixture->GetObjectField(TEXT("classic_ui"))->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedInterfaceKeys%lld"),FDateTime::UtcNow().GetTicks()));
                ApplyInventory(Fixture->GetObjectField(TEXT("inventory")));ApplyPlayerStatus(Fixture->GetObjectField(TEXT("player_status")));ApplyClassicUI(Fixture->GetObjectField(TEXT("classic_ui")));CloseClassicTrainer();
                Session=TEXT("isolated-interface-keys");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Isolated keys capture"),false);Outgoing.Empty();KeyConfiguration->Reset();
                auto Press=[&](const FString& Binding){PC->PlayerInput->FlushPressedKeys();PC->PlayerInput->ProcessInputStack({},1.f/60,false);FBridgeKeyConfiguration::FChord C;Check(FBridgeKeyConfiguration::Parse(Binding,C),TEXT("native dispatch chord parses"));
                    auto Down=[&](FKey Key){PC->InputKey(FInputKeyEventArgs(nullptr,FInputDeviceId::CreateFromInternalId(0),Key,IE_Pressed,FPlatformTime::Cycles64()));};
                    if(C.Shift)Down(EKeys::LeftShift);if(C.Ctrl)Down(EKeys::LeftControl);if(C.Alt)Down(EKeys::LeftAlt);Down(C.Key);PC->PlayerInput->ProcessInputStack({},1.f/60,false);
                };
                auto Capture=[&](const TCHAR* Action){Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> V;
                    Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),V)&&V.IsValid()&&V->GetStringField(TEXT("action"))==Action,TEXT("exactly one original UI command dispatched"));return V;
                };
                for(int32 Bar=0;Bar<3;++Bar)for(int32 Slot=0;Slot<10;++Slot){Press(KeyConfiguration->Text(FString::Printf(TEXT("qb%d_%d"),Bar+1,Slot+1),0));UpdateClassicInput();auto V=Capture(TEXT("ui_use_slot"));if(V)Check(V->GetIntegerField(TEXT("bar"))==Bar&&V->GetIntegerField(TEXT("slot"))==Slot,TEXT("original bar and slot indices preserved"));}
                for(int32 Bank=0;Bank<10;++Bank){Press(KeyConfiguration->Text(FString::Printf(TEXT("qbank_%d"),Bank+1),0));UpdateClassicInput();auto V=Capture(TEXT("ui_bank"));if(V)Check(V->GetIntegerField(TEXT("bar"))==0&&V->GetIntegerField(TEXT("bank"))==Bank,TEXT("Shift bank does not execute a quickbar action"));}
                Check(KeyConfiguration->Bind(TEXT("qb2_4"),0,TEXT("Ctrl+Q"),Message),TEXT("quickbar action accepts changed chord"));Press(TEXT("Ctrl+Q"));UpdateClassicInput();auto Changed=Capture(TEXT("ui_use_slot"));if(Changed)Check(Changed->GetIntegerField(TEXT("bar"))==1&&Changed->GetIntegerField(TEXT("slot"))==3,TEXT("remapped chord keeps authoritative quickbar indices"));
                Press(TEXT("Alt+Four"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("former quickbar chord no longer activates"));
                for(const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("P"),TEXT("character")},{TEXT("H"),TEXT("skills")},{TEXT("J"),TEXT("combat")},{TEXT("G"),TEXT("group")}}){Press(Pair.Key);UpdateClassicInput();Check(ClassicTab==Pair.Value&&bClassicOpen,TEXT("actual existing window action retains original sheet"));}
                if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeWeaponSprintTest"))){
                    auto PreviousInventory=InventoryState;InventoryState=MakeShared<FJsonObject>();InventoryState->SetBoolField(TEXT("ready"),true);InventoryState->SetNumberField(TEXT("state_revision"),5);
                    TArray<TSharedPtr<FJsonValue>> WeaponItems;for(int32 Slot:{10,12,13}){auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),Slot);Item->SetStringField(TEXT("token"),FString::Printf(TEXT("item-%d"),Slot));WeaponItems.Add(MakeShared<FJsonValueObject>(Item));}InventoryState->SetArrayField(TEXT("items"),WeaponItems);
                    auto Vitals=PlayerState->GetObjectField(TEXT("vitals"));Vitals->SetBoolField(TEXT("alive"),true);PlayerState->SetBoolField(TEXT("ready"),true);PlayerState->SetNumberField(TEXT("generation"),7);
                    for(const auto& Pair:TArray<TPair<FString,FString>>{{TEXT("B"),TEXT("standard")},{TEXT("Shift+B"),TEXT("twohand")},{TEXT("Comma"),TEXT("ranged")}}){Press(Pair.Key);UpdatePlayerStatusInput();auto V=Capture(TEXT("weapon_select"));if(V){Check(V->GetStringField(TEXT("mode"))==Pair.Value&&V->GetIntegerField(TEXT("inventory_revision"))==5&&V->GetIntegerField(TEXT("player_generation"))==7,TEXT("weapon shortcut carries current server state identity"));Check(!V->GetStringField(TEXT("item_token")).IsEmpty(),TEXT("weapon shortcut pins current item token"));}}
                    Press(TEXT("V"));UpdatePlayerStatusInput();auto Sprint=Capture(TEXT("player_sprint"));if(Sprint)Check(Sprint->GetIntegerField(TEXT("player_generation"))==7,TEXT("sprint shortcut uses current character"));
                    Check(KeyConfiguration->Bind(TEXT("weapon_right"),0,TEXT("Ctrl+B"),Message),TEXT("weapon shortcut is editable"));Press(TEXT("Ctrl+B"));UpdatePlayerStatusInput();Capture(TEXT("weapon_select"));
                    Press(TEXT("B"));UpdatePlayerStatusInput();Check(Outgoing.IsEmpty(),TEXT("old weapon binding is inactive"));
                    Press(TEXT("V"));bChatOpen=true;UpdatePlayerStatusInput();Check(Outgoing.IsEmpty(),TEXT("typing suppresses sprint"));bChatOpen=false;
                    Press(TEXT("V"));bOptionsOpen=true;UpdatePlayerStatusInput();Check(Outgoing.IsEmpty(),TEXT("menu suppresses sprint"));bOptionsOpen=false;
                    Vitals->SetBoolField(TEXT("alive"),false);Press(TEXT("V"));UpdatePlayerStatusInput();Check(Outgoing.IsEmpty(),TEXT("dead character cannot sprint"));Vitals->SetBoolField(TEXT("alive"),true);
                    InventoryState->SetArrayField(TEXT("items"),{});Press(TEXT("Ctrl+B"));UpdatePlayerStatusInput();Check(Outgoing.IsEmpty(),TEXT("empty weapon slot cannot fabricate an item"));
                    InventoryState=PreviousInventory;KeyConfiguration->Reset();Vitals->RemoveField(TEXT("alive"));
                }
                Check(KeyConfiguration->Bind(TEXT("show_spells"),0,TEXT("B"),Message),TEXT("unassigned magic window accepts optional shortcut"));Press(TEXT("B"));UpdateClassicInput();Check(ClassicTab==TEXT("magic"),TEXT("magic shortcut opens original magic sheet"));
                Press(TEXT("F7"));UpdateClassicInput();Capture(TEXT("target_self"));
                Press(TEXT("One"));bChatOpen=true;UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("typing suppresses actual quickbar dispatch"));bChatOpen=false;
                Press(TEXT("One"));bOptionsOpen=true;UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("options suppresses actual quickbar dispatch"));bOptionsOpen=false;
                auto Vitals=PlayerState->GetObjectField(TEXT("vitals"));Vitals->SetNumberField(TEXT("health_pct"),0);Press(TEXT("One"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("dead character cannot execute ordinary quickbar slot"));
                auto Slot=ClassicSlot(0,0);if(Slot){Slot->SetStringField(TEXT("kind"),TEXT("macro"));Press(TEXT("One"));UpdateClassicInput();Capture(TEXT("ui_use_slot"));Slot->RemoveField(TEXT("kind"));}Vitals->SetNumberField(TEXT("health_pct"),100);
                PC->PlayerInput->FlushPressedKeys();KeyConfiguration->Reset();RemoveClassicUI();RemovePlayerStatusUI();RemoveInventoryUI();Outgoing.Empty();Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();bLocalAvailable=false;
            }
        }
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
