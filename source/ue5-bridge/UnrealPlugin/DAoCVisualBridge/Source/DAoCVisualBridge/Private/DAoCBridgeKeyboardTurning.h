#pragma once
#include "CoreMinimal.h"

// Original modern-mode keyboard turning. Input availability is decided by the
// existing movement/session/posture gates, not by a second movement controller.
struct FBridgeKeyboardTurning {
    struct FFrame {float BodyYaw=0,CameraYaw=0,Strafe=0;bool Turning=false;};
    static FFrame Advance(bool Enabled,bool Left,bool Right,bool RightMouse,bool LeftMouse,float Delta,float BodyYaw,float CameraYaw){
        FFrame Frame;Frame.BodyYaw=BodyYaw;Frame.CameraYaw=CameraYaw;
        if(!Enabled||!FMath::IsFinite(Delta)||Delta<=0||!FMath::IsFinite(BodyYaw)||!FMath::IsFinite(CameraYaw))return Frame;
        const float Side=(Right?1.f:0.f)-(Left?1.f:0.f);
        if(RightMouse){Frame.Strafe=Side;return Frame;}
        if(Side==0)return Frame;
        Frame.Turning=true;
        Frame.BodyYaw=FRotator::NormalizeAxis(BodyYaw+Side*180.f*FMath::Min(Delta,1.f));
        if(!LeftMouse)Frame.CameraYaw=Frame.BodyYaw;
        return Frame;
    }
};
