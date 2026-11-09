#pragma once
#include "CoreMinimal.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/StrongObjectPtr.h"
class AActor;
class UMeshComponent;

// Candidate actor-local ghost presentation. No shared asset or player-stealth edits.
class FBridgeGhostMaterials
{
public:
    ~FBridgeGhostMaterials();
    bool Load(const FString& Manifest);
    bool Apply(AActor* Actor,bool Confirmed,bool Ghost,bool RaceFigure);
    void Restore();
    int32 ChangedSlots() const {return Slots.Num();}
    int32 DepthProxies() const {return Proxies.Num();}
    int32 MissingSlots() const {return Missing;}
    static const FName DepthTag;
private:
    struct FSlot {
        TWeakObjectPtr<UMeshComponent> Component;
        int32 Index=0;
        TStrongObjectPtr<UMaterialInterface> Original;
        TStrongObjectPtr<UMaterialInstanceDynamic> Ghost;
    };
    struct FProxy {
        TWeakObjectPtr<UMeshComponent> Source;
        TWeakObjectPtr<UMeshComponent> Depth;
    };
    TWeakObjectPtr<AActor> CurrentActor;
    TArray<FSlot> Slots;
    TArray<FProxy> Proxies;
    TMap<FString,FString> Mapping;
    TMap<FString,TStrongObjectPtr<UMaterialInterface>> Loaded;
    int32 Missing=0;
    UMaterialInterface* Variant(UMaterialInterface* Source);
    UMeshComponent* ProxyFor(UMeshComponent* Source);
};
