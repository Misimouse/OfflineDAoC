#pragma once
#include "CoreMinimal.h"
class USkeletalMeshComponent;
class FBridgeLiveRidingData {
    struct FSeat {FName Anchor;FVector Reference;double WalkStride=0,RunStride=0;};
    TMap<int32,FSeat> Seats;
public:
    bool Load(const FString& Path);
    float GaitRate(int32 Model,const FString& Gait,double SpeedMps,double ClipSeconds,double InstanceScale=1)const;
    bool Resolve(USkeletalMeshComponent* Mesh,int32 Model,FVector& WorldSeat)const;
};
