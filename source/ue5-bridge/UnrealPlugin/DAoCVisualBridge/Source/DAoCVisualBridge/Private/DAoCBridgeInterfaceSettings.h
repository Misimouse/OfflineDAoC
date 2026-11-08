#pragma once
#include "CoreMinimal.h"

struct FBridgeInterfaceSettings {
    float Scale=1.f;
    FString File;
    static bool Valid(float Value);
    static float EffectiveScale(FVector2D Viewport,float Preference);
    bool Load(const FString& Path);
    bool Save() const;
};
