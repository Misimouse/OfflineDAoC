#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"

void UDAoCBridgeSubsystem::UpdateInteractionTest(float Elapsed){
    if(Elapsed>14&&!(InteractionTestSteps&1)){
        FString BestId;double Best=600;bool MerchantFound=false;
        for(const auto& Pair:Entities){
            auto* Row=EntityRows.Find(Pair.Key);FVector Aim;if(!Row||!Pair.Key.StartsWith(TEXT("npc:"))||!CanSelect(Pair.Key,Aim))continue;
            FString Guild;(*Row)->TryGetStringField(TEXT("guild"),Guild);const bool Merchant=Guild.Contains(TEXT("merchant"),ESearchCase::IgnoreCase);
            const double Distance=FVector::Dist(PlayerPosition,Pair.Value->GetActorLocation());if(Distance>=600)continue;
            if((Merchant&&!MerchantFound)||(Merchant==MerchantFound&&Distance<Best)){BestId=Pair.Key;Best=Distance;MerchantFound=Merchant;}
        }
        if(!BestId.IsEmpty()){
            FVector Aim;FVector2D Pixel;if(CanSelect(BestId,Aim)&&GetWorld()->GetFirstPlayerController()->ProjectWorldLocationToScreen(Aim,Pixel))if(TargetAtCursor(false,Pixel)==BestId)InteractionTestSteps|=4;
            SelectEntity(BestId);InteractionTestSteps|=1;
        }
    }
    if(Elapsed>15&&(InteractionTestSteps&1)&&!(InteractionTestSteps&2)&&!CurrentTarget().IsEmpty()){InteractSelected();InteractionTestSteps|=2;}
    if(Elapsed>19&&bCaptured&&(InteractionTestSteps&2)&&!(InteractionTestSteps&8)){Send(TEXT("dismiss_interaction"));SelectEntity(TEXT(""));InteractionTestSteps|=8;}
}
bool UDAoCBridgeSubsystem::TickInteractionAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInteractionTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    TArray<TSharedPtr<FJsonValue>> Failures;int32 Checks=0;auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Input;TSharedPtr<FJsonObject> Fixture;
    Check(FFileHelper::LoadFileToString(Input,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Fixture),TEXT("fixture parsed"));
    if(Fixture.IsValid()){
        const auto& Cases=Fixture->GetArrayField(TEXT("cases"));
        for(const auto& Value:Cases){
            auto State=Value->AsObject();ApplyInteraction(State);
            Check(InteractionState==State,TEXT("server state retained"));
            Check(CurrentTarget()==State->GetObjectField(TEXT("target"))->GetStringField(TEXT("id")),TEXT("target identity"));
            Check(InteractionRevision==State->GetIntegerField(TEXT("revision")),TEXT("UI revision"));
            Check(InteractionOverlay.IsValid()&&InteractionPanel.IsValid(),TEXT("viewport widgets created"));
        }
        ClearEntities();Check(CurrentTarget().IsEmpty()&&!InteractionOverlay.IsValid(),TEXT("disconnect removes stale UI"));
        Check(Socket==nullptr,TEXT("offline test has no bridge socket"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("checks"),Checks);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".native.json")));
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
