#pragma once
#include "CoreMinimal.h"
#include "ProceduralMeshComponent.h"
class AStaticMeshActor;
class FJsonObject;
class UTexture2D;

// Source controller data is local art, never server or character state.
class FDAoCLobbyMotion {
    struct FSection {
        TArray<FVector> Vertices,Normals;
        TArray<int32> Indices;
        TArray<FVector2D> UV[4];
        TArray<FLinearColor> Colors;
        TArray<FProcMeshTangent> Tangents;
        FString Material;
        bool Moving=false;
    };
    struct FController {
        int32 Section=0,Offset=0;
        TArray<FVector> Base;
        TArray<TArray<FVector>> Shapes;
        TArray<double> Times;
        TArray<TArray<double>> Weights;
        double Start=0,Stop=0,Frequency=1,Phase=0;
        FString Cycle;
    };
    TArray<FSection> Sections;
    TArray<FController> Controllers;
    struct FBillboard {int32 Section=0,Offset=0;FVector Origin,Toward;TArray<FVector> Base;bool Animated=false;};
    TArray<FBillboard> Billboards;
    TArray<TWeakObjectPtr<UTexture2D>> ResidentTextures;
    struct FAmbientEmitter {TSharedPtr<FJsonObject> Spec;UProceduralMeshComponent* Mesh=nullptr;TArray<FVector> Vertices,Normals;TArray<FVector2D> UV;TArray<int32> Indices;TArray<FLinearColor> Colors;int32 Slots=0;};
    TArray<FAmbientEmitter> Ambient;
    void LoadAmbient(AStaticMeshActor* Actor,const FString& Path);
    void TickAmbient(double Time);
    FVector Camera=FVector(-72.7,-428,-381);
    double LastResidency=-60;
    UProceduralMeshComponent* Mesh=nullptr; // owned by the retained backdrop actor
    double Began=0,Last=-1;
public:
    static TSharedPtr<FDAoCLobbyMotion> Load(AStaticMeshActor* Actor,const FString& Path);
    void Tick();
    void SetCamera(FVector Eye){Camera=Eye;}
    int32 MovingSurfaces()const{return Controllers.Num();}
    int32 AmbientEmitters()const{return Ambient.Num();}
    int32 AmbientParticles()const{int32 N=0;for(const auto& E:Ambient)N+=E.Slots;return N;}
    bool CheckAmbientMotion(); // opt-in native acceptance; no live world
};
