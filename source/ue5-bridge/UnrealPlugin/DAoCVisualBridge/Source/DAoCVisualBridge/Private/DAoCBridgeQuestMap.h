#pragma once

#include "Dom/JsonObject.h"

namespace BridgeQuestMap
{
inline TArray<FVector2D> StepUnits(const TSharedPtr<FJsonObject>& State)
{
    TArray<FVector2D> Points;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!State || !State->TryGetArrayField(TEXT("quest_map_marks"), Rows) || Rows->Num() > 128)
        return Points;
    for (const auto& Value : *Rows)
    {
        if (!Value || Value->Type != EJson::Object)
            continue;
        const auto Row = Value->AsObject();
        const TArray<TSharedPtr<FJsonValue>>* Position = nullptr;
        if (!Row->TryGetArrayField(TEXT("position_m"), Position) || Position->Num() != 2)
            continue;
        double X = 0, Y = 0;
        if (!(*Position)[0]->TryGetNumber(X) || !(*Position)[1]->TryGetNumber(Y) ||
            !FMath::IsFinite(X) || !FMath::IsFinite(Y))
            continue;
        Points.Add(FVector2D(X * 40, Y * 40));
    }
    return Points;
}
}
