#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"

void UDAoCBridgeSubsystem::UpdateInteractionTest(float Elapsed){
    if(Elapsed>14&&!(InteractionTestSteps&1)){
        FString BestId;double Best=600;bool MerchantFound=false;
        for(const auto& Pair:Entities){
            auto* Row=EntityRows.Find(Pair.Key);FVector Aim;if(!Row||!Pair.Key.StartsWith(TEXT("npc:"))||!CanSelect(Pair.Key,Aim))continue;
            FString Guild;(*Row)->TryGetStringField(TEXT("guild"),Guild);const bool Merchant=Guild.Contains(TEXT("merchant"),ESearchCase::IgnoreCase);
            const double Distance=FVector::Dist(PlayerPosition,Pair.Value->GetActorLocation());if(Distance>=600)continue;
            if((Merchant&&!MerchantFound)||(Merchant==MerchantFound&&Distance<Best)){BestId=Pair.Key;Best=Distance;MerchantFound=Merchant;}
        }
        if(!BestId.IsEmpty()){
            FVector Aim;FVector2D Pixel;if(CanSelect(BestId,Aim)&&GetWorld()->GetFirstPlayerController()->ProjectWorldLocationToScreen(Aim,Pixel))if(TargetAtCursor(false,Pixel)==BestId)InteractionTestSteps|=4;
            SelectEntity(BestId);InteractionTestSteps|=1;
        }
    }
    if(Elapsed>15&&(InteractionTestSteps&1)&&!(InteractionTestSteps&2)&&!CurrentTarget().IsEmpty()){InteractSelected();InteractionTestSteps|=2;}
    if(Elapsed>19&&bCaptured&&(InteractionTestSteps&2)&&!(InteractionTestSteps&8)){Send(TEXT("dismiss_interaction"));SelectEntity(TEXT(""));InteractionTestSteps|=8;}
}
bool UDAoCBridgeSubsystem::TickInteractionAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeInteractionTest="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    TArray<TSharedPtr<FJsonValue>> Failures;int32 Checks=0;auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Input;TSharedPtr<FJsonObject> Fixture;
    Check(FFileHelper::LoadFileToString(Input,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Fixture),TEXT("fixture parsed"));
    if(Fixture.IsValid()){
        const auto& Cases=Fixture->GetArrayField(TEXT("cases"));
        for(const auto& Value:Cases){
            auto State=Value->AsObject();ApplyInteraction(State);
            Check(InteractionState==State,TEXT("server state retained"));
            Check(CurrentTarget()==State->GetObjectField(TEXT("target"))->GetStringField(TEXT("id")),TEXT("target identity"));
            Check(InteractionRevision==State->GetIntegerField(TEXT("revision")),TEXT("UI revision"));
            Check(InteractionOverlay.IsValid()&&InteractionPanel.IsValid(),TEXT("viewport widgets created"));
        }
        auto* Actor=GetWorld()->SpawnActor<AStaticMeshActor>();auto* Root=Actor->GetStaticMeshComponent();
        auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));Root->SetMobility(EComponentMobility::Movable);Root->SetStaticMesh(Cube);Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);Actor->SetActorLocation(FVector(0,0,50));
        auto AddPart=[&](FVector Position,FVector Scale,bool Visible,bool Equipment){auto* Part=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(Part);Part->SetStaticMesh(Cube);Part->SetupAttachment(Root);Part->SetRelativeLocation(Position);Part->SetRelativeScale3D(Scale);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetVisibility(Visible);if(Equipment)Part->ComponentTags.Add(TEXT("DAoCBridgeEquipment"));Part->RegisterComponent();return Part;};
        AddPart(FVector(0,0,150),FVector(.5,.5,4),true,false);
        AddPart(FVector(0,0,1000),FVector(20),false,false);
        AddPart(FVector(1000,0,0),FVector(20),true,true);
        const FBox Bounds=EntitySelectionBounds(Actor);
        Check(Bounds.IsValid&&FMath::IsNearlyEqual(Bounds.Max.Z,400.,.1),TEXT("selection includes full visible body above the original root"));
        Check(Bounds.IsValid&&Bounds.Max.X<51&&Bounds.Max.Z<401,TEXT("hidden meshes and equipped weapons do not enlarge picking"));
        Check(Root->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&Root->GetComponentScale()==FVector::OneVector,TEXT("picking never changes movement collision or actor scale"));
        Entities.Add(TEXT("npc:pick-test"),Actor);auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("health"),1);Row->SetNumberField(TEXT("realm"),0);EntityRows.Add(TEXT("npc:pick-test"),Row);PlayerPosition=FVector::ZeroVector;
        auto* PC=GetWorld()->GetFirstPlayerController();auto* TestCamera=GetWorld()->SpawnActor<ACameraActor>(FVector(0,-600,150),FRotator(0,90,0));
        if(PC&&PC->PlayerCameraManager){
            PC->SetViewTarget(TestCamera);PC->PlayerCameraManager->UpdateCamera(0);
            auto Pick=[&](FVector Point){FVector2D Pixel;return PC->ProjectWorldLocationToScreen(Point,Pixel)?TargetAtCursor(false,Pixel):FString();};
            Check(Pick(FVector(0,0,350))==TEXT("npc:pick-test"),TEXT("click selects upper visible body beyond the old fixed-radius circle"));
            Check(Pick(FVector(0,0,20))==TEXT("npc:pick-test"),TEXT("click still selects the lower visible body"));
            Check(Pick(FVector(150,0,200)).IsEmpty(),TEXT("click outside the visible body does not use a giant circular target"));
            Row->SetBoolField(TEXT("targetable"),false);Check(Pick(FVector(0,0,350)).IsEmpty(),TEXT("untargetable state still rejects a body click"));
            Row->SetBoolField(TEXT("targetable"),true);Row->SetNumberField(TEXT("health"),0);Check(Pick(FVector(0,0,350)).IsEmpty(),TEXT("dead state still rejects a body click"));
        }else Check(false,TEXT("projection acceptance has a player controller and camera"));
        ClearEntities();TestCamera->Destroy();Check(CurrentTarget().IsEmpty()&&!InteractionOverlay.IsValid(),TEXT("disconnect removes stale UI"));
        Check(Socket==nullptr,TEXT("offline test has no bridge socket"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("checks"),Checks);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".native.json")));
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
