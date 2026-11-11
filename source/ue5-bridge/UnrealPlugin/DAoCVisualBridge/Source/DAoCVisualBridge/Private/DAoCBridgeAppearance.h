#pragma once
#include "CoreMinimal.h"
class ASkeletalMeshActor;
class FJsonObject;
FString DAoCAppearancePath();
void ClearCharacterAppearance(ASkeletalMeshActor* Actor);
// Original, morph-capable appearance parts; the caller retains the actor.
bool ApplyCharacterAppearance(ASkeletalMeshActor* Actor,int32 Model,TSharedPtr<FJsonObject> Look,TSharedPtr<FJsonObject> Armour,const FString& CatalogPath,TSharedPtr<FJsonObject> Worn,uint32 NpcOid=0);

class USceneCaptureComponent2D;
// Shared linear presentation and capture-owned neutral ambient for character previews.
void ConfigureCharacterPreviewCapture(USceneCaptureComponent2D* Capture);
