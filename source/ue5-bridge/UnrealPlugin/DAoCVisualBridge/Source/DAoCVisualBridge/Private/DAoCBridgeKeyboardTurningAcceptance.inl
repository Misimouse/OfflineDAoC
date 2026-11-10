// Included inside the private key-dispatch fixture, after Press/Capture exist.
if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeKeyboardTurnInputTest"))){
    bHavePlayer=true;bNavigationReady=true;bControls=true;PlayerPosition=FVector(0,0,10000);ServerRunSpeed=600;ChatClosedAt=-100;
    auto TurnVitals=PlayerState->GetObjectField(TEXT("vitals"));TurnVitals->SetBoolField(TEXT("alive"),true);TurnVitals->SetBoolField(TEXT("sitting"),false);PlayerState->SetBoolField(TEXT("ready"),true);
    auto RunTurn=[&](const FString& Binding,float Delta){Press(Binding);if(PlayerPawn)PlayerPawn->ConsumeMovementInputVector();LastMove=FPlatformTime::Seconds();UpdateControls(Delta);Outgoing.Empty();};
    RunTurn(TEXT("Left"),0);const float StartYaw=PlayerPawn->GetActorRotation().Yaw;
    RunTurn(TEXT("Left"),.25f);Check(FMath::Abs(FRotator::NormalizeAxis(PlayerPawn->GetActorRotation().Yaw-StartYaw+45))<.01f,TEXT("actual idle Left input turns character at original rate"));
    Check(FMath::Abs(FRotator::NormalizeAxis(CameraYaw-PlayerPawn->GetActorRotation().Yaw))<.01f,TEXT("actual idle turn swings camera behind character"));
    Check(PlayerPawn->GetPendingMovementInputVector().IsNearlyZero(),TEXT("idle turning does not invent translation"));
    const float OrbitStart=PlayerPawn->GetActorRotation().Yaw;CameraYaw=81;bLeftPointerHeld=true;
    RunTurn(TEXT("Right"),.25f);Check(FMath::Abs(FRotator::NormalizeAxis(PlayerPawn->GetActorRotation().Yaw-OrbitStart-45))<.01f&&CameraYaw==81,TEXT("actual left-button camera stays independent of character turn"));
    bLeftPointerHeld=false;bRightPointerHeld=true;CameraYaw=0;PlayerPawn->SetActorRotation(FRotator::ZeroRotator);
    RunTurn(TEXT("Right"),.25f);Check(CameraYaw==0&&FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&PlayerPawn->GetPendingMovementInputVector().Y>.9f,TEXT("actual right-mouse turn key strafes without angular input"));
    bRightPointerHeld=false;PlayerPawn->GetCharacterMovement()->StopMovementImmediately();
    Press(TEXT("Left"));Outgoing.Empty();LastMove=0;UpdateControls(.25f);auto Heading=Capture(TEXT("move"));
    if(Heading){const auto Direction=Heading->GetArrayField(TEXT("forward_xz"));const float YawRadians=FMath::DegreesToRadians(PlayerPawn->GetActorRotation().Yaw);
        Check(Direction.Num()==2&&FMath::Abs(Direction[0]->AsNumber()-FMath::Cos(YawRadians))<.0001&&FMath::Abs(Direction[1]->AsNumber()-FMath::Sin(YawRadians))<.0001,TEXT("idle keyboard yaw reaches existing authoritative movement packet"));
        Check(FMath::IsNearlyZero(Heading->GetNumberField(TEXT("speed_mps")),.001),TEXT("idle turn packet does not invent running speed"));}
    CameraYaw=0;PlayerPawn->SetActorRotation(FRotator::ZeroRotator);
    bLocalMounted=true;RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f),TEXT("riding blocks keyboard body turn"));bLocalMounted=false;
    const FString TurnSession=Session;Session.Empty();RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f),TEXT("missing session blocks keyboard body turn"));Session=TurnSession;
    bRightPointerHeld=false;TurnVitals->SetBoolField(TEXT("sitting"),true);
    RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&CameraYaw==0&&PlayerPawn->GetPendingMovementInputVector().IsNearlyZero(),TEXT("actual seated character does not turn or move"));TurnVitals->SetBoolField(TEXT("sitting"),false);
    TurnVitals->SetBoolField(TEXT("alive"),false);RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&CameraYaw==0,TEXT("actual corpse cannot turn from keyboard"));TurnVitals->SetBoolField(TEXT("alive"),true);
    bChatOpen=true;RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&CameraYaw==0,TEXT("chat blocks actual keyboard turning"));bChatOpen=false;
    bOptionsOpen=true;RunTurn(TEXT("Left"),.25f);Check(FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&CameraYaw==0,TEXT("options blocks actual keyboard turning"));bOptionsOpen=false;
    auto PreviousTracking=TargetTracking;TargetTracking=MakeShared<FBridgeTargetTracking>();
    auto* TurnTarget=GetWorld()->SpawnActor<AActor>();auto* TurnRoot=NewObject<UBoxComponent>(TurnTarget);TurnTarget->SetRootComponent(TurnRoot);TurnRoot->RegisterComponent();TurnRoot->SetCollisionEnabled(ECollisionEnabled::NoCollision);TurnTarget->SetActorLocation(PlayerPawn->FeetPosition()+FVector(1000,0,0));
    const FString TurnId=TEXT("npc:keyboard-turn-fixture");Entities.Add(TurnId,TurnTarget);auto TurnRow=MakeShared<FJsonObject>();TurnRow->SetNumberField(TEXT("health"),1);TurnRow->SetBoolField(TEXT("targetable"),true);EntityRows.Add(TurnId,TurnRow);
    Check(TargetTracking->Begin(1,TEXT("follow"),TurnId,TEXT("Private target"),PlayerPawn->FeetPosition(),TurnTarget->GetActorLocation(),true),TEXT("private follow fixture begins"));
    RunTurn(TEXT("Left"),.25f);Check(!TargetTracking->Active,TEXT("actual keyboard turn cancels follow"));
    Check(TargetTracking->Begin(3,TEXT("stick"),TurnId,TEXT("Private target"),PlayerPawn->FeetPosition(),TurnTarget->GetActorLocation(),true),TEXT("private stick fixture begins"));
    RunTurn(TEXT("Left"),.25f);Check(!TargetTracking->Active,TEXT("actual keyboard turn cancels stick"));
    Check(TargetTracking->Begin(4,TEXT("face"),TurnId,TEXT("Private target"),PlayerPawn->FeetPosition(),TurnTarget->GetActorLocation(),true),TEXT("private face fixture begins"));
    RunTurn(TEXT("Right"),.25f);Check(TargetTracking->Active&&FMath::Abs(FRotator::NormalizeAxis(PlayerPawn->GetActorRotation().Yaw-45))<.01f,TEXT("original face remains active and applies keyboard angular offset"));
    CameraYaw=0;bRightPointerHeld=true;RunTurn(TEXT("Right"),.25f);Check(TargetTracking->Active&&FMath::IsNearlyZero(PlayerPawn->GetActorRotation().Yaw,.01f)&&PlayerPawn->GetPendingMovementInputVector().Y>.9f,TEXT("original face permits turn-key right-mouse strafe around target"));
    TargetTracking=PreviousTracking;TurnTarget->Destroy();Entities.Remove(TurnId);EntityRows.Remove(TurnId);bRightPointerHeld=false;TurnVitals->RemoveField(TEXT("alive"));KeyConfiguration->Reset();Outgoing.Empty();
}
