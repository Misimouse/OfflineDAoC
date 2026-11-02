// Four camera directions, actual shared-font rendering; no account or bridge socket.
#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/World.h"
#include "Camera/CameraActor.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "UnrealClient.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickNameplateRenderTest(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNameplateRender="),Path))return false;
    static double Start=0;static int Phase=-1;static uint32 Captures=0;static bool Done=false;static TArray<TSharedPtr<FJsonValue>> Samples;
    if(Done)return true;auto* PC=GetWorld()->GetFirstPlayerController();if(!PC)return true;
    if(Start==0){
        Start=FPlatformTime::Seconds();Session=TEXT("nameplate-render-test");Sequence=0;ClearEntities();
        auto Snapshot=MakeShared<FJsonObject>();Snapshot->SetStringField(TEXT("session"),Session);Snapshot->SetNumberField(TEXT("seq"),1);Snapshot->SetNumberField(TEXT("zone_id"),207);
        Snapshot->SetArrayField(TEXT("origin_m"),{MakeShared<FJsonValueNumber>(1364),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263)});
        TArray<TSharedPtr<FJsonValue>> Rows;
        for(int I=0;I<4;++I){
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),I==0?TEXT("player:local"):FString::Printf(TEXT("npc:%d"),I));Row->SetStringField(TEXT("kind"),I==0?TEXT("player"):TEXT("npc"));Row->SetNumberField(TEXT("model_id"),999980);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);
            Row->SetStringField(TEXT("name"),I==1?TEXT("Hibernia"):I==2?TEXT("Objetivo"):TEXT("Enemigo"));Row->SetStringField(TEXT("guild"),I==1?TEXT("Guardia"):TEXT(""));
            Row->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(I==0?1361:1364),MakeShared<FJsonValueNumber>(130),MakeShared<FJsonValueNumber>(1263+(I-2)*2)});Row->SetArrayField(TEXT("forward_xz"),{MakeShared<FJsonValueNumber>(0),MakeShared<FJsonValueNumber>(1)});
            auto Plate=MakeShared<FJsonObject>();Plate->SetBoolField(TEXT("show"),true);Plate->SetArrayField(TEXT("color_rgb"),{MakeShared<FJsonValueNumber>(I==1?175:245),MakeShared<FJsonValueNumber>(I==1?223:0),MakeShared<FJsonValueNumber>(I==1?208:0)});Row->SetObjectField(TEXT("nameplate"),Plate);Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Snapshot->SetArrayField(TEXT("entities"),Rows);ApplySnapshot(Snapshot);Entities[TEXT("player:local")]->SetActorHiddenInGame(true);
        InteractionState=MakeShared<FJsonObject>();auto Target=MakeShared<FJsonObject>();Target->SetStringField(TEXT("id"),TEXT("npc:2"));InteractionState->SetObjectField(TEXT("target"),Target);
        Camera=GetWorld()->SpawnActor<ACameraActor>();PC->SetViewTarget(Camera);
    }
    const double Elapsed=FPlatformTime::Seconds()-Start;const int Current=FMath::Min(int(Elapsed/2),3);
    if(Current!=Phase){Phase=Current;const float Angle=FMath::DegreesToRadians(Current*90.f);const FVector Position(-750*FMath::Cos(Angle),-750*FMath::Sin(Angle),200);Camera->SetActorLocation(Position);Camera->SetActorRotation((FVector(0,0,90)-Position).Rotation());}
    if(Elapsed-Current*2>.8&&!(Captures&(1<<Current))){FScreenshotRequest::RequestScreenshot(Path+FString::Printf(TEXT("-angle%d.png"),Current),true,false);Captures|=1<<Current;auto S=MakeShared<FJsonObject>();S->SetNumberField(TEXT("angle"),Current*90);S->SetNumberField(TEXT("names"),NameplatesVisible);Samples.Add(MakeShared<FJsonValueObject>(S));}
    if(Elapsed>8){auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("angles"),Samples);bool Passed=Captures==15;for(auto S:Samples)Passed&=S->AsObject()->GetIntegerField(TEXT("names"))==3;Report->SetBoolField(TEXT("passed"),Passed);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".json")));Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),PC,EQuitPreference::Quit,false);}
    return true;
}
