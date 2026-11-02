// Offline replay of decoded Godot events through the real native consumer.
#include "DAoCBridgeSubsystem.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickEntityAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeEntityTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Failures;int32 Checks=0;
    auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Text;TSharedPtr<FJsonObject> Fixture;
    const bool Loaded=FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture);
    Check(Loaded,TEXT("fixture loaded"));
    if(Loaded){
        Session=TEXT("entity-acceptance");Sequence=0;ClearEntities();
        const TArray<TSharedPtr<FJsonValue>>* Cases=nullptr;
        Check(Fixture->TryGetArrayField(TEXT("cases"),Cases),TEXT("replay cases"));
        if(Cases)for(const auto& Value:*Cases){
            auto Case=Value->AsObject();auto Snapshot=Case->GetObjectField(TEXT("snapshot"));FString Label=Case->GetStringField(TEXT("label"));
            TMap<FString,TWeakObjectPtr<AActor>> Before;for(const auto& Pair:Entities)Before.Add(Pair.Key,Pair.Value.Get());
            auto BeforeModels=EntityModels;
            ApplySnapshot(Snapshot);
            auto Rows=Snapshot->GetArrayField(TEXT("entities"));
            Check(Entities.Num()==Rows.Num(),Label+TEXT(": entity count"));
            int32 Npcs=0;bool Local=false;
            for(const auto& RowValue:Rows){
                auto Row=RowValue->AsObject();FString Id=Row->GetStringField(TEXT("id"));
                auto* Found=Entities.Find(Id);AActor* Actor=Found?Found->Get():nullptr;
                Check(IsValid(Actor),Label+TEXT(": actor ")+Id);if(!IsValid(Actor))continue;
                auto P=Row->GetArrayField(TEXT("position_m"));FVector Expected((P[0]->AsNumber()-1364)*100,(P[2]->AsNumber()-1263)*100,(P[1]->AsNumber()-130)*100);
                Check(Actor->GetActorLocation().Equals(Expected,.02),Label+TEXT(": position ")+Id);
                double Heading=0;if(Row->TryGetNumberField(TEXT("heading_4096"),Heading)){
                    double Offset=0;if(auto* Entry=ModelCatalog.Find(FString::FromInt(Row->GetIntegerField(TEXT("model_id")))))(*Entry)->TryGetNumberField(TEXT("yaw_offset"),Offset);
                    const float ExpectedYaw=float(90+Heading*360/4096+Offset);
                    Check(FMath::Abs(FRotator::NormalizeAxis(Actor->GetActorRotation().Yaw-ExpectedYaw))<.01,Label+TEXT(": server heading ")+Id);
                }
                const int32 Model=Row->GetIntegerField(TEXT("model_id"));
                Check(EntityModels.FindRef(Id)==Model,Label+TEXT(": model ")+Id);
                if(BeforeModels.Contains(Id)&&BeforeModels[Id]!=Model)Check(Before[Id].Get()!=Actor,Label+TEXT(": rebuilt model"));
                if(Id==TEXT("player:local")){Local=true;Check(PlayerPosition.Equals(Expected,.02),Label+TEXT(": local authority"));}
                else if(Row->GetStringField(TEXT("kind"))==TEXT("npc"))++Npcs;
            }
            Check(NpcCount==Npcs,Label+TEXT(": NPC count excludes players"));
            Check(bLocalAvailable==Local,Label+TEXT(": local availability"));
            Check(AnimationStates.Num()<=Entities.Num(),Label+TEXT(": animation cache bounded"));
        }
        Check(Socket==nullptr,TEXT("offline replay never opens game bridge"));
        ClearEntities();Check(EntityModels.IsEmpty()&&AnimationStates.IsEmpty()&&!bLocalAvailable,TEXT("session cleanup"));
    }
    Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("real_server"),false);Report->SetBoolField(TEXT("native_actor_consumer"),true);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".native.json")));
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
