#pragma once
#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "DAoCBridgeMovement.generated.h"
UCLASS()
class DAOCVISUALBRIDGE_API UDAoCBridgeMovement : public UCharacterMovementComponent {
    GENERATED_BODY()
public:
    int32 ThresholdSteps=0;
    int32 StepCalls=0,ThresholdCandidates=0,ThresholdLandings=0,ThresholdBlocked=0;
    virtual bool StepUp(const FVector& GravDir,const FVector& Delta,const FHitResult& Hit,FStepDownResult* OutStepDownResult=nullptr) override;
};
