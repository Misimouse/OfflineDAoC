#pragma once
#include "CoreMinimal.h"

struct FBridgeTargetTracking {
    int64 Sequence=0;
    FString Mode,EntityId,Name,StopReason;
    bool Active=false;
    void Reset(){Sequence=0;Mode.Empty();EntityId.Empty();Name.Empty();StopReason.Empty();Active=false;}
    void Stop(const FString& Reason){Active=false;Mode.Empty();StopReason=Reason;}
    bool Begin(int64 Seq,const FString& Wanted,const FString& Id,const FString& TargetName,const FVector& Local,const FVector& Target,bool Valid){
        if(Seq<=Sequence)return false;
        Sequence=Seq;EntityId=Id;Name=TargetName;Stop(TEXT("rejected"));
        if(Wanted.IsEmpty()){Stop(TEXT("cleared"));return false;}
        if((Wanted!=TEXT("face")&&Wanted!=TEXT("follow")&&Wanted!=TEXT("stick"))||Id.IsEmpty()||Id==TEXT("player:local")||!Valid||Local.ContainsNaN()||Target.ContainsNaN())return false;
        if(Wanted!=TEXT("face")&&FVector::Dist(Local,Target)>2500)return false;
        Mode=Wanted;Active=true;StopReason.Empty();return true;
    }
    bool Advance(const FVector& Local,const FVector& Target,bool Valid,bool Enabled,bool Manual,FVector& Desired,FVector& Facing){
        if(!Active)return false;
        if(!Enabled||Manual||!Valid||Local.ContainsNaN()||Target.ContainsNaN()){Stop(!Enabled?TEXT("input"):Manual?TEXT("manual"):TEXT("target"));return false;}
        const FVector Delta=Target-Local;
        if(Mode==TEXT("stick")&&Delta.Size()>3750){Stop(TEXT("range"));return false;}
        Facing=Delta.GetSafeNormal2D();
        const double Gap=Delta.Size2D();const double Limit=Mode==TEXT("follow")?300:140;
        Desired=Mode!=TEXT("face")&&Gap>Limit?Facing:FVector::ZeroVector;return true;
    }
};
