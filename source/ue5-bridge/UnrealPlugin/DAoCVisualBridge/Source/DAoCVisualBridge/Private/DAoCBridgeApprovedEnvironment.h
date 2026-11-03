#pragma once
#include "CoreMinimal.h"
class UWorld;
class FJsonObject;

// Optional visual bindings supplied by the launcher. These never save art maps.
void EnsureDAoCApprovedEnvironment(UWorld* World);
TSharedPtr<FJsonObject> InspectDAoCApprovedEnvironment(UWorld* World);
