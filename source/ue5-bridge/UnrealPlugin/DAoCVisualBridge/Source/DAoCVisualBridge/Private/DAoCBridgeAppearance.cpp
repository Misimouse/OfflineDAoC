#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureCube.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"

namespace {
TSharedPtr<FJsonObject> Obj(TSharedPtr<FJsonObject> O,const FString& K){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
FString Str(TSharedPtr<FJsonObject> O,const FString& K){FString V;if(O)O->TryGetStringField(K,V);return V;}
TArray<TSharedPtr<FJsonValue>> Arr(TSharedPtr<FJsonObject> O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
int32 Num(TSharedPtr<FJsonObject> O,const TCHAR* K,int32 D=0){double V=D;if(O)O->TryGetNumberField(K,V);return int32(V);}
TSharedPtr<FJsonObject> Choice(TSharedPtr<FJsonObject> Meta,const TCHAR* Key,int32 I){auto A=Arr(Meta,Key);return A.IsEmpty()?nullptr:A[FMath::Clamp(I,0,A.Num()-1)]->AsObject();}
float Linear(float V){return V<=.04045f?V/12.92f:FMath::Pow((V+.055f)/1.055f,2.4f);}
FLinearColor Tint(const TArray<TSharedPtr<FJsonValue>>& V,bool Skin){if(V.Num()<3)return FLinearColor::White;auto C=[Skin](double X){return Linear(Skin?(1+X)*.5:X);};return FLinearColor(C(V[0]->AsNumber()),C(V[1]->AsNumber()),C(V[2]->AsNumber()),1);}
}
FString DAoCAppearancePath(){FString Path;if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLobbyAppearance="),Path))return Path;Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/Pregame/appearance_catalog.json");return FPaths::FileExists(Path)?Path:FString();}
void ClearCharacterAppearance(ASkeletalMeshActor* Actor){if(!Actor)return;TArray<USkeletalMeshComponent*> Previous;Actor->GetComponents(Previous);for(auto* Part:Previous)if(Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHead"))||Part->ComponentHasTag(TEXT("DAoCBridgeAppearanceHair")))Part->DestroyComponent();}
bool ApplyCharacterAppearance(ASkeletalMeshActor* Actor,int32 Model,TSharedPtr<FJsonObject> Look,TSharedPtr<FJsonObject> Armour,const FString& CatalogPath,TSharedPtr<FJsonObject> Worn){
    if(!Actor)return false;
    FString Text;TSharedPtr<FJsonObject> Catalog;if(!FFileHelper::LoadFileToString(Text,*CatalogPath)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog))return false;
    auto Figure=Obj(Obj(Catalog,TEXT("figures")),FString::FromInt(Model)),Meta=Obj(Figure,TEXT("meta")),Parts=Obj(Figure,TEXT("parts"));
    auto* Parent=Actor->GetSkeletalMeshComponent();auto* Body=Parent->GetSkeletalMeshAsset();auto Definition=Obj(Obj(Armour,TEXT("figures")),Body?Body->GetPathName():TEXT(""));
    if(!Meta||!Parts||!Definition||!Body)return false;
    // Expansion figures may retain their validated materials without replacing
    // the globally calibrated appearance of existing races.
    auto MaterialPath=[Figure,Catalog](const TCHAR* Kind){const FString Override=Str(Obj(Figure,TEXT("materials")),Kind);return Override.IsEmpty()?Str(Obj(Catalog,TEXT("materials")),Kind):Override;};
    auto* HeadMesh=LoadObject<USkeletalMesh>(nullptr,*Str(Obj(Parts,TEXT("head")),TEXT("asset")));auto* Master=LoadObject<UMaterialInterface>(nullptr,*MaterialPath(TEXT("skin")));
    if(!HeadMesh||!Master)return false;
    auto Texture=[Catalog](const FString& Name)->UTexture2D*{const FString Path=Str(Obj(Catalog,TEXT("textures")),Name.ToLower());auto* T=Path.IsEmpty()?nullptr:LoadObject<UTexture2D>(nullptr,*Path);if(T)T->SetForceMipLevelsToBeResident(60);return T;};
    auto SourceColour=[Catalog](UMaterialInstanceDynamic* M,const FString& Name,UTexture2D* Enhanced){
        const FString Path=Str(Obj(Catalog,TEXT("original_color_textures")),Name.ToLower());
        if(auto* T=Path.IsEmpty()?nullptr:LoadObject<UTexture2D>(nullptr,*Path)){
            M->SetTextureParameterValue(TEXT("OriginalColorTexture"),T);M->SetScalarParameterValue(TEXT("HasOriginalColor"),1);
            M->SetScalarParameterValue(TEXT("OriginalColorMipBias"),FMath::Max(0.f,FMath::Log2(float(Enhanced->GetSizeX())/FMath::Max(1,T->GetSizeX()))));
        }
    };
    auto Face=Choice(Meta,TEXT("faces"),Num(Look,TEXT("face")));auto* FaceTexture=Texture(Str(Face,TEXT("tex")));if(!FaceTexture)return false;
    auto* Render=Body->GetResourceForRendering();if(!Render)return false;
    ClearCharacterAppearance(Actor);
    USkeletalMeshComponent* HelmetComponent=nullptr;TArray<USkeletalMeshComponent*> Current;Actor->GetComponents(Current);for(auto* Part:Current)if(Part->ComponentHasTag(TEXT("DAoCBridgeHelmet")))HelmetComponent=Part;
    auto Helmet=Obj(Obj(Obj(Armour,TEXT("helmets")),Str(Definition,TEXT("base_id"))),FString::FromInt(Num(Worn,TEXT("helmet"))));bool FullHelmet=false;if(HelmetComponent&&Helmet)Helmet->TryGetBoolField(TEXT("full"),FullHelmet);
    bool Hood=false;for(auto V:Arr(Definition,TEXT("sections"))){auto S=V->AsObject();if(Str(S,TEXT("slot"))==TEXT("cloak")&&Num(S,TEXT("variant"))==2&&Parent->IsMaterialSectionShown(Num(S,TEXT("index")),0))Hood=true;}
    if(HelmetComponent&&Helmet){auto* HM=HelmetComponent->GetSkeletalMeshAsset();auto* HR=HM?HM->GetResourceForRendering():nullptr;if(HR)for(auto V:Arr(Helmet,TEXT("sections"))){auto S=V->AsObject();bool Hair=false;S->TryGetBoolField(TEXT("hair"),Hair);if(!Hair)continue;const int32 Mat=Num(S,TEXT("index"));for(int32 L=0;L<HR->LODRenderData.Num();++L){const auto& D=HR->LODRenderData[L];for(int32 I=0;I<D.RenderSections.Num();++I)if(D.RenderSections[I].MaterialIndex==Mat)HelmetComponent->ShowMaterialSection(Mat,I,false,L);}}}
    auto Attach=[Actor,Parent](USkeletalMesh* Mesh){auto* C=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(C);C->SetSkeletalMesh(Mesh);C->SetupAttachment(Parent);C->SetRelativeTransform(FTransform::Identity);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);C->SetCastShadow(false);C->RegisterComponent();C->SetLeaderPoseComponent(Parent,false,true);C->SetForcedLOD(1);C->SetTextureForceResidentFlag(true);return C;};
    auto* Head=Attach(HeadMesh);Head->ComponentTags.Add(TEXT("DAoCBridgeAppearanceHead"));Head->SetVisibility(!FullHelmet);auto* Material=UMaterialInstanceDynamic::Create(Master,Head);Material->SetTextureParameterValue(TEXT("FigureTexture"),FaceTexture);
    auto Tones=Arr(Meta,TEXT("skin_tones"));FLinearColor Skin=FLinearColor::White;if(!Tones.IsEmpty())Skin=Tint(Tones[FMath::Clamp(Num(Look,TEXT("skin")),0,Tones.Num()-1)]->AsArray(),true);
    // Keep the original saved tone index and palette metadata. An optional
    // display calibration reduces excessive tint chroma at equal luminance.
    double Chroma=1;Figure->TryGetNumberField(TEXT("skin_tint_chroma"),Chroma);
    const float Luma=.2126f*Skin.R+.7152f*Skin.G+.0722f*Skin.B;
    Skin=FMath::Lerp(FLinearColor(Luma,Luma,Luma,1),Skin,float(FMath::Clamp(Chroma,0.,1.)));
    Material->SetVectorParameterValue(TEXT("FigureTint"),Skin);SourceColour(Material,Str(Face,TEXT("tex")),FaceTexture);
    // Original alpha-masked starter clothes expose skin on hands/arms on some
    // races. Real equipped armour keeps its separate dye/material behaviour.
    const TMap<FString,FString> Slots={{TEXT("body"),TEXT("torso")},{TEXT("arms"),TEXT("arms")},{TEXT("gloves"),TEXT("gloves")},{TEXT("boots"),TEXT("boots")},{TEXT("legs"),TEXT("legs")}};
    auto Tinted=Obj(Meta,TEXT("skin_tint_parts")),Clothes=Obj(Meta,TEXT("clothes"));
    for(auto V:Arr(Definition,TEXT("sections"))){auto S=V->AsObject();const FString Slot=Str(S,TEXT("slot"));bool IsTinted=false;if(Tinted)Tinted->TryGetBoolField(Slot,IsTinted);auto Clothing=Obj(Clothes,Slot);if(!IsTinted||Str(Clothing,TEXT("chan"))!=TEXT("a")||!Slots.Contains(Slot)||Num(Worn,*Slots.FindRef(Slot))>0)continue;
        const FString TextureName=Str(Clothing,TEXT("tex"));
        if(auto* T=Texture(TextureName)){
            // Optional surface-specific detail materials leave the face,
            // other bare parts and equipped armour on their existing path.
            auto* SurfaceMaster=Master;const FString SurfacePath=Str(Obj(Catalog,TEXT("surface_materials")),TextureName.ToLower());
            if(!SurfacePath.IsEmpty())if(auto* Override=LoadObject<UMaterialInterface>(nullptr,*SurfacePath))SurfaceMaster=Override;
            auto* M=UMaterialInstanceDynamic::Create(SurfaceMaster,Parent);M->SetTextureParameterValue(TEXT("FigureTexture"),T);M->SetVectorParameterValue(TEXT("FigureTint"),Skin);M->SetScalarParameterValue(TEXT("UseSkinMask"),1);SourceColour(M,TextureName,T);Parent->SetMaterial(Num(S,TEXT("index")),M);
        }
    }
    auto Eyes=Arr(Meta,TEXT("eyes"));if(!Eyes.IsEmpty())if(auto* T=Texture(Eyes[FMath::Clamp(Num(Look,TEXT("eyes")),0,Eyes.Num()-1)]->AsString())){Material->SetTextureParameterValue(TEXT("EyeTexture"),T);Material->SetScalarParameterValue(TEXT("HasEye"),1);}
    if(Num(Look,TEXT("tattoo"))>0)if(auto* T=Texture(Str(Choice(Meta,TEXT("tattoos"),Num(Look,TEXT("tattoo"))),TEXT("tex")))){Material->SetTextureParameterValue(TEXT("TattooTexture"),T);Material->SetScalarParameterValue(TEXT("HasTattoo"),1);}
    for(int32 I=0;I<Head->GetNumMaterials();++I)Head->SetMaterial(I,Material);
    auto Sliders=Arr(Meta,TEXT("sliders")),Values=Arr(Look,TEXT("sliders"));for(int32 I=0;I<Sliders.Num();++I){const float V=I<Values.Num()?FMath::Clamp(float(Values[I]->AsNumber()),0.f,8.f):4;Head->SetMorphTarget(FName(*Str(Sliders[I]->AsObject(),TEXT("low"))),FMath::Max((4-V)/4,0.f));Head->SetMorphTarget(FName(*Str(Sliders[I]->AsObject(),TEXT("high"))),FMath::Max((V-4)/4,0.f));}
    // Leader-pose followers can skip pose evaluation. Publish the explicit
    // morph overrides to render weights before a capture or frozen copy.
    Head->TickAnimation(0,false);Head->RefreshBoneTransforms();Head->ApplyAnimationCurvesToComponent(nullptr,&Head->GetMorphTargetCurves());Head->MarkRenderDynamicDataDirty();
    auto Style=Choice(Meta,TEXT("hair_styles"),Num(Look,TEXT("hair")));auto Hair=Obj(Parts,Str(Style,TEXT("node")));auto Colors=Arr(Style,TEXT("colours"));
    if(Hair&&!Colors.IsEmpty()&&!FullHelmet&&!Hood){
        auto Color=Colors[FMath::Clamp(Num(Look,TEXT("hair_color")),0,Colors.Num()-1)]->AsObject();auto* HairMesh=LoadObject<USkeletalMesh>(nullptr,*Str(Hair,TEXT("asset")));auto* HairMaster=LoadObject<UMaterialInterface>(nullptr,*MaterialPath(TEXT("hair")));auto* T=Texture(Str(Color,TEXT("tex")));
        if(HairMesh&&HairMaster&&T){auto* C=Attach(HairMesh);C->ComponentTags.Add(TEXT("DAoCBridgeAppearanceHair"));auto* M=UMaterialInstanceDynamic::Create(HairMaster,C);M->SetTextureParameterValue(TEXT("FigureTexture"),T);M->SetVectorParameterValue(TEXT("FigureTint"),Tint(Arr(Color,TEXT("tint")),false));for(int32 I=0;I<C->GetNumMaterials();++I)C->SetMaterial(I,M);// Hair/beard target names differ from head targets. Match their original
        // feature codes through the exported binding, retaining helmet morphs.
        if(auto Bindings=Obj(Hair,TEXT("facial_morphs")))for(int32 I=0;I<Sliders.Num();++I){
            const float V=I<Values.Num()?FMath::Clamp(float(Values[I]->AsNumber()),0.f,8.f):4;
            for(const auto& Side:TArray<TPair<FString,float>>{{TEXT("low"),FMath::Max((4-V)/4,0.f)},{TEXT("high"),FMath::Max((V-4)/4,0.f)}}){
                const FString Target=Str(Bindings,Str(Sliders[I]->AsObject(),Side.Key));
                if(!Target.IsEmpty())C->SetMorphTarget(FName(*Target),Side.Value);
            }
        }
        const int32 Mode=HelmetComponent?Num(Helmet,TEXT("hair_mode")):0;if(Mode>1){const FString Morph=Str(Obj(Obj(Meta,TEXT("helm_hair")),Str(Style,TEXT("node"))),FString::FromInt(Mode));if(!Morph.IsEmpty())C->SetMorphTarget(FName(*Morph),1);}C->TickAnimation(0,false);C->RefreshBoneTransforms();C->ApplyAnimationCurvesToComponent(nullptr,&C->GetMorphTargetCurves());C->MarkRenderDynamicDataDirty();}
    }
    // Replace only original head/hair sections. Armour and weapons retain their own pipeline.
    for(auto V:Arr(Definition,TEXT("sections"))){auto S=V->AsObject();bool HairSection=false;S->TryGetBoolField(TEXT("hood_hair"),HairSection);if(Str(S,TEXT("slot"))!=TEXT("head")&&!HairSection)continue;const int32 MaterialIndex=Num(S,TEXT("index"),-1);for(int32 L=0;L<Render->LODRenderData.Num();++L){const auto& D=Render->LODRenderData[L];for(int32 I=0;I<D.RenderSections.Num();++I)if(D.RenderSections[I].MaterialIndex==MaterialIndex)Parent->ShowMaterialSection(MaterialIndex,I,false,L);}}
    return true;
}

void ConfigureCharacterPreviewCapture(USceneCaptureComponent2D* Capture){
    if(!Capture)return;
    // Show-only geometry and lighting channels do not exclude a map's skylight
    // or reflection captures. Supply neutral ambient per capture instead.
    Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorHDR;
    Capture->ShowFlags.SetSkyLighting(false);Capture->ShowFlags.SetReflectionEnvironment(false);
    Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetMotionBlur(false);
    Capture->ShowFlags.SetGlobalIllumination(false);Capture->ShowFlags.SetDynamicShadows(false);Capture->ShowFlags.SetAmbientOcclusion(false);Capture->ShowFlags.SetPostProcessMaterial(false);
    auto& PP=Capture->PostProcessSettings;
    PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
    PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
    PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=0;
    PP.AmbientCubemap=LoadObject<UTextureCube>(nullptr,TEXT("/DAoCVisualBridge/AppearanceColour_v02/T_CharacterAmbient.T_CharacterAmbient"));
    PP.bOverride_AmbientCubemapIntensity=true;PP.AmbientCubemapIntensity=.75f;
    PP.bOverride_AmbientCubemapTint=true;PP.AmbientCubemapTint=FLinearColor::White;
}
