#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/World.h"
#include "Components/PointLightComponent.h"

// Original zone light definitions are independent of fixture meshes and NPCs.
// Keep them transient so the bridge never saves changes into the art map.
void UDAoCBridgeSubsystem::ApplyZoneLights(const TSharedPtr<FJsonObject>& Snapshot){
 const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;
 if(!Snapshot||!Snapshot->TryGetArrayField(TEXT("zone_lights"),Rows)||Rows->Num()>512)return;
 FString Signature;FJsonSerializer::Serialize(*Rows,TJsonWriterFactory<>::Create(&Signature));if(Signature==ZoneLightSignature)return;
 for(auto Actor:ZoneLightActors)if(Actor.IsValid())Actor->Destroy();ZoneLightActors.Empty();ZoneLightSignature=Signature;
 auto Point=[](const TSharedPtr<FJsonObject>& O,const TCHAR* Key,FVector& Out){const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(!O->TryGetArrayField(Key,A)||A->Num()!=3)return false;double V[3];for(int I=0;I<3;++I)if(!(*A)[I]->TryGetNumber(V[I])||!FMath::IsFinite(V[I]))return false;Out=FVector(V[0],V[1],V[2]);return true;};
 for(const auto& Value:*Rows){if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();FVector Pos,Color;double Range=0;
  if(!Point(Row,TEXT("pos"),Pos)||!Point(Row,TEXT("color"),Color)||!Row->TryGetNumberField(TEXT("range_m"),Range)||!FMath::IsFinite(Range)||Range<=0||Range>100||Pos.GetAbsMax()>1000000||Color.GetMin()<0||Color.GetMax()>1)continue;
  FString Name;Row->TryGetStringField(TEXT("name"),Name);const bool Fire=Name.Contains(TEXT("fire"),ESearchCase::IgnoreCase);
  FActorSpawnParameters P;P.ObjectFlags|=RF_Transient;auto* Actor=GetWorld()->SpawnActor<AActor>(P);if(!Actor)continue;Actor->Tags.Add(TEXT("DAoCBridgeZoneLight"));
  auto* Light=NewObject<UPointLightComponent>(Actor);Actor->SetRootComponent(Light);Light->SetMobility(EComponentMobility::Movable);Light->SetWorldLocation(FVector((Pos.X-1364)*100,(Pos.Z-1263)*100,(Pos.Y-130)*100));
  Light->SetLightColor(FLinearColor(Color.X,Color.Y,Color.Z),false);Light->SetAttenuationRadius(Range*(Fire?250.f:150.f));Light->SetCastShadows(false);Light->bUseInverseSquaredFalloff=true;Light->SetIntensityUnits(ELightUnits::Lumens);
  // A bounded local fill preserves the original coloured glow with dynamic GI off.
  Light->SetIntensity(800.f);Light->MaxDrawDistance=16000;Light->MaxDistanceFadeRange=4000;Light->RegisterComponent();ZoneLightActors.Add(Actor);
 }
}
