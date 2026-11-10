#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

namespace {
bool GroundNumber(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key,double& N,double Min,double Max){return Row.IsValid()&&Row->TryGetNumberField(Key,N)&&FMath::IsFinite(N)&&N>=Min&&N<=Max&&FMath::FloorToDouble(N)==N;}
bool GroundArray(const TSharedPtr<FJsonObject>& Row,const TCHAR* Key,int32 Count,TArray<double>& Out){
    const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(!Row.IsValid()||!Row->TryGetArrayField(Key,A)||A->Num()!=Count)return false;Out.Empty();
    for(const auto& V:*A){if(V->Type!=EJson::Number||!FMath::IsFinite(V->AsNumber()))return false;Out.Add(V->AsNumber());}return true;
}
}

void UDAoCBridgeSubsystem::ApplyGroundObjects(const TSharedPtr<FJsonObject>& Snapshot,TSet<FString>& Seen){
    const TSharedPtr<FJsonObject>* State=nullptr;const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;double Generation=0;
    if(!Snapshot->TryGetObjectField(TEXT("world_objects"),State)||!GroundNumber(*State,TEXT("generation"),Generation,0,2147483647)||!(*State)->TryGetArrayField(TEXT("objects"),Rows)||Rows->Num()>128)return;
    GroundObjectGeneration=int64(Generation);
    if(!GroundObjectCatalog.IsValid()){
        FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/WorldObjects_v01/world_catalog.json"),Text;TSharedPtr<FJsonObject> Catalog;
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectCatalog="),Path);
        const TSharedPtr<FJsonObject>* Definitions=nullptr;
        if(!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog)||!Catalog->TryGetObjectField(TEXT("models"),Definitions))return;
        GroundObjectCatalog=*Definitions;
    }
    TSet<int32> LivingOids;
    for(const FString& Id:Seen)if(!Id.StartsWith(TEXT("object:")))LivingOids.Add(FCString::Atoi(*Id.Mid(Id.Find(TEXT(":"))+1)));
    TSet<int32> Used;
    const float Cull=Quality==TEXT("accessible")?6000:Quality==TEXT("balanced")?9000:Quality==TEXT("high")?12500:15000;
    for(const auto& Value:*Rows){
        if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();double Oid=0,Model=0,Heading=0,RowGeneration=0;FString Id,Kind,Token;TArray<double> P;
        if(!GroundNumber(Row,TEXT("oid"),Oid,1,65535)||!GroundNumber(Row,TEXT("model_id"),Model,0,32767)||!GroundNumber(Row,TEXT("heading_4096"),Heading,0,4095)||!GroundNumber(Row,TEXT("world_generation"),RowGeneration,0,2147483647)||RowGeneration!=Generation||
           !Row->TryGetStringField(TEXT("id"),Id)||Id!=FString::Printf(TEXT("object:%d"),int32(Oid))||!Row->TryGetStringField(TEXT("kind"),Kind)||Kind!=TEXT("object")||!Row->TryGetStringField(TEXT("object_token"),Token)||Token.Len()!=64||!GroundArray(Row,TEXT("position_m"),3,P)||
           P[0]<0||P[0]>1638.4||P[2]<0||P[2]>1638.4||P[1]<-100||P[1]>2000||LivingOids.Contains(int32(Oid))||Used.Contains(int32(Oid)))continue;
        Used.Add(int32(Oid));FVector Position((P[0]-1364)*100,(P[2]-1263)*100,(P[1]-130)*100);
        if(FVector::DistSquared(PlayerPosition,Position)>FMath::Square(Cull))continue;
        const TSharedPtr<FJsonObject>* Definition=nullptr;
        const bool Fallback=!GroundObjectCatalog->TryGetObjectField(FString::FromInt(int32(Model)),Definition);
        if(Fallback&&!GroundObjectCatalog->TryGetObjectField(TEXT("488"),Definition))continue;
        FString Asset;const TSharedPtr<FJsonObject>* Frame=nullptr;TArray<double> T,Q,S;
        if(!(*Definition)->TryGetStringField(TEXT("asset"),Asset)||!Asset.StartsWith(TEXT("/DAoCVisualBridge/Equipment_All_v01/Model_"))||!(*Definition)->TryGetObjectField(TEXT("world_transform"),Frame)||!GroundArray(*Frame,TEXT("translation_cm"),3,T)||!GroundArray(*Frame,TEXT("quaternion_xyzw"),4,Q)||!GroundArray(*Frame,TEXT("scale"),3,S))continue;
        const FTransform Transform(FQuat(Q[0],Q[1],Q[2],Q[3]),FVector(T[0],T[1],T[2]),FVector(S[0],S[1],S[2]));if(!Transform.IsValid())continue;
        const double Floor=GroundHeight(Position.X,Position.Y);if(FMath::Abs(Floor-Position.Z)<400)Position.Z=Floor;
        AActor* Actor=Entities.Contains(Id)?Entities[Id].Get():nullptr;
        if(Actor&&EntityModels.FindRef(Id)!=int32(Model)){Actor->Destroy();Entities.Remove(Id);Actor=nullptr;}
        if(!Actor){
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Asset);if(!Mesh)continue;
            FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Owner=GetWorld()->SpawnActor<AActor>(Position,FRotator::ZeroRotator,Params);if(!Owner)continue;
            auto* Root=NewObject<USceneComponent>(Owner);Owner->SetRootComponent(Root);Root->SetMobility(EComponentMobility::Movable);Root->RegisterComponent();Owner->SetActorLocation(Position);
            auto* Body=NewObject<UStaticMeshComponent>(Owner);Body->SetupAttachment(Root);Body->SetMobility(EComponentMobility::Movable);Body->SetStaticMesh(Mesh);Body->SetRelativeTransform(Transform);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);Body->SetCastShadow(false);Body->SetCullDistance(Cull);Body->RegisterComponent();
            Owner->Tags.Add(TEXT("DAoCBridgeEntity"));Owner->Tags.Add(TEXT("DAoCBridgeGroundObject"));Actor=Owner;Entities.Add(Id,Actor);EntityModels.Add(Id,int32(Model));
        }
        Actor->SetActorLocationAndRotation(Position,FRotator(0,Heading*360./4096.,0));
        Seen.Add(Id);EntityRows.Add(Id,Row);
    }
}

bool UDAoCBridgeSubsystem::SendGroundObjectAction(const FString& Action,const FString& Id){
    if(Action!=TEXT("target_object")&&Action!=TEXT("target_loot")&&Action!=TEXT("get_object"))return false;
    if(!bLocalAvailable||Session.IsEmpty()||bExiting||GroundObjectGeneration<0)return false;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("world_generation"),GroundObjectGeneration);
    if(Action!=TEXT("target_loot")){
        const auto Row=EntityRows.FindRef(Id);FString Token;double Generation=0;
        if(!Id.StartsWith(TEXT("object:"))||!Row.IsValid()||!Row->TryGetStringField(TEXT("object_token"),Token)||Token.Len()!=64||!Row->TryGetNumberField(TEXT("world_generation"),Generation)||Generation!=GroundObjectGeneration)return false;
        V->SetStringField(TEXT("entity_id"),Id);V->SetStringField(TEXT("object_token"),Token);
    }
    if(Action==TEXT("get_object")&&PlayerIsDead())return false;
    Send(Action,V);return true;
}
