#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Engine/World.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickJumpLandingAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeJumpLandingTest="),File))return false;
    static TWeakObjectPtr<ADAoCBridgeCharacter> Pawn;static int32 Phase=0,Checks=0,InitialLandings=0;static double Began=FPlatformTime::Seconds(),Apex=0;static bool SawAir=false;static TArray<FString> Failures;
    auto Check=[&](bool Value,const TCHAR* Label){++Checks;if(!Value)Failures.Add(Label);};
    if(!Pawn.IsValid()){
        auto* Floor=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Floor);Floor->AddInstanceComponent(Box);Floor->SetRootComponent(Box);
        Box->SetBoxExtent(FVector(1000,1000,50));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Box->RegisterComponent();Floor->SetActorLocation(FVector(0,0,-50));Floor->SetActorEnableCollision(true);
        FActorSpawnParameters P;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Pawn=GetWorld()->SpawnActor<ADAoCBridgeCharacter>(FVector(0,0,93),FRotator::ZeroRotator,P);Pawn->GetCharacterMovement()->bRunPhysicsWithNoController=true;Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
        Check(FMath::IsNearlyEqual(Pawn->GetCharacterMovement()->JumpZVelocity,460.f),TEXT("original jump speed"));
        Check(FMath::IsNearlyEqual(Pawn->GetCharacterMovement()->GetGravityZ(),-1800.f,.1f),TEXT("original gravity"));
        return true;
    }
    auto* Move=Pawn->GetCharacterMovement();const double Height=Pawn->FeetPosition().Z;
    if(Phase==0&&Move->IsMovingOnGround()){
        InitialLandings=Pawn->LandingCount;Pawn->PendingLandingSpeedMps=0;Pawn->Jump();Phase=1;
    }else if(Phase==1){
        Apex=FMath::Max(Apex,Height);SawAir|=Move->IsFalling();
        if(SawAir&&Move->IsMovingOnGround()&&Pawn->LandingCount>InitialLandings){
            Check(Apex>50&&Apex<75,TEXT("actual jump apex near original 0.59m"));
            Check(Pawn->LastLandingSpeedMps>3&&Pawn->LastLandingSpeedMps<6,TEXT("safe jump records pre-impact speed"));
            Check(Pawn->PendingLandingSpeedMps==Pawn->LastLandingSpeedMps,TEXT("landing speed survives walking velocity reset"));
            Pawn->TeleportFeet(FVector(0,0,900));Check(Pawn->PendingLandingSpeedMps==0,TEXT("teleport clears stale landing"));
            InitialLandings=Pawn->LandingCount;Move->SetMovementMode(MOVE_Falling);Phase=2;
        }
    }else if(Phase==2&&Move->IsMovingOnGround()&&Pawn->LandingCount>InitialLandings){
        Check(Pawn->LastLandingSpeedMps>15&&Pawn->LastLandingSpeedMps<20,TEXT("actual nine-metre fall captures impact velocity"));
        Check(Pawn->PendingLandingSpeedMps>15,TEXT("fall retains speed until outgoing ground packet"));
        Check(Move->Velocity.Z==0,TEXT("engine already cleared instantaneous vertical velocity"));Phase=3;
    }
    if(FPlatformTime::Seconds()-Began>20){UE_LOG(LogTemp,Warning,TEXT("JumpQA phase=%d feet=%f mode=%d velocity=%f landings=%d tick=%d collision=%d"),Phase,Height,int(Move->MovementMode),Move->Velocity.Z,Pawn->LandingCount,int(Move->IsComponentTickEnabled()),int(Pawn->GetActorEnableCollision()));Check(false,TEXT("physics trajectory timeout"));Phase=3;}
    if(Phase==3){
        auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("jump_apex_cm"),Apex);Report->SetNumberField(TEXT("fall_impact_mps"),Pawn->LastLandingSpeedMps);
        TArray<TSharedPtr<FJsonValue>> Errors;for(auto& E:Failures)Errors.Add(MakeShared<FJsonValueString>(E));Report->SetArrayField(TEXT("failures"),Errors);
        FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);Phase=4;
    }
    return true;
}
