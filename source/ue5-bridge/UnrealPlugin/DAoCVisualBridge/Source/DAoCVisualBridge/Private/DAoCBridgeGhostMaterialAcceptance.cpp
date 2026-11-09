#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeGhostMaterials.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/KismetSystemLibrary.h"
#include "HAL/IConsoleManager.h"

bool TickPrivateNpcGhostVisual(UWorld* World);
bool UDAoCBridgeSubsystem::TickNpcGhostMaterialAcceptance(){
    if(TickPrivateNpcGhostVisual(GetWorld()))return true;
    FString Output;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostMaterialsTest="),Output))return false;
    static bool Done=false;if(Done)return true;Done=true;
    int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Manifest,Samples,Text;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostMaterials="),Manifest);FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostSamples="),Samples);
    TSharedPtr<FJsonObject> Root;const bool Read=FFileHelper::LoadFileToString(Text,*Samples)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)&&Root.IsValid();Check(Read,TEXT("private original sample manifest loads"));
    if(Read){
        const TSharedPtr<FJsonObject>* Models=nullptr;Check(Root->TryGetObjectField(TEXT("models"),Models),TEXT("sample models available"));
        if(Models)for(const FString Id:{FString(TEXT("110")),FString(TEXT("307"))}){
            const TSharedPtr<FJsonObject>* Row=nullptr;if(!(*Models)->TryGetObjectField(Id,Row)){Check(false,TEXT("missing sample ")+Id);continue;}
            FString MeshPath;(*Row)->TryGetStringField(TEXT("asset"),MeshPath);auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*MeshPath);Check(Mesh!=nullptr,TEXT("original sample mesh loads ")+Id);if(!Mesh)continue;
            auto* A=GetWorld()->SpawnActor<ASkeletalMeshActor>();auto* B=GetWorld()->SpawnActor<ASkeletalMeshActor>();
            auto* Body=A->GetSkeletalMeshComponent();auto* Other=B->GetSkeletalMeshComponent();Body->SetSkeletalMeshAsset(Mesh);Other->SetSkeletalMeshAsset(Mesh);
            TArray<UMaterialInterface*> Originals;for(int32 I=0;I<Body->GetNumMaterials();++I)Originals.Add(Body->GetMaterial(I));
            FBridgeGhostMaterials Ghost;Check(Ghost.Load(Manifest),TEXT("separate ghost library loads ")+Id);
            Check(Ghost.Apply(A,true,true,Id==TEXT("307")),TEXT("original outfit ghosted atomically ")+Id);
            Check(Ghost.ChangedSlots()==Originals.Num()&&Ghost.DepthProxies()==1&&Ghost.MissingSlots()==0,TEXT("one proxy per mesh and every material mapped ")+Id);
            float Opacity=0;auto* First=Cast<UMaterialInstanceDynamic>(Body->GetMaterial(0));
            Check(First&&First->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeGhostOpacity")),Opacity)&&FMath::IsNearlyEqual(Opacity,Id==TEXT("307")?.9f:.5f),TEXT("original monster/race opacity retained ")+Id);
            Check(Other->GetMaterial(0)==Originals[0]&&Mesh->GetMaterials()[0].MaterialInterface==Originals[0],TEXT("other NPC and shared skeletal material untouched ")+Id);
            TArray<USkeletalMeshComponent*> Parts;A->GetComponents(Parts);USkeletalMeshComponent* Depth=nullptr;for(auto* Part:Parts)if(Part->ComponentHasTag(FBridgeGhostMaterials::DepthTag))Depth=Part;
            Check(Depth&&Depth->LeaderPoseComponent.Get()==Body&&Depth->GetAttachParent()==Body,TEXT("depth follows the source pose and component transform ")+Id);
            Check(Depth&&Depth->bRenderCustomDepth&&!Depth->bRenderInMainPass&&!Depth->bRenderInDepthPass&&Depth->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("proxy writes custom depth only and has no collision ")+Id);
            Body->SetCullDistance(4321.f);Body->SetBoundsScale(1.2f);Ghost.Apply(A,true,true,Id==TEXT("307"));
            Check(Depth&&FMath::IsNearlyEqual(Depth->LDMaxDrawDistance,4321.f)&&FMath::IsNearlyEqual(Depth->BoundsScale,1.2f),TEXT("proxy respects source draw distance and bounds ")+Id);
            const int32 Slots=Ghost.ChangedSlots();Ghost.Apply(A,true,true,Id==TEXT("307"));Check(Ghost.ChangedSlots()==Slots&&Ghost.DepthProxies()==1,TEXT("repeat snapshot does not duplicate materials or proxies ")+Id);
            Ghost.Apply(A,false,true,true);Check(Ghost.ChangedSlots()==0&&Ghost.DepthProxies()==0&&Body->GetMaterial(0)==Originals[0],TEXT("unknown state restores exact original materials ")+Id);
            if(auto* CustomDepth=IConsoleManager::Get().FindConsoleVariable(TEXT("r.CustomDepth"))){const int32 Previous=CustomDepth->GetInt();CustomDepth->Set(0,ECVF_SetByCode);Check(!Ghost.Apply(A,true,true,false)&&Ghost.ChangedSlots()==0&&Body->GetMaterial(0)==Originals[0],TEXT("disabled depth pass preserves ordinary visible appearance ")+Id);CustomDepth->Set(Previous,ECVF_SetByCode);}
            auto* Tint=UMaterialInstanceDynamic::Create(Originals[0],Body);Tint->SetScalarParameterValue(TEXT("RoughnessFactor"),.61f);Body->SetMaterial(0,Tint);Ghost.Apply(A,true,true,false);
            float Roughness=0;Check(Body->GetMaterial(0)->GetScalarParameterValue(FMaterialParameterInfo(TEXT("RoughnessFactor")),Roughness)&&FMath::IsNearlyEqual(Roughness,.61f),TEXT("original MID uniforms survive the ghost copy ")+Id);
            Ghost.Restore();Check(Body->GetMaterial(0)==Tint,TEXT("restoration retains actual source MID identity ")+Id);
            Body->SetMaterial(0,Originals[0]);Ghost.Apply(A,true,true,false);
            auto* Equipment=NewObject<UStaticMeshComponent>(A);A->AddInstanceComponent(Equipment);Equipment->SetupAttachment(Body);Equipment->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Equipment->SetMaterial(0,Originals[0]);Equipment->RegisterComponent();
            Check(Ghost.Apply(A,true,true,false)&&Ghost.DepthProxies()==2,TEXT("new static equipment receives an independent depth proxy ")+Id);
            Equipment->SetVisibility(false);Ghost.Apply(A,true,true,false);Check(Ghost.DepthProxies()==1&&Equipment->GetMaterial(0)==Originals[0],TEXT("hidden equipment releases ghost material and depth ")+Id);
            A->RemoveInstanceComponent(Equipment);Equipment->DestroyComponent();
            auto* NewOutfit=UMaterial::GetDefaultMaterial(MD_Surface);Body->SetMaterial(0,NewOutfit);
            Check(!Ghost.Apply(A,true,true,false)&&Ghost.MissingSlots()>0&&Ghost.ChangedSlots()==0&&Ghost.DepthProxies()==0,TEXT("unmapped replacement restores entire outfit ")+Id);
            Check(Body->GetMaterial(0)==NewOutfit,TEXT("cleanup cannot overwrite a newer outfit ")+Id);
            Body->SetMaterial(0,Originals[0]);Ghost.Apply(A,true,true,false);Ghost.Apply(B,true,true,false);
            Check(Body->GetMaterial(0)==Originals[0]&&Ghost.DepthProxies()==1,TEXT("actor identity switch restores the previous NPC ")+Id);
            Ghost.Apply(B,true,false,false);Check(Ghost.ChangedSlots()==0&&Ghost.DepthProxies()==0&&Other->GetMaterial(0)==Originals[0],TEXT("ordinary state clears the new NPC ghost presentation ")+Id);
            Ghost.Apply(B,true,true,false);B->Destroy();Ghost.Restore();Check(Ghost.ChangedSlots()==0&&Ghost.DepthProxies()==0,TEXT("removed actor cleanup has no retained ghost slots ")+Id);
            A->Destroy();
        }
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);Report->SetBoolField(TEXT("installed"),false);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Output);UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
