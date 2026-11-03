#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "GameFramework/SpringArmComponent.h"

void UDAoCBridgeSubsystem::ApplyCameraView(){
    if(!IsValid(PlayerPawn)||!PlayerPawn->CameraArm)return;
    PlayerPawn->CameraArm->TargetArmLength=bFirstPerson?0.f:ThirdPersonDistance;
    PlayerPawn->CameraArm->bDoCollisionTest=!bFirstPerson;
    PlayerPawn->CameraArm->bEnableCameraLag=!bFirstPerson;
}
void UDAoCBridgeSubsystem::ToggleFirstPerson(){
    if(PlayerIsDead()||bChatOpen||bExiting)return;
    bFirstPerson=!bFirstPerson;ApplyCameraView();
}
void UDAoCBridgeSubsystem::AdjustCameraZoom(float Steps){
    if(!FMath::IsFinite(Steps)||FMath::Abs(Steps)>20||PlayerIsDead()||bChatOpen||bExiting)return;
    if(bFirstPerson){if(Steps>=0)return;bFirstPerson=false;ThirdPersonDistance=80;}
    ThirdPersonDistance=FMath::Clamp(ThirdPersonDistance-Steps*60.f,80.f,1200.f);ApplyCameraView();
}
