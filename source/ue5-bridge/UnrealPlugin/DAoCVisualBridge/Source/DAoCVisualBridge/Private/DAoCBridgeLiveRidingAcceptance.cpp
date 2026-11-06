#include "DAoCBridgeSubsystem.h"
#include "Engine/SkeletalMesh.h"
#include "DAoCBridgeLiveRiding.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Animation/AnimSequenceBase.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickLiveRidingAssetAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeLiveRidingAssetTest="),File))return false;
    static bool Done=false;if(Done)return true;Done=true;int32 Checks=0;TArray<FString> Failures;
    auto Check=[&](bool V,const FString& Label){++Checks;if(!V)Failures.Add(Label);};
    auto Report=MakeShared<FJsonObject>();auto Riders=MakeShared<FJsonObject>();
    for(int32 Id:{318,1983,1984,388,378,310,382,700,352,708,1075,1087,1419}){
        auto Row=MakeShared<FJsonObject>();auto* Entry=ModelCatalog.Find(FString::FromInt(Id));FString Path;
        const bool Found=Entry&&(*Entry)->TryGetStringField(TEXT("ride_horse"),Path);Check(Found,FString::Printf(TEXT("original rider %d has ride_horse catalog entry"),Id));
        auto* Clip=Found?LoadObject<UAnimSequenceBase>(nullptr,*Path):nullptr;Check(Clip&&Clip->GetPlayLength()>0,FString::Printf(TEXT("original rider %d animation loads"),Id));
        Row->SetStringField(TEXT("animation"),Path);Row->SetNumberField(TEXT("seconds"),Clip?Clip->GetPlayLength():0);Riders->SetObjectField(FString::FromInt(Id),Row);
    }
    auto* Entry=ModelCatalog.Find(TEXT("2174"));FString Path;if(Entry)(*Entry)->TryGetStringField(TEXT("asset"),Path);
    auto* Horse=LoadObject<USkeletalMesh>(nullptr,*Path);Check(Horse!=nullptr,TEXT("original Hibernian stable horse mesh loads"));
    TArray<TSharedPtr<FJsonValue>> Bones;
    if(Horse){
        const FReferenceSkeleton& Ref=Horse->GetRefSkeleton();bool Spine=false;
        for(int32 I=0;I<Ref.GetNum();++I){
            FTransform Transform=Ref.GetRefBonePose()[I];for(int32 P=Ref.GetParentIndex(I);P>=0;P=Ref.GetParentIndex(P))Transform=Transform*Ref.GetRefBonePose()[P];
            auto Bone=MakeShared<FJsonObject>();const FString Name=Ref.GetBoneName(I).ToString();Bone->SetStringField(TEXT("name"),Name);Bone->SetNumberField(TEXT("index"),I);Bone->SetNumberField(TEXT("parent"),Ref.GetParentIndex(I));
            const FVector P=Transform.GetLocation();Bone->SetArrayField(TEXT("component_cm"),{MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)});Bones.Add(MakeShared<FJsonValueObject>(Bone));
            FString Clean=Name.Replace(TEXT("_"),TEXT("")).Replace(TEXT("-"),TEXT("")).Replace(TEXT(" "),TEXT(""));if(Clean.Equals(TEXT("Bip01Spine1"),ESearchCase::IgnoreCase))Spine=true;
        }
        Check(Spine,TEXT("horse spine anchor survives import"));
        for(const FString Key:{TEXT("idle"),TEXT("walk"),TEXT("run")}){FString Animation;(*Entry)->TryGetStringField(Key,Animation);Check(LoadObject<UAnimSequenceBase>(nullptr,*Animation)!=nullptr,TEXT("horse locomotion loads: ")+Key);}
    }
    FString DataPath;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeRidingCatalog="),DataPath);FBridgeLiveRidingData Data;
    Check(Data.Load(DataPath),TEXT("source-verified saddle catalog loads"));
    FBridgeLiveRidingData Missing;Check(!Missing.Load(DataPath+TEXT(".absent")),TEXT("missing seat data cannot silently use guessed saddle"));
    FVector Seat;Check(!Data.Resolve(nullptr,2174,Seat),TEXT("missing component rejected"));
    if(Horse){
        auto* First=GetWorld()->SpawnActor<ASkeletalMeshActor>();auto* Second=GetWorld()->SpawnActor<ASkeletalMeshActor>();
        auto* Mesh=First->GetSkeletalMeshComponent();auto* Other=Second->GetSkeletalMeshComponent();
        Mesh->SetSkeletalMeshAsset(Horse);Other->SetSkeletalMeshAsset(Horse);Mesh->RefreshBoneTransforms();Other->RefreshBoneTransforms();
        const FVector Reference(-.00000718784,8.24311027246,158.02972997649); // independently recovered original glTF rest point, cm
        for(double Scale:{.5,1.,1.3}){
            const FTransform Transform(FRotator(0,73,0),FVector(234,-162,58),FVector(Scale));Mesh->SetWorldTransform(Transform);Mesh->RefreshBoneTransforms();
            Check(Data.Resolve(Mesh,2174,Seat),TEXT("instance-scaled saddle resolves"));
            Check(FVector::Dist(Seat,Transform.TransformPosition(Reference))<.05,TEXT("rest saddle matches original source under scale rotation and translation"));
        }
        Check(!Data.Resolve(Mesh,449,Seat),TEXT("unprepared horse model has no invented seat"));
        Mesh->SetWorldTransform(FTransform::Identity);Other->SetWorldTransform(FTransform(FQuat::Identity,FVector(0,400,0),FVector(.75)));
        Mesh->RefreshBoneTransforms();Other->RefreshBoneTransforms();FVector FirstRest,OtherRest;Data.Resolve(Mesh,2174,FirstRest);Data.Resolve(Other,2174,OtherRest);
        FString Run;(*Entry)->TryGetStringField(TEXT("run"),Run);if(auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Run)){
            Mesh->PlayAnimation(Clip,true);Mesh->TickAnimation(.32f,false);Mesh->RefreshBoneTransforms();FVector Posed;Check(Data.Resolve(Mesh,2174,Posed),TEXT("animated spine resolves original saddle offset"));
            Check(FVector::Dist(Posed,FirstRest)>.5,TEXT("seat follows actual galloping back instead of remaining at fixed height"));
            FVector OtherAfter;Data.Resolve(Other,2174,OtherAfter);Check(OtherAfter.Equals(OtherRest,.01),TEXT("another horse instance cannot reuse this horse posed saddle"));
        }
        First->Destroy();Second->Destroy();
    }
    Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetObjectField(TEXT("riders"),Riders);Report->SetArrayField(TEXT("horse_bones"),Bones);
    TArray<TSharedPtr<FJsonValue>> Errors;for(const auto& F:Failures)Errors.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Errors);
    FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(Report,Writer);FFileHelper::SaveStringToFile(Json,*File);
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
