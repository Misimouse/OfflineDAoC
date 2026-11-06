#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeWaterData.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/SecureHash.h"

bool UDAoCBridgeSubsystem::TickWaterAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWaterDataTest="),File))return false;
    static bool Done=false;if(Done)return true;Done=true;
    TArray<FString> Failures;int32 Checks=0;
    auto Check=[&](bool V,const TCHAR* Name){++Checks;if(!V)Failures.Add(Name);};
    FBridgeWaterData Water;FString Path;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeWaterField="),Path);
    Check(Water.Load(Path),TEXT("bounded original water catalog loads"));
    int32 Wet=0;FVector Witness=FVector::ZeroVector;float Height=0;
    if(Water.Ready)for(int32 Y=0;Y<256;++Y)for(int32 X=0;X<256;++X){
        const FVector Point(((X+.5)*6.4-1364)*100,((Y+.5)*6.4-1263)*100,0);
        const auto Sample=Water.Sample(Point,-20000);if(Sample.Present){++Wet;Witness=Point;Height=Sample.Height;}
        Check(Sample.Present==(Water.Mask[Y*256+X]!=255),TEXT("native cell sampler preserves original wet/dry mask"));
    }
    Check(Wet==6785,TEXT("all original Connacht water cells retained"));
    Witness.Z=Height-30;
    Check(Water.Sample(Witness,Height-200).Swimming,TEXT("deep water enters surface swim"));
    Check(!Water.Sample(Witness,Height-125).Swimming,TEXT("exact original depth threshold stays wading"));
    Check(Water.Sample(Witness,Height-125.1).Swimming,TEXT("depth above original threshold swims"));
    Check(FMath::Abs(Water.Sample(Witness,Height-200).TargetFeet-(Height-30))<.01,TEXT("original feet offset retained"));
    Witness.Z=Height+5;Check(!Water.Sample(Witness,Height-200).Swimming,TEXT("bridge and above-surface feet do not swim"));
    Witness.Z=Height-11;Check(Water.Sample(Witness,Height-100).Wading,TEXT("shallow water selects wet steps"));
    Witness.Z=Height-10;Check(!Water.Sample(Witness,Height-100).Wading,TEXT("exact wet-step threshold remains dry"));
    Check(!Water.Sample(FVector(-200000,0,0),Height-200).Present,TEXT("outside map cannot extend river footprint"));
    for(const int32 Model:{318,1983,1984,388,378,310,382,700,352,708,1075,1087,1419}){
        const auto* Row=ModelCatalog.Find(FString::FromInt(Model));FString Clip;if(Row)(*Row)->TryGetStringField(TEXT("swim"),Clip);
        Check(!Clip.IsEmpty()&&LoadObject<UAnimSequence>(nullptr,*Clip)!=nullptr,TEXT("playable original swim clip available"));
    }
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("wet_cells"),Wet);
    uint8 Hash[20]={};if(!Water.Mask.IsEmpty())FSHA1::HashBuffer(Water.Mask.GetData(),Water.Mask.Num(),Hash);Report->SetStringField(TEXT("mask_sha1"),BytesToHex(Hash,20).ToLower());
    TArray<TSharedPtr<FJsonValue>> Errors;for(const auto& E:Failures)Errors.Add(MakeShared<FJsonValueString>(E));Report->SetArrayField(TEXT("failures"),Errors);
    Report->SetBoolField(TEXT("movement_implemented"),false);Report->SetBoolField(TEXT("visuals_modified"),false);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
    bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
