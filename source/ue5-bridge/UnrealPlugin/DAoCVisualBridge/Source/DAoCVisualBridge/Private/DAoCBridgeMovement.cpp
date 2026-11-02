#include "DAoCBridgeMovement.h"
#include "GameFramework/Character.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"

bool UDAoCBridgeMovement::StepUp(const FVector& GravDir,const FVector& Delta,const FHitResult& Hit,FStepDownResult* Out){
    ++StepCalls;
    if(Super::StepUp(GravDir,Delta,Hit,Out))return true;
    if(!CharacterOwner||GravDir.Z>-.99||Hit.ImpactNormal.Z<-.05||Hit.ImpactNormal.Z>=GetWalkableFloorZ())return false;
    const auto* Capsule=CharacterOwner->GetCapsuleComponent();const FVector Start=UpdatedComponent->GetComponentLocation();
    const float Feet=Start.Z-Capsule->GetScaledCapsuleHalfHeight();
    if(Hit.ImpactPoint.Z<Feet||Hit.ImpactPoint.Z>Feet+MaxStepHeight)return false;
    ++ThresholdCandidates;
    // Imported DAoC access lips and stair risers have steep or vertical faces. At high
    // frame rates a normal forward substep can stop short of their flat top.
    // Only retry if a real, walkable landing exists within one capsule width.
    const float Radius=Capsule->GetScaledCapsuleRadius();
    const FVector Direction=Acceleration.IsNearlyZero()?Delta.GetSafeNormal2D():Acceleration.GetSafeNormal2D();
    for(const float Reach:{Radius+12,Radius*2+12}){
        if(Delta.Size2D()>=Reach)continue;
        const FVector Forward=Direction*Reach;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeThreshold),false,CharacterOwner);FHitResult Floor;
        if(!GetWorld()->LineTraceSingleByChannel(Floor,FVector(Start.X+Forward.X,Start.Y+Forward.Y,Feet+MaxStepHeight+3),
            FVector(Start.X+Forward.X,Start.Y+Forward.Y,Feet-3),ECC_Pawn,Query))continue;
        // Original two-sided floors can have downward triangle winding. The
        // downward pick's supporting face is the upward-facing side.
        if(Floor.ImpactNormal.Z<0){Floor.ImpactNormal=-Floor.ImpactNormal;Floor.Normal=Floor.ImpactNormal;}
        if(!IsWalkable(Floor)||Floor.ImpactPoint.Z<Feet+3||Floor.ImpactPoint.Z>Feet+MaxStepHeight)continue;
        ++ThresholdLandings;
        const FVector SavedVelocity=Velocity;
        // Reuse UE's full up/forward/down capsule sweeps, ceiling checks and
        // rollback. Closed door leaves and walls retain their collision.
        if(!Super::StepUp(GravDir,Forward,Hit,Out)){++ThresholdBlocked;continue;}
        Velocity=SavedVelocity;bJustTeleported=true;bForceNextFloorCheck=true;++ThresholdSteps;return true;
    }
    return false;
}
