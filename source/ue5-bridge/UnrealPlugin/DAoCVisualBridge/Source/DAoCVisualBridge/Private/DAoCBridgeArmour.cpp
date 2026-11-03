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
bool ArmourFlag(TSharedPtr<FJsonObject> O,const TCHAR* K){bool V=false;if(O)O->TryGetBoolField(K,V);return V;}
}

void UDAoCBridgeSubsystem::ApplyBodyArmour(AActor* Actor,TSharedPtr<FJsonObject> Equipment){
    auto* Figure=Cast<ASkeletalMeshActor>(Actor);if(!Figure||!ArmourCatalog)return;
    auto* Component=Figure->GetSkeletalMeshComponent();auto* Mesh=Component->GetSkeletalMeshAsset();if(!Mesh)return;
    auto Definition=ArmourObject(ArmourObject(ArmourCatalog,TEXT("figures")),Mesh->GetPathName());if(!Definition)return;
    auto Clothes=ArmourObject(Definition,TEXT("clothes"));auto Variants=ArmourObject(Definition,TEXT("variants"));
    TMap<FString,TSharedPtr<FJsonObject>> Worn;const TArray<TSharedPtr<FJsonValue>>* Items=nullptr;
    if(Equipment&&Equipment->TryGetArrayField(TEXT("items"),Items))for(auto Value:*Items){
        if(Value->Type!=EJson::Object)continue;auto Item=Value->AsObject();FString Slot;
        switch(ArmourNumber(Item,TEXT("slot"))){case 25:Slot=TEXT("body");break;case 28:Slot=TEXT("arms");break;case 22:Slot=TEXT("gloves");break;case 27:Slot=TEXT("legs");break;case 23:Slot=TEXT("boots");break;case 26:Slot=TEXT("cloak");break;default:continue;}
        Worn.Add(Slot,Item);
    }
    const TArray<TSharedPtr<FJsonValue>>* Sections=nullptr;if(!Definition->TryGetArrayField(TEXT("sections"),Sections))return;
    auto* Master=LoadObject<UMaterialInterface>(nullptr,*ArmourString(ArmourCatalog,TEXT("material")));
    auto Models=ArmourObject(ArmourCatalog,TEXT("models"));auto Textures=ArmourObject(ArmourCatalog,TEXT("textures"));
    const FString Gender=ArmourString(Definition,TEXT("gender"));auto* Render=Mesh->GetResourceForRendering();if(!Render)return;
    auto Appearance=ArmourObject(Equipment,TEXT("gear"));if(!Appearance)Appearance=Equipment;
    auto* CloakItem=Worn.Find(TEXT("cloak"));auto Cloak=CloakItem?*CloakItem:nullptr;
    auto CloakParts=ArmourObject(ArmourObject(Models,FString::FromInt(ArmourNumber(Cloak,TEXT("model")))),Gender);
    const TArray<TSharedPtr<FJsonValue>>* CloakData=nullptr;const bool CloakWorn=CloakParts&&CloakParts->TryGetArrayField(TEXT("cloak"),CloakData)&&CloakData->Num()>=2;
    const TArray<TSharedPtr<FJsonValue>>* CloakShapes=nullptr;TArray<int32> AvailableCloaks;
    if(Definition->TryGetArrayField(TEXT("cloaks"),CloakShapes))for(auto Value:*CloakShapes)AvailableCloaks.Add(int32(Value->AsNumber()));
    const bool CloakShown=CloakWorn&&!ArmourFlag(Appearance,TEXT("cloak_hidden"));const bool HoodCovers=CloakShown&&ArmourFlag(Appearance,TEXT("hood"))&&AvailableCloaks.Contains(2);
    const int32 CloakVariant=HoodCovers?2:AvailableCloaks.Contains(1)?1:AvailableCloaks.IsEmpty()?0:AvailableCloaks[0];
    const FString CloakMaterialPath=ArmourString(ArmourCatalog,TEXT("cloak_material"));
    auto* CloakMaster=CloakMaterialPath.IsEmpty()?nullptr:LoadObject<UMaterialInterface>(nullptr,*CloakMaterialPath);
    for(auto Value:*Sections){
        auto Section=Value->AsObject();const int32 Material=ArmourNumber(Section,TEXT("index"),-1);if(Material<0||Material>=Mesh->GetMaterials().Num())continue;
        const FString Slot=ArmourString(Section,TEXT("slot"));bool Modular=false;Section->TryGetBoolField(TEXT("modular"),Modular);bool Visible=true;
        UMaterialInterface* Surface=Mesh->GetMaterials()[Material].MaterialInterface;
        if(HoodCovers&&ArmourFlag(Section,TEXT("hood_hair")))Visible=false;
        if(Slot==TEXT("cloak")){
            Visible=CloakShown&&ArmourNumber(Section,TEXT("variant"))==CloakVariant;
            if(Visible&&CloakMaster){
                const FString Path=ArmourString(Textures,(*CloakData)[1]->AsString());
                if(auto* Image=Path.IsEmpty()?nullptr:LoadObject<UTexture>(nullptr,*Path)){
                    auto* Copy=UMaterialInstanceDynamic::Create(CloakMaster,Component);Copy->SetTextureParameterValue(TEXT("ArmorTexture"),Image);
                    FLinearColor Tint=FLinearColor::White;const TArray<TSharedPtr<FJsonValue>>* Dye=nullptr;auto Palette=ArmourObject(ArmourCatalog,TEXT("dyes"));
                    if(Palette&&Palette->TryGetArrayField(FString::FromInt(ArmourNumber(Cloak,TEXT("color"))),Dye)&&Dye->Num()==3)Tint=FLinearColor((*Dye)[0]->AsNumber(),(*Dye)[1]->AsNumber(),(*Dye)[2]->AsNumber(),1);
                    Copy->SetVectorParameterValue(TEXT("ArmorDye"),Tint);
                    const int32 Emblem=ArmourNumber(Cloak,TEXT("emblem")),LogoId=Emblem>>9,PatternId=LogoId==0?512:Emblem&511;
                    auto Emblems=ArmourObject(ArmourCatalog,TEXT("cloak_emblems"));const FString PatternPath=ArmourString(ArmourObject(Emblems,TEXT("patterns")),FString::FromInt(PatternId));const FString LogoPath=ArmourString(ArmourObject(Emblems,TEXT("logos")),FString::FromInt(LogoId));
                    auto* Pattern=Emblem>0&&!PatternPath.IsEmpty()?LoadObject<UTexture>(nullptr,*PatternPath):nullptr;auto* Logo=Pattern&&!LogoPath.IsEmpty()?LoadObject<UTexture>(nullptr,*LogoPath):nullptr;
                    Copy->SetScalarParameterValue(TEXT("HasEmblem"),Pattern?1.f:0.f);Copy->SetScalarParameterValue(TEXT("HasLogo"),Logo?1.f:0.f);if(Pattern)Copy->SetTextureParameterValue(TEXT("Pattern"),Pattern);if(Logo)Copy->SetTextureParameterValue(TEXT("Logo"),Logo);
                    Surface=Copy;
                }
            }
        }
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
