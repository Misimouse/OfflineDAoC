#include "DAoCBridgeSubsystem.h"
#include "Engine/StaticMesh.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Kismet/KismetSystemLibrary.h"
#if WITH_EDITOR
#include "MeshDescription.h"
#include "StaticMeshAttributes.h"
#endif

// Private acceptance entry point: never runs during an ordinary session.
bool UDAoCBridgeSubsystem::TickGroundObjectFrameAcceptance(){
    FString ReportPath;
    if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectFramesTest="),ReportPath))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    int32 Checks=0,Assets=0,Models=0;int64 Vertices=0;double MaxError=0;
    TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    Check(Socket==nullptr,TEXT("no live connection"));
    FString Input,Text;TSharedPtr<FJsonObject> Catalog;
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectCatalog="),Input);
    Check(FFileHelper::LoadFileToString(Text,*Input)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog),TEXT("measured candidate catalogue loads"));
#if WITH_EDITOR
    if(Catalog.IsValid()){
        TSet<FString> Seen;
        const auto Rows=Catalog->GetObjectField(TEXT("models"));Models=Rows->Values.Num();
        for(const auto& Pair:Rows->Values){
            const auto Row=Pair.Value->AsObject();const FString AssetPath=Row->GetStringField(TEXT("asset"));
            if(Seen.Contains(AssetPath))continue;Seen.Add(AssetPath);++Assets;
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*AssetPath);
            Check(Mesh!=nullptr,AssetPath+TEXT(": native mesh loads"));if(!Mesh)continue;
            const FMeshDescription* Description=Mesh->GetMeshDescription(0);
            Check(Description!=nullptr,AssetPath+TEXT(": original imported vertices available"));if(!Description)continue;
            const auto TransformRow=Row->GetObjectField(TEXT("world_transform"));
            auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());};
            const auto& Q=TransformRow->GetArrayField(TEXT("quaternion_xyzw"));
            const FTransform Transform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),Vec(TransformRow->GetArrayField(TEXT("translation_cm"))),Vec(TransformRow->GetArrayField(TEXT("scale"))));
            Check(Transform.IsValid(),AssetPath+TEXT(": world transform valid"));
            FStaticMeshConstAttributes Attributes(*Description);const auto Positions=Attributes.GetVertexPositions();FBox Actual(ForceInit);
            for(const FVertexID Vertex:Description->Vertices().GetElementIDs()){Actual+=Transform.TransformPosition(FVector(Positions[Vertex]));++Vertices;}
            const auto& Bounds=Row->GetArrayField(TEXT("original_world_bounds_cm"));
            const FVector ExpectedMin=Vec(Bounds[0]->AsArray()),ExpectedMax=Vec(Bounds[1]->AsArray());
            double Error=0;for(int32 Axis=0;Axis<3;++Axis)Error=FMath::Max(Error,FMath::Max(FMath::Abs(Actual.Min[Axis]-ExpectedMin[Axis]),FMath::Abs(Actual.Max[Axis]-ExpectedMax[Axis])));
            MaxError=FMath::Max(MaxError,Error);
            Check(Actual.IsValid&&Error<.02,AssetPath+FString::Printf(TEXT(": actual world bounds error %.9f cm"),Error));
        }
        Check(Models==1021&&Assets==918,TEXT("all prepared rigid models verified against native assets"));
    }
#else
    Check(false,TEXT("editor mesh source required"));
#endif
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("assets"),Assets);Report->SetNumberField(TEXT("models"),Models);Report->SetNumberField(TEXT("vertices"),Vertices);Report->SetNumberField(TEXT("max_bounds_error_cm"),MaxError);Report->SetArrayField(TEXT("failures"),Failures);
    FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*ReportPath);
    UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
