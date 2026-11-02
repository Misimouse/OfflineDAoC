#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovement.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
ADAoCBridgeCharacter::ADAoCBridgeCharacter(const FObjectInitializer& ObjectInitializer):Super(ObjectInitializer.SetDefaultSubobjectClass<UDAoCBridgeMovement>(ACharacter::CharacterMovementComponentName)){
    GetCapsuleComponent()->InitCapsuleSize(28,88);
    GetMesh()->SetVisibility(false);GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    bUseControllerRotationYaw=true;bUseControllerRotationPitch=false;bUseControllerRotationRoll=false;
    auto* Move=GetCharacterMovement();Move->MaxWalkSpeed=477.5;Move->MaxAcceleration=1600;
    Move->BrakingDecelerationWalking=1600;Move->GroundFriction=8;Move->MaxStepHeight=45;
    Move->SetWalkableFloorAngle(50);Move->bOrientRotationToMovement=false;
    Move->bUseFlatBaseForFloorChecks=true;
    CameraArm=CreateDefaultSubobject<USpringArmComponent>(TEXT("BridgeCameraArm"));
    CameraArm->SetupAttachment(GetCapsuleComponent());CameraArm->SetRelativeLocation(FVector(0,0,82));
    CameraArm->TargetArmLength=350;CameraArm->ProbeSize=12;CameraArm->ProbeChannel=ECC_Camera;
    CameraArm->bDoCollisionTest=true;CameraArm->bUsePawnControlRotation=true;
    CameraArm->bEnableCameraLag=true;CameraArm->CameraLagSpeed=18;CameraArm->CameraLagMaxDistance=35;
    CameraArm->bEnableCameraRotationLag=false;
}
FVector ADAoCBridgeCharacter::FeetPosition()const{return GetActorLocation()-FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight());}
void ADAoCBridgeCharacter::TeleportFeet(const FVector& Feet){GetCharacterMovement()->StopMovementImmediately();SetActorLocation(Feet+FVector(0,0,GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),false,nullptr,ETeleportType::TeleportPhysics);if(CameraArm){const bool Lag=CameraArm->bEnableCameraLag;CameraArm->bEnableCameraLag=false;CameraArm->TickComponent(0.f,LEVELTICK_All,nullptr);CameraArm->bEnableCameraLag=Lag;}}
