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
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture.h"
#include "Engine/World.h"
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
            FString Idle;(*Base)->TryGetStringField(TEXT("idle"),Idle);auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Idle);if(Clip){Body->PlayAnimation(Clip,true);Body->TickAnimation(.1f,false);Body->RefreshBoneTransforms();}
            Check(Clip&&Body->GetSingleNodeInstance()&&Body->GetSingleNodeInstance()->GetAnimationAsset()==Clip,TEXT("original animation runs on the modular figure"));
            if(BaseId==CaptureFigure&&!Capture.IsEmpty()){
                Entities.Add(TEXT("player:local"),Actor);EntityModels.Add(TEXT("player:local"),FCString::Atoi(*BaseId));InventoryState=Gear;InventoryState->SetNumberField(TEXT("state_revision"),1);UpdateClassicDoll();
                auto* Doll=Cast<ASkeletalMeshActor>(ClassicDollActor);bool Same=Doll!=nullptr;
                if(Doll)for(auto V:Sections){const int32 Index=V->AsObject()->GetIntegerField(TEXT("index"));Same&=Doll->GetSkeletalMeshComponent()->IsMaterialSectionShown(Index,0)==Body->IsMaterialSectionShown(Index,0);}
                Check(Same,TEXT("independent preview copies worn section visibility"));
            }
            ApplyBodyArmour(Actor,nullptr);Correct=true;Visible=0;for(auto V:Sections){auto S=V->AsObject();if(S->GetStringField(TEXT("slot"))!=TEXT("body"))continue;const int32 Index=S->GetIntegerField(TEXT("index"));if(Body->IsMaterialSectionShown(Index,0)){++Visible;Correct&=S->GetIntegerField(TEXT("variant"))==Clothes->GetObjectField(TEXT("body"))->GetIntegerField(TEXT("variant"));}}
            Check(Visible>=1&&Correct,TEXT("unequipping restores the original starter body"));
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
