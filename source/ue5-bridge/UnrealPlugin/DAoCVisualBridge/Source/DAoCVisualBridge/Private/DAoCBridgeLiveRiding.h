#pragma once
#include "CoreMinimal.h"
class USkeletalMeshComponent;
class FBridgeLiveRidingData {
    struct FSeat {FName Anchor;FVector Reference;};
    TMap<int32,FSeat> Seats;
public:
    bool Load(const FString& Path);
    bool Resolve(USkeletalMeshComponent* Mesh,int32 Model,FVector& WorldSeat)const;
};
