#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeMovementKeys.h"
#include "DAoCBridgeKeyboardTurning.h"
#include "Animation/AnimSequence.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include <limits>

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
    if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeKeyboardTurningTest"))){
        for(int32 Fps:{15,30,60,144})for(bool Right:{false,true}){
            float Body=12,CameraAngle=81;for(int32 Frame=0;Frame<Fps;++Frame){auto Turn=FBridgeKeyboardTurning::Advance(true,!Right,Right,false,false,1.f/Fps,Body,CameraAngle);Body=Turn.BodyYaw;CameraAngle=Turn.CameraYaw;}
            Check(FMath::Abs(FRotator::NormalizeAxis(Body-12-(Right?180.f:-180.f)))<.005f,TEXT("one second keyboard turn retains original 180-degree rate across frame rates"));
            Check(FMath::IsNearlyEqual(Body,CameraAngle,.001f),TEXT("unheld camera follows idle keyboard turn"));
        }
        for(bool Left:{false,true})for(bool Right:{false,true})for(bool Rmb:{false,true})for(bool Lmb:{false,true}){
            auto Blocked=FBridgeKeyboardTurning::Advance(false,Left,Right,Rmb,Lmb,.2f,12,81);
            Check(!Blocked.Turning&&Blocked.Strafe==0&&Blocked.BodyYaw==12&&Blocked.CameraYaw==81,TEXT("existing blocked-input gate preserves body and camera"));
            auto Frame=FBridgeKeyboardTurning::Advance(true,Left,Right,true,Lmb,.2f,12,81);
            Check(!Frame.Turning&&Frame.BodyYaw==12&&Frame.CameraYaw==81&&Frame.Strafe==(Right?1.f:0.f)-(Left?1.f:0.f),TEXT("original modern right-mouse turn keys strafe without rotation"));
        }
        auto Orbit=FBridgeKeyboardTurning::Advance(true,true,false,false,true,.25f,12,81);
        Check(Orbit.Turning&&Orbit.BodyYaw==-33&&Orbit.CameraYaw==81,TEXT("left-button orbit retains camera independently of body turn"));
        auto Opposed=FBridgeKeyboardTurning::Advance(true,true,true,false,false,.25f,12,81);
        Check(!Opposed.Turning&&Opposed.BodyYaw==12&&Opposed.CameraYaw==81,TEXT("opposed keyboard turns cancel"));
        for(float Delta:{0.f,-1.f,std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}){
            auto Invalid=FBridgeKeyboardTurning::Advance(true,true,false,false,false,Delta,12,81);
            Check(!Invalid.Turning&&Invalid.BodyYaw==12&&Invalid.CameraYaw==81,TEXT("invalid elapsed time cannot rotate character or camera"));
        }
        auto Stalled=FBridgeKeyboardTurning::Advance(true,false,true,false,false,1000,12,81);
        Check(Stalled.Turning&&FMath::Abs(FRotator::NormalizeAxis(Stalled.BodyYaw-12))==180,TEXT("stalled frame has bounded angular displacement"));
    }
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
