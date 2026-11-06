#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "DAoCBridgeWaterData.h"
#include "Dom/JsonObject.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"

void UDAoCBridgeSubsystem::UpdateWaterMovement(bool Enabled,bool StopHorizontal){
    if(!WaterData){
        WaterData=MakeShared<FBridgeWaterData>();
        FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/WaterMovement_v01/water_field.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWaterField="),Path);WaterData->Load(Path);
    }
    auto* Pawn=PlayerPawn.Get();if(!Pawn)return;
    auto* Move=Pawn->GetCharacterMovement();const bool Before=bLocalSwimming;
    bLocalSwimming=false;LocalGroundSurface=TEXT("dirt");
    if(Enabled&&Heights.Num()==257*257&&WaterData->Ready){
        const FVector Feet=Pawn->FeetPosition();const auto Water=WaterData->Sample(Feet,GroundHeight(Feet.X,Feet.Y));
        bLocalSwimming=Water.Swimming;LocalWaterHeight=Water.Height;
        LocalGroundSurface=Water.Swimming?TEXT("swim"):Water.Wading?TEXT("water"):TEXT("dirt");
        if(bLocalSwimming){
            // UE flying physics supplies swept horizontal collision without an
            // artificial volume that could cover a bridge. Only the original
            // swimming flag is sent to DAoC; free flight is never enabled.
            if(Move->MovementMode!=MOVE_Flying)Move->SetMovementMode(MOVE_Flying);
            Move->MaxFlySpeed=ServerRunSpeed*.65f;
            Move->BrakingDecelerationFlying=1600;
            const FVector Horizontal(Move->Velocity.X,Move->Velocity.Y,0);
            const FVector Limited=StopHorizontal?FVector::ZeroVector:Horizontal.GetClampedToMaxSize(Move->MaxFlySpeed);
            Move->Velocity.X=Limited.X;Move->Velocity.Y=Limited.Y;
            Move->Velocity.Z=FMath::Clamp((Water.TargetFeet-Feet.Z)*4.f,-300.f,300.f);
        }
    }
    if(Before&&!bLocalSwimming&&Move->MovementMode==MOVE_Flying){Move->SetMovementMode(MOVE_Falling);Move->Velocity.Z=0;}
}
void UDAoCBridgeSubsystem::ClearWaterMovement(){
    if(auto* Pawn=PlayerPawn.Get())if(bLocalSwimming&&Pawn->GetCharacterMovement()->MovementMode==MOVE_Flying){Pawn->GetCharacterMovement()->StopMovementImmediately();Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Falling);}
    bLocalSwimming=false;LocalGroundSurface=TEXT("dirt");LocalWaterHeight=0;
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::WaterMovementReport()const{
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("ready"),WaterData&&WaterData->Ready);
    Report->SetBoolField(TEXT("swimming"),bLocalSwimming);Report->SetStringField(TEXT("surface"),LocalGroundSurface);
    Report->SetStringField(TEXT("animation"),AnimationStates.FindRef(TEXT("player:local")));
    if(auto* Pawn=PlayerPawn.Get()){
        Report->SetNumberField(TEXT("speed_mps"),Pawn->GetVelocity().Size2D()/100);
        Report->SetNumberField(TEXT("vertical_speed_mps"),Pawn->GetVelocity().Z/100);
        Report->SetBoolField(TEXT("on_ground"),Pawn->GetCharacterMovement()->IsMovingOnGround());
        const FVector Feet=Pawn->FeetPosition();
        Report->SetArrayField(TEXT("feet_m"),{MakeShared<FJsonValueNumber>(Feet.X/100+1364),MakeShared<FJsonValueNumber>(Feet.Z/100+130),MakeShared<FJsonValueNumber>(Feet.Y/100+1263)});
    }
    Report->SetNumberField(TEXT("surface_native_z_cm"),LocalWaterHeight);return Report;
}
