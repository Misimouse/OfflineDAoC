#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"

// Presentation order only: never reorder the server's indexed roster/vitals.
struct FBridgeGroupTargeting {
    static bool Me(const TSharedPtr<FJsonValue>& V){bool Own=false;return V.IsValid()&&V->Type==EJson::Object&&V->AsObject().IsValid()&&V->AsObject()->TryGetBoolField(TEXT("me"),Own)&&Own;}
    static TArray<TSharedPtr<FJsonValue>> Ordered(const TArray<TSharedPtr<FJsonValue>>& Source){
        TArray<TSharedPtr<FJsonValue>> Rows;const int32 Count=FMath::Min(Source.Num(),8);int32 Own=-1;
        for(int32 I=0;I<Count;++I)if(Me(Source[I])){if(Own>=0){Rows.Append(Source.GetData(),Count);return Rows;}Own=I;}
        if(Own>=0)Rows.Add(Source[Own]);
        for(int32 I=0;I<Count;++I)if(I!=Own)Rows.Add(Source[I]);
        return Rows;
    }
    static TSharedPtr<FJsonObject> Member(const TArray<TSharedPtr<FJsonValue>>& Rows,int32 Slot){
        if(Slot<1||Slot>7||!Rows.IsValidIndex(Slot)||!Rows.Num()||!Me(Rows[0]))return nullptr;
        int32 OwnCount=0;for(const auto& V:Rows)if(Me(V))++OwnCount;if(OwnCount!=1)return nullptr;
        const auto& V=Rows[Slot];if(!V.IsValid()||V->Type!=EJson::Object||!V->AsObject().IsValid()||Me(V))return nullptr;
        auto M=V->AsObject();double Oid=0;FString Token;
        if(!M->TryGetNumberField(TEXT("oid"),Oid)||!FMath::IsFinite(Oid)||Oid<1||Oid>65535||Oid!=FMath::FloorToDouble(Oid)||!M->TryGetStringField(TEXT("token"),Token)||Token.IsEmpty())return nullptr;
        int32 Same=0;for(const auto& R:Rows)if(R.IsValid()&&R->Type==EJson::Object&&R->AsObject().IsValid()){double Other=0;if(R->AsObject()->TryGetNumberField(TEXT("oid"),Other)&&Other==Oid)++Same;}
        return Same==1?M:nullptr;
    }
};
