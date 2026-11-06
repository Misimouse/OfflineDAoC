#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/CameraActor.h"
#include "Engine/World.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

class FBridgeFootsteps {
    UDAoCBridgeSubsystem* S;
    TMap<FString,TArray<float>> Contacts;
    TSharedPtr<FJsonObject> Index;
    TWeakObjectPtr<UAnimSequence> Previous;
    TWeakObjectPtr<ASkeletalMeshActor> PreviousActor;
    FString PreviousKey;
    float LastTime=0;
    int32 Steps=0,Sampled=0;
public:
    explicit FBridgeFootsteps(UDAoCBridgeSubsystem* Owner):S(Owner){
        FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalFootstepAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeFootstepSoundCatalog="),Path);
        FString Text;if(FFileHelper::LoadFileToString(Text,*Path))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Index);
    }
    const TArray<float>& ContactTimes(int32 Model,const FString& Clip,UAnimSequence* Animation){
        const FString Key=FString::FromInt(Model)+TEXT(":")+Clip+TEXT(":")+GetPathNameSafe(Animation);
        if(const auto* Found=Contacts.Find(Key))return *Found;
        TArray<float> Times;
        auto Child=[](const TSharedPtr<FJsonObject>& O,const FString& Name){const TSharedPtr<FJsonObject>* V=nullptr;return O&&O->TryGetObjectField(Name,V)?*V:TSharedPtr<FJsonObject>();};
        auto Source=Child(Child(Child(Child(Index,TEXT("local_player_models")),FString::FromInt(Model)),TEXT("contacts")),Clip);
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;double Length=0;
        // Use the original Godot bone-contact witness. Refuse changed clips;
        // do not infer steps from a timer or a retargeted reference skeleton.
        if(Animation&&Source&&Source->TryGetNumberField(TEXT("length"),Length)&&FMath::IsFinite(Length)&&Length>0&&
            FMath::Abs(Animation->GetPlayLength()-Length)<=.02&&Source->TryGetArrayField(TEXT("contacts"),Values)&&Values->Num()<=16){
            for(const auto& Value:*Values){
                double T=0;if(!Value->TryGetNumber(T)||!FMath::IsFinite(T)||T<0||T>=Length||(!Times.IsEmpty()&&T<=Times.Last())){Times.Empty();break;}
                Times.Add(float(T*Animation->GetPlayLength()/Length));
            }
        }
        ++Sampled;return Contacts.Add(Key,MoveTemp(Times));
    }
    bool Advance(int32 Model,const FString& Clip,UAnimSequence* Animation,float At,bool Moving){
        const FString Key=FString::FromInt(Model)+TEXT(":")+Clip;
        if(!Animation||!Moving||Previous!=Animation||PreviousKey!=Key){Previous=Animation;PreviousKey=Key;LastTime=At;return false;}
        bool Crossed=false;for(float T:ContactTimes(Model,Clip,Animation))if(At>=LastTime?(T>LastTime&&T<=At):(T>LastTime||T<=At)){Crossed=true;break;}
        LastTime=At;if(Crossed)++Steps;return Crossed;
    }
    void Tick(){
        auto* Actor=Cast<ASkeletalMeshActor>(S->Entities.FindRef(TEXT("player:local")));
        auto* Row=S->EntityRows.Find(TEXT("player:local"));auto* Pawn=S->PlayerPawn.Get();
        if(!Actor||!Row||!Pawn){Previous.Reset();PreviousActor.Reset();return;}
        if(PreviousActor!=Actor){Previous.Reset();PreviousActor=Actor;}
        auto* Mesh=Actor->GetSkeletalMeshComponent();auto* Instance=Mesh->GetSingleNodeInstance();
        auto* Animation=Instance?Cast<UAnimSequence>(Instance->GetCurrentAsset()):nullptr;
        const FString Clip=S->AnimationStates.FindRef(TEXT("player:local"));
        const bool Locomotion=Clip==TEXT("walk")||Clip==TEXT("run")||Clip==TEXT("walk_back")||Clip==TEXT("strafe_left")||Clip==TEXT("strafe_right")||Clip==TEXT("swim");
        const bool Moving=Locomotion&&((Clip==TEXT("swim")&&S->bLocalSwimming)||(Pawn->GetCharacterMovement()->IsMovingOnGround()&&Pawn->GetVelocity().Size2D()>5.f));
        const int32 Model=(*Row)->GetIntegerField(TEXT("model_id"));
        if(Advance(Model,Clip,Animation,Instance?Instance->GetCurrentTime():0,Moving))S->PlayLocalFootstep(Model,S->LocalGroundSurface);
    }
    TSharedPtr<FJsonObject> Report()const{auto Out=MakeShared<FJsonObject>();Out->SetNumberField(TEXT("contacts_crossed"),Steps);Out->SetNumberField(TEXT("clips_sampled"),Sampled);return Out;}
};

void UDAoCBridgeSubsystem::TickFootsteps(){if(!Footsteps)Footsteps=MakeShared<FBridgeFootsteps>(this);Footsteps->Tick();}
void UDAoCBridgeSubsystem::ClearFootsteps(){Footsteps.Reset();}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::FootstepReport()const{return Footsteps?Footsteps->Report():MakeShared<FJsonObject>();}

bool UDAoCBridgeSubsystem::TickFootstepAcceptance(){
    FString File;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeFootstepTest="),File))return false;
    struct FRun {bool Started=false,Done=false;double Began=0;int32 Checks=0;TArray<FString> Failures;TSharedPtr<FJsonObject> Contacts=MakeShared<FJsonObject>();};
    static FRun Run;if(Run.Done)return true;
    auto Check=[&](bool Ok,const FString& Name){++Run.Checks;if(!Ok)Run.Failures.Add(Name);};
    const double Now=FPlatformTime::Seconds();
    if(!Run.Started){
        Run.Started=true;Run.Began=Now;Footsteps=MakeShared<FBridgeFootsteps>(this);
        FString Catalog=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalFootstepAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeFootstepSoundCatalog="),Catalog);
        FString Text;TSharedPtr<FJsonObject> Index;FFileHelper::LoadFileToString(Text,*Catalog);FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Index);
        const TSharedPtr<FJsonObject>* Models=nullptr;
        Check(Index&&Index->TryGetObjectField(TEXT("local_player_models"),Models),TEXT("original player step mapping loaded"));
        if(Models)for(const auto& Pair:(*Models)->Values){
            const FString Model(*Pair.Key);
            const auto* Entry=ModelCatalog.Find(Model);Check(Entry!=nullptr,FString(TEXT("native player model available "))+Model);if(!Entry)continue;
            auto ModelContacts=MakeShared<FJsonObject>();
            for(const FString Clip:{TEXT("walk"),TEXT("run")}){
                FString Asset;(*Entry)->TryGetStringField(Clip,Asset);auto* Animation=LoadObject<UAnimSequence>(nullptr,*Asset);
                Check(Animation!=nullptr,Model+TEXT(" original clip ")+Clip);if(!Animation)continue;
                const auto& Times=Footsteps->ContactTimes(FCString::Atoi(*Model),Clip,Animation);Check(!Times.IsEmpty(),Model+TEXT(" original foot contacts match native clip ")+Clip);
                TArray<TSharedPtr<FJsonValue>> Values;for(float T:Times)Values.Add(MakeShared<FJsonValueNumber>(T));ModelContacts->SetArrayField(*Clip,Values);
                Check(!Footsteps->Advance(FCString::Atoi(*Model),Clip,Animation,0,false),TEXT("stationary baseline is silent"));
                int32 Triggered=0;for(int32 I=1;I<=96;++I)Triggered+=Footsteps->Advance(FCString::Atoi(*Model),Clip,Animation,Animation->GetPlayLength()*I/96.f,true);
                Check(Triggered==Times.Num(),Model+TEXT(" one event per actual contact ")+Clip);
                Check(!Footsteps->Advance(FCString::Atoi(*Model),Clip,Animation,0,false)&&!Footsteps->Advance(FCString::Atoi(*Model),Clip,Animation,.5,false),TEXT("blocked or stopped animation is silent"));
            }
            Run.Contacts->SetObjectField(*Model,ModelContacts);
        }
        if(!Camera)Camera=GetWorld()->SpawnActor<ACameraActor>();
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),TEXT("player:local"));Row->SetStringField(TEXT("kind"),TEXT("player"));Row->SetStringField(TEXT("name"),TEXT("Footstep acceptance"));Row->SetNumberField(TEXT("model_id"),1984);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);
        EntityRows.Add(TEXT("player:local"),Row);auto* Local=CreateEntity(TEXT("player:local"),Row,FVector::ZeroVector);
        Check(IsValid(Local),TEXT("actual local player actor exists"));PlayLocalFootstep(1984);TickSpellAudio();
        Check(SpellAudioReport()->GetBoolField(TEXT("footstep_ready")),TEXT("separate original footstep audio catalog ready"));
    }
    TickSpellAudio();
    if(Now-Run.Began>1){
        auto Audio=SpellAudioReport();if(Audio->GetNumberField(TEXT("pcm_consumed_bytes"))<=0&&Now-Run.Began<4)return true;
        Check(Audio->GetNumberField(TEXT("played_clips"))==1,TEXT("one original local dirt step reaches playback"));
        Check(Audio->GetNumberField(TEXT("pcm_consumed_bytes"))>0,TEXT("engine consumes original footstep PCM"));
        Check(Audio->GetNumberField(TEXT("invalid_resources"))==0,TEXT("no invalid footstep resource"));
        Audio->SetObjectField(TEXT("sampled_contacts"),Run.Contacts);Audio->SetObjectField(TEXT("footstep_clock"),FootstepReport());Audio->SetNumberField(TEXT("checks"),Run.Checks);Audio->SetBoolField(TEXT("passed"),Run.Failures.IsEmpty());
        TArray<TSharedPtr<FJsonValue>> Failures;for(const auto& Name:Run.Failures)Failures.Add(MakeShared<FJsonValueString>(Name));Audio->SetArrayField(TEXT("failures"),Failures);
        Audio->SetBoolField(TEXT("owner_listening_accepted"),false);FString Text;FJsonSerializer::Serialize(Audio,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);
        ClearSpellAudio();ClearFootsteps();Run.Done=true;bExiting=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
    }
    return true;
}
