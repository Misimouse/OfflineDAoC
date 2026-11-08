#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Widgets/Text/STextBlock.h"

bool UDAoCBridgeSubsystem::TickPlayerVitalsAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePlayerVitalsTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const TCHAR* Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString FixtureFile,Text;TSharedPtr<FJsonObject> Fixture;
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeVitalsFixture="),FixtureFile);
    Check(FFileHelper::LoadFileToString(Text,*FixtureFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("captured real-server snapshot loads"));
    if(Fixture.IsValid()){
        auto State=Fixture->GetObjectField(TEXT("player_status"));auto Vitals=State->GetObjectField(TEXT("vitals"));
        Check(Vitals->GetNumberField(TEXT("health"))==1&&Vitals->GetNumberField(TEXT("health_pct"))==0,TEXT("fixture is original one HP with rounded zero percentage"));
        PlayerState=State;bLocalAvailable=true;bExiting=false;Session=TEXT("private-vitals-command-capture");
        Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private vitals capture"),false);Outgoing.Empty();
        Check(!PlayerIsDead(),TEXT("positive original points keep native character alive"));Check(PlayerCanMove(),TEXT("one HP permits movement"));
        RequestAttack(true);Check(Outgoing.Num()>0,TEXT("living zero percent can request original attack mode"));Outgoing.Empty();
        RequestSit(true);Check(Outgoing.Num()>0,TEXT("living zero percent can request original sit"));Outgoing.Empty();
        RequestRelease();Check(Outgoing.IsEmpty(),TEXT("living zero percent cannot request release"));
        ApplyPlayerStatus(State);
        TFunction<bool(TSharedRef<SWidget>,const FString&)> HasText=[&](TSharedRef<SWidget> W,const FString& Name){if(W->GetTypeAsString()==TEXT("STextBlock")&&StaticCastSharedRef<STextBlock>(W)->GetText().ToString()==Name)return true;auto* C=W->GetChildren();for(int32 I=0;I<C->Num();++I)if(HasText(C->GetChildAt(I),Name))return true;return false;};
        Check(PlayerStatusPanel.IsValid()&&!HasText(PlayerStatusPanel.ToSharedRef(),TEXT("You are dead")),TEXT("original controls do not show false death or release"));
        TSharedPtr<FJsonObject> Row;
        for(const auto& E:Fixture->GetArrayField(TEXT("entities")))if(E->AsObject()->GetStringField(TEXT("id"))==TEXT("player:local")){Row=E->AsObject();break;}
        Check(Row.IsValid()&&Row->GetNumberField(TEXT("health"))>0,TEXT("real bridge publishes positive local health fraction"));
        auto* Local=Row.IsValid()?Cast<ASkeletalMeshActor>(CreateEntity(TEXT("player:local"),Row,FVector::ZeroVector)):nullptr;
        Check(Local!=nullptr,TEXT("actual original character model loads"));
        if(Local){
            EntityRows.Add(TEXT("player:local"),Row);SetEntityAnimation(TEXT("player:local"),TEXT("idle"));
            auto* Anim=Local->GetSkeletalMeshComponent()->GetSingleNodeInstance();
            Check(Anim&&AnimationStates.FindRef(TEXT("player:local"))==TEXT("idle")&&Anim->IsLooping(),TEXT("one HP retains actual living idle animation"));
            SetEntityAnimation(TEXT("player:local"),TEXT("run"));Check(AnimationStates.FindRef(TEXT("player:local"))==TEXT("run"),TEXT("one HP retains original locomotion"));
            Vitals->SetBoolField(TEXT("alive"),false);Vitals->SetNumberField(TEXT("health"),0);State->SetNumberField(TEXT("revision"),State->GetNumberField(TEXT("revision"))+1);
            Check(PlayerIsDead()&&!PlayerCanMove(),TEXT("confirmed death blocks movement"));Outgoing.Empty();RequestAttack(true);RequestSit(true);Check(Outgoing.IsEmpty(),TEXT("confirmed death blocks attack and sitting"));
            RequestRelease();Check(Outgoing.Num()>0,TEXT("confirmed death permits original release request"));Outgoing.Empty();
            ApplyPlayerStatus(State);Check(HasText(PlayerStatusPanel.ToSharedRef(),TEXT("You are dead")),TEXT("confirmed death displays release controls"));
            SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(Anim&&AnimationStates.FindRef(TEXT("player:local"))==TEXT("death")&&!Anim->IsLooping(),TEXT("confirmed death plays original nonlooping death"));
            if(Anim){Anim->SetPosition(.4f,false);PosePlayback[TEXT("player:local")].DiedAt=FPlatformTime::Seconds()-.4;SetEntityAnimation(TEXT("player:local"),TEXT("idle"));Check(FMath::IsNearlyEqual(Anim->GetCurrentTime(),.4f,.01f),TEXT("repeated death snapshots do not restart corpse"));}
            Vitals->SetBoolField(TEXT("alive"),true);Vitals->SetNumberField(TEXT("health"),1);SetEntityAnimation(TEXT("player:local"),TEXT("idle"));
            Check(!PlayerIsDead()&&PlayerCanMove()&&AnimationStates.FindRef(TEXT("player:local"))==TEXT("idle"),TEXT("real one-HP revival restores movement and living pose"));
            Vitals->RemoveField(TEXT("alive"));Check(!PlayerIsDead(),TEXT("absolute points fallback also keeps character alive"));
            Vitals->SetNumberField(TEXT("health"),0);Check(PlayerIsDead(),TEXT("absolute zero fallback remains dead"));Vitals->RemoveField(TEXT("absolute_health_known"));Vitals->SetNumberField(TEXT("health_pct"),100);Check(!PlayerIsDead(),TEXT("legacy percent-only fixture remains compatible"));
            Vitals->SetNumberField(TEXT("health_pct"),0);Check(PlayerIsDead(),TEXT("legacy percent-only death remains compatible"));
        }
        ClearEntities();RemovePlayerStatusUI();Disconnect();
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server_snapshot"),true);Report->SetBoolField(TEXT("server_started"),false);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*Path);UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
