// Explicit offline acceptance mode. Uses real CharacterMovement and the saved
// map collision layer; never sends teleports or movement to the game server.
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeMovement.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"

namespace { FVector TraversalPoint(const TSharedPtr<FJsonValue>& V){const auto& A=V->AsArray();return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());} }
bool UDAoCBridgeSubsystem::TickTraversal(float Dt){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeTraversal="),File))return false;
    if(!bTraversalLoaded){
        bTraversalLoaded=true;TraversalOutput=File+TEXT(".results.json");
        FString Text;TSharedPtr<FJsonObject> Root;
        if(!FFileHelper::LoadFileToString(Text,*File)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)){
            UE_LOG(LogTemp,Error,TEXT("Invalid traversal file"));UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
        }
        bool Open=false;Root->TryGetBoolField(TEXT("doors_open"),Open);for(auto& Pair:Doors){Pair.Value.Open=Open;Pair.Value.Alpha=Open?1:0;}TickDoors(0);
        double CloseAt=0;if(Root->TryGetNumberField(TEXT("close_doors_at_s"),CloseAt))TraversalCloseAt=CloseAt;
        for(TActorIterator<APawn> It(GetWorld());It;++It){It->SetActorEnableCollision(false);It->SetActorHiddenInGame(true);}
        for(const auto& Value:Root->GetArrayField(TEXT("routes"))){
            FTraversalRun Run;Run.Definition=Value->AsObject();Run.Start=TraversalPoint(Run.Definition->GetField<EJson::Array>(TEXT("start")));
            for(const auto& P:Run.Definition->GetArrayField(TEXT("points")))Run.Points.Add(TraversalPoint(P));
            FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Pawn=GetWorld()->SpawnActor<ADAoCBridgeCharacter>(Run.Start+FVector(0,0,90.2),FRotator::ZeroRotator,Params);
            Pawn->GetCharacterMovement()->bRunPhysicsWithNoController=true;
            Pawn->AIControllerClass=LoadClass<AController>(nullptr,TEXT("/Script/AIModule.AIController"));Pawn->SpawnDefaultController();
            Pawn->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
            Pawn->GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera,ECR_Ignore);
            double Step=0;if(Run.Definition->TryGetNumberField(TEXT("step_override_cm"),Step))Pawn->GetCharacterMovement()->MaxStepHeight=Step;
            Run.Pawn=Pawn;Run.Previous=Pawn->FeetPosition();TraversalRuns.Add(MoveTemp(Run));
        }
    }
    TraversalTime+=Dt;
    if(TraversalCloseAt>0&&TraversalTime>TraversalCloseAt){for(auto& Pair:Doors)Pair.Value.Open=false;TraversalCloseAt=-1;}
    bool AllDone=true;
    for(auto& Run:TraversalRuns){
        if(Run.Done)continue;AllDone=false;auto* Pawn=Run.Pawn.Get();if(!Pawn){Run.Done=true;continue;}
        Run.Elapsed+=Dt;const FVector Feet=Pawn->FeetPosition();auto* Move=Pawn->GetCharacterMovement();
        Run.Distance+=FVector::Dist2D(Feet,Run.Previous);Run.Previous=Feet;
        if(Run.Elapsed<1)continue;
        ++Run.Frames;if(Move->IsMovingOnGround())++Run.Grounded;
        if(Pawn->CameraArm->IsCollisionFixApplied())++Run.CameraAdjusted;
        Run.MaxFallSpeed=FMath::Max(Run.MaxFallSpeed,double(-Pawn->GetVelocity().Z));
        Run.PeakSpeed=FMath::Max(Run.PeakSpeed,Pawn->GetVelocity().Size2D()/100);
        for(const auto& Pair:Doors)if(!Pair.Value.Open&&Pair.Value.Alpha>.02&&Run.Elapsed>3){++Run.DoorHeldSamples;break;}
        const FVector Target=Run.Points[Run.Point];const float Distance=FVector::Dist2D(Feet,Target);
        const bool Reached=Distance<18&&FMath::Abs(Feet.Z-Target.Z)<28;
        if(Reached&&Run.Point+1<Run.Points.Num()){++Run.Point;continue;}
        if(Reached){Pawn->ConsumeMovementInputVector();Move->StopMovementImmediately();Run.Still+=Dt;}
        else {FVector Direction=Target-Feet;Direction.Z=0;Pawn->SetActorRotation(Direction.Rotation());Pawn->AddMovementInput(Direction.GetSafeNormal(),FMath::Clamp(Distance/90.f,.12f,1.f),true);}
        double Timeout=30;Run.Definition->TryGetNumberField(TEXT("timeout_s"),Timeout);
        double Minimum=0;Run.Definition->TryGetNumberField(TEXT("minimum_s"),Minimum);
        if((Run.Still>.4&&Run.Elapsed>Minimum)||Run.Elapsed>Timeout||Feet.Z<Run.Start.Z-2000){
            auto Result=MakeShared<FJsonObject>();Result->SetStringField(TEXT("id"),Run.Definition->GetStringField(TEXT("id")));
            Result->SetBoolField(TEXT("reached"),Run.Still>.4);Result->SetNumberField(TEXT("waypoints_reached"),Run.Point+(Reached?1:0));
            Result->SetNumberField(TEXT("waypoints_total"),Run.Points.Num());Result->SetNumberField(TEXT("distance_cm"),Run.Distance);
            Result->SetNumberField(TEXT("elapsed_s"),Run.Elapsed);Result->SetNumberField(TEXT("grounded_fraction"),double(Run.Grounded)/FMath::Max(1,Run.Frames));
            Result->SetNumberField(TEXT("final_distance_cm"),Distance);Result->SetNumberField(TEXT("max_fall_speed_cm_s"),Run.MaxFallSpeed);
            Result->SetBoolField(TEXT("final_grounded"),Move->IsMovingOnGround());Result->SetNumberField(TEXT("camera_adjusted_frames"),Run.CameraAdjusted);
            Result->SetNumberField(TEXT("step_height_cm"),Move->MaxStepHeight);
            Result->SetNumberField(TEXT("threshold_steps"),Cast<UDAoCBridgeMovement>(Move)->ThresholdSteps);
            auto* BridgeMove=Cast<UDAoCBridgeMovement>(Move);Result->SetNumberField(TEXT("step_calls"),BridgeMove->StepCalls);Result->SetNumberField(TEXT("threshold_candidates"),BridgeMove->ThresholdCandidates);Result->SetNumberField(TEXT("threshold_landings"),BridgeMove->ThresholdLandings);Result->SetNumberField(TEXT("threshold_blocked"),BridgeMove->ThresholdBlocked);
            Result->SetNumberField(TEXT("peak_speed_mps"),Run.PeakSpeed);Result->SetNumberField(TEXT("door_held_samples"),Run.DoorHeldSamples);
            FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(TraversalBlock),false,Pawn);
            Query.bReturnFaceIndex=true;
            if(GetWorld()->SweepSingleByChannel(Hit,Feet+FVector(0,0,90),Target+FVector(0,0,90),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(28,88),Query)){
                if(auto* Body=Cast<UStaticMeshComponent>(Hit.GetComponent()))if(Body->GetStaticMesh())Result->SetStringField(TEXT("blocking_mesh"),Body->GetStaticMesh()->GetPathName());
                Result->SetArrayField(TEXT("hit_point"),{MakeShared<FJsonValueNumber>(Hit.ImpactPoint.X),MakeShared<FJsonValueNumber>(Hit.ImpactPoint.Y),MakeShared<FJsonValueNumber>(Hit.ImpactPoint.Z)});
                Result->SetArrayField(TEXT("hit_normal"),{MakeShared<FJsonValueNumber>(Hit.ImpactNormal.X),MakeShared<FJsonValueNumber>(Hit.ImpactNormal.Y),MakeShared<FJsonValueNumber>(Hit.ImpactNormal.Z)});
                Result->SetNumberField(TEXT("hit_face"),Hit.FaceIndex);
                Result->SetBoolField(TEXT("hit_step_allowed"),Hit.GetComponent()&&Hit.GetComponent()->CanCharacterStepUp(Pawn));
            }
            Result->SetArrayField(TEXT("final_feet"),{MakeShared<FJsonValueNumber>(Feet.X),MakeShared<FJsonValueNumber>(Feet.Y),MakeShared<FJsonValueNumber>(Feet.Z)});
            bool Blocked=false;Run.Definition->TryGetBoolField(TEXT("expect_blocked"),Blocked);
            bool Passed=Blocked?(!Reached&&Distance>60&&Run.Distance>10&&Move->IsMovingOnGround()):(Run.Still>.4&&Move->IsMovingOnGround()&&Run.MaxFallSpeed<700);
            bool RequireHold=false;Run.Definition->TryGetBoolField(TEXT("require_door_hold"),RequireHold);if(RequireHold)Passed&=Run.DoorHeldSamples>10;
            Result->SetBoolField(TEXT("passed"),Passed&&bNavigationReady);TraversalResults.Add(MakeShared<FJsonValueObject>(Result));
            Run.Done=true;Pawn->Destroy();
        }
    }
    if(AllDone){
        TraversalFinishWait+=Dt;if(TraversalFinishWait<1.3)return true;
        auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("map"),GetWorld()->GetMapName());Root->SetBoolField(TEXT("real_server"),false);
        Root->SetBoolField(TEXT("real_character_movement"),true);Root->SetArrayField(TEXT("routes"),TraversalResults);
        TArray<TSharedPtr<FJsonValue>> States;for(const auto& Pair:Doors){auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("id"),double(Pair.Key));State->SetBoolField(TEXT("open"),Pair.Value.Open);State->SetNumberField(TEXT("alpha"),Pair.Value.Alpha);States.Add(MakeShared<FJsonValueObject>(State));}Root->SetArrayField(TEXT("doors"),States);
        FString Text;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*TraversalOutput);
        UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);
    }
    return true;
}
