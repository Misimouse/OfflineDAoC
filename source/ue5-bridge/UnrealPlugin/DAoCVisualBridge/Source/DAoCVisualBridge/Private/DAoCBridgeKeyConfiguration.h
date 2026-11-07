#pragma once
#include "CoreMinimal.h"
#include "InputCoreTypes.h"
class APlayerController;

// Movement/target-tracking subset. Defaults preserve the delivered bridge controls.
// Original reference: game/ui/keybinds.gd and options_window.gd (two slots, exact press modifiers).
struct FBridgeKeyConfiguration {
    struct FAction { FString Id, Label; TArray<FString> Defaults, Bindings; bool Held=false; FString Category=TEXT("Movement"); };
    struct FChord { FKey Key; bool Shift=false,Ctrl=false,Alt=false; };
    TArray<FAction> Actions;
    FString Path;
    FBridgeKeyConfiguration();
    static bool Parse(const FString& Text,FChord& Out);
    static FString Describe(FKey Key,bool Shift,bool Ctrl,bool Alt);
    static bool Reserved(const FKey& Key);
    static bool Matches(const FChord& Chord,FKey Key,bool Shift,bool Ctrl,bool Alt,bool Held);
    FAction* Find(const FString& Id);
    const FAction* Find(const FString& Id) const;
    FString Text(const FString& Id,int32 Slot) const;
    bool Bind(const FString& Id,int32 Slot,const FString& Value,FString& Message);
    bool Pressed(APlayerController* PC,const FString& Id) const;
    bool Held(APlayerController* PC,const FString& Id) const;
    void Reset();
    void Load(const FString& File);
    bool Save() const;
};
