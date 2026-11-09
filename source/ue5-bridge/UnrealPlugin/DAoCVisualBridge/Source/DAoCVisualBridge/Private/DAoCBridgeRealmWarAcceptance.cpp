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

bool UDAoCBridgeSubsystem::TickRealmWarAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRealmWarTest="),Path))return false;
    struct FRun{int32 Phase=0,Checks=0;double At=0;TArray<FString> Failures;TSharedPtr<FJsonObject> Classic,State;};static FRun Run;if(Run.Phase==99)return true;
    auto Check=[&](bool Good,const TCHAR* Label){++Run.Checks;if(!Good)Run.Failures.Add(Label);};
    auto TextOf=[](TSharedRef<SWidget> Root){FString Text;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> Widget){if(Widget->GetTypeAsString()==TEXT("STextBlock"))Text+=StaticCastSharedRef<STextBlock>(Widget)->GetText().ToString()+TEXT("\n");auto Children=Widget->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(Root);return Text;};
    auto Buttons=[&](){TArray<TSharedPtr<SButton>> Found;if(RealmWarPanel){TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> Widget){if(Widget->GetTypeAsString()==TEXT("SButton"))Found.Add(StaticCastSharedRef<SButton>(Widget));auto Children=Widget->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};Visit(RealmWarPanel.ToSharedRef());}return Found;};
    auto Click=[&](const FString& Label){for(auto Button:Buttons())if(TextOf(Button.ToSharedRef()).TrimStartAndEnd()==Label){Button->SimulateClick();return true;}return false;};
    auto Capture=[&](const TCHAR* Suffix){TArray<FColor> Pixels;TArray<uint8> Bytes;FIntVector Size=FIntVector::ZeroValue;bool OK=RealmWarPanel.IsValid()&&FSlateApplication::Get().TakeScreenshot(RealmWarPanel.ToSharedRef(),Pixels,Size);if(OK){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);OK=FFileHelper::SaveArrayToFile(Bytes,*(Path+Suffix));}return OK;};
    auto Command=[&](){FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Outgoing.GetData()),Outgoing.Num());FString Text(Converted.Length(),Converted.Get());TSharedPtr<FJsonObject> Value;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Value);return Value;};
    if(Run.Phase==0){
        FString FixturePath,Text;TSharedPtr<FJsonObject> Fixture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRealmWarFixture="),FixturePath);Check(FFileHelper::LoadFileToString(Text,*FixturePath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("original classic interface fixture loads"));
        if(Fixture){Run.Classic=Fixture->GetObjectField(TEXT("classic_ui"));Run.Classic->SetStringField(TEXT("character"),FString::Printf(TEXT("IsolatedRealmWar%lld"),FDateTime::UtcNow().GetTicks()));bLocalAvailable=true;ApplyClassicUI(Run.Classic);}
        LoadRealmWarData();Check(RealmWarData.IsValid(),TEXT("original map data available"));
        Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Isolated realm-war acceptance"),false);Session=TEXT("private-realm-war-fixture");Outgoing.Empty();
        Run.State=MakeShared<FJsonObject>();Run.State->SetNumberField(TEXT("revision"),1);Run.State->SetBoolField(TEXT("pending"),false);Run.State->SetObjectField(TEXT("pages"),MakeShared<FJsonObject>());ApplyRealmWar(Run.State);ToggleRealmWar();
        Check(bRealmWarOpen&&RealmWarPanel.IsValid()&&RealmWarPage==3,TEXT("original realm-war window opens on Hibernia"));Check(RealmWarPanel&&TextOf(RealmWarPanel.ToSharedRef()).Contains(TEXT("OWNERSHIP UNKNOWN")),TEXT("static atlas defaults are not current keep ownership"));
        auto Request=Command();Check(Request&&Request->GetStringField(TEXT("action"))==TEXT("warmap_request")&&Request->GetNumberField(TEXT("page"))==3,TEXT("opening sends read-only page request"));Outgoing.Empty();
        Check(Buttons().Num()==5,TEXT("original close three tabs and Update are actual buttons"));Run.Phase=1;Run.At=FPlatformTime::Seconds();return true;
    }
    if(FPlatformTime::Seconds()-Run.At<1)return true;
    if(Run.Phase==1){
        Check(RealmWarPanel&&WorldPointerBlocked(RealmWarPanel->GetCachedGeometry().LocalToAbsolute(FVector2D(150,100))),TEXT("map panel blocks world selection and camera wheel"));
        Check(RealmWarPanel&&RealmWarPanel->GetCachedGeometry().GetLocalSize().Equals(FVector2D(342,458),.1),TEXT("original Hibernia window dimensions"));Check(Capture(TEXT(".hib-unknown.png")),TEXT("original Hibernia atlas rendered"));
        auto Pages=MakeShared<FJsonObject>();for(int32 Page=1;Page<=3;++Page){auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("ready"),true);auto Keeps=MakeShared<FJsonObject>();auto Keep=MakeShared<FJsonObject>();Keep->SetNumberField(TEXT("realm"),Page);Keep->SetBoolField(TEXT("claimed"),true);Keep->SetStringField(TEXT("guild"),TEXT("Original fixture guild"));Keep->SetBoolField(TEXT("siege"),true);Keeps->SetObjectField(FString::FromInt((Page+1)*25),Keep);State->SetObjectField(TEXT("keeps"),Keeps);TArray<TSharedPtr<FJsonValue>> Relics;for(int32 I=0;I<6;++I)Relics.Add(MakeShared<FJsonValueNumber>((I%3)+1));State->SetArrayField(TEXT("relics"),Relics);Pages->SetObjectField(FString::FromInt(Page),State);}Run.State->SetObjectField(TEXT("pages"),Pages);Run.State->SetNumberField(TEXT("revision"),2);ApplyRealmWar(Run.State);
        Check(RealmWarPanel&&TextOf(RealmWarPanel.ToSharedRef()).Contains(TEXT("HIBERNIA HOLDS 1")),TEXT("ownership totals derive from received keeps only"));
        Check(CloseClassicPanel()&&!bRealmWarOpen,TEXT("Escape closes realm war before character panel"));
        RealmWarLastRequest=-10000;ToggleRealmWar();Outgoing.Empty();RealmWarLastRequest=-10000;Check(Click(TEXT("ALBION"))&&RealmWarPage==1,TEXT("actual Albion tab changes original page"));auto Request=Command();Check(Request&&Request->GetStringField(TEXT("action"))==TEXT("warmap_request")&&Request->GetNumberField(TEXT("page"))==1,TEXT("realm tab sends page one without teleport"));Outgoing.Empty();Run.Phase=2;Run.At=FPlatformTime::Seconds();return true;
    }
    if(Run.Phase==2){Check(Capture(TEXT(".alb.png")),TEXT("original Albion atlas rendered"));RealmWarLastRequest=-10000;Check(Click(TEXT("MIDGARD"))&&RealmWarPage==2,TEXT("actual Midgard tab changes original page"));Outgoing.Empty();Run.Phase=3;Run.At=FPlatformTime::Seconds();return true;}
    Check(RealmWarPanel&&RealmWarPanel->GetCachedGeometry().GetLocalSize().Equals(FVector2D(406,394),.1),TEXT("original Midgard window dimensions"));Check(Capture(TEXT(".mid.png")),TEXT("original Midgard atlas rendered"));
    RealmWarLastRequest=-10000;Check(Click(TEXT("UPDATE")),TEXT("actual Update button requests current page"));auto Request=Command();Check(Request&&Request->GetNumberField(TEXT("page"))==2,TEXT("Update retains selected realm"));Outgoing.Empty();
    auto All=Buttons();if(All.Num()==5)All[0]->SimulateClick();Check(!bRealmWarOpen&&!RealmWarOverlay.IsValid(),TEXT("actual painted close cross closes window"));Outgoing.Empty();
    RealmWarPosition={140,90};SaveClassicLayout();RemoveClassicUI();ClassicLayoutCharacter.Empty();ApplyClassicUI(Run.Classic);Check(RealmWarPosition.Equals(FVector2D(140,90),.1),TEXT("window position persists per character"));
    Check(!RealmWarState.IsValid()&&!bRealmWarOpen,TEXT("character UI cleanup removes old realm-war cache"));RemoveClassicUI();if(Socket){Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;}Outgoing.Empty();Session.Empty();bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Run.Checks);Report->SetBoolField(TEXT("server_started"),false);TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& F:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Failures);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Run.Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
