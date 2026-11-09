#include "DAoCBridgeStealthMaterials.h"
#include "DAoCBridgeSubsystem.h"
#include "Components/MeshComponent.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UDAoCBridgeSubsystem::ResetLocalStealthMaterials(){
    if(StealthMaterials)StealthMaterials->Restore();
}

void UDAoCBridgeSubsystem::TickLocalStealthMaterials(){
    const auto Row=EntityRows.FindRef(TEXT("player:local"));
    bool Known=false,Hidden=false;
    if(Row){Row->TryGetBoolField(TEXT("stealth_render_known"),Known);Row->TryGetBoolField(TEXT("stealth_render_hidden"),Hidden);}
    auto* Actor=Entities.FindRef(TEXT("player:local")).Get();
    if(!Known||!Hidden||!IsValid(Actor)){ResetLocalStealthMaterials();return;}
    if(!bStealthMaterialsLoadTried){
        bStealthMaterialsLoadTried=true;
        FString Path;
        if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthMaterials="),Path))Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/stealth_materials.json");
        auto Prepared=MakeShared<FBridgeStealthMaterials>();
        if(Prepared->Load(Path))StealthMaterials=Prepared;
        else UE_LOG(LogTemp,Warning,TEXT("DAoC stealth material catalogue unavailable; preserving original appearance."));
    }
    if(StealthMaterials)StealthMaterials->Apply(Actor,Known,Hidden);
}

FBridgeStealthMaterials::~FBridgeStealthMaterials(){Restore();}

bool FBridgeStealthMaterials::Load(const FString& Manifest){
    Restore();Mapping.Empty();Loaded.Empty();
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*Manifest)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid())return false;
    bool Passed=false;if(!Root->TryGetBoolField(TEXT("passed"),Passed)||!Passed)return false;
    const TSharedPtr<FJsonObject>* Rows=nullptr;
    if(!Root->TryGetObjectField(TEXT("materials"),Rows)||(*Rows)->Values.Num()>20000)return false;
    for(const auto& Pair:(*Rows)->Values){
        const FString Key(*Pair.Key);FString Target;
        if(Key.Len()>1024||!Key.StartsWith(TEXT("/"))||!Pair.Value->TryGetString(Target)||Target.Len()>1024||!Target.StartsWith(TEXT("/DAoCVisualBridge/Stealth_v01/"))){Mapping.Empty();return false;}
        Mapping.Add(Key,Target);
    }
    return !Mapping.IsEmpty();
}

UMaterialInterface* FBridgeStealthMaterials::Variant(UMaterialInterface* Source){
    // Appearance and dyes use MIDs. Find their original asset parent, whose
    // prepared counterpart retains its static switches and inherited settings.
    for(int32 Depth=0;Source&&Depth<32;++Depth){
        const FString Path=Source->GetPathName();
        if(const FString* Target=Mapping.Find(Path)){
            if(const auto* Cached=Loaded.Find(Path))return Cached->Get();
            auto* Material=LoadObject<UMaterialInterface>(nullptr,**Target);
            if(!Material||Material->GetBlendMode()!=BLEND_Translucent)return nullptr;
            float Opacity=0;
            if(!Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeStealthOpacity")),Opacity))return nullptr;
            Loaded.Add(Path,TStrongObjectPtr<UMaterialInterface>(Material));return Material;
        }
        // An unmapped constant instance can carry static switches. Falling
        // back to its root would silently lose those original permutations.
        auto* Instance=Cast<UMaterialInstanceDynamic>(Source);
        Source=Instance?Instance->Parent.Get():nullptr;
    }
    return nullptr;
}

void FBridgeStealthMaterials::Restore(){
    for(auto& Slot:Slots)if(auto* Component=Slot.Component.Get()){
        // A new outfit may already have replaced the override. Preserve that
        // newer material rather than putting the previous outfit back on it.
        if(Component->GetMaterial(Slot.Index)==Slot.Hidden.Get()){
            Component->SetMaterial(Slot.Index,Slot.Original.Get());++Restorations;
        }
    }
    Slots.Empty();CurrentActor.Reset();Missing=0;
}

void FBridgeStealthMaterials::Apply(AActor* Actor,bool Confirmed,bool Hidden){
    if(!Confirmed||!Hidden||!IsValid(Actor)){if(!Slots.IsEmpty()||CurrentActor.IsValid())Restore();return;}
    if(CurrentActor.Get()!=Actor){Restore();CurrentActor=Actor;}
    Slots.RemoveAll([](const FSlot& Slot){return !Slot.Component.IsValid();});Missing=0;
    TArray<UMeshComponent*> Components;Actor->GetComponents<UMeshComponent>(Components);
    for(auto* Component:Components){
        if(!IsValid(Component))continue;
        const int32 Count=FMath::Min(Component->GetNumMaterials(),128);
        for(int32 Index=0;Index<Count;++Index){
            auto* Source=Component->GetMaterial(Index);if(!Source)continue;
            const int32 Found=Slots.IndexOfByPredicate([Component,Index](const FSlot& S){return S.Component.Get()==Component&&S.Index==Index;});
            if(Found!=INDEX_NONE){
                if(Source==Slots[Found].Hidden.Get())continue;
                Slots.RemoveAt(Found);
            }
            auto* Parent=Variant(Source);if(!Parent){++Missing;continue;}
            auto* Copy=UMaterialInstanceDynamic::Create(Parent,Component);if(!Copy){++Missing;continue;}
            Copy->CopyMaterialUniformParameters(Source);
            Copy->SetScalarParameterValue(TEXT("BridgeStealthOpacity"),.45f);
            FSlot Slot;Slot.Component=Component;Slot.Index=Index;
            Slot.Original.Reset(Source);Slot.Hidden.Reset(Copy);
            Component->SetMaterial(Index,Copy);Slots.Add(MoveTemp(Slot));++Replacements;
        }
    }
}
