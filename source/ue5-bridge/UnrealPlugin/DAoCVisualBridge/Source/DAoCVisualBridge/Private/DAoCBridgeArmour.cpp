#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"

namespace {
TSharedPtr<FJsonObject> ArmourObject(TSharedPtr<FJsonObject> O,const FString& K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
FString ArmourString(TSharedPtr<FJsonObject> O,const FString& K){FString V;if(O)O->TryGetStringField(K,V);return V;}
int32 ArmourNumber(TSharedPtr<FJsonObject> O,const FString& K,int32 D=0){double V=D;if(O)O->TryGetNumberField(K,V);return int32(V);}
}

void UDAoCBridgeSubsystem::ApplyBodyArmour(AActor* Actor,TSharedPtr<FJsonObject> Equipment){
    auto* Figure=Cast<ASkeletalMeshActor>(Actor);if(!Figure||!ArmourCatalog)return;
    auto* Component=Figure->GetSkeletalMeshComponent();auto* Mesh=Component->GetSkeletalMeshAsset();if(!Mesh)return;
    auto Definition=ArmourObject(ArmourObject(ArmourCatalog,TEXT("figures")),Mesh->GetPathName());if(!Definition)return;
    auto Clothes=ArmourObject(Definition,TEXT("clothes"));auto Variants=ArmourObject(Definition,TEXT("variants"));
    TMap<FString,TSharedPtr<FJsonObject>> Worn;const TArray<TSharedPtr<FJsonValue>>* Items=nullptr;
    if(Equipment&&Equipment->TryGetArrayField(TEXT("items"),Items))for(auto Value:*Items){
        if(Value->Type!=EJson::Object)continue;auto Item=Value->AsObject();FString Slot;
        switch(ArmourNumber(Item,TEXT("slot"))){case 25:Slot=TEXT("body");break;case 28:Slot=TEXT("arms");break;case 22:Slot=TEXT("gloves");break;case 27:Slot=TEXT("legs");break;case 23:Slot=TEXT("boots");break;default:continue;}
        Worn.Add(Slot,Item);
    }
    const TArray<TSharedPtr<FJsonValue>>* Sections=nullptr;if(!Definition->TryGetArrayField(TEXT("sections"),Sections))return;
    auto* Master=LoadObject<UMaterialInterface>(nullptr,*ArmourString(ArmourCatalog,TEXT("material")));
    auto Models=ArmourObject(ArmourCatalog,TEXT("models"));auto Textures=ArmourObject(ArmourCatalog,TEXT("textures"));
    const FString Gender=ArmourString(Definition,TEXT("gender"));auto* Render=Mesh->GetResourceForRendering();if(!Render)return;
    for(auto Value:*Sections){
        auto Section=Value->AsObject();const int32 Material=ArmourNumber(Section,TEXT("index"),-1);if(Material<0||Material>=Mesh->GetMaterials().Num())continue;
        const FString Slot=ArmourString(Section,TEXT("slot"));bool Modular=false;Section->TryGetBoolField(TEXT("modular"),Modular);bool Visible=true;
        UMaterialInterface* Surface=Mesh->GetMaterials()[Material].MaterialInterface;
        if(Modular){
            auto Default=ArmourObject(Clothes,Slot);int32 Wanted=ArmourNumber(Default,TEXT("variant"),1);FString Texture;
            const FString SourceSlot=Slot==TEXT("lbody")?TEXT("body"):Slot;auto* Equipped=Worn.Find(SourceSlot);TSharedPtr<FJsonObject> Item=Equipped?*Equipped:nullptr;
            auto Model=Item?ArmourObject(Models,FString::FromInt(ArmourNumber(Item,TEXT("model")))):nullptr;
            auto Parts=ArmourObject(Model,Gender);const TArray<TSharedPtr<FJsonValue>>* Part=nullptr;
            if(Parts&&Parts->TryGetArrayField(SourceSlot,Part)&&Part->Num()>=2){Wanted=int32((*Part)[0]->AsNumber());Texture=(*Part)[1]->AsString();}
            const TArray<TSharedPtr<FJsonValue>>* Available=nullptr;bool Supported=false;
            if(Variants&&Variants->TryGetArrayField(Slot,Available))for(auto V:*Available)if(int32(V->AsNumber())==Wanted)Supported=true;
            if(!Supported)Wanted=ArmourNumber(Default,TEXT("variant"),1);
            Visible=ArmourNumber(Section,TEXT("variant"),1)==Wanted;
            if(Slot==TEXT("lbody"))Texture=ArmourString(Default,TEXT("tex"));
            if(Visible&&!Texture.IsEmpty()&&Master){
                const FString Path=ArmourString(Textures,Texture);
                if(auto* Image=Path.IsEmpty()?nullptr:LoadObject<UTexture>(nullptr,*Path)){
                    auto* Copy=UMaterialInstanceDynamic::Create(Master,Component);Copy->SetTextureParameterValue(TEXT("ArmorTexture"),Image);
                    FLinearColor Tint=FLinearColor::White;const TArray<TSharedPtr<FJsonValue>>* Dye=nullptr;
                    auto Palette=ArmourObject(ArmourCatalog,TEXT("dyes"));
                    if(Item&&Palette&&Palette->TryGetArrayField(FString::FromInt(ArmourNumber(Item,TEXT("color"))),Dye)&&Dye->Num()==3)Tint=FLinearColor((*Dye)[0]->AsNumber(),(*Dye)[1]->AsNumber(),(*Dye)[2]->AsNumber(),1);
                    Copy->SetVectorParameterValue(TEXT("ArmorDye"),Tint);Surface=Copy;
                }
            }
        }
        Component->SetMaterial(Material,Surface);
        for(int32 LOD=0;LOD<Render->LODRenderData.Num();++LOD){const auto& Data=Render->LODRenderData[LOD];for(int32 Index=0;Index<Data.RenderSections.Num();++Index)if(Data.RenderSections[Index].MaterialIndex==Material)Component->ShowMaterialSection(Material,Index,Visible,LOD);}
    }
}
