// Deterministic motion tests, recorded real-server replay, and a physical wall probe.
#include "DAoCBridgeSubsystem.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Components/BoxComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickRemoteMotionAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeMotionTest="),Path))return false;
    static bool Started=false,Done=false,CorrectionSent=false;static double Began=0;static int Checks=0;static TArray<TSharedPtr<FJsonValue>> Failures;
    static TSharedPtr<FJsonObject> Report,ProbeRow;static TWeakObjectPtr<AActor> Wall,Probe,SmallProbe;static TArray<TWeakObjectPtr<AActor>> Extra;static FVector Frozen;
    auto Check=[&](bool Ok,const FString& Name){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Name));};
    if(Done)return true;
    if(!Started){
        Started=true;Report=MakeShared<FJsonObject>();
        FBridgeRemoteMotion M;FVector Goal(2000,0,0);M.Sample(1,0,0,FVector::ZeroVector,FVector::ForwardVector,2,5,&Goal,false);
        for(int I=1;I<=120;++I){M.Sample(1,I/60.,0,FVector::ZeroVector,FVector::ForwardVector,2,5,&Goal,false);M.Tick(I/60.,1/60.);}
        Check(FMath::Abs(M.Rendered.X-400)<.1,TEXT("continuous two metres per second"));Check(M.Samples==1,TEXT("repeated snapshots never reset source age"));Check(M.MovingFrames>115,TEXT("movement between server packets"));Check(M.MaximumStepCm<6,TEXT("normal frames are bounded"));
        FBridgeRemoteMotion End;Goal=FVector(500,0,0);End.Sample(1,0,0,FVector::ZeroVector,FVector::ForwardVector,2,5,&Goal,false);
        for(int I=1;I<=360;++I){End.Tick(I/60.,1/60.);Check(End.Rendered.X<=500.01,TEXT("no waypoint overshoot"));}
        Check(FMath::Abs(End.Rendered.X-500)<.1&&!End.ForecastActive(6),TEXT("stops at known waypoint"));
        Goal=FVector(1000,0,0);End.Sample(2,6,0,FVector(500,0,0),FVector::ForwardVector,2,5,&Goal,false);for(int I=1;I<=60;++I)End.Tick(6+I/60.,1/60.);
        Check(FMath::Abs(End.Rendered.X-700)<.1,TEXT("next server waypoint resumes"));
        End.Sample(3,7,0,FVector(695,0,0),FVector::ForwardVector,0,5,nullptr,false);for(int I=1;I<=60;++I)End.Tick(7+I/60.,1/60.);
        Check(FMath::Abs(End.Rendered.X-695)<.1&&!End.ForecastActive(8),TEXT("server stop settles and stays stopped"));
        FBridgeRemoteMotion Stale;Stale.Sample(1,0,0,FVector::ZeroVector,FVector::ForwardVector,2,.2,nullptr,false);for(int I=1;I<=600;++I)Stale.Tick(I/60.,1/60.);
        Check(Stale.Rendered.X<=201&&!Stale.ForecastActive(10),TEXT("unknown destination cannot predict indefinitely"));
        FBridgeRemoteMotion Old;Goal=FVector(10000,0,0);Old.Sample(1,0,0,FVector::ZeroVector,FVector::ForwardVector,2,.5,&Goal,false);for(int I=1;I<=1200;++I)Old.Tick(I/60.,1/60.);
        Check(Old.Rendered.X<=1201&&!Old.ForecastActive(20),TEXT("known route still has freshness limit"));
        Old.Sample(2,20,0,FVector(5000,0,0),FVector::ForwardVector,0,.5,nullptr,false);Check(Old.Rendered.X==5000&&Old.HardCorrections==1,TEXT("large authoritative teleport applied immediately"));
        Old.Sample(3,21,0,FVector(5100,0,0),FVector::ForwardVector,2,.5,&Goal,true);for(int I=1;I<=60;++I)Old.Tick(21+I/60.,1/60.);
        Check(Old.Rendered.X==5100&&!Old.ForecastActive(22),TEXT("dead entity never extrapolates"));
        FBridgeRemoteMotion Aged;Aged.Sample(1,10,8,FVector::ZeroVector,FVector::ForwardVector,2,.5,nullptr,false);Check(!Aged.ForecastActive(10)&&Aged.Rendered.X<=201,TEXT("transport backlog does not rejuvenate sample"));

        FString Text;TArray<TSharedPtr<FJsonValue>> Trace;
        Check(FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Trace)&&!Trace.IsEmpty(),TEXT("real-server trace loaded"));
        if(!Trace.IsEmpty()){
            auto Point=[](const TArray<TSharedPtr<FJsonValue>>& P){return FVector(P[0]->AsNumber()*100,P[2]->AsNumber()*100,P[1]->AsNumber()*100);};
            const double First=Trace[0]->AsObject()->GetNumberField(TEXT("at_ms"));const double Last=Trace.Last()->AsObject()->GetNumberField(TEXT("at_ms"));
            TMap<FString,FBridgeRemoteMotion> Movers;int Index=0;double RawMax=0,SmoothMax=0;int Frames=0,Moving=0,Corrections=0;
            for(double T=0;T<(Last-First)/1000+2;T+=1/60.){
                while(Index<Trace.Num()&&(Trace[Index]->AsObject()->GetNumberField(TEXT("at_ms"))-First)/1000<=T){
                    auto Row=Trace[Index++]->AsObject();FString Id=Row->GetStringField(TEXT("id"));auto Data=Row->GetObjectField(TEXT("motion"));auto& Motion=Movers.FindOrAdd(Id);FVector P=Point(Row->GetArrayField(TEXT("position_m")));
                    if(Motion.Initialized&&(Motion.Speed>0||Data->GetNumberField(TEXT("speed_mps"))>0))RawMax=FMath::Max(RawMax,FVector::Dist(Motion.Anchor,P));
                    const auto& F=Row->GetArrayField(TEXT("forward_xz"));FVector Direction(F[0]->AsNumber(),F[1]->AsNumber(),0),Dest;const TArray<TSharedPtr<FJsonValue>>* GoalValues=nullptr;const bool HasGoal=Data->TryGetArrayField(TEXT("destination_m"),GoalValues);if(HasGoal)Dest=Point(*GoalValues);
                    Motion.Sample(Data->GetIntegerField(TEXT("seq")),T,0,P,Direction,Data->GetNumberField(TEXT("speed_mps")),Data->GetNumberField(TEXT("interval_ms"))/1000,HasGoal?&Dest:nullptr,Row->GetStringField(TEXT("state"))==TEXT("dead"));
                }
                for(auto& Pair:Movers){auto& Motion=Pair.Value;if(Motion.Speed<=0)continue;const FVector Before=Motion.Rendered;Motion.Tick(T,1/60.);const double Step=FVector::Dist(Before,Motion.Rendered);SmoothMax=FMath::Max(SmoothMax,Step);++Frames;if(Step>.05)++Moving;}
            }
            for(auto& Pair:Movers)Corrections+=Pair.Value.HardCorrections;
            Report->SetNumberField(TEXT("trace_events"),Trace.Num());Report->SetNumberField(TEXT("trace_entities"),Movers.Num());Report->SetNumberField(TEXT("raw_max_jump_m"),RawMax/100);Report->SetNumberField(TEXT("smooth_max_regular_step_m"),SmoothMax/100);Report->SetNumberField(TEXT("simulated_moving_frames"),Moving);Report->SetNumberField(TEXT("simulated_frames"),Frames);Report->SetNumberField(TEXT("authoritative_corrections"),Corrections);
            Check(Moving>1000,TEXT("real trace has substantial continuous movement"));Check(SmoothMax<RawMax*.25,TEXT("recorded trace avoids raw packet jumps"));Check(SmoothMax<100,TEXT("regular replay step below one metre at 60 Hz"));
        }
        // Actual saved-world collision queries, in the empty engine test level.
        FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;auto* Barrier=GetWorld()->SpawnActor<AActor>(Params);auto* Box=NewObject<UBoxComponent>(Barrier);Barrier->SetRootComponent(Box);Box->SetBoxExtent(FVector(10,150,150));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Ignore);Box->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);Box->SetCollisionResponseToChannel(ECC_Camera,ECR_Block);Box->RegisterComponent();Barrier->SetActorLocation(FVector(150,0,80));Wall=Barrier;
        ProbeRow=MakeShared<FJsonObject>();ProbeRow->SetStringField(TEXT("id"),TEXT("npc:wall"));ProbeRow->SetStringField(TEXT("kind"),TEXT("npc"));ProbeRow->SetNumberField(TEXT("model_id"),999980);ProbeRow->SetNumberField(TEXT("size"),50);ProbeRow->SetStringField(TEXT("name"),TEXT("Collision probe"));ProbeRow->SetStringField(TEXT("state"),TEXT("walk"));ProbeRow->SetArrayField(TEXT("forward_xz"),{MakeShared<FJsonValueNumber>(1),MakeShared<FJsonValueNumber>(0)});
        auto Data=MakeShared<FJsonObject>();Data->SetNumberField(TEXT("seq"),1);Data->SetNumberField(TEXT("age_ms"),0);Data->SetNumberField(TEXT("speed_mps"),2);Data->SetNumberField(TEXT("interval_ms"),5000);Data->SetArrayField(TEXT("destination_m"),{MakeShared<FJsonValueNumber>(1369),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});ProbeRow->SetObjectField(TEXT("motion"),Data);
        auto BoxActor=[&](FVector Position,FVector Extent,bool Tree){auto* A=GetWorld()->SpawnActor<AActor>();auto* C=NewObject<UBoxComponent>(A);A->SetRootComponent(C);C->SetBoxExtent(Extent);C->SetCollisionEnabled(ECollisionEnabled::QueryOnly);C->SetCollisionObjectType(ECC_WorldStatic);C->SetCollisionResponseToAllChannels(ECR_Ignore);C->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);if(Tree)C->ComponentTags.Add(TEXT("DAoCBridgeTree"));C->RegisterComponent();A->SetActorLocation(Position);Extra.Add(A);return A;};
        BoxActor(FVector(1500,0,-5),FVector(200,200,5),false);BoxActor(FVector(1500,0,15),FVector(20,20,20),true);
        auto TreeRow=MakeShared<FJsonObject>(*ProbeRow);auto TreeData=MakeShared<FJsonObject>(*Data);TreeData->SetNumberField(TEXT("speed_mps"),0);TreeData->RemoveField(TEXT("destination_m"));TreeRow->SetObjectField(TEXT("motion"),TreeData);auto* TreeProbe=CreateEntity(TEXT("npc:treefloor"),TreeRow,FVector(1500,0,0));ApplyRemoteMotion(TEXT("npc:treefloor"),TreeProbe,TreeRow,FVector(1500,0,0));Check(RemoteMotion[TEXT("npc:treefloor")].Grounded&&RemoteMotion[TEXT("npc:treefloor")].RejectedTreeFloors>0&&FMath::Abs(RemoteMotion[TEXT("npc:treefloor")].GroundOffset)<.1,TEXT("tree top is rejected as floor and actual ground beneath remains available"));Check(FMath::Abs(TreeProbe->GetActorLocation().Z)<.1,TEXT("NPC does not climb the low trunk surface"));
        BoxActor(FVector(-350,0,15),FVector(10,150,15),false);auto* Small=GetWorld()->SpawnActor<AActor>();auto* Body=NewObject<UBoxComponent>(Small);Small->SetRootComponent(Body);Body->SetBoxExtent(FVector(10));Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Body->RegisterComponent();Small->SetActorLocation(FVector(-500,0,0));Entities.Add(TEXT("npc:small"),Small);SmallProbe=Small;
        auto SmallRow=MakeShared<FJsonObject>(*ProbeRow);auto SmallData=MakeShared<FJsonObject>(*Data);SmallData->SetArrayField(TEXT("destination_m"),{MakeShared<FJsonValueNumber>(1364),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});SmallRow->SetObjectField(TEXT("motion"),SmallData);ApplyRemoteMotion(TEXT("npc:small"),Small,SmallRow,FVector(-500,0,0));
        Probe=CreateEntity(TEXT("npc:wall"),ProbeRow,FVector::ZeroVector);EntityRows.Add(TEXT("npc:wall"),ProbeRow);ApplyRemoteMotion(TEXT("npc:wall"),Probe.Get(),ProbeRow,FVector::ZeroVector);Began=FPlatformTime::Seconds();
    }
    const double Elapsed=FPlatformTime::Seconds()-Began;TickRemoteMotion(GetWorld()->GetDeltaSeconds());
    if(Elapsed>2&&!CorrectionSent){
        Check(Probe.IsValid()&&Probe->GetActorLocation().X>30&&Probe->GetActorLocation().X<131,TEXT("predicted actor blocked by actual wall"));
        Check(SmallProbe.IsValid()&&SmallProbe->GetActorLocation().X>-450&&SmallProbe->GetActorLocation().X<-369,TEXT("small MOB collides with a low obstacle below the old eighty-centimetre trace"));
        auto Data=ProbeRow->GetObjectField(TEXT("motion"));Data->SetNumberField(TEXT("seq"),2);Data->SetNumberField(TEXT("speed_mps"),0);ApplyRemoteMotion(TEXT("npc:wall"),Probe.Get(),ProbeRow,FVector(350,0,0));
        Check(Probe->GetActorLocation().X<131&&RemoteMotion[TEXT("npc:wall")].Anchor.X==350,TEXT("small server correction preserves authority without teleporting actor through a wall"));CorrectionSent=true;
    }
    if(Elapsed>4){
        Check(Probe->GetActorLocation().X<131&&RemoteMotion[TEXT("npc:wall")].CollisionContacts>0,TEXT("repeated correction frames cannot tunnel through the wall"));
        auto* Local=GetWorld()->SpawnActor<AActor>();Entities.Add(TEXT("player:local"),Local);PlayerPosition=FVector::ZeroVector;bLocalAvailable=true;ProbeRow->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(1367.5),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});Check(!BridgeLineOfSight(TEXT("player:local"),TEXT("npc:wall")),TEXT("server spell visibility uses original position across wall, not blocked visual position"));
        Frozen=Probe->GetActorLocation();auto Data=ProbeRow->GetObjectField(TEXT("motion"));Data->SetNumberField(TEXT("seq"),3);Data->SetBoolField(TEXT("position_valid"),false);ProbeRow->SetStringField(TEXT("state"),TEXT("dead"));ApplyRemoteMotion(TEXT("npc:wall"),Probe.Get(),ProbeRow,FVector::ZeroVector);
        Check(Probe->GetActorLocation().Equals(Frozen,.01),TEXT("death without new coordinates freezes at current visual position"));
        Data->SetNumberField(TEXT("seq"),4);Data->SetBoolField(TEXT("position_valid"),true);ProbeRow->SetStringField(TEXT("state"),TEXT("idle"));ApplyRemoteMotion(TEXT("npc:wall"),Probe.Get(),ProbeRow,FVector(4000,0,0));Check(Probe->GetActorLocation().Equals(FVector(4000,0,0),.01),TEXT("genuine long-distance server reposition is retained"));
        Check(Socket==nullptr,TEXT("tests never connect to the game bridge"));ClearEntities();Check(RemoteMotion.IsEmpty(),TEXT("despawn/session cleanup removes motion state"));if(Wall.IsValid())Wall->Destroy();for(auto A:Extra)if(A.IsValid())A->Destroy();
        Report->SetNumberField(TEXT("checks"),Checks);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server_during_test"),false);Report->SetBoolField(TEXT("recorded_real_packets"),true);
        FString Output;FJsonSerializer::Serialize(Report.ToSharedRef(),TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*(Path+TEXT(".motion-results.json")));Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
