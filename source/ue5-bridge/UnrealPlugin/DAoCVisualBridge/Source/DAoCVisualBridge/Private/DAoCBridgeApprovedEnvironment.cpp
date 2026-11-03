#include "DAoCBridgeApprovedEnvironment.h"
#include "Engine/World.h"
#include "Engine/LevelStreamingAlwaysLoaded.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonSerializer.h"

namespace {
FString Text(TSharedPtr<FJsonObject> O,const TCHAR* Key){FString V;if(O)O->TryGetStringField(Key,V);return V;}
TArray<TSharedPtr<FJsonValue>> Array(TSharedPtr<FJsonObject> O,const TCHAR* Key){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(Key,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
TArray<TSharedPtr<FJsonObject>> Bindings(UWorld* World){
    TArray<TSharedPtr<FJsonObject>> Result;FString File,Json;TSharedPtr<FJsonObject> Root;double Version=0;
    if(!World||!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeEnvironmentCatalog="),File)||!FFileHelper::LoadFileToString(Json,*File)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root)||!Root||!Root->TryGetNumberField(TEXT("version"),Version)||Version!=1)return Result;
    const FString Map=World->GetOutermost()->GetName();
    for(auto Value:Array(Root,TEXT("bindings"))){if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();for(auto Package:Array(Row,TEXT("maps")))if(Package->Type==EJson::String&&Package->AsString()==Map){Result.Add(Row);break;}}
    return Result;
}
ULevelStreaming* FindLayer(UWorld* World,const FString& Package){for(auto* Level:World->GetStreamingLevels())if(Level&&Level->GetWorldAssetPackageFName()==FName(*Package))return Level;return nullptr;}
}

void EnsureDAoCApprovedEnvironment(UWorld* World){
    for(auto Binding:Bindings(World)){
        const FString Package=Text(Binding,TEXT("layer"));if(!Package.StartsWith(TEXT("/Game/")))continue;
        auto* Level=FindLayer(World,Package);
        if(!Level){
            // Add a single transient reference when an art-map save omitted it.
            // Existing saved sublevels are reused, so their actors cannot duplicate.
            auto* Asset=LoadObject<UWorld>(nullptr,*(Package+TEXT(".")+FPackageName::GetShortName(Package)));if(!Asset){UE_LOG(LogTemp,Warning,TEXT("Approved environment layer unavailable: %s"),*Package);continue;}
            Level=NewObject<ULevelStreamingAlwaysLoaded>(World,NAME_None,RF_Transient);Level->SetWorldAssetByPackageName(FName(*Package));Level->LevelTransform=FTransform::Identity;World->AddStreamingLevel(Level);
            Level->SetShouldBeLoaded(true);Level->SetShouldBeVisible(true);World->FlushLevelStreaming(EFlushLevelStreamingType::Full);
        }
        if(!Level->IsLevelLoaded())continue;
        TArray<UStaticMeshComponent*> Terrain,OldWater;
        for(TActorIterator<AActor> It(World);It;++It){
            if(It->ActorHasTag(FName(*Text(Binding,TEXT("tag")))))continue;
            TInlineComponentArray<UStaticMeshComponent*> Components;It->GetComponents(Components);
            for(auto* C:Components){if(!C->GetStaticMesh()||!C->GetComponentTransform().Equals(FTransform::Identity,.01))continue;const FString Mesh=C->GetStaticMesh()->GetPathName();
                if(Mesh==Text(Binding,TEXT("terrain_mesh")))Terrain.Add(C);
                if(Mesh==Text(Binding,TEXT("old_water_mesh")))OldWater.Add(C);
            }
        }
        if(Terrain.Num()!=1||OldWater.Num()>1)continue;
        auto* C=Terrain[0];auto* Current=C->GetMaterial(0);const FString Existing=Current?Current->GetPathName():TEXT("");
        const FString Approved=Text(Binding,TEXT("terrain_material"));
        // A different, newly authored terrain material requires a deliberate merge.
        if(Existing!=Approved&&Existing!=Text(Binding,TEXT("previous_terrain_material")))continue;
        if(auto* Material=LoadObject<UMaterialInterface>(nullptr,*Approved)){
            C->SetMaterial(0,Material);if(!OldWater.IsEmpty()){OldWater[0]->SetVisibility(false);OldWater[0]->SetHiddenInGame(true);}
        }
    }
}

TSharedPtr<FJsonObject> InspectDAoCApprovedEnvironment(UWorld* World){
    auto Result=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Rows;
    for(auto Binding:Bindings(World)){
        auto Row=MakeShared<FJsonObject>();const FString Package=Text(Binding,TEXT("layer"));auto* Layer=FindLayer(World,Package);int32 References=0,Actors=0,Components=0,Instances=0,Logs=0,Algae=0,Aquatic=0,Visible=0,OldWaterComponents=0;bool TerrainMatches=false,OldWaterHidden=true;
        for(auto* Level:World->GetStreamingLevels())if(Level&&Level->GetWorldAssetPackageFName()==FName(*Package))++References;
        for(TActorIterator<AActor> It(World);It;++It){if(!It->ActorHasTag(FName(*Text(Binding,TEXT("tag")))))continue;++Actors;
            TInlineComponentArray<UStaticMeshComponent*> Parts;It->GetComponents(Parts);for(auto* C:Parts){if(!C->GetStaticMesh())continue;++Components;if(auto* I=Cast<UInstancedStaticMeshComponent>(C))Instances+=I->GetInstanceCount();const FString Path=C->GetStaticMesh()->GetPathName().ToLower();if(Path.Contains(TEXT("fallenlog"))||Path.Contains(TEXT("driftwood_log")))++Logs;if(Path.Contains(TEXT("algae_film")))++Algae;if(Path.Contains(TEXT("river_aquatic_communities")))++Aquatic;if(!It->IsHidden()&&C->IsVisible()&&!C->bHiddenInGame)++Visible;}
        }
        for(TActorIterator<AActor> It(World);It;++It){if(It->ActorHasTag(FName(*Text(Binding,TEXT("tag")))))continue;TInlineComponentArray<UStaticMeshComponent*> Parts;It->GetComponents(Parts);for(auto* C:Parts){if(!C->GetStaticMesh()||!C->GetComponentTransform().Equals(FTransform::Identity,.01))continue;const FString Mesh=C->GetStaticMesh()->GetPathName();if(Mesh==Text(Binding,TEXT("terrain_mesh")))TerrainMatches=C->GetMaterial(0)&&C->GetMaterial(0)->GetPathName()==Text(Binding,TEXT("terrain_material"));if(Mesh==Text(Binding,TEXT("old_water_mesh"))){++OldWaterComponents;OldWaterHidden&=!C->IsVisible()&&C->bHiddenInGame;}}}
        Row->SetStringField(TEXT("release_id"),Text(Binding,TEXT("release_id")));Row->SetStringField(TEXT("layer"),Package);Row->SetNumberField(TEXT("references"),References);Row->SetBoolField(TEXT("loaded"),Layer&&Layer->IsLevelLoaded());Row->SetNumberField(TEXT("actors"),Actors);Row->SetNumberField(TEXT("components"),Components);Row->SetNumberField(TEXT("instances"),Instances);Row->SetNumberField(TEXT("logs"),Logs);Row->SetNumberField(TEXT("algae_films"),Algae);Row->SetNumberField(TEXT("aquatic_components"),Aquatic);Row->SetNumberField(TEXT("visible_components"),Visible);Row->SetBoolField(TEXT("terrain_matches"),TerrainMatches);Row->SetBoolField(TEXT("old_water_hidden"),OldWaterHidden);Row->SetNumberField(TEXT("old_water_components"),OldWaterComponents);Rows.Add(MakeShared<FJsonValueObject>(Row));
    }
    Result->SetArrayField(TEXT("bindings"),Rows);return Result;
}
