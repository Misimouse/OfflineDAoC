#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"

struct FBridgeMovementKeys {
    bool RunLock=false,WalkToggle=false;
    TMap<int32,FVector2D> Backward;
    bool Load(const FString& Path){
        FString Text;TSharedPtr<FJsonObject> Root;double Version=0;const TSharedPtr<FJsonObject>* Models=nullptr;
        if(!FFileHelper::LoadFileToString(Text,*Path)||Text.Len()>16384||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root||!Root->TryGetNumberField(TEXT("version"),Version)||Version!=1||!Root->TryGetObjectField(TEXT("models"),Models)||(*Models)->Values.Num()!=13)return false;
        TMap<int32,FVector2D> Parsed;
        for(auto& Row:(*Models)->Values){int32 Model=0;double Stride=0,Length=0;
            if(!LexTryParseString(Model,*Row.Key)||Model<=0||Row.Value->Type!=EJson::Object)return false;
            auto O=Row.Value->AsObject();if(!O->TryGetNumberField(TEXT("stride_units"),Stride)||!O->TryGetNumberField(TEXT("clip_seconds"),Length)||!FMath::IsFinite(Stride)||!FMath::IsFinite(Length)||Stride<=0||Stride>1000||Length<=0||Length>10)return false;
            Parsed.Add(Model,FVector2D(Stride,Length));
        }
        Backward=MoveTemp(Parsed);return true;
    }
    float BackwardRate(int32 Model,float SpeedMps)const{
        const auto* Row=Backward.Find(Model);if(!Row||!FMath::IsFinite(SpeedMps))return 1;
        return FMath::Clamp((SpeedMps/.025f)/(Row->X/Row->Y),.3,3.);
    }
    struct FFrame {float Forward=0,Right=0,SpeedFactor=1;};
    void Reset(){RunLock=false;WalkToggle=false;}
    FFrame Advance(bool Enabled,bool ToggleRun,bool ToggleWalk,bool ForwardPressed,bool BackPressed,bool Forward,bool Back,bool Left,bool Right,bool Shift,bool BothMouse){
        FFrame Frame;
        if(!Enabled){RunLock=false;return Frame;}
        if(ToggleRun)RunLock=!RunLock;
        if(ToggleWalk)WalkToggle=!WalkToggle;
        if(ForwardPressed||BackPressed||BothMouse)RunLock=false;
        Frame.Forward=((Forward||RunLock||BothMouse)?1.f:0.f)-(Back?1.f:0.f);
        Frame.Right=(Right?1.f:0.f)-(Left?1.f:0.f);
        // Original modern-mode ordering: backwards precedes walk/Shift.
        Frame.SpeedFactor=Frame.Forward<0?.65f:(WalkToggle||Shift)?.35f:1.f;
        return Frame;
    }
};
