#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeKeyConfiguration.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

bool UDAoCBridgeSubsystem::TickPersonalTorchAcceptance(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgePersonalTorchTest="),Path))return false;
    static bool Done=false;if(Done)return true;Done=true;int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const TCHAR* Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FBridgeKeyConfiguration Keys;Check(Keys.Text(TEXT("show_trainer"),0)==TEXT("T")&&Keys.Text(TEXT("personal_torch"),0)==TEXT("Shift+T"),TEXT("torch does not replace original training key"));
    FString Message;Check(Keys.Bind(TEXT("personal_torch"),0,TEXT("Ctrl+T"),Message)&&Keys.Text(TEXT("show_trainer"),0)==TEXT("T"),TEXT("torch is editable without changing trainer"));
    FFileHelper::SaveStringToFile(TEXT("[KeyConfiguration]\nVersion=1\n[Bindings]\njump0=Shift+T\n"),*(Path+TEXT(".keys.ini")));FBridgeKeyConfiguration Migrated;Migrated.Load(Path+TEXT(".keys.ini"));
    Check(Migrated.Text(TEXT("jump"),0)==TEXT("Shift+T")&&Migrated.Text(TEXT("personal_torch"),0)==TEXT("-"),TEXT("saved binding takes precedence over new torch default"));
    FFileHelper::SaveStringToFile(TEXT("{\"preserved_test_field\":\"retained\"}"),*ControlsFile);const bool SavedPreference=bPersonalTorchEnabled;bPersonalTorchEnabled=false;SaveControls();
    FString SavedText;TSharedPtr<FJsonObject> Saved;FFileHelper::LoadFileToString(SavedText,*ControlsFile);FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(SavedText),Saved);
    Check(Saved.IsValid()&&Saved->GetStringField(TEXT("preserved_test_field"))==TEXT("retained")&&!Saved->GetBoolField(TEXT("personal_torch")),TEXT("torch preference persists and preserves unrelated settings"));bPersonalTorchEnabled=SavedPreference;
    Session=TEXT("PrivateTorchTest");bLocalAvailable=true;PlayerPosition=FVector::ZeroVector;LastSnapshot=FPlatformTime::Seconds();bControls=false;
    auto Spawn=[&](){auto* A=GetWorld()->SpawnActor<AActor>();auto* Root=NewObject<USceneComponent>(A);A->SetRootComponent(Root);A->AddInstanceComponent(Root);Root->SetMobility(EComponentMobility::Movable);Root->RegisterComponent();return A;};
    auto* Local=Spawn();Entities.Add(TEXT("player:local"),Local);
    auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("enabled"),true);State->SetNumberField(TEXT("energy_scale"),1.);
    ApplyPersonalTorch(State);TickPersonalTorch();Check(PersonalTorchLights.Num()==1,TEXT("one local source created"));
    auto* Lamp=PersonalTorchLights.FindRef(TEXT("player:local")).Get();auto* Light=Lamp?Cast<UPointLightComponent>(Lamp->GetRootComponent()):nullptr;
    Check(Light&&Light->AttenuationRadius==3000.f&&!Light->CastShadows,TEXT("original 30 metre range and no shadows"));
    Check(Light&&Light->LightColor==FColor::White&&Light->IntensityUnits==ELightUnits::Lumens,TEXT("white source uses explicit Unreal photometry"));
    Check(Lamp&&Lamp->GetActorLocation().Equals(FVector(0,0,320),.01),TEXT("original 3.2 metre world height"));
    if(Local){Local->SetActorScale3D(FVector(4));Local->SetActorLocation(FVector(10,20,30));}TickPersonalTorch();
    Check(Lamp&&Lamp->GetActorLocation().Equals(FVector(10,20,350),.01),TEXT("figure scale does not magnify torch height"));
    State->SetNumberField(TEXT("energy_scale"),.15);ApplyPersonalTorch(State);TickPersonalTorch();Check(Light&&FMath::IsNearlyEqual(Light->Intensity,90.f),TEXT("daytime attenuates personal light only"));
    State->SetBoolField(TEXT("enabled"),false);ApplyPersonalTorch(State);TickPersonalTorch();Check(PersonalTorchLights.IsEmpty(),TEXT("server-confirmed off destroys source"));
    for(int32 I=0;I<25;++I){FString Id=FString::Printf(TEXT("player:%d"),I);auto* A=Spawn();Entities.Add(Id,A);auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("kind"),TEXT("player"));Row->SetBoolField(TEXT("torch_on"),true);EntityRows.Add(Id,Row);}
    TickPersonalTorch();Check(PersonalTorchLights.Num()==16,TEXT("nearby peer lights have hard source budget"));
    for(auto& P:Entities)if(P.Key!=TEXT("player:local")&&P.Value){P.Value->SetActorLocation(FVector(10000,0,0));}
    TickPersonalTorch();Check(PersonalTorchLights.IsEmpty(),TEXT("distant peers do not retain sources"));
    State->SetBoolField(TEXT("enabled"),true);ApplyPersonalTorch(State);TickPersonalTorch();Check(PersonalTorchLights.Num()==1,TEXT("local source returns after toggling on"));
    State->SetNumberField(TEXT("energy_scale"),5.);ApplyPersonalTorch(State);TickPersonalTorch();Check(PersonalTorchLights.IsEmpty(),TEXT("out of range intensity clears stale source"));
    State->SetNumberField(TEXT("energy_scale"),1.);State->SetStringField(TEXT("enabled"),TEXT("true"));ApplyPersonalTorch(State);Check(!bPersonalTorchMetadata,TEXT("non boolean torch state refused"));
    State->SetBoolField(TEXT("enabled"),true);ApplyPersonalTorch(State);TickPersonalTorch();LastSnapshot=FPlatformTime::Seconds()-4.;TickPersonalTorch();Check(PersonalTorchLights.IsEmpty(),TEXT("lost snapshot cannot leave ghost light"));
    LastSnapshot=FPlatformTime::Seconds();ApplyPersonalTorch(State);TickPersonalTorch();bLocalAvailable=false;TickPersonalTorch();Check(PersonalTorchLights.IsEmpty(),TEXT("lobby or missing local player removes light"));
    const bool Preference=bPersonalTorchEnabled;ClearPersonalTorch();Check(bPersonalTorchEnabled==Preference,TEXT("world cleanup preserves user preference"));
    for(auto& P:Entities)if(IsValid(P.Value))P.Value->Destroy();Entities.Empty();EntityRows.Empty();Session.Empty();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("real_server"),false);Report->SetBoolField(TEXT("visual_intensity_approved"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
