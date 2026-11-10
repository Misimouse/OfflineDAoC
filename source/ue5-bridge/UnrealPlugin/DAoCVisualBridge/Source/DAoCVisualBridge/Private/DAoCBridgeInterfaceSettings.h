#pragma once
#include "CoreMinimal.h"
#include "Widgets/SWidget.h"

struct FBridgeInterfaceSettings {
    // Transient presentation state; never written to character/layout settings.
    bool Hidden=false;
    struct FHiddenRoot {TWeakPtr<SWidget> Widget;EVisibility Previous=EVisibility::Visible;};
    TArray<FHiddenRoot> HiddenRoots;
    void SetHidden(bool Value);
    void ApplyVisibility(const TArray<TSharedPtr<SWidget>>& Roots);
    float Scale=1.f;
    FString File;
    static bool Valid(float Value);
    static float EffectiveScale(FVector2D Viewport,float Preference);
    bool Load(const FString& Path);
    bool Save() const;
};
