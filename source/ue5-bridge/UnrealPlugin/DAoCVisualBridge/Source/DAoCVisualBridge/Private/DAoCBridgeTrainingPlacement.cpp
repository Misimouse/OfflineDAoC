#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Engine/World.h"
#include "Components/PrimitiveComponent.h"
#include "Kismet/KismetSystemLibrary.h"

// Read-only placement queries against the same private runtime collision layer
// used by the character. Nothing is spawned in the server or saved in the map.
bool UDAoCBridgeSubsystem::TickTrainingPlacement(){
    FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeTrainingPlacement="),Path))return false;
    static bool Ran=false;if(Ran)return true;Ran=true;
    FString Text;TSharedPtr<FJsonObject> Input;auto Out=MakeShared<FJsonObject>();bool Found=false;int32 Checked=0;
    if(FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Input)){
        auto P=Input->GetArrayField(TEXT("center_m"));const FVector Center((P[0]->AsNumber()-1364)*100,(P[2]->AsNumber()-1263)*100,(P[1]->AsNumber()-130)*100);double Yaw=0;Input->TryGetNumberField(TEXT("yaw"),Yaw);
        for(double Radius:{800.,1200.,1600.,2000.}){
            if(Found)break;
            for(double Angle:{0.,45.,-45.,90.,-90.,135.,-135.,180.}){
                ++Checked;FVector At=Center+FRotator(0,Yaw+Angle,0).Vector()*Radius;FCollisionQueryParams Query(SCENE_QUERY_STAT(BridgeTrainingPlacement),true);FHitResult Floor;bool Hit=false;
                for(int32 I=0;I<8;++I){if(!GetWorld()->LineTraceSingleByChannel(Floor,At+FVector(0,0,1000),At-FVector(0,0,2000),ECC_Pawn,Query))break;auto* C=Floor.GetComponent();if(C&&C->ComponentHasTag(TEXT("DAoCBridgeTree"))){Query.AddIgnoredComponent(C);continue;}Hit=C&&C->ComponentHasTag(TEXT("DAoCBridgeTerrain"))&&Floor.ImpactNormal.Z>.8;break;}
                if(!Hit)continue;At.Z=Floor.ImpactPoint.Z;FCollisionQueryParams Body(SCENE_QUERY_STAT(BridgeTrainingClearance),true);Body.AddIgnoredActor(Floor.GetActor());
                if(GetWorld()->OverlapBlockingTestByChannel(At+FVector(0,0,102),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(40,100),Body))continue;
                Out->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(At.X/100+1364),MakeShared<FJsonValueNumber>(At.Z/100+130),MakeShared<FJsonValueNumber>(At.Y/100+1263)});Out->SetNumberField(TEXT("distance_m"),Radius/100);Out->SetNumberField(TEXT("facing_yaw"),(Center-At).Rotation().Yaw);Found=true;break;
            }
        }
    }
    Out->SetBoolField(TEXT("passed"),Found&&bNavigationReady);Out->SetNumberField(TEXT("positions_checked"),Checked);Out->SetBoolField(TEXT("map_saved"),false);Out->SetBoolField(TEXT("server_modified"),false);FJsonSerializer::Serialize(Out,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".result.json")));UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
