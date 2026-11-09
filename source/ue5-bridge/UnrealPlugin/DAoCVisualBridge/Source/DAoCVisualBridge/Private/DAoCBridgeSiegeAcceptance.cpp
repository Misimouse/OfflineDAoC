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
#include "Widgets/Text/STextBlock.h"

bool UDAoCBridgeSubsystem::TickSiegeAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSiegeTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;TSharedPtr<FJsonObject> Classic,State;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Label){++Run.Checks;if(!Good)Run.Failures.Add(Label);};
    auto TextOf=[](TSharedRef<SWidget> Root){FString Text;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("STextBlock"))Text+=StaticCastSharedRef<STextBlock>(W)->GetText().ToString()+TEXT("\n");auto C=W->GetChildren();for(int32 I=0;I<C->Num();++I)Visit(C->GetChildAt(I));};Visit(Root);return Text;};
    auto Buttons=[&](){TArray<TSharedPtr<SButton>> Found;if(SiegePanel){TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SButton"))Found.Add(StaticCastSharedRef<SButton>(W));auto C=W->GetChildren();for(int32 I=0;I<C->Num();++I)Visit(C->GetChildAt(I));};Visit(SiegePanel.ToSharedRef());}return Found;};
    auto Click=[&](const FString& Label){for(auto B:Buttons())if(TextOf(B.ToSharedRef()).TrimStartAndEnd()==Label){B->SimulateClick();return true;}return false;};
    auto Command=[&](){FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Outgoing.GetData()),Outgoing.Num());FString Text(Converted.Length(),Converted.Get());TSharedPtr<FJsonObject> V;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),V);Outgoing.Empty();return V;};
    if(Run.Phase==0){
        FString F,Text;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSiegeFixture="),F);Check(FFileHelper::LoadFileToString(Text,*F)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("original classic fixture loads"));
        if(Fixture){Run.Classic=Fixture->GetObjectField(TEXT("classic_ui"));Run.Classic->SetStringField(TEXT("character"),FString::Printf(TEXT("PrivateSiege%lld"),FDateTime::UtcNow().GetTicks()));bLocalAvailable=true;ApplyClassicUI(Run.Classic);}
        ApplySiege(nullptr);Check(!SiegePanel&&!bSiegeOpen,TEXT("no siege interface without server control"));
        Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private siege acceptance"),false);Session=TEXT("private-siege-fixture");Outgoing.Empty();
        Run.State=MakeShared<FJsonObject>();Run.State->SetNumberField(TEXT("revision"),1);Run.State->SetBoolField(TEXT("visible"),true);Run.State->SetBoolField(TEXT("controlled"),true);Run.State->SetNumberField(TEXT("time_left"),5);
        auto W=MakeShared<FJsonObject>();W->SetNumberField(TEXT("oid"),37);W->SetStringField(TEXT("name"),TEXT("Field ballista (Inactive)"));W->SetNumberField(TEXT("action"),2);W->SetBoolField(TEXT("can_move"),true);auto A=MakeShared<FJsonObject>();A->SetNumberField(TEXT("index"),2);A->SetNumberField(TEXT("count"),4);A->SetStringField(TEXT("name"),TEXT("Ballista bolt"));W->SetArrayField(TEXT("ammo"),{MakeShared<FJsonValueObject>(A)});Run.State->SetObjectField(TEXT("weapon"),W);ApplySiege(Run.State);
        Check(SiegePanel&&bSiegeOpen,TEXT("server control opens original siege window"));Check(Buttons().Num()==11,TEXT("original nine commands plus ammo row and painted close"));Check(SiegeAmmoIndex==2,TEXT("original ammunition index selected without renumbering"));Run.Phase=1;Run.At=FPlatformTime::Seconds();return true;
    }
    if(FPlatformTime::Seconds()-Run.At<1)return true;
    Check(SiegePanel&&SiegePanel->GetCachedGeometry().GetLocalSize().Equals(FVector2D(210,196),.1),TEXT("original siege window dimensions"));Check(SiegePanel&&WorldPointerBlocked(SiegePanel->GetCachedGeometry().LocalToAbsolute(FVector2D(100,90))),TEXT("siege window blocks world selection and wheel"));Check(SiegePanel&&TextOf(SiegePanel.ToSharedRef()).Contains(TEXT("ARMING")),TEXT("original server action shown"));
    TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool Captured=SiegePanel&&FSlateApplication::Get().TakeScreenshot(SiegePanel.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("original frame and ammunition captured"));
    const TCHAR* Labels[]={TEXT("LOAD"),TEXT("ARM"),TEXT("AIM"),TEXT("FIRE"),TEXT("MOVE"),TEXT("STOP"),TEXT("REPAIR"),TEXT("SALVAGE"),TEXT("RELEASE")};const int32 Ids[]={1,2,3,4,5,9,6,7,8};
    for(int32 I=0;I<9;++I){bool Clicked=Click(Labels[I]);auto V=Command();Check(Clicked&&V&&V->GetStringField(TEXT("action"))==TEXT("siege_command")&&V->GetNumberField(TEXT("command"))==Ids[I]&&V->GetNumberField(TEXT("ammo"))==(I==0?2:0)&&V->GetNumberField(TEXT("oid"))==37&&V->GetNumberField(TEXT("revision"))==1,TEXT("actual original command delegate preserves weapon revision and ammo"));}
    Check(SiegePanel&&bSiegeOpen,TEXT("RELEASE click waits for authoritative server close"));
    auto OldArm=Buttons().Num()==11?Buttons()[3]:TSharedPtr<SButton>();auto All=Buttons();if(All.Num()==11)All[0]->SimulateClick();auto Hide=Command();Check(!SiegePanel&&!bSiegeOpen&&Hide&&Hide->GetStringField(TEXT("action"))==TEXT("siege_hide"),TEXT("painted close hides without sending release"));
    Run.State->SetNumberField(TEXT("revision"),2);Run.State->SetBoolField(TEXT("visible"),false);ApplySiege(Run.State);SubmitChat(TEXT("/siege"));Check(SiegePanel&&bSiegeOpen,TEXT("siege command reopens a hidden controlled window without taking new control"));
    Run.State->SetNumberField(TEXT("revision"),3);Run.State->SetBoolField(TEXT("visible"),true);ApplySiege(Run.State);Check(SiegePanel&&bSiegeOpen,TEXT("new original update reopens hidden siege window"));
    if(OldArm)OldArm->SimulateClick();Check(Outgoing.IsEmpty(),TEXT("detached stale window button cannot act on a newer control revision"));
    Run.State->SetNumberField(TEXT("revision"),4);Run.State->SetBoolField(TEXT("controlled"),false);Run.State->SetBoolField(TEXT("visible"),false);ApplySiege(Run.State);Check(!SiegePanel&&!bSiegeOpen,TEXT("original server close removes siege interface"));
    SiegePosition={150,80};SaveClassicLayout();RemoveClassicUI();ClassicLayoutCharacter.Empty();ApplyClassicUI(Run.Classic);Check(SiegePosition.Equals(FVector2D(150,80),.1),TEXT("siege position saved per character"));Check(!SiegeState&&SiegeRevision==-1,TEXT("character cleanup discards prior siege identity"));
    RemoveClassicUI();if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Outgoing.Empty();Session.Empty();bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);Report->SetBoolField(TEXT("server_started"),false);TArray<TSharedPtr<FJsonValue>> Failures;for(auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
