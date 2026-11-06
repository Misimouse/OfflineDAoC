#include "DAoCBridgeSubsystem.h"
#include "Engine/SkeletalMesh.h"
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
    Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetObjectField(TEXT("riders"),Riders);Report->SetArrayField(TEXT("horse_bones"),Bones);
    TArray<TSharedPtr<FJsonValue>> Errors;for(const auto& F:Failures)Errors.Add(MakeShared<FJsonValueString>(F));Report->SetArrayField(TEXT("failures"),Errors);
    FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(Report,Writer);FFileHelper::SaveStringToFile(Json,*File);
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
