#include "DAoCBridgeLiveRiding.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/FileHelper.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

bool FBridgeLiveRidingData::Load(const FString& Path){
    Seats.Empty();FString Text;if(!FFileHelper::LoadFileToString(Text,*Path)||Text.Len()>1024*1024)return false;
    TSharedPtr<FJsonObject> Root;const TSharedPtr<FJsonObject>* Models=nullptr;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)||!Root.IsValid()||!Root->TryGetObjectField(TEXT("models"),Models)||(*Models)->Values.Num()>128)return false;
    TMap<int32,FSeat> Parsed;
    for(const auto& Pair:(*Models)->Values){
        const FString Key(*Pair.Key);if(Pair.Value->Type!=EJson::Object||!Key.IsNumeric())return false;const int32 Id=FCString::Atoi(*Key);if(Id<1||Id>65535||FString::FromInt(Id)!=Key)return false;
        auto Row=Pair.Value->AsObject();FString Name;const TArray<TSharedPtr<FJsonValue>>* Point=nullptr;
        if(!Row->TryGetStringField(TEXT("anchor_bone"),Name)||Name.IsEmpty()||Name.Len()>128||!Row->TryGetArrayField(TEXT("saddle_reference_component_cm"),Point)||Point->Num()!=3)return false;
        double V[3];for(int32 I=0;I<3;++I)if(!(*Point)[I]->TryGetNumber(V[I])||!FMath::IsFinite(V[I])||FMath::Abs(V[I])>10000)return false;
        const TSharedPtr<FJsonObject>* Strides=nullptr;double Walk=0,Run=0;
        if(!Row->TryGetObjectField(TEXT("stride_m"),Strides)||!(*Strides)->TryGetNumberField(TEXT("walk"),Walk)||!(*Strides)->TryGetNumberField(TEXT("run"),Run)||!FMath::IsFinite(Walk)||!FMath::IsFinite(Run)||Walk<=.1||Run<=.1||Walk>=30||Run>=30)return false;
        Parsed.Add(Id,{FName(*Name),FVector(V[0],V[1],V[2]),Walk,Run});
    }
    if(Parsed.IsEmpty())return false;Seats=MoveTemp(Parsed);return true;
}
bool FBridgeLiveRidingData::Resolve(USkeletalMeshComponent* Mesh,int32 Model,FVector& WorldSeat)const{
    const auto* Seat=Seats.Find(Model);if(!Seat||!IsValid(Mesh)||!Mesh->GetSkeletalMeshAsset())return false;
    const FReferenceSkeleton& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();const int32 Index=Ref.FindBoneIndex(Seat->Anchor);if(Index<0)return false;
    FTransform Rest=Ref.GetRefBonePose()[Index];for(int32 Parent=Ref.GetParentIndex(Index);Parent>=0;Parent=Ref.GetParentIndex(Parent))Rest=Rest*Ref.GetRefBonePose()[Parent];
    const FVector Offset=Rest.InverseTransformPosition(Seat->Reference);
    const FTransform Posed=Mesh->GetSocketTransform(Seat->Anchor,RTS_Component);
    WorldSeat=Mesh->GetComponentTransform().TransformPosition(Posed.TransformPosition(Offset));return !WorldSeat.ContainsNaN();
}

float FBridgeLiveRidingData::GaitRate(int32 Model,const FString& Gait,double SpeedMps,double ClipSeconds,double InstanceScale)const{
    const auto* Seat=Seats.Find(Model);if(!Seat||!FMath::IsFinite(SpeedMps)||!FMath::IsFinite(ClipSeconds)||SpeedMps<=0||ClipSeconds<=0||!FMath::IsFinite(InstanceScale)||InstanceScale<.01||InstanceScale>20)return 1.f;
    const double Stride=Gait==TEXT("run")?Seat->RunStride:Gait==TEXT("walk")?Seat->WalkStride:0;
    return Stride>0?float(FMath::Clamp(SpeedMps*ClipSeconds/(Stride*InstanceScale),.3,3.)):1.f;
}
