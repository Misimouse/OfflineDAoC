#pragma once
#include "CoreMinimal.h"

// Visual-only dead reckoning from decoded server waypoints. No game commands.
struct FBridgeRemoteMotion {
    FVector Anchor=FVector::ZeroVector,Forward=FVector::ForwardVector,Destination=FVector::ZeroVector;
    FVector Rendered=FVector::ZeroVector,Correction=FVector::ZeroVector;
    double SampleAt=0,CorrectionAt=0,CorrectionDuration=.12,Speed=0,Horizon=1,LastTickAt=0,CorrectionRate=150;
    int64 Revision=-1;
    bool ConstrainToWorld=false;
    int32 CollisionContacts=0,BlockedCorrections=0,RejectedTreeFloors=0;
    bool Initialized=false,HasDestination=false,Dead=false,HardSnap=false,Blocked=false,Grounded=false;
    double GroundOffset=0;
    int32 Samples=0,HardCorrections=0,VisualFrames=0,MovingFrames=0,ForecastStops=0;
    double MaximumStepCm=0,MaximumErrorCm=0;

    FVector Predict(double Now) const {
        if(Dead||Speed<=0)return Anchor;
        const double Elapsed=FMath::Clamp(Now-SampleAt,0.,Horizon);
        FVector Delta=HasDestination?Destination-Anchor:Forward;Delta.Z=0;
        const double Length=Delta.Size2D();
        if(Length<.001)return Anchor;
        return Anchor+Delta/Length*(HasDestination?FMath::Min(Length,Speed*Elapsed):Speed*Elapsed);
    }
    bool ForecastActive(double Now) const {
        if(Dead||Speed<=0||Now-SampleAt>=Horizon||Blocked)return false;
        return !HasDestination||FVector::Dist2D(Predict(Now),Destination)>.5;
    }
    bool Sample(int64 Seq,double Now,double AgeSeconds,const FVector& Position,const FVector& Direction,double MetresPerSecond,double IntervalSeconds,const FVector* Goal,bool IsDead){
        if(Initialized&&Seq<=Revision)return false;
        const FVector Previous=Rendered;const bool WasInitialized=Initialized;const double PreviousSpeed=Speed;
        Revision=Seq;Anchor=Position;Forward=Direction.GetSafeNormal2D();Speed=FMath::Clamp(MetresPerSecond*100.,0.,10000.);
        SampleAt=Now-FMath::Clamp(AgeSeconds,0.,60.);HasDestination=Goal!=nullptr;if(Goal)Destination=*Goal;
        Dead=IsDead;if(Dead)Speed=0;CorrectionRate=FMath::Max(150.,FMath::Max(PreviousSpeed,Speed)*.75);
        Horizon=HasDestination?FMath::Clamp(IntervalSeconds*2+1,6.,10.):FMath::Clamp(IntervalSeconds*1.5+.1,.25,1.0);
        const FVector Target=Predict(Now);const double Error=FVector::Dist(Previous,Target);
        MaximumErrorCm=FMath::Max(MaximumErrorCm,WasInitialized?Error:0.);
        HardSnap=!WasInitialized||Dead||Error>FMath::Max(600.,Speed>1000?Speed*2:600.);
        if(HardSnap){Rendered=Target;Correction=FVector::ZeroVector;if(WasInitialized)++HardCorrections;}
        else{Correction=Previous-Target;Correction.Z=Previous.Z-Anchor.Z;CorrectionAt=Now;CorrectionDuration=FMath::Clamp(Error/CorrectionRate,.12,.8);}
        Initialized=true;Blocked=false;++Samples;return true;
    }
    FVector Tick(double Now,double DeltaTime){
        if(!Initialized)return Rendered;
        FVector Target=Predict(Now);const double T=FMath::Clamp((Now-CorrectionAt)/CorrectionDuration,0.,1.);
        const double Blend=T*T*(3-2*T);Target+=Correction*(1-Blend);
        const FVector Previous=Rendered;
        if(HardSnap){HardSnap=false;}
        else {const double MaximumRate=Speed+CorrectionRate;Rendered=FMath::VInterpConstantTo(Rendered,Target,float(FMath::Clamp(DeltaTime,0.,.1)),float(MaximumRate));}
        const double Step=FVector::Dist(Previous,Rendered);MaximumStepCm=FMath::Max(MaximumStepCm,Step);++VisualFrames;if(Step>.05)++MovingFrames;
        if(!ForecastActive(Now)&&Speed>0)++ForecastStops;LastTickAt=Now;return Rendered;
    }
};
