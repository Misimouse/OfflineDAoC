#pragma once
#include "CoreMinimal.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/StrongObjectPtr.h"
class AActor;
class UMeshComponent;

// Per-avatar overrides only. Shared mesh assets and original material instances
// remain untouched; strong references retain the exact materials for restoration.
class FBridgeStealthMaterials
{
public:
    ~FBridgeStealthMaterials();
    bool Load(const FString& Manifest);
    void Apply(AActor* Actor,bool Confirmed,bool Hidden);
    void Restore();
    int32 ChangedSlots() const {return Slots.Num();}
    int32 MissingSlots() const {return Missing;}
    int32 ReplacementCount() const {return Replacements;}
    int32 RestorationCount() const {return Restorations;}
private:
    struct FSlot {
        TWeakObjectPtr<UMeshComponent> Component;
        int32 Index=0;
        TStrongObjectPtr<UMaterialInterface> Original;
        TStrongObjectPtr<UMaterialInstanceDynamic> Hidden;
    };
    TWeakObjectPtr<AActor> CurrentActor;
    TArray<FSlot> Slots;
    TMap<FString,FString> Mapping;
    TMap<FString,TStrongObjectPtr<UMaterialInterface>> Loaded;
    int32 Missing=0,Replacements=0,Restorations=0;
    UMaterialInterface* Variant(UMaterialInterface* Source);
};
