#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "Engine/DirectionalLight.h"
#include "Components/LightComponent.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickArmourAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeArmourTest="),Path))return false;
    static bool Ran=false;static double Started=0;static int32 Checks=0;static TArray<TSharedPtr<FJsonValue>> Failures;static TSharedPtr<FJsonObject> Report;
    auto Check=[&](bool Ok,const FString& Label){++Checks;if(!Ok)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Capture;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeArmourCapture="),Capture);
    FString CaptureFigure=TEXT("1984");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeArmourCaptureFigure="),CaptureFigure);
    if(!Ran){
        Ran=true;Started=FPlatformTime::Seconds();Report=MakeShared<FJsonObject>();Check(Socket==nullptr,TEXT("no live session"));Check(ArmourCatalog.IsValid(),TEXT("original armour catalogue loaded"));
        if(!Capture.IsEmpty()){
            FActorSpawnParameters Params;Params.ObjectFlags|=RF_Transient;
            for(int32 I=0;I<2;++I){auto* Light=GetWorld()->SpawnActor<ADirectionalLight>(FVector::ZeroVector,FRotator(I==0?-35.f:-20.f,I==0?120.f:-60.f,0),Params);if(Light)Light->GetLightComponent()->SetIntensity(I==0?4.f:2.f);}
            Report->SetBoolField(TEXT("controlled_preview_lighting"),true);
        }
        const TSharedPtr<FJsonObject>* Figures=nullptr;
        if(ArmourCatalog&&ArmourCatalog->TryGetObjectField(TEXT("figures"),Figures))for(const auto& Pair:(*Figures)->Values){
            auto Definition=Pair.Value->AsObject();auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Pair.Key);Check(Mesh!=nullptr,TEXT("modular figure loads"));if(!Mesh)continue;
            const FString BaseId=Definition->GetStringField(TEXT("base_id"));auto* Base=ModelCatalog.Find(BaseId);Check(Base!=nullptr,TEXT("original animation catalogue retained"));if(!Base)continue;
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("model_id"),FCString::Atoi(*BaseId));Row->SetNumberField(TEXT("size"),50);
            auto* Actor=Cast<ASkeletalMeshActor>(CreateEntity(TEXT("armour:")+BaseId,Row,FVector::ZeroVector));Check(Actor!=nullptr,TEXT("figure spawns through normal entity loader"));if(!Actor)continue;auto* Body=Actor->GetSkeletalMeshComponent();
            Check(Body->GetSkeletalMeshAsset()==Mesh,TEXT("new figure selected without changing animations"));
            auto* Original=LoadObject<USkeletalMesh>(nullptr,*Definition->GetStringField(TEXT("original_asset")));
            Check(Original&&Original->GetRefSkeleton().GetNum()==Mesh->GetRefSkeleton().GetNum(),TEXT("full original skeleton bone count preserved"));
            if(Original){const auto& A=Original->GetRefSkeleton();const auto& B=Mesh->GetRefSkeleton();bool Same=true;for(int32 I=0;I<B.GetNum();++I){const int32 J=A.FindBoneIndex(B.GetBoneName(I));if(J==INDEX_NONE||!A.GetRefBonePose()[J].Equals(B.GetRefBonePose()[I],.01))Same=false;}Check(Same,TEXT("original bone names and reference transforms preserved"));}
            auto Gear=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Worn;
            auto Item=MakeShared<FJsonObject>();Item->SetNumberField(TEXT("slot"),25);Item->SetNumberField(TEXT("model"),41);Item->SetNumberField(TEXT("color"),2);Worn.Add(MakeShared<FJsonValueObject>(Item));Gear->SetArrayField(TEXT("items"),Worn);ApplyBodyArmour(Actor,Gear);
            const auto& Sections=Definition->GetArrayField(TEXT("sections"));const auto Clothes=Definition->GetObjectField(TEXT("clothes"));const auto Variants=Definition->GetObjectField(TEXT("variants"));bool HasFive=false;for(auto V:Variants->GetArrayField(TEXT("body")))if(int32(V->AsNumber())==5)HasFive=true;
            const int32 Expected=HasFive?5:Clothes->GetObjectField(TEXT("body"))->GetIntegerField(TEXT("variant"));int32 Visible=0;bool Correct=true,Texture=false;
            for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))!=TEXT("body"))continue;const int32 Index=S->GetIntegerField(TEXT("index"));if(Body->IsMaterialSectionShown(Index,0)){++Visible;Correct&=S->GetIntegerField(TEXT("variant"))==Expected;UTexture* Image=nullptr;if(auto* Material=Body->GetMaterial(Index))Texture|=Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("ArmorTexture")),Image)&&Image!=nullptr;}}
            Check(Visible>=1&&Correct,TEXT("chain armour selects its original body variant without overlaps"));Check(Texture,TEXT("equipped armour samples its original texture"));
            const int32 PartSlots[]={22,23,27,28},PartModels[]={34,40,32,33};const TCHAR* PartNames[]={TEXT("gloves"),TEXT("boots"),TEXT("legs"),TEXT("arms")};
            for(int32 N=0;N<4;++N){auto Piece=MakeShared<FJsonObject>();Piece->SetNumberField(TEXT("slot"),PartSlots[N]);Piece->SetNumberField(TEXT("model"),PartModels[N]);Worn.Add(MakeShared<FJsonValueObject>(Piece));Gear->SetArrayField(TEXT("items"),Worn);ApplyBodyArmour(Actor,Gear);bool Textured=false;for(auto V:Sections){auto S=V->AsObject();const int32 Index=S->GetIntegerField(TEXT("index"));if(S->GetStringField(TEXT("slot"))==PartNames[N]&&Body->IsMaterialSectionShown(Index,0)){UTexture* Image=nullptr;if(auto* Material=Body->GetMaterial(Index))Textured|=Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("ArmorTexture")),Image)&&Image!=nullptr;}}Check(Textured,TEXT("original equipment slot dresses ")+FString(PartNames[N]));}
            if(Definition->HasField(TEXT("cloaks"))){
                auto Cloak=MakeShared<FJsonObject>();Cloak->SetNumberField(TEXT("slot"),26);Cloak->SetNumberField(TEXT("model"),57);Cloak->SetNumberField(TEXT("color"),2);Worn.Add(MakeShared<FJsonValueObject>(Cloak));Gear->SetArrayField(TEXT("items"),Worn);
                auto Flags=MakeShared<FJsonObject>();Gear->SetObjectField(TEXT("gear"),Flags);
                auto CapeShape=[&](int32 ExpectedShape){int32 Count=0;bool Correct=true;for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))!=TEXT("cloak"))continue;const bool Shown=Body->IsMaterialSectionShown(S->GetIntegerField(TEXT("index")),0);if(Shown){++Count;Correct&=S->GetIntegerField(TEXT("variant"))==ExpectedShape;}}return ExpectedShape==0?Count==0:Count==1&&Correct;};
                Check(CapeShape(0),TEXT("no cloak visible before a cloak is equipped"));ApplyBodyArmour(Actor,Gear);Check(CapeShape(1),TEXT("worn cloak selects the original hood-down mesh"));
                bool Textured=false,Dyed=false,SingleSided=false,Emblemed=false;const auto Palette=ArmourCatalog->GetObjectField(TEXT("dyes"));const auto Dye=Palette->GetArrayField(TEXT("2"));
                for(auto V:Sections){auto S=V->AsObject();const int32 Index=S->GetIntegerField(TEXT("index"));if(S->GetStringField(TEXT("slot"))!=TEXT("cloak" )||!Body->IsMaterialSectionShown(Index,0))continue;auto* Material=Body->GetMaterial(Index);UTexture* Tex=nullptr;FLinearColor Tint;Textured=Material&&Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("ArmorTexture")),Tex)&&Tex;Dyed=Material&&Material->GetVectorParameterValue(FMaterialParameterInfo(TEXT("ArmorDye")),Tint)&&FMath::IsNearlyEqual(Tint.R,float(Dye[0]->AsNumber()),.001f)&&FMath::IsNearlyEqual(Tint.G,float(Dye[1]->AsNumber()),.001f);SingleSided=Material&&!Material->IsTwoSided();}
                Check(Textured,TEXT("cloak samples original item texture"));Check(Dyed,TEXT("cloak applies original dye palette"));Check(SingleSided,TEXT("cloak preserves original single-sided rendering"));
                const auto* Data=Body->GetSkeletalMeshAsset()->GetResourceForRendering();Check(Data&&!Data->LODRenderData.IsEmpty()&&Data->LODRenderData[0].GetNumTexCoords()>=3,TEXT("cloak mesh retains texture pattern and logo UV channels"));
                Flags->SetBoolField(TEXT("hood"),true);ApplyBodyArmour(Actor,Gear);Check(CapeShape(2),TEXT("hood flag switches to original raised-hood mesh"));
                bool HairHidden=true;for(auto V:Sections){auto S=V->AsObject();bool Hair=false;S->TryGetBoolField(TEXT("hood_hair"),Hair);if(Hair&&Body->IsMaterialSectionShown(S->GetIntegerField(TEXT("index")),0))HairHidden=false;}Check(HairHidden,TEXT("raised hood covers the original hair sections"));
                Flags->SetBoolField(TEXT("cloak_hidden"),true);ApplyBodyArmour(Actor,Gear);Check(CapeShape(0),TEXT("server hidden-cloak flag hides both cape and hood"));
                Flags->SetBoolField(TEXT("cloak_hidden"),false);Flags->SetBoolField(TEXT("hood"),false);Cloak->SetNumberField(TEXT("emblem"),513);ApplyBodyArmour(Actor,Gear);
                for(auto V:Sections){auto S=V->AsObject();const int32 Index=S->GetIntegerField(TEXT("index"));if(S->GetStringField(TEXT("slot"))!=TEXT("cloak")||!Body->IsMaterialSectionShown(Index,0))continue;auto* Material=Body->GetMaterial(Index);float Has=0,Logo=0;UTexture* Pattern=nullptr;UTexture* Mark=nullptr;Emblemed=Material&&Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("HasEmblem")),Has)&&Has==1&&Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("HasLogo")),Logo)&&Logo==1&&Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Pattern")),Pattern)&&Pattern&&Material->GetTextureParameterValue(FMaterialParameterInfo(TEXT("Logo")),Mark)&&Mark;}
                Check(Emblemed,TEXT("cloak uses original guild pattern and logo"));
                // Remote equipment packets carry these flags directly rather than in inventory.gear.
                Gear->RemoveField(TEXT("gear"));Gear->SetBoolField(TEXT("hood"),true);ApplyBodyArmour(Actor,Gear);Check(CapeShape(2),TEXT("remote equipment hood flags use the same cloak selection"));Gear->SetBoolField(TEXT("hood"),false);ApplyBodyArmour(Actor,Gear);
            }
            const TSharedPtr<FJsonObject>* Helmets=nullptr;const TSharedPtr<FJsonObject>* RaceHelmets=nullptr;
            auto FindHelmet=[&](){TArray<USkeletalMeshComponent*> Parts;Actor->GetComponents(Parts);USkeletalMeshComponent* Found=nullptr;for(auto* Part:Parts)if(Part->ComponentHasTag(TEXT("DAoCBridgeHelmet")))Found=Part;return Found;};
            if(ArmourCatalog->TryGetObjectField(TEXT("helmets"),Helmets)&&(*Helmets)->TryGetObjectField(BaseId,RaceHelmets)){
                auto Hat=MakeShared<FJsonObject>();Hat->SetNumberField(TEXT("slot"),21);Hat->SetNumberField(TEXT("color"),2);
                auto WithHat=Worn;WithHat.Add(MakeShared<FJsonValueObject>(Hat));Gear->SetArrayField(TEXT("items"),WithHat);
                for(const auto& Entry:(*RaceHelmets)->Values){Hat->SetNumberField(TEXT("model"),FCString::Atoi(*Entry.Key));ApplyBodyArmour(Actor,Gear);auto* Part=FindHelmet();
                    Check(Part&&Part->GetSkeletalMeshAsset()->GetPathName()==Entry.Value->AsObject()->GetStringField(TEXT("asset")),TEXT("original race-specific helmet assembly loads ")+BaseId+TEXT("/")+Entry.Key);
                    Check(Part&&Part->LeaderPoseComponent.Get()==Body&&Part->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&Part->GetRelativeTransform().Equals(FTransform::Identity),TEXT("helmet follows the figure bones without offset or collision"));
                    bool Full=false;Entry.Value->AsObject()->TryGetBoolField(TEXT("full"),Full);bool CorrectHead=true;
                    for(auto V:Sections){auto S=V->AsObject();const int32 Index=S->GetIntegerField(TEXT("index"));if(S->GetStringField(TEXT("slot"))==TEXT("head"))CorrectHead&=Body->IsMaterialSectionShown(Index,0)!=Full;bool Hair=false;S->TryGetBoolField(TEXT("hood_hair"),Hair);if(Hair)CorrectHead&=!Body->IsMaterialSectionShown(Index,0);}
                    Check(CorrectHead,TEXT("full helmets replace head; ordinary helmets retain face and use original helmet hair"));
                    ApplyBodyArmour(Actor,Gear);Check(FindHelmet()==Part,TEXT("unchanged helmet does not recreate its component"));
                }
                Gear->SetBoolField(TEXT("helm_hidden"),true);ApplyBodyArmour(Actor,Gear);Check(FindHelmet()==nullptr,TEXT("hidden helmet flag removes the original assembly"));Gear->SetBoolField(TEXT("helm_hidden"),false);
                Gear->SetBoolField(TEXT("hood"),true);ApplyBodyArmour(Actor,Gear);Check(FindHelmet()==nullptr,TEXT("visible raised hood hides the helmet"));Gear->SetBoolField(TEXT("hood"),false);
                Gear->SetArrayField(TEXT("items"),Worn);ApplyBodyArmour(Actor,Gear);Check(FindHelmet()==nullptr,TEXT("unequipping the helmet removes the assembly"));
                Hat->SetNumberField(TEXT("model"),999999);Gear->SetArrayField(TEXT("items"),WithHat);ApplyBodyArmour(Actor,Gear);bool FaceRestored=FindHelmet()==nullptr;
                for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))==TEXT("head"))FaceRestored&=Body->IsMaterialSectionShown(S->GetIntegerField(TEXT("index")),0);}
                Check(FaceRestored,TEXT("unsupported helmet safely retains the original face"));Gear->SetArrayField(TEXT("items"),Worn);ApplyBodyArmour(Actor,Gear);
            }
            FString Idle;(*Base)->TryGetStringField(TEXT("idle"),Idle);auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Idle);if(Clip){Body->PlayAnimation(Clip,true);Body->TickAnimation(.1f,false);Body->RefreshBoneTransforms();}
            Check(Clip&&Body->GetSingleNodeInstance()&&Body->GetSingleNodeInstance()->GetAnimationAsset()==Clip,TEXT("original animation runs on the modular figure"));
            if(BaseId==CaptureFigure&&!Capture.IsEmpty()){
                int32 CaptureHelmet=0;if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeArmourCaptureHelmet="),CaptureHelmet)&&CaptureHelmet>0){auto Hat=MakeShared<FJsonObject>();Hat->SetNumberField(TEXT("slot"),21);Hat->SetNumberField(TEXT("model"),CaptureHelmet);Worn.Add(MakeShared<FJsonValueObject>(Hat));Gear->SetArrayField(TEXT("items"),Worn);ApplyBodyArmour(Actor,Gear);Check(FindHelmet()!=nullptr,TEXT("render preview wears requested original helmet"));}
                if(Definition->HasField(TEXT("cloaks"))&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeArmourCaptureHood"))){Gear->SetBoolField(TEXT("hood"),true);ApplyBodyArmour(Actor,Gear);}
                double CaptureYaw=0;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeArmourCaptureYaw="),CaptureYaw);ClassicDollYaw=float(CaptureYaw);
                Entities.Add(TEXT("player:local"),Actor);EntityModels.Add(TEXT("player:local"),FCString::Atoi(*BaseId));InventoryState=Gear;InventoryState->SetNumberField(TEXT("state_revision"),1);UpdateClassicDoll();
                auto* Doll=Cast<ASkeletalMeshActor>(ClassicDollActor);bool Same=Doll!=nullptr;
                if(Doll)for(auto V:Sections){const int32 Index=V->AsObject()->GetIntegerField(TEXT("index"));Same&=Doll->GetSkeletalMeshComponent()->IsMaterialSectionShown(Index,0)==Body->IsMaterialSectionShown(Index,0);}
                Check(Same,TEXT("independent preview copies worn section visibility"));
                if(CaptureHelmet>0){bool PreviewHelmet=false;auto* WornHelmet=FindHelmet();if(Doll&&WornHelmet){TArray<USkeletalMeshComponent*> Parts;Doll->GetComponents(Parts);for(auto* Part:Parts)if(Part!=Doll->GetSkeletalMeshComponent()&&Part->GetSkeletalMeshAsset()==WornHelmet->GetSkeletalMeshAsset())PreviewHelmet|=Part->LeaderPoseComponent.Get()==Doll->GetSkeletalMeshComponent()&&Part->bPauseAnims&&!Part->IsComponentTickEnabled();}Check(PreviewHelmet,TEXT("inventory helmet follows only the frozen independent preview body"));}
                if(Doll&&ClassicCapture&&ClassicDollTarget){
                    const FBox Box=Doll->GetSkeletalMeshComponent()->CalcBounds(Doll->GetSkeletalMeshComponent()->GetComponentTransform()).GetBox();const FVector Eye=ClassicCapture->GetComponentLocation();const FRotator Rotation=ClassicCapture->GetComponentRotation();
                    const FVector Forward=Rotation.Vector(),Right=FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y),Up=FRotationMatrix(Rotation).GetUnitAxis(EAxis::Z);const double TanH=FMath::Tan(FMath::DegreesToRadians(ClassicCapture->FOVAngle*.5)),TanV=TanH*ClassicDollTarget->SizeY/FMath::Max(1,ClassicDollTarget->SizeX);
                    bool Fits=true;double Low=100,High=-100;
                    for(int32 Corner=0;Corner<8;++Corner){const FVector Point((Corner&1)?Box.Max.X:Box.Min.X,(Corner&2)?Box.Max.Y:Box.Min.Y,(Corner&4)?Box.Max.Z:Box.Min.Z);const FVector Delta=Point-Eye;const double Depth=FVector::DotProduct(Delta,Forward);if(Depth<=0){Fits=false;continue;}const double X=FVector::DotProduct(Delta,Right)/(Depth*TanH),Y=FVector::DotProduct(Delta,Up)/(Depth*TanV);Fits&=FMath::Abs(X)<.99&&FMath::Abs(Y)<.99;Low=FMath::Min(Low,Y);High=FMath::Max(High,Y);}
                    Check(Fits,TEXT("preview keeps full body and hood inside the image"));Check(High-Low>=1,TEXT("preview frames small and large races at a useful scale"));
                }
            }
            ApplyBodyArmour(Actor,nullptr);Correct=true;Visible=0;for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))!=TEXT("body"))continue;const int32 Index=S->GetIntegerField(TEXT("index"));if(Body->IsMaterialSectionShown(Index,0)){++Visible;Correct&=S->GetIntegerField(TEXT("variant"))==Clothes->GetObjectField(TEXT("body"))->GetIntegerField(TEXT("variant"));}}
            Check(Visible>=1&&Correct,TEXT("unequipping restores the original starter body"));
            if(Definition->HasField(TEXT("cloaks"))){bool Hidden=true;for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))==TEXT("cloak")&&Body->IsMaterialSectionShown(S->GetIntegerField(TEXT("index")),0))Hidden=false;}Check(Hidden,TEXT("unequipping removes the cape without leaving a hood"));}
        }
        else Check(false,TEXT("modular figures present"));
        if(!Capture.IsEmpty())return true;
    }
    if(!Capture.IsEmpty()){
        if(FPlatformTime::Seconds()-Started<4)return true;
        if(ClassicCapture)ClassicCapture->CaptureScene();FlushRenderingCommands();FBufferArchive Bytes;Check(ClassicDollTarget&&FImageUtils::ExportRenderTarget2DAsPNG(ClassicDollTarget,Bytes)&&FFileHelper::SaveArrayToFile(Bytes,*Capture),TEXT("preview image exported"));
    }
    Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetBoolField(TEXT("real_server"),false);
    FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);FJsonSerializer::Serialize(Report.ToSharedRef(),Writer);FFileHelper::SaveStringToFile(Text,*Path);
    RemoveClassicUI();ClearEntities();UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
