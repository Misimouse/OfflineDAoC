#include "DAoCBridgeSubsystem.h"
#include "Components/PointLightComponent.h"
#include "Engine/World.h"

void UDAoCBridgeSubsystem::ClearPersonalTorch(){
    for(auto& Pair:PersonalTorchLights)if(Pair.Value.IsValid())Pair.Value->Destroy();
    PersonalTorchLights.Empty();bPersonalTorchMetadata=false;PersonalTorchGeneration=-1;PersonalTorchSentAt=-10000;
}
void UDAoCBridgeSubsystem::ApplyPersonalTorch(TSharedPtr<FJsonObject> State){
    bPersonalTorchMetadata=false;
    double Scale=0;bool Enabled=false;
    if(State.IsValid()&&State->HasTypedField<EJson::Boolean>(TEXT("enabled"))&&State->HasTypedField<EJson::Number>(TEXT("energy_scale"))&&State->TryGetBoolField(TEXT("enabled"),Enabled)&&State->TryGetNumberField(TEXT("energy_scale"),Scale)&&FMath::IsFinite(Scale)&&Scale>=.15-1.e-6&&Scale<=1.){
        bPersonalTorchMetadata=true;bPersonalTorchServerEnabled=Enabled;PersonalTorchScale=float(Scale);
    }
    if(!bLocalAvailable||CharacterLobbyOverlay.IsValid()||!bPersonalTorchMetadata){ClearPersonalTorch();return;}
    double Generation=-1;
    if(PlayerState.IsValid()&&PlayerState->TryGetNumberField(TEXT("generation"),Generation)&&FMath::IsFinite(Generation)&&Generation>=0&&Generation==FMath::FloorToDouble(Generation)){
        const bool NewGeneration=PersonalTorchGeneration!=int64(Generation);PersonalTorchGeneration=int64(Generation);
        if(bControls&&(NewGeneration||bPersonalTorchEnabled!=Enabled)&&FPlatformTime::Seconds()-PersonalTorchSentAt>=1.)RequestPersonalTorch();
    }
}
void UDAoCBridgeSubsystem::RequestPersonalTorch(){
    if(!bControls||!bLocalAvailable||CharacterLobbyOverlay.IsValid()||!PlayerState.IsValid()||Session.IsEmpty()||bExiting)return;
    double Generation=-1;bool Ready=false;
    if(!PlayerState->TryGetBoolField(TEXT("ready"),Ready)||!Ready||!PlayerState->TryGetNumberField(TEXT("generation"),Generation)||!FMath::IsFinite(Generation)||Generation<0||Generation!=FMath::FloorToDouble(Generation))return;
    auto Value=MakeShared<FJsonObject>();Value->SetBoolField(TEXT("on"),bPersonalTorchEnabled);Value->SetNumberField(TEXT("player_generation"),Generation);Send(TEXT("personal_torch"),Value);PersonalTorchSentAt=FPlatformTime::Seconds();
}
void UDAoCBridgeSubsystem::TickPersonalTorch(){
    if(!GetWorld()||!bPersonalTorchMetadata||!bLocalAvailable||CharacterLobbyOverlay.IsValid()||Session.IsEmpty()||FPlatformTime::Seconds()-LastSnapshot>3.){ClearPersonalTorch();return;}
    // Bounded nearby sources; world-space height avoids scaled or transformed figure offsets.
    struct FCandidate{FString Id;AActor* Actor;double Distance;};TArray<FCandidate> Candidates;
    for(auto& Pair:Entities){
        auto* A=Pair.Value.Get();if(!IsValid(A))continue;
        const bool Local=Pair.Key==TEXT("player:local");bool Enabled=Local?bPersonalTorchServerEnabled:false;
        if(!Local){auto* Row=EntityRows.Find(Pair.Key);if(!Row||!Row->IsValid())continue;FString Kind;(*Row)->TryGetStringField(TEXT("kind"),Kind);if(Kind!=TEXT("player"))continue;(*Row)->TryGetBoolField(TEXT("torch_on"),Enabled);}
        const double Distance=FVector::DistSquared(A->GetActorLocation(),PlayerPosition);
        if(Enabled&&(Local||Distance<=FMath::Square(6000.)))Candidates.Add({Pair.Key,A,Local?-1.:Distance});
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Distance<B.Distance;});TSet<FString> Keep;
    for(int32 I=0;I<FMath::Min(Candidates.Num(),16);++I){
        const auto& C=Candidates[I];AActor* Lamp=PersonalTorchLights.FindRef(C.Id).Get();
        if(!IsValid(Lamp)){
            Lamp=GetWorld()->SpawnActor<AActor>();if(!Lamp)continue;
            auto* Light=NewObject<UPointLightComponent>(Lamp);Lamp->SetRootComponent(Light);Lamp->AddInstanceComponent(Light);
            Light->SetMobility(EComponentMobility::Movable);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetLightColor(FLinearColor::White);
            Light->SetAttenuationRadius(3000.f);Light->SetCastShadows(false);Light->SetIndirectLightingIntensity(0.f);Light->SetVolumetricScatteringIntensity(0.f);Light->RegisterComponent();
            PersonalTorchLights.Add(C.Id,Lamp);
        }
        Lamp->SetActorLocation(C.Actor->GetActorLocation()+FVector(0,0,320));
        if(auto* Light=Cast<UPointLightComponent>(Lamp->GetRootComponent()))Light->SetIntensity(600.f*PersonalTorchScale);
        Keep.Add(C.Id);
    }
    TArray<FString> Gone;for(auto& Pair:PersonalTorchLights)if(!Keep.Contains(Pair.Key)){if(Pair.Value.IsValid())Pair.Value->Destroy();Gone.Add(Pair.Key);}for(const auto& Id:Gone)PersonalTorchLights.Remove(Id);
}
