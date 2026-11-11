#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

namespace BridgeQuestIndicator
{
    inline int32 FromRow(const FJsonObject& Row)
    {
        double Indicator = 0, Health = 0;
        FString Kind, State;
        if (!Row.TryGetStringField(TEXT("kind"), Kind) || Kind != TEXT("npc") ||
            !Row.TryGetNumberField(TEXT("health"), Health) || !FMath::IsFinite(Health) || Health <= 0 ||
            !Row.TryGetNumberField(TEXT("quest_indicator"), Indicator))
            return 0;
        if (Row.TryGetStringField(TEXT("state"), State) && State == TEXT("dead"))
            return 0;
        return Indicator == 1 || Indicator == 2 || Indicator == 4 || Indicator == 8 || Indicator == 16 ? int32(Indicator) : 0;
    }

    inline FLinearColor Color(int32 Indicator)
    {
        if (Indicator == 2)
            return FLinearColor(.3f, 1.f, .35f);
        if (Indicator == 16)
            return FLinearColor(1.f, .55f, .1f);
        return FLinearColor(1.f, .85f, .15f);
    }
}
