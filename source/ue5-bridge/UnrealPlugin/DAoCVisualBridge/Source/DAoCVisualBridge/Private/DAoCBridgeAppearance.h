#pragma once
#include "CoreMinimal.h"
class ASkeletalMeshActor;
class FJsonObject;
FString DAoCAppearancePath();
// Original, morph-capable appearance parts; the caller retains the actor.
bool ApplyLobbyAppearance(ASkeletalMeshActor* Actor,int32 Model,TSharedPtr<FJsonObject> Look,TSharedPtr<FJsonObject> Armour,const FString& CatalogPath,TSharedPtr<FJsonObject> Worn);
