#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeQuestIndicator.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "ProceduralMeshComponent.h"

void UDAoCBridgeSubsystem::UpdateNpcQuestIndicator(const FString& Id, AActor& Actor, const FJsonObject& Row)
{
    const int32 Indicator = BridgeQuestIndicator::FromRow(Row);
    UProceduralMeshComponent* Ring = NpcQuestRings.FindRef(Id).Get();
    if (Ring && Ring->GetOwner() != &Actor)
    {
        Ring->DestroyComponent();
        Ring = nullptr;
    }
    if (!Indicator)
    {
        if (Ring)
            Ring->DestroyComponent();
        NpcQuestRings.Remove(Id);
        return;
    }

    if (!Ring)
    {
        auto* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/DAoCVisualBridge/SpellVisuals_v01/M_SpellAdd.M_SpellAdd"));
        auto* White = LoadObject<UTexture2D>(nullptr, TEXT("/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture"));
        if (!Base || !White || !Actor.GetRootComponent())
            return;
        Ring = NewObject<UProceduralMeshComponent>(&Actor);
        Actor.AddInstanceComponent(Ring);
        Ring->SetupAttachment(Actor.GetRootComponent());
        Ring->SetAbsolute(false, true, true);
        Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Ring->SetGenerateOverlapEvents(false);
        Ring->SetCanEverAffectNavigation(false);
        Ring->SetCastShadow(false);
        Ring->bReceivesDecals = false;
        const float Cull = Quality == TEXT("accessible") ? 6000.f : Quality == TEXT("balanced") ? 9000.f : Quality == TEXT("high") ? 12500.f : 15000.f;
        Ring->SetCullDistance(Cull);
        Ring->RegisterComponent();

        TArray<FVector> Positions;
        TArray<int32> Indices;
        TArray<FVector2D> UV;
        constexpr int32 ArcSegments = 12;
        for (int32 Arc = 0; Arc < 3; ++Arc)
        {
            const int32 Start = Positions.Num();
            for (int32 Step = 0; Step <= ArcSegments; ++Step)
            {
                const float T = float(Step) / ArcSegments;
                const double Angle = (double(Arc) + .12 + .85 * T) * UE_TWO_PI / 3.0;
                const FVector Direction(FMath::Cos(Angle), FMath::Sin(Angle), 0);
                const float HalfWidth = FMath::Lerp(1.2f, 5.2f, T);
                Positions.Add(Direction * (59.f - HalfWidth));
                Positions.Add(Direction * (59.f + HalfWidth));
                UV.Add(FVector2D(.5, .5));
                UV.Add(FVector2D(.5, .5));
                if (Step == 0)
                    continue;
                const int32 Vertex = Start + 2 * (Step - 1);
                Indices.Append({Vertex, Vertex + 1, Vertex + 2, Vertex + 1, Vertex + 3, Vertex + 2});
            }
        }
        TArray<FVector> Normals;
        Normals.Init(FVector::UpVector, Positions.Num());
        Ring->CreateMeshSection_LinearColor(0, Positions, Indices, Normals, UV, TArray<FLinearColor>(), TArray<FProcMeshTangent>(), false);
        auto* Material = UMaterialInstanceDynamic::Create(Base, Ring);
        Material->SetTextureParameterValue(TEXT("Sprite"), White);
        Material->SetScalarParameterValue(TEXT("Opacity"), .85f);
        Ring->SetMaterial(0, Material);
        Ring->ComponentTags.Add(TEXT("DAoCNpcQuestRing"));
        NpcQuestRings.Add(Id, Ring);
    }
    if (auto* Material = Cast<UMaterialInstanceDynamic>(Ring->GetMaterial(0)))
        Material->SetVectorParameterValue(TEXT("Tint"), BridgeQuestIndicator::Color(Indicator));
    const double ScaleZ = FMath::Max(.01, FMath::Abs(Actor.GetActorScale3D().Z));
    Ring->SetRelativeLocation(FVector(0, 0, 6 / ScaleZ));
}
