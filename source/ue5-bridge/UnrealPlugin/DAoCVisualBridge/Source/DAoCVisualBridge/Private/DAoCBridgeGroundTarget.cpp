#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/Texture2D.h"
#include "Engine/EngineTypes.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "Framework/Application/SlateApplication.h"
#include "ImageUtils.h"

namespace{
double GN(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double Default=0){double V=Default;if(O)O->TryGetNumberField(K,V);return V;}
TArray<TSharedPtr<FJsonValue>> GA(const TSharedPtr<FJsonObject>& O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>();}
FVector GPoint(const TArray<TSharedPtr<FJsonValue>>& P){return FVector((P[0]->AsNumber()-1364)*100,(P[2]->AsNumber()-1263)*100,(P[1]->AsNumber()-130)*100);}
}
void UDAoCBridgeSubsystem::ResetGroundTarget(){if(GroundTargetMarker.IsValid())GroundTargetMarker->Destroy();GroundTargetMarker.Reset();GroundTargetState.Reset();GroundTargetRevision=-1;bHasGroundTarget=false;LastGroundTargetSight=-10000;}
void UDAoCBridgeSubsystem::TickGroundTargetSight(){
    const double Now=FPlatformTime::Seconds();if(!bHasGroundTarget||!bLocalAvailable||bExiting||Session.IsEmpty()||Now-LastGroundTargetSight<.3)return;
    auto Value=MakeShared<FJsonObject>();Value->SetNumberField(TEXT("ground_target_revision"),GroundTargetRevision);Value->SetBoolField(TEXT("ground_target_in_view"),GroundTargetVisible());Send(TEXT("ground_target_sight"),Value);LastGroundTargetSight=Now;
}
bool UDAoCBridgeSubsystem::GroundTargetVisible()const{
    if(!bHasGroundTarget||!bLocalAvailable||!GetWorld()||GroundTargetPoint.ContainsNaN())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeGroundSight),true);if(PlayerPawn)Query.AddIgnoredActor(PlayerPawn);for(const auto& Pair:Entities)if(IsValid(Pair.Value.Get()))Query.AddIgnoredActor(Pair.Value.Get());
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,PlayerPosition+FVector(0,0,100),GroundTargetPoint+FVector(0,0,4),ECC_Camera,Query);
}
bool UDAoCBridgeSubsystem::SendGroundTargetPoint(const FVector& Point,bool Visible){
    if(!bLocalAvailable||bExiting||Session.IsEmpty()||Point.ContainsNaN()||FVector::DistSquared(Point,PlayerPosition)>FMath::Square(25000.f))return false;
    auto V=MakeShared<FJsonObject>();V->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(Point.X/100+1364),MakeShared<FJsonValueNumber>(Point.Z/100+130),MakeShared<FJsonValueNumber>(Point.Y/100+1263)});V->SetBoolField(TEXT("visible"),Visible);Send(TEXT("ground_target"),V);return true;
}
bool UDAoCBridgeSubsystem::PickGroundTargetRay(const FVector& Origin,const FVector& Direction,FVector& Point)const{
    if(!GetWorld()||Origin.ContainsNaN()||Direction.ContainsNaN()||Direction.IsNearlyZero())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeGroundPick),true);if(PlayerPawn)Query.AddIgnoredActor(PlayerPawn);for(const auto& Pair:Entities)if(IsValid(Pair.Value.Get()))Query.AddIgnoredActor(Pair.Value.Get());
    FHitResult Hit;if(!GetWorld()->LineTraceSingleByChannel(Hit,Origin,Origin+Direction.GetSafeNormal()*25000,ECC_Camera,Query))return false;Point=Hit.ImpactPoint;return !Point.ContainsNaN();
}
void UDAoCBridgeSubsystem::RequestGroundTarget(){
    if(!bLocalAvailable||bExiting||bChatOpen||bOptionsOpen||!GetWorld()||WorldPointerBlocked(FSlateApplication::Get().GetCursorPos()))return;
    auto* PC=GetWorld()->GetFirstPlayerController();float X=0,Y=0;FVector From,Direction;if(!PC||!PC->GetMousePosition(X,Y)||!PC->DeprojectScreenPositionToWorld(X,Y,From,Direction))return;
    FVector Point;if(!PickGroundTargetRay(From,Direction,Point))return;
    const FVector Previous=GroundTargetPoint;const bool Had=bHasGroundTarget;GroundTargetPoint=Point;bHasGroundTarget=true;const bool Visible=GroundTargetVisible();GroundTargetPoint=Previous;bHasGroundTarget=Had;SendGroundTargetPoint(Point,Visible);
}
void UDAoCBridgeSubsystem::ApplyGroundTarget(TSharedPtr<FJsonObject> State){
    bool Has=false;if(State)State->TryGetBoolField(TEXT("has_point"),Has);auto Position=GA(State,TEXT("position_m"));const int64 Revision=int64(GN(State,TEXT("revision"),-1));
    if(!Has||Position.Num()!=3){ResetGroundTarget();GroundTargetState=State;GroundTargetRevision=Revision;return;}
    for(const auto& P:Position)if(P->Type!=EJson::Number||!FMath::IsFinite(P->AsNumber()))return;
    GroundTargetState=State;if(Revision==GroundTargetRevision&&GroundTargetMarker.IsValid())return;
    ResetGroundTarget();GroundTargetState=State;GroundTargetRevision=Revision;GroundTargetPoint=GPoint(Position);bHasGroundTarget=true;if(!GetWorld())return;
    auto* Owner=GetWorld()->SpawnActor<AActor>();if(!Owner)return;Owner->Tags.Add(TEXT("DAoCGroundTarget"));GroundTargetMarker=Owner;auto* Root=NewObject<USceneComponent>(Owner);Owner->SetRootComponent(Root);Root->RegisterComponent();Owner->SetActorLocation(GroundTargetPoint);
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/DAoCVisualBridge/SpellVisuals_v01/M_SpellAdd.M_SpellAdd"));if(!Base)return;
    auto Make=[&](const TArray<FVector>& Vertices,const TArray<int32>& Indices,const TArray<FVector2D>& UV,UTexture2D* Texture,FLinearColor Tint){auto* Mesh=NewObject<UProceduralMeshComponent>(Owner);Owner->AddInstanceComponent(Mesh);Mesh->SetupAttachment(Root);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->bReceivesDecals=false;Mesh->RegisterComponent();auto* Material=UMaterialInstanceDynamic::Create(Base,Mesh);if(Texture)Material->SetTextureParameterValue(TEXT("Sprite"),Texture);Material->SetVectorParameterValue(TEXT("Tint"),Tint);Material->SetScalarParameterValue(TEXT("Opacity"),1);TArray<FVector> Normals;TArray<FLinearColor> Colors;Normals.Init(FVector::UpVector,Vertices.Num());Colors.Init(FLinearColor::White,Vertices.Num());Mesh->CreateMeshSection_LinearColor(0,Vertices,Indices,Normals,UV,Colors,TArray<FProcMeshTangent>(),false);Mesh->SetMaterial(0,Material);};
    FString Text;TSharedPtr<FJsonObject> Model;const auto Folder=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/GroundTarget_v01");
    if(FFileHelper::LoadFileToString(Text,*(Folder/TEXT("model.json")))&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Model)){
        TArray<FVector> Vertices;TArray<FVector2D> UV;TArray<int32> Indices;for(const auto& V:GA(Model,TEXT("vertices"))){const auto& P=V->AsArray();if(P.Num()!=3)continue;Vertices.Add(FVector(P[0]->AsNumber(),P[2]->AsNumber(),P[1]->AsNumber())*70+FVector(0,0,2));}for(const auto& V:GA(Model,TEXT("uv"))){const auto& P=V->AsArray();if(P.Num()==2)UV.Add({P[0]->AsNumber(),P[1]->AsNumber()});}for(const auto& V:GA(Model,TEXT("indices")))Indices.Add(int32(V->AsNumber()));if(Vertices.Num()==24&&Indices.Num()==36&&UV.Num()==24)Make(Vertices,Indices,UV,LoadObject<UTexture2D>(nullptr,TEXT("/Engine/EngineResources/WhiteSquareTexture.WhiteSquareTexture")),{1,.88f,.12f,1});
    }
    // Project the original 2m bitmap onto world geometry only. Unlike a world
    // decal this mesh cannot paint the character bodies standing above it.
    auto* Texture=FImageUtils::ImportFileAsTexture2D(Folder/TEXT("target.png"));if(!Texture)return;Texture->SRGB=true;Texture->Filter=TF_Bilinear;
    TArray<FVector> Vertices;TArray<FVector2D> UV;TArray<int32> Indices;TArray<bool> Valid;FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeGroundProjection),true);Query.AddIgnoredActor(Owner);if(PlayerPawn)Query.AddIgnoredActor(PlayerPawn);for(const auto& Pair:Entities)if(IsValid(Pair.Value.Get()))Query.AddIgnoredActor(Pair.Value.Get());
    for(int32 Y=0;Y<=8;++Y)for(int32 X=0;X<=8;++X){FVector P=GroundTargetPoint+FVector((X-4)*25,(Y-4)*25,0);FHitResult Hit;bool OK=GetWorld()->LineTraceSingleByChannel(Hit,P+FVector(0,0,150),P-FVector(0,0,150),ECC_Camera,Query);Vertices.Add((OK?Hit.ImpactPoint+FVector(0,0,1.5):P)-GroundTargetPoint);UV.Add({X/8.,Y/8.});Valid.Add(OK);}
    auto Triangle=[&](int32 A,int32 B,int32 C){if(Valid[A]&&Valid[B]&&Valid[C]&&FMath::Max3(Vertices[A].Z,Vertices[B].Z,Vertices[C].Z)-FMath::Min3(Vertices[A].Z,Vertices[B].Z,Vertices[C].Z)<50){Indices.Add(A);Indices.Add(B);Indices.Add(C);}};
    for(int32 Y=0;Y<8;++Y)for(int32 X=0;X<8;++X){int32 A=Y*9+X;Triangle(A,A+1,A+9);Triangle(A+1,A+10,A+9);}Make(Vertices,Indices,UV,Texture,FLinearColor::White);
}
