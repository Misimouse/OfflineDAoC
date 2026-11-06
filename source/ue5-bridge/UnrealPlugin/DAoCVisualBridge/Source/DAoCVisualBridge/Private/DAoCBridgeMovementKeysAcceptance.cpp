#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeMovementKeys.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

bool UDAoCBridgeSubsystem::TickMovementKeysAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeMovementKeysTest="),File))return false;
    static bool Done=false;if(Done)return true;Done=true;int32 Checks=0;TArray<FString> Failures;
    auto Check=[&](bool Value,const TCHAR* Label){++Checks;if(!Value)Failures.Add(Label);};
    FBridgeMovementKeys K;
    auto F=K.Advance(true,true,false,false,false,false,false,false,false,false,false);Check(K.RunLock&&F.Forward==1&&F.SpeedFactor==1,TEXT("NumLock starts forward run"));
    F=K.Advance(true,false,false,false,false,false,false,false,false,false,false);Check(K.RunLock&&F.Forward==1,TEXT("run lock persists without held key"));
    F=K.Advance(true,false,true,false,false,false,false,false,false,false,false);Check(K.WalkToggle&&F.Forward==1&&F.SpeedFactor==.35f,TEXT("ScrollLock walks while run lock remains active"));
    F=K.Advance(true,false,false,false,true,false,true,false,false,false,false);Check(!K.RunLock&&F.Forward==-1&&F.SpeedFactor==.65f,TEXT("backward cancels run lock and uses original modern speed"));
    F=K.Advance(true,false,false,false,false,false,false,false,false,false,false);Check(F.Forward==0&&K.WalkToggle,TEXT("releasing backward stops without resuming run lock"));
    K.Reset();F=K.Advance(true,false,false,true,false,true,false,false,false,true,false);Check(F.Forward==1&&F.SpeedFactor==.35f,TEXT("Shift walk remains available"));
    K.RunLock=true;F=K.Advance(true,false,false,false,false,false,false,false,false,false,true);Check(!K.RunLock&&F.Forward==1,TEXT("both mouse buttons retain forward movement and cancel lock"));
    K.RunLock=true;F=K.Advance(false,true,true,false,false,false,false,false,false,false,false);Check(!K.RunLock&&!K.WalkToggle&&F.Forward==0,TEXT("blocked input ignores toggles and clears automatic movement"));
    K.RunLock=true;K.WalkToggle=true;K.Reset();Check(!K.RunLock&&!K.WalkToggle,TEXT("logout resets both movement toggles"));
    F=K.Advance(true,false,false,false,false,true,false,true,true,false,false);Check(F.Forward==1&&F.Right==0,TEXT("opposed strafe inputs cancel"));
    K.RunLock=true;F=K.Advance(true,false,false,true,false,true,false,false,false,false,false);Check(!K.RunLock&&F.Forward==1,TEXT("manual forward cancels automatic mode"));
    K.RunLock=true;F=K.Advance(true,true,false,false,false,false,false,false,false,false,false);Check(!K.RunLock&&F.Forward==0,TEXT("second NumLock stops"));
    FString Catalog;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeMovementKeysCatalog="),Catalog);Check(K.Load(Catalog)&&K.Backward.Num()==13,TEXT("all original backward strides load"));
    for(const auto& Row:K.Backward){
        const auto* Entry=ModelCatalog.Find(FString::FromInt(Row.Key));FString Path;if(Entry)(*Entry)->TryGetStringField(TEXT("walk_back"),Path);auto* Clip=LoadObject<UAnimSequence>(nullptr,*Path);
        Check(Clip!=nullptr,TEXT("original model backward animation resolves"));
        Check(Clip&&FMath::IsNearlyEqual(double(Clip->GetPlayLength()),Row.Value.Y,.01),TEXT("native backward clip retains original duration"));
        const double Expected=FMath::Clamp((3.10375/.025)/(Row.Value.X/Row.Value.Y),.3,3.);
        Check(FMath::IsNearlyEqual(double(K.BackwardRate(Row.Key,3.10375f)),Expected,.001),TEXT("model-specific backward cadence follows original stride"));
    }
    Check(K.BackwardRate(-1,3)==1,TEXT("unknown model keeps its default cadence"));
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("models"),K.Backward.Num());TArray<TSharedPtr<FJsonValue>> Errors;for(auto& E:Failures)Errors.Add(MakeShared<FJsonValueString>(E));Report->SetArrayField(TEXT("failures"),Errors);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
