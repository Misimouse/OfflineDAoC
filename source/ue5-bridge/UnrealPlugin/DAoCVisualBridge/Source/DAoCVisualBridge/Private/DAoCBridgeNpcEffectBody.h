#pragma once
#include "Components/BoxComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

inline UBoxComponent* BridgeNpcEffectBounds(AActor* Actor){
    if(!IsValid(Actor)||!Actor->ActorHasTag(TEXT("DAoCBridgeEffectBody")))return nullptr;
    TInlineComponentArray<UBoxComponent*> Boxes;Actor->GetComponents(Boxes);
    for(auto* Box:Boxes)if(Box->ComponentHasTag(TEXT("DAoCBridgeEffectBounds")))return Box;
    return nullptr;
}

inline AActor* BridgeCreateNpcEffectBody(UWorld* World,const FVector& Position,const FActorSpawnParameters& Params){
    auto* Actor=World->SpawnActor<AActor>(Position,FRotator::ZeroRotator,Params);if(!Actor)return nullptr;
    Actor->Tags.Add(TEXT("DAoCBridgeEffectBody"));
    auto* Root=NewObject<USceneComponent>(Actor);Actor->AddInstanceComponent(Root);Actor->SetRootComponent(Root);
    Root->SetMobility(EComponentMobility::Movable);Root->RegisterComponent();Actor->SetActorLocation(Position);
    auto* Box=NewObject<UBoxComponent>(Actor);Actor->AddInstanceComponent(Box);Box->SetupAttachment(Root);
    Box->ComponentTags.Add(TEXT("DAoCBridgeEffectBounds"));Box->SetBoxExtent(FVector(1));
    Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);Box->SetGenerateOverlapEvents(false);
    Box->SetCanEverAffectNavigation(false);Box->SetHiddenInGame(false);Box->SetVisibility(false);Box->RegisterComponent();
    return Actor;
}
