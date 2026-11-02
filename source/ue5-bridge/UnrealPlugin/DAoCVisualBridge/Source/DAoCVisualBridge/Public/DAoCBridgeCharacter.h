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
    FVector FeetPosition() const;
    void TeleportFeet(const FVector& Feet);
};
