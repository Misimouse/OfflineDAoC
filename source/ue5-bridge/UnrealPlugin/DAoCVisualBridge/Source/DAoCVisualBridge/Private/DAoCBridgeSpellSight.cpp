#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
bool UDAoCBridgeSubsystem::BridgeLineOfSight(const FString& Source,const FString& Target)const{
 auto* A=Entities.Find(Source);auto* B=Entities.Find(Target);if(!A||!B||!IsValid(*A)||!IsValid(*B)||!GetWorld())return false;
 auto Position=[&](const FString& Id,AActor* Actor){if(Id==TEXT("player:local")&&bLocalAvailable)return PlayerPosition;const auto* Row=EntityRows.Find(Id);const TArray<TSharedPtr<FJsonValue>>* P=nullptr;if(Row&&(*Row)->TryGetArrayField(TEXT("position_m"),P)&&P->Num()==3)return FVector(((*P)[0]->AsNumber()-1364)*100,((*P)[2]->AsNumber()-1263)*100,((*P)[1]->AsNumber()-130)*100);return Actor->GetActorLocation();};
 const FVector From=Position(Source,*A),To=Position(Target,*B);
 if(From.ContainsNaN()||To.ContainsNaN())return false;FVector Flat=To-From;Flat.Z=0;if(Source==Target)return true;
 const FVector Edge=Flat.GetSafeNormal()*40;FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeSpellSight),true);Query.AddIgnoredActor(*A);Query.AddIgnoredActor(*B);if(PlayerPawn)Query.AddIgnoredActor(PlayerPawn);
 for(float Height:{60.f,150.f,220.f}){FHitResult Hit;if(!GetWorld()->LineTraceSingleByChannel(Hit,From+Edge+FVector(0,0,Height),To-Edge+FVector(0,0,Height),ECC_Camera,Query))return true;}
 return false;
}
void UDAoCBridgeSubsystem::AnswerLineOfSightQueries(const TSharedPtr<FJsonObject>& Snapshot){
 const TArray<TSharedPtr<FJsonValue>>* Queries=nullptr;if(!Snapshot.IsValid()||!Snapshot->TryGetArrayField(TEXT("los_queries"),Queries)||Queries->Num()>32)return;
 for(const auto& Value:*Queries){if(Value->Type!=EJson::Object)continue;auto Q=Value->AsObject();FString Id,Token,Source,Target;if(!Q->TryGetStringField(TEXT("id"),Id)||!Q->TryGetStringField(TEXT("token"),Token)||!Q->TryGetStringField(TEXT("source_id"),Source)||!Q->TryGetStringField(TEXT("target_id"),Target)||Id.IsEmpty()||Token.IsEmpty())continue;
  const FString Key=Id+TEXT("|")+Token;if(AnsweredSightQueries.Contains(Key))continue;if(AnsweredSightQueries.Num()>256)AnsweredSightQueries.Empty();AnsweredSightQueries.Add(Key);
  auto Reply=MakeShared<FJsonObject>();Reply->SetStringField(TEXT("query_id"),Id);Reply->SetStringField(TEXT("query_token"),Token);Reply->SetBoolField(TEXT("visible"),BridgeLineOfSight(Source,Target));Send(TEXT("los_reply"),Reply);
 }
}
