#include "DAoCBridgeGhostMaterials.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "HAL/IConsoleManager.h"

const FName FBridgeGhostMaterials::DepthTag(TEXT("DAoCGhostDepthProxy"));
FBridgeGhostMaterials::~FBridgeGhostMaterials(){Restore();}

bool FBridgeGhostMaterials::Load(const FString& Manifest){
    Restore();Mapping.Empty();Loaded.Empty();
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*Manifest)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid())return false;
    bool Passed=false,Originals=false;
    if(!Root->TryGetBoolField(TEXT("passed"),Passed)||!Passed||!Root->TryGetBoolField(TEXT("originals_unchanged"),Originals)||!Originals)return false;
    const TSharedPtr<FJsonObject>* Rows=nullptr;
    if(!Root->TryGetObjectField(TEXT("materials"),Rows)||(*Rows)->Values.IsEmpty()||(*Rows)->Values.Num()>20000)return false;
    for(const auto& Pair:(*Rows)->Values){
        const FString Key(*Pair.Key);FString Target;
        if(Key.Len()>1024||!Key.StartsWith(TEXT("/"))||!Pair.Value->TryGetString(Target)||Target.Len()>1024||!Target.StartsWith(TEXT("/DAoCVisualBridge/GhostAppearance_v01/Materials/"))){Mapping.Empty();return false;}
        Mapping.Add(Key,Target);
    }
    return true;
}

UMaterialInterface* FBridgeGhostMaterials::Variant(UMaterialInterface* Source){
    // Only MIDs can fall back to their asset parent. Skipping an unmapped constant
    // instance could discard its original static switches and texture coverage.
    for(int32 Depth=0;Source&&Depth<32;++Depth){
        const FString Path=Source->GetPathName();
        if(const FString* Target=Mapping.Find(Path)){
            if(const auto* Cached=Loaded.Find(Path))return Cached->Get();
            auto* Material=LoadObject<UMaterialInterface>(nullptr,**Target);float Opacity=0,Known=0;
            if(!Material||Material->GetBlendMode()!=BLEND_Translucent||
                !Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeGhostOpacity")),Opacity)||
                !Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeGhostDepthKnown")),Known))return nullptr;
            Loaded.Add(Path,TStrongObjectPtr<UMaterialInterface>(Material));return Material;
        }
        auto* Dynamic=Cast<UMaterialInstanceDynamic>(Source);Source=Dynamic?Dynamic->Parent.Get():nullptr;
    }
    return nullptr;
}

UMeshComponent* FBridgeGhostMaterials::ProxyFor(UMeshComponent* Source){
    UMeshComponent* Proxy=nullptr;
    for(auto& Pair:Proxies)if(Pair.Source.Get()==Source){Proxy=Pair.Depth.Get();break;}
    auto* Owner=Source->GetOwner();if(!IsValid(Owner))return nullptr;
    if(!Proxy){
        if(Cast<USkeletalMeshComponent>(Source))Proxy=NewObject<USkeletalMeshComponent>(Owner);
        else if(Cast<UStaticMeshComponent>(Source)&&!Source->IsA<UInstancedStaticMeshComponent>())Proxy=NewObject<UStaticMeshComponent>(Owner);
        if(!Proxy)return nullptr;
        Proxy->ComponentTags.Add(DepthTag);Owner->AddInstanceComponent(Proxy);
        Proxy->SetMobility(EComponentMobility::Movable);
        Proxy->SetupAttachment(Source);Proxy->SetRelativeTransform(FTransform::Identity);
        Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);Proxy->SetGenerateOverlapEvents(false);
        Proxy->SetCastShadow(false);Proxy->SetVisibleInRayTracing(false);Proxy->SetRenderInMainPass(false);Proxy->SetRenderInDepthPass(false);
        Proxy->SetRenderCustomDepth(true);
        Proxies.Add({Source,Proxy});
    }
    if(auto* Skeletal=Cast<USkeletalMeshComponent>(Source)){
        auto* Copy=CastChecked<USkeletalMeshComponent>(Proxy);
        if(Copy->GetSkeletalMeshAsset()!=Skeletal->GetSkeletalMeshAsset())Copy->SetSkeletalMeshAsset(Skeletal->GetSkeletalMeshAsset());
        Copy->SetLeaderPoseComponent(Skeletal,true,true);
    }else if(auto* Static=Cast<UStaticMeshComponent>(Source)){
        auto* Copy=CastChecked<UStaticMeshComponent>(Proxy);
        if(Copy->GetStaticMesh()!=Static->GetStaticMesh())Copy->SetStaticMesh(Static->GetStaticMesh());
    }
    if(!Proxy->IsRegistered())Proxy->RegisterComponent();
    Proxy->SetCullDistance(Source->LDMaxDrawDistance);
    Proxy->SetBoundsScale(Source->BoundsScale);
    return Proxy;
}

void FBridgeGhostMaterials::Restore(){
    for(auto& Slot:Slots)if(auto* Component=Slot.Component.Get()){
        if(Component->GetMaterial(Slot.Index)==Slot.Ghost.Get())Component->SetMaterial(Slot.Index,Slot.Original.Get());
    }
    for(auto& Pair:Proxies)if(auto* Depth=Pair.Depth.Get()){
        if(auto* Owner=Depth->GetOwner())Owner->RemoveInstanceComponent(Depth);
        Depth->DestroyComponent();
    }
    Proxies.Empty();Slots.Empty();CurrentActor.Reset();
}

bool FBridgeGhostMaterials::Apply(AActor* Actor,bool Confirmed,bool Ghost,bool RaceFigure){
    Missing=0;
    if(!Confirmed||!Ghost||!IsValid(Actor)){Restore();return true;}
    auto* CustomDepth=IConsoleManager::Get().FindConsoleVariable(TEXT("r.CustomDepth"));
    if(!CustomDepth||CustomDepth->GetInt()==0){++Missing;Restore();return false;}
    if(CurrentActor.Get()!=Actor){Restore();CurrentActor=Actor;}
    Proxies.RemoveAll([](const FProxy& Pair){return !Pair.Depth.IsValid();});
    struct FPending{UMeshComponent* Component;int32 Index;UMaterialInterface* Source;UMaterialInterface* Parent;};
    TArray<FPending> Pending;TArray<UMeshComponent*> Components;Actor->GetComponents(Components);
    for(auto* Component:Components){
        if(!IsValid(Component)||Component->ComponentHasTag(DepthTag)||!Component->IsVisible())continue;
        if((!Cast<USkeletalMeshComponent>(Component)&&!Cast<UStaticMeshComponent>(Component))||Component->IsA<UInstancedStaticMeshComponent>()){++Missing;continue;}
        if(Pending.Num()>1024||Component->GetNumMaterials()>128){++Missing;break;}
        for(int32 Index=0;Index<Component->GetNumMaterials();++Index){
            auto* Source=Component->GetMaterial(Index);if(!Source)continue;
            for(auto& Slot:Slots)if(Slot.Component.Get()==Component&&Slot.Index==Index&&Source==Slot.Ghost.Get()){Source=Slot.Original.Get();break;}
            auto* Parent=Variant(Source);if(!Parent){++Missing;continue;}
            Pending.Add({Component,Index,Source,Parent});
        }
    }
    // A partial library must never turn only half of an outfit into a ghost.
    if(Missing||Pending.IsEmpty()){Restore();return false;}
    TSet<UMeshComponent*> Active;
    for(auto& Item:Pending){
        auto* Proxy=ProxyFor(Item.Component);if(!Proxy){++Missing;Restore();return false;}Active.Add(Item.Component);
        FSlot* Slot=Slots.FindByPredicate([&](const FSlot& S){return S.Component.Get()==Item.Component&&S.Index==Item.Index;});
        if(!Slot){FSlot New;New.Component=Item.Component;New.Index=Item.Index;Slots.Add(MoveTemp(New));Slot=&Slots.Last();}
        if(Slot->Original.Get()!=Item.Source||!Slot->Ghost.IsValid()){
            Slot->Original.Reset(Item.Source);Slot->Ghost.Reset(UMaterialInstanceDynamic::Create(Item.Parent,Item.Component));
        }
        if(!Slot->Ghost.IsValid()){++Missing;Restore();return false;}
        Slot->Ghost->CopyMaterialUniformParameters(Item.Source);
        Slot->Ghost->SetScalarParameterValue(TEXT("BridgeGhostOpacity"),RaceFigure?.9f:.5f);
        Slot->Ghost->SetScalarParameterValue(TEXT("BridgeGhostDepthKnown"),1.f);
        Proxy->SetMaterial(Item.Index,Item.Source);Item.Component->SetMaterial(Item.Index,Slot->Ghost.Get());
    }
    // Equipment can remove/hide a mesh without deleting the actor.
    for(int32 I=Slots.Num()-1;I>=0;--I)if(!Pending.ContainsByPredicate([&](const FPending& P){return P.Component==Slots[I].Component.Get()&&P.Index==Slots[I].Index;})){
        auto& Slot=Slots[I];if(auto* C=Slot.Component.Get())if(C->GetMaterial(Slot.Index)==Slot.Ghost.Get())C->SetMaterial(Slot.Index,Slot.Original.Get());Slots.RemoveAt(I);
    }
    for(int32 I=Proxies.Num()-1;I>=0;--I)if(!Active.Contains(Proxies[I].Source.Get())){
        if(auto* C=Proxies[I].Depth.Get()){if(auto* Owner=C->GetOwner())Owner->RemoveInstanceComponent(C);C->DestroyComponent();}Proxies.RemoveAt(I);
    }
    return true;
}
