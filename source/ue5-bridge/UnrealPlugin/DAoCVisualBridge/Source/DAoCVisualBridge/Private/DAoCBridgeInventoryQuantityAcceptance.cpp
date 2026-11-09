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
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Widgets/Input/SButton.h"

bool UDAoCBridgeSubsystem::TickInventoryQuantityAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeQuantityTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Label){++Run.Checks;if(!Good)Run.Failures.Add(Label);};
    auto Setup=[&](){CloseClassicQuantity();bLocalAvailable=true;bExiting=false;Session=TEXT("private-quantity-fixture");PlayerState.Reset();InventoryState=MakeShared<FJsonObject>();InventoryState->SetNumberField(TEXT("state_revision"),7);InventoryState->SetBoolField(TEXT("ready"),true);InventoryState->SetBoolField(TEXT("pending"),false);auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),40);Item->SetNumberField(TEXT("count"),10);Item->SetStringField(TEXT("name"),TEXT("Stack fixture"));Item->SetStringField(TEXT("token"),TEXT("original-stack"));InventoryState->SetArrayField(TEXT("items"),{MakeShared<FJsonValueObject>(Item)});};
    if(Run.Phase==0){
        Setup();Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Isolated quantity acceptance"),false);Outgoing.Empty();
        MoveClassicInventoryDrag(40,41,true);Check(ClassicQuantityValid()&&ClassicQuantityPanel.IsValid(),TEXT("shift drag opens original quantity chooser"));Check(ClassicQuantityMaximum==10&&ClassicQuantitySelected==1,TEXT("choice is bounded by original stack count"));Check(Outgoing.IsEmpty(),TEXT("opening chooser never sends a move"));
        CloseClassicQuantity();Check(Outgoing.IsEmpty()&&!ClassicQuantityCommand.IsValid(),TEXT("cancel discards choice without moving"));
        MoveClassicInventoryDrag(40,10,true);Check(!ClassicQuantityCommand.IsValid()&&Outgoing.IsEmpty(),TEXT("quantity chooser cannot equip or poison"));
        MoveClassicInventoryDrag(40,41,true);ClassicQuantitySelected=11;AcceptClassicQuantity();Check(Outgoing.IsEmpty(),TEXT("excess quantity rejected at accept"));
        MoveClassicInventoryDrag(40,41,true);InventoryState->SetNumberField(TEXT("state_revision"),8);AcceptClassicQuantity();Check(Outgoing.IsEmpty(),TEXT("stale revision cannot move replacement object"));
        Setup();MoveClassicInventoryDrag(40,41,true);Session=TEXT("different-session");AcceptClassicQuantity();Check(Outgoing.IsEmpty(),TEXT("session change invalidates chooser"));
        Setup();MoveClassicInventoryDrag(40,41,true);ClassicQuantitySelected=3;AcceptClassicQuantity();Check(!Outgoing.IsEmpty()&&!ClassicQuantityCommand.IsValid(),TEXT("accept sends one command and closes chooser"));
        FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Outgoing.GetData()),Outgoing.Num());FString Text(Converted.Length(),Converted.Get());TSharedPtr<FJsonObject> Command;const bool Parsed=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Command);Check(Parsed&&Command->GetStringField(TEXT("action"))==TEXT("inventory_move")&&Command->GetNumberField(TEXT("count"))==3&&Command->GetNumberField(TEXT("slot"))==40&&Command->GetNumberField(TEXT("to_slot"))==41,TEXT("accepted command carries exact original slots and count"));
        const int32 Bytes=Outgoing.Num();AcceptClassicQuantity();Check(Outgoing.Num()==Bytes,TEXT("second accept cannot duplicate command"));Outgoing.Empty();
        Setup();MoveClassicInventoryDrag(40,41,false);Check(!ClassicQuantityCommand.IsValid()&&!Outgoing.IsEmpty(),TEXT("normal drag keeps whole stack protocol"));Outgoing.Empty();
        MoveClassicInventoryDrag(40,41,true);Check(CloseClassicPanel()&&!ClassicQuantityCommand.IsValid()&&Outgoing.IsEmpty(),TEXT("Escape closes chooser before other panels"));
        MoveClassicInventoryDrag(40,41,true);InventoryState->SetNumberField(TEXT("state_revision"),9);ApplyInventory(InventoryState);Check(!ClassicQuantityCommand.IsValid(),TEXT("received inventory update cancels stale chooser"));
        Setup();MoveClassicInventoryDrag(40,41,true);Run.At=FPlatformTime::Seconds();Run.Phase=1;return true;
    }
    if(FPlatformTime::Seconds()-Run.At<1)return true;
    if(ClassicQuantityPanel){
        Check(ClassicQuantityPanel->GetCachedGeometry().GetLocalSize().Equals(FVector2D(128,96),.1),TEXT("original XML dimensions retained"));
        TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool Captured=FSlateApplication::Get().TakeScreenshot(ClassicQuantityPanel.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("original quantity window rendered"));
        TArray<TSharedPtr<SButton>> Buttons;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> Widget){if(Widget->GetTypeAsString()==TEXT("SButton"))Buttons.Add(StaticCastSharedRef<SButton>(Widget));auto Children=Widget->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(ClassicQuantityPanel.ToSharedRef());Check(Buttons.Num()==5,TEXT("close arrows accept cancel have actual buttons"));
        if(Buttons.Num()==5){Buttons[2]->SimulateClick();Check(ClassicQuantitySelected==2,TEXT("actual increment button changes quantity"));Buttons[4]->SimulateClick();Check(!ClassicQuantityCommand.IsValid()&&Outgoing.IsEmpty(),TEXT("actual cancel button sends nothing"));}
    }else Check(false,TEXT("quantity panel survives to render"));
    CloseClassicQuantity();if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Outgoing.Empty();Session.Empty();bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);Report->SetBoolField(TEXT("server_started"),false);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
