#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "DAoCBridgeCharacter.generated.h"
class USpringArmComponent;
UCLASS()
class DAOCVISUALBRIDGE_API ADAoCBridgeCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    ADAoCBridgeCharacter(const FObjectInitializer& ObjectInitializer=FObjectInitializer::Get());
    UPROPERTY() TObjectPtr<USpringArmComponent> CameraArm;
    virtual void BeginPlay() override;
    virtual void Landed(const FHitResult& Hit) override;
    double PendingLandingSpeedMps=0;
    double LastLandingSpeedMps=0;
    int32 LandingCount=0;
    double AirborneSince=0;
    FVector FeetPosition() const;
    void TeleportFeet(const FVector& Feet);
};
