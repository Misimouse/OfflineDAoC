#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeTargetTracking.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickTargetTrackingAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeTargetTrackingTest="),File))return false;
    static bool Done=false;if(Done)return true;Done=true;int32 Checks=0;TArray<FString> Failures;
    auto Check=[&](bool Value,const FString& Label){++Checks;if(!Value)Failures.Add(Label);};
    FBridgeTargetTracking T;FVector D=FVector::ZeroVector,F=FVector::ZeroVector;int64 Seq=0;
    auto Start=[&](const FString& Mode,FVector P,bool Valid=true){return T.Begin(++Seq,Mode,TEXT("npc:1"),TEXT("Witness"),FVector::ZeroVector,P,Valid);};
    Check(!T.Begin(++Seq,TEXT("follow"),TEXT("player:local"),TEXT("Self"),FVector::ZeroVector,FVector(100,0,0),true),TEXT("cannot track self"));
    Check(!Start(TEXT("unknown"),FVector(100,0,0)),TEXT("unknown mode rejected"));
    Check(!Start(TEXT("follow"),FVector(100,0,0),false),TEXT("absent dead or untargetable actor rejected"));
    Check(!Start(TEXT("follow"),FVector(2500.1,0,0)),TEXT("outside original start range rejected"));
    Check(Start(TEXT("follow"),FVector(2500,0,0)),TEXT("exact original start range accepted"));
    Check(!T.Begin(Seq,TEXT("face"),TEXT("npc:2"),TEXT("Other"),FVector::ZeroVector,FVector(100,0,0),true)&&T.Mode==TEXT("follow"),TEXT("repeated sequence cannot retarget"));
    Check(T.Advance(FVector::ZeroVector,FVector(300,0,0),true,true,false,D,F)&&D.IsNearlyZero(),TEXT("follow stops at exactly three metres"));
    Check(T.Advance(FVector::ZeroVector,FVector(301,0,0),true,true,false,D,F)&&D.Equals(FVector(1,0,0)),TEXT("follow resumes outside gap"));
    Check(T.Advance(FVector::ZeroVector,FVector(0,700,0),true,true,false,D,F)&&D.Equals(FVector(0,1,0)),TEXT("moving target updates native direction"));
    Check(T.Advance(FVector::ZeroVector,FVector(0,700,0),true,true,false,D,F)&&F.Equals(D),TEXT("body faces actual tracked direction"));
    Check(T.Advance(FVector::ZeroVector,FVector(10000,0,0),true,true,false,D,F)&&T.Active,TEXT("follow retains original absence of stick break limit"));
    Check(!T.Advance(FVector::ZeroVector,FVector(700,0,0),true,true,true,D,F)&&!T.Active&&T.StopReason==TEXT("manual"),TEXT("manual movement cancels tracking"));
    Check(Start(TEXT("stick"),FVector(200,0,0)),TEXT("near stick starts"));
    Check(T.Advance(FVector::ZeroVector,FVector(140,0,0),true,true,false,D,F)&&D.IsNearlyZero(),TEXT("stick stops at original 1.4m gap"));
    Check(T.Advance(FVector::ZeroVector,FVector(141,0,0),true,true,false,D,F)&&!D.IsNearlyZero(),TEXT("stick moves beyond gap"));
    Check(T.Advance(FVector::ZeroVector,FVector(3750,0,0),true,true,false,D,F)&&T.Active,TEXT("exact original break distance retained"));
    Check(!T.Advance(FVector::ZeroVector,FVector(3750.1,0,0),true,true,false,D,F)&&T.StopReason==TEXT("range"),TEXT("stick breaks beyond 37.5m"));
    Check(Start(TEXT("face"),FVector(10000,0,0)),TEXT("face has no follow start limit"));
    Check(T.Advance(FVector::ZeroVector,FVector(10000,0,0),true,true,false,D,F)&&D.IsNearlyZero()&&F.Equals(FVector(1,0,0)),TEXT("face only rotates without movement"));
    Check(T.Advance(FVector::ZeroVector,FVector(0,-500,0),true,true,false,D,F)&&D.IsNearlyZero()&&F.Equals(FVector(0,-1,0)),TEXT("face tracks a moving target"));
    for(const FString Reason:{TEXT("death"),TEXT("chat"),TEXT("options"),TEXT("focus"),TEXT("posture")}){
        Check(Start(TEXT("follow"),FVector(700,0,0)),TEXT("new tracking after earlier cancellation"));
        Check(!T.Advance(FVector::ZeroVector,FVector(700,0,0),true,false,false,D,F)&&!T.Active,TEXT("blocked input cancels without automatic resume: ")+Reason);
    }
    Check(Start(TEXT("follow"),FVector(700,0,0)),TEXT("following restarts explicitly"));
    Check(!T.Advance(FVector::ZeroVector,FVector(700,0,0),false,true,false,D,F)&&!T.Active,TEXT("dead/despawned target stops"));
    Check(Start(TEXT("face"),FVector(0,0,0)),TEXT("coincident target remains finite"));
    Check(T.Advance(FVector::ZeroVector,FVector::ZeroVector,true,true,false,D,F)&&D.IsNearlyZero()&&F.IsNearlyZero(),TEXT("coincident feet cannot create an invalid direction"));
    T.Reset();Check(T.Sequence==0&&!T.Active&&T.EntityId.IsEmpty(),TEXT("new session clears native target and generation"));
    auto O=MakeShared<FJsonObject>();O->SetBoolField(TEXT("passed"),Failures.IsEmpty());O->SetNumberField(TEXT("checks"),Checks);TArray<TSharedPtr<FJsonValue>> Errors;for(auto& E:Failures)Errors.Add(MakeShared<FJsonValueString>(E));O->SetArrayField(TEXT("failures"),Errors);FString Text;FJsonSerializer::Serialize(O,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
