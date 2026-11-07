#pragma once
#include "CoreMinimal.h"

// Display preferences only. Never applies scalability or renderer presets.
struct FBridgeDisplaySettings {
    FIntPoint Resolution=FIntPoint(1280,720);
    int32 Mode=2,Cap=0; // UE Fullscreen=0, WindowedFullscreen=1, Windowed=2.
    bool HasSaved=false;
    FString File;
    static const TArray<int32>& Caps();
    static bool Valid(FIntPoint Size,int32 WindowMode,int32 FrameCap);
    static TArray<FIntPoint> Resolutions(FIntPoint Desktop,FIntPoint Current);
    bool Load(const FString& Path);
    bool Save() const;
    void Apply(bool Resize=true) const;
};
