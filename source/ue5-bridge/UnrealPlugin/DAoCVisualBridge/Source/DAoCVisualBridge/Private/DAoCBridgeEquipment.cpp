#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeAppearance.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UnrealClient.h"

namespace {
double EquipmentAnimationLastMs=0,EquipmentAnimationPeakMs=0;
TSharedPtr<FJsonObject> EquipmentDyePalette,EquipmentEmblemCatalog;int32 EquipmentDyeMissingParameters=0;
bool GearFlag(const TSharedPtr<FJsonObject>& O,const TCHAR* K){bool V=false;if(O.IsValid())O->TryGetBoolField(K,V);return V;}
double GearNum(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
FString GearStr(const TSharedPtr<FJsonObject>& O,const TCHAR* K){FString V;if(O.IsValid())O->TryGetStringField(K,V);return V;}
TSharedPtr<FJsonObject> GearObj(const TSharedPtr<FJsonObject>& O,const FString& K){const TSharedPtr<FJsonObject>* V=nullptr;return O.IsValid()&&O->TryGetObjectField(K,V)?*V:nullptr;}
bool GearArray(const TSharedPtr<FJsonObject>& O,const TCHAR* K,int32 Count,TArray<double>& Out){
    const TArray<TSharedPtr<FJsonValue>>* A=nullptr;if(!O.IsValid()||!O->TryGetArrayField(K,A)||A->Num()!=Count)return false;
    for(const auto& V:*A){double N=0;if(!V->TryGetNumber(N)||!FMath::IsFinite(N))return false;Out.Add(N);}return true;
}
float GearSrgb(float C){return C<=.0031308f?C*12.92f:1.055f*FMath::Pow(C,1.f/2.4f)-.055f;}
float GearLinear(float C){return C<=.04045f?C/12.92f:FMath::Pow((C+.055f)/1.055f,2.4f);}
int32 ApplyOriginalDye(UMeshComponent* Component,int32 Id){
    if(!Component||Id<=0||!EquipmentDyePalette.IsValid())return 0;TArray<double> Values;
    if(!GearArray(EquipmentDyePalette,*FString::FromInt(Id),3,Values))return 0;
    for(double C:Values)if(C<0||C>1)return 0;
    if(Values[0]==1&&Values[1]==1&&Values[2]==1)return 0;
    int32 Applied=0;
    for(int32 Slot=0;Slot<Component->GetNumMaterials();++Slot){auto* Source=Component->GetMaterial(Slot);if(!Source)continue;FLinearColor Base;
        if(!Source->GetVectorParameterValue(FMaterialParameterInfo(TEXT("BaseColorFactor")),Base)){++EquipmentDyeMissingParameters;continue;}
        const FLinearColor Tint(GearLinear(GearSrgb(Base.R)*float(Values[0])),GearLinear(GearSrgb(Base.G)*float(Values[1])),GearLinear(GearSrgb(Base.B)*float(Values[2])),Base.A);
        auto* Copy=UMaterialInstanceDynamic::Create(Source,Component);Copy->SetVectorParameterValue(TEXT("BaseColorFactor"),Tint);Component->SetMaterial(Slot,Copy);++Applied;
    }
    return Applied;
}
int32 ApplyOriginalEmblem(UMeshComponent* Component,const TSharedPtr<FJsonObject>& Info,int32 Id){
    if(!Component||Id<=0||!EquipmentEmblemCatalog.IsValid())return 0;
    const FString SurfaceName=GearStr(Info,TEXT("emblem"));if(SurfaceName.IsEmpty())return 0;
    auto* Material=LoadObject<UMaterialInterface>(nullptr,*GearStr(EquipmentEmblemCatalog,TEXT("material")));
    auto* Surface=LoadObject<UTexture>(nullptr,*GearStr(GearObj(EquipmentEmblemCatalog,TEXT("surfaces")),*SurfaceName));
    const int32 LogoId=Id>>9,PatternKey=LogoId==0?512:Id&511;
    auto* Pattern=LoadObject<UTexture>(nullptr,*GearStr(GearObj(EquipmentEmblemCatalog,TEXT("patterns")),*FString::FromInt(PatternKey)));
    const FString LogoPath=GearStr(GearObj(EquipmentEmblemCatalog,TEXT("logos")),*FString::FromInt(LogoId));auto* Logo=LogoPath.IsEmpty()?nullptr:LoadObject<UTexture>(nullptr,*LogoPath);
    if(!Material||!Surface||!Pattern)return 0;
    auto* Copy=UMaterialInstanceDynamic::Create(Material,Component);Copy->SetTextureParameterValue(TEXT("Surface"),Surface);Copy->SetTextureParameterValue(TEXT("Pattern"),Pattern);Copy->SetScalarParameterValue(TEXT("HasLogo"),Logo?1.f:0.f);if(Logo)Copy->SetTextureParameterValue(TEXT("Logo"),Logo);
    // Godot applies the emblem after dye and replaces every shield surface with this material.
    const int32 Count=Component->GetNumMaterials();for(int32 Slot=0;Slot<Count;++Slot)Component->SetMaterial(Slot,Copy);return Count;
}
bool GearReference(const TSharedPtr<FJsonObject>& O,FTransform& Out){
    TArray<double> T,Q,S;if(!GearArray(O,TEXT("translation_cm"),3,T)||!GearArray(O,TEXT("quaternion_xyzw"),4,Q)||!GearArray(O,TEXT("scale"),3,S))return false;
    for(double V:S)if(V<=.00001||V>100)return false;FQuat Rotation(Q[0],Q[1],Q[2],Q[3]);if(!Rotation.IsNormalized())return false;
    Out=FTransform(Rotation,FVector(T[0],T[1],T[2]),FVector(S[0],S[1],S[2]));return true;
}
}
void UDAoCBridgeSubsystem::LoadEquipmentCatalog(){
    FString Path;EquipmentDyePalette.Reset();EquipmentEmblemCatalog.Reset();if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeEquipmentCatalog="),Path))return;
    FString Text;TSharedPtr<FJsonObject> Root;if(FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root)&&GearNum(Root,TEXT("version"))==1){EquipmentCatalog=GearObj(Root,TEXT("models"));ArmourCatalog=GearObj(Root,TEXT("armour"));EquipmentDyePalette=GearObj(Root,TEXT("dyes"));EquipmentEmblemCatalog=GearObj(Root,TEXT("emblems"));}
}
bool UDAoCBridgeSubsystem::BuildEmblemPickerShield(UStaticMeshComponent* Component,int32 Value){
    auto Row=GearObj(EquipmentCatalog,TEXT("60"));if(!Component||!Row||Value<512||Value>131071)return false;
    auto* Mesh=LoadObject<UStaticMesh>(nullptr,*GearStr(Row,TEXT("asset")));if(!Mesh)return false;
    if(Component->GetStaticMesh()!=Mesh)Component->SetStaticMesh(Mesh);
    return ApplyOriginalEmblem(Component,GearObj(Row,TEXT("info")),Value)>0;
}
void UDAoCBridgeSubsystem::ClearLocalEquipment(){
    ResetLocalStealthMaterials();
    for(auto& Pair:LocalEquipment)if(Pair.Value.Component.IsValid())Pair.Value.Component->DestroyComponent();
    LocalEquipment.Empty();EquipmentActor.Reset();EquipmentFingerprint.Empty();EquipmentMissingModels=0;EquipmentMissingBones=0;
    for(auto& Pair:RemoteEquipment)for(auto& Gear:Pair.Value.Bindings)if(Gear.Value.Component.IsValid())Gear.Value.Component->DestroyComponent();RemoteEquipment.Empty();
}
bool UDAoCBridgeSubsystem::AttachEquipment(AActor* Actor,int32 Slot,TSharedPtr<FJsonObject> Item,bool Combat,TMap<int32,FEquipmentBinding>& Bindings,int32& MissingModels,int32& MissingBones){
    auto* Skel=Cast<ASkeletalMeshActor>(Actor);if(!Skel||!Item.IsValid())return false;auto* Parent=Skel->GetSkeletalMeshComponent();
    const int32 Model=int32(GearNum(Item,TEXT("model")));auto Entry=GearObj(EquipmentCatalog,FString::FromInt(Model));auto Info=GearObj(Entry,TEXT("info"));if(!Entry.IsValid()){++MissingModels;return false;}if(GearStr(Entry,TEXT("type"))==TEXT("hidden"))return false;
        const bool ShieldModel=GearNum(Info,TEXT("shield"))>0;
        const bool Shield=int32(GearNum(Item,TEXT("object_type")))==42||(ShieldModel&&Slot==11);
        const FString Stance=GearStr(Item,TEXT("weapon_stance"));const bool Back=int32(GearNum(Item,TEXT("hand")))==1||Slot==12||Slot==13||Stance==TEXT("2h")||Stance==TEXT("pole")||Stance==TEXT("staff")||Stance==TEXT("scy");
        FString Bone;
        if(Shield)Bone=TEXT("Bip01-L-Shield");
        else if(Combat||GearNum(Info,TEXT("belt"),1)!=1){
            const bool Left=Slot==11||Slot==13;Bone=ShieldModel?(Left?TEXT("Bip01-L-Shield"):TEXT("Bip01-R-Shield")):(Left?TEXT("Bip01-L-Held"):TEXT("Bip01-R-Held"));
        }else if(Back)Bone=TEXT("Bip01-R-Back");
        else Bone=Slot==11?TEXT("Bip01-R-Belt"):TEXT("Bip01-L-Belt");
        if(Parent->GetBoneIndex(FName(*Bone))==INDEX_NONE){auto Normalize=[](FString S){S.ReplaceInline(TEXT("-"),TEXT(""));S.ReplaceInline(TEXT("_"),TEXT(""));S.ReplaceInline(TEXT(" "),TEXT(""));return S.ToLower();};TArray<FName> Names;Parent->GetBoneNames(Names);for(auto N:Names)if(Normalize(N.ToString())==Normalize(Bone)){Bone=N.ToString();break;}}
        if(Parent->GetBoneIndex(FName(*Bone))==INDEX_NONE){++MissingBones;return false;}
        auto Variant=GearObj(Entry,TEXT("left_variant"));if((Slot==11||Slot==13)&&Variant.IsValid())Entry=Variant;
        FTransform Reference;if(!GearReference(GearObj(Entry,TEXT("reference")),Reference)){++MissingModels;return false;}
        UMeshComponent* Component=nullptr;
        if(GearStr(Entry,TEXT("type"))==TEXT("skeletal")){
            auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*GearStr(Entry,TEXT("asset")));if(!Mesh){++MissingModels;return false;}
            auto* Animated=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Animated->SetSkeletalMesh(Mesh);Animated->bComponentUseFixedSkelBounds=true;Animated->SetAnimationMode(EAnimationMode::AnimationSingleNode);Animated->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;Component=Animated;
        }else{
            auto* Mesh=LoadObject<UStaticMesh>(nullptr,*GearStr(Entry,TEXT("asset")));if(!Mesh){++MissingModels;return false;}
            auto* Rigid=NewObject<UStaticMeshComponent>(Actor,NAME_None,RF_Transient);Rigid->SetStaticMesh(Mesh);Component=Rigid;
        }
        Actor->AddInstanceComponent(Component);Component->SetMobility(EComponentMobility::Movable);Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCastShadow(false);Component->SetCullDistance(Actor==Entities.FindRef(TEXT("player:local")).Get()?0.f:Quality==TEXT("accessible")?6000.f:Quality==TEXT("balanced")?9000.f:Quality==TEXT("high")?12500.f:15000.f);Component->SetGenerateOverlapEvents(false);Component->ComponentTags.Add(TEXT("DAoCBridgeEquipment"));Component->RegisterComponent();
        Component->AttachToComponent(Parent,FAttachmentTransformRules::SnapToTargetIncludingScale,FName(*Bone));Component->SetRelativeTransform(Reference.Inverse());
        FEquipmentBinding Binding;Binding.Component=Component;Binding.Model=Model;Binding.Bone=Bone;Binding.Descriptor=Entry;Binding.Drawn=Combat;Binding.Dye=int32(GearNum(Item,TEXT("color")));Binding.Emblem=int32(GearNum(Item,TEXT("emblem")));Binding.Effect=int32(GearNum(Item,TEXT("effect")));Binding.DyedMaterials=ApplyOriginalDye(Component,Binding.Dye);ApplyOriginalEmblem(Component,Info,Binding.Emblem);Bindings.Add(Slot,Binding);return true;
}
void UDAoCBridgeSubsystem::UpdateLocalEquipment(){
    auto* Found=Entities.Find(TEXT("player:local"));auto* Actor=Found&&IsValid(*Found)?Cast<ASkeletalMeshActor>(*Found):nullptr;
    if(!EquipmentCatalog.IsValid()||!Actor||!bLocalAvailable||!GearFlag(InventoryState,TEXT("ready"))){if(!LocalEquipment.IsEmpty()||EquipmentActor.IsValid())ClearLocalEquipment();return;}
    auto* LocalRow=EntityRows.Find(TEXT("player:local"));
    if(LocalRow&&GearFlag(*LocalRow,TEXT("morphed"))){if(!LocalEquipment.IsEmpty()||EquipmentActor.IsValid())ClearLocalEquipment();return;}
    if(EquipmentActor.Get()!=Actor){ClearLocalEquipment();EquipmentActor=Actor;}
    const bool Combat=GearFlag(PlayerState,TEXT("attack_on"));const FString Set=GearStr(InventoryState,TEXT("weapon_set"));
    auto Look=LocalRow?GearObj(*LocalRow,TEXT("look")):nullptr;FString LookKey;if(Look)FJsonSerializer::Serialize(Look.ToSharedRef(),TJsonWriterFactory<>::Create(&LookKey));
    const FString Fingerprint=FString::Printf(TEXT("%lld:%d:%s"),int64(GearNum(InventoryState,TEXT("state_revision"),-1)),int32(Combat),*Set)+LookKey;
    bool Intact=true;for(const auto& Pair:LocalEquipment)if(!Pair.Value.Component.IsValid())Intact=false;
    if(EquipmentFingerprint==Fingerprint&&Intact)return;
    for(auto& Pair:LocalEquipment)if(Pair.Value.Component.IsValid())Pair.Value.Component->DestroyComponent();LocalEquipment.Empty();EquipmentMissingModels=0;EquipmentMissingBones=0;EquipmentFingerprint=Fingerprint;
    ApplyBodyArmour(Actor,InventoryState);
    const FString AppearancePath=DAoCAppearancePath();
    if(Look&&!AppearancePath.IsEmpty()){
        auto Worn=MakeShared<FJsonObject>();const TMap<int32,FString> Names={{21,TEXT("helmet")},{22,TEXT("gloves")},{23,TEXT("boots")},{25,TEXT("torso")},{26,TEXT("cloak")},{27,TEXT("legs")},{28,TEXT("arms")}};
        for(const auto& Slot:Names)if(auto Item=InventoryItem(Slot.Key))Worn->SetNumberField(Slot.Value,int32(GearNum(Item,TEXT("model"))));
        const int32 Model=EntityModels.FindRef(TEXT("player:local"));
        if(ApplyCharacterAppearance(Actor,Model,Look,ArmourCatalog,AppearancePath,Worn)){
            auto* Definition=ModelCatalog.Find(FString::FromInt(Model));const double Base=Definition?GearNum(*Definition,TEXT("scale"),1):1;const double ServerSize=LocalRow?GearNum(*LocalRow,TEXT("size"),50):50;const int32 Size=FMath::Clamp(int32(GearNum(Look,TEXT("size"),1)),0,2);
            Actor->SetActorScale3D(FVector(FMath::Clamp(Base*ServerSize/50.,.01,20.)*(Size==0?.95:Size==2?1.05:1.)));
        }
    }
    TArray<int32> Slots=Set==TEXT("twohand")?TArray<int32>{12}:Set==TEXT("ranged")?TArray<int32>{13}:TArray<int32>{10,11};
    auto* Parent=Actor->GetSkeletalMeshComponent();auto Right=InventoryItem(10);auto RightInfo=GearObj(GearObj(EquipmentCatalog,FString::FromInt(int32(GearNum(Right,TEXT("model"))))),TEXT("info"));
    for(int32 Slot:Slots){
        auto Item=InventoryItem(Slot);if(!Item.IsValid())continue;const int32 Model=int32(GearNum(Item,TEXT("model")));auto Entry=GearObj(EquipmentCatalog,FString::FromInt(Model));auto Info=GearObj(Entry,TEXT("info"));
        if(!Entry.IsValid()){++EquipmentMissingModels;continue;}
        if(Slot==11&&GearNum(Info,TEXT("shield"))>0&&GearNum(Info,TEXT("stance"))!=13&&GearNum(RightInfo,TEXT("shield"))>0)continue;
        AttachEquipment(Actor,Slot,Item,Combat,LocalEquipment,EquipmentMissingModels,EquipmentMissingBones);
    }
}
void UDAoCBridgeSubsystem::UpdateRemoteEquipment(){
    for(auto It=RemoteEquipment.CreateIterator();It;++It)if(!Entities.Contains(It.Key())||!It.Value().Actor.IsValid()){for(auto& Pair:It.Value().Bindings)if(Pair.Value.Component.IsValid())Pair.Value.Component->DestroyComponent();It.RemoveCurrent();}
    for(auto& Pair:Entities){
        if(Pair.Key==TEXT("player:local")||!IsValid(Pair.Value))continue;auto* Actor=Cast<ASkeletalMeshActor>(Pair.Value.Get());auto* Row=EntityRows.Find(Pair.Key);if(!Actor||!Row)continue;
        auto Gear=GearObj(*Row,TEXT("equipment"));
        // Match local player-form presentation using the original catalogue's
        // known race/body distinction. NPCs keep their own authored weapons;
        // unknown catalogue entries must not silently hide race equipment.
        auto* Model=ModelCatalog.Find(FString::FromInt(int32(GearNum(*Row,TEXT("model_id")))));
        auto Body=Model?GearObj(*Model,TEXT("ghost_render")):nullptr;
        bool RaceFigure=false;
        const bool PlayerForm=GearStr(*Row,TEXT("kind"))==TEXT("player")&&GearFlag(Body,TEXT("known"))&&Body.IsValid()&&Body->TryGetBoolField(TEXT("race_figure"),RaceFigure)&&!RaceFigure;
        if(!Gear.IsValid()||PlayerForm){if(auto* Old=RemoteEquipment.Find(Pair.Key)){for(auto& B:Old->Bindings)if(B.Value.Component.IsValid())B.Value.Component->DestroyComponent();RemoteEquipment.Remove(Pair.Key);}continue;}
        const bool Combat=GearFlag(*Row,TEXT("combat_active"));const int32 Ws=int32(GearNum(Gear,TEXT("weapon_slots"),255))&15;
        const FString Fingerprint=FString::Printf(TEXT("%lld:%d:%d"),int64(GearNum(Gear,TEXT("revision"))),int32(Combat),int32(GearNum(*Row,TEXT("model_id"))));auto& State=RemoteEquipment.FindOrAdd(Pair.Key);
        if(State.Actor.Get()==Actor&&State.Fingerprint==Fingerprint)continue;
        for(auto& B:State.Bindings)if(B.Value.Component.IsValid())B.Value.Component->DestroyComponent();State.Bindings.Empty();State.Actor=Actor;State.Fingerprint=Fingerprint;ApplyBodyArmour(Actor,Gear);
        TMap<int32,TSharedPtr<FJsonObject>> Items;const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;if(Gear->TryGetArrayField(TEXT("items"),Rows))for(auto V:*Rows)if(V->Type==EJson::Object){auto I=V->AsObject();const int32 Slot=int32(GearNum(I,TEXT("slot")));if(Slot>=10&&Slot<=13&&GearNum(I,TEXT("model"))>0)Items.Add(Slot,I);}
        int32 Set=Ws;if(Ws==15)Set=Items.Contains(12)?2:Items.Contains(10)||Items.Contains(11)?0:3;
        const TArray<int32> Slots=Set==2?TArray<int32>{12}:Set==3?TArray<int32>{13}:TArray<int32>{10,11};
        const bool Drawn=Combat||Actor->GetSkeletalMeshComponent()->GetBoneIndex(TEXT("Bip01-R-Belt"))==INDEX_NONE;
        for(int32 Slot:Slots)if(auto* Item=Items.Find(Slot)){
            if(Slot==11&&Items.Contains(10)){auto L=GearObj(GearObj(EquipmentCatalog,FString::FromInt(int32(GearNum(*Item,TEXT("model"))))),TEXT("info"));auto R=GearObj(GearObj(EquipmentCatalog,FString::FromInt(int32(GearNum(Items[10],TEXT("model"))))),TEXT("info"));if(GearNum(L,TEXT("shield"))>0&&GearNum(L,TEXT("stance"))!=13&&GearNum(R,TEXT("shield"))>0)continue;}
            AttachEquipment(Actor,Slot,*Item,Drawn,State.Bindings,RemoteEquipmentMissingModels,RemoteEquipmentMissingBones);
        }
    }
}
// The chain follows its original animation clips, synchronized to confirmed body actions.
void UDAoCBridgeSubsystem::TickEquipmentAnimations(){
    const double Now=FPlatformTime::Seconds();
    auto Animate=[&](const FString& Id,TMap<int32,FEquipmentBinding>& Bindings){
        auto* Row=EntityRows.Find(Id);auto Combat=Row?GearObj(*Row,TEXT("combat_visual")):nullptr;const TArray<TSharedPtr<FJsonValue>>* Events=nullptr;if(Combat.IsValid())Combat->TryGetArrayField(TEXT("events"),Events);
        for(auto& Pair:Bindings){auto& Binding=Pair.Value;auto* Mesh=Cast<USkeletalMeshComponent>(Binding.Component.Get());if(!Mesh)continue;auto Clips=GearObj(Binding.Descriptor,TEXT("animations"));if(!Clips.IsValid())continue;
            if(Binding.Drawn&&Events&&Events->Num()<=8)for(auto Value:*Events){if(Value->Type!=EJson::Object)continue;auto Event=Value->AsObject();const double Seq=GearNum(Event,TEXT("seq")),Age=GearNum(Event,TEXT("age_ms"),-1);if(!FMath::IsFinite(Seq)||Seq<1||Seq>9e15||FMath::FloorToDouble(Seq)!=Seq||int64(Seq)<=Binding.ActionSeq)continue;Binding.ActionSeq=int64(Seq);const FString Kind=GearStr(Event,TEXT("kind")),Body=GearStr(Event,TEXT("clip"));if(!FMath::IsFinite(Age)||Age<0||Age>5000||(Kind!=TEXT("attack")&&Kind!=TEXT("style")))continue;
                FString Swing;
                if(Kind==TEXT("style")){int32 Start=Body.Len();while(Start>0&&FChar::IsDigit(Body[Start-1]))--Start;const int32 Number=Start<Body.Len()?FCString::Atoi(*Body.Mid(Start)):1;int32 Best=MAX_int32;for(int32 K:{1,3,4,6,7}){const FString Key=FString::Printf(TEXT("style_%d"),K);const int32 Distance=FMath::Abs(K-Number);if(Clips->HasField(Key)&&Distance<Best){Best=Distance;Swing=Key;}}}
                if(Swing.IsEmpty()){const FString First=Body.Contains(TEXT("high"))?TEXT("attack_high"):TEXT("attack_low"),Second=Body.Contains(TEXT("high"))?TEXT("attack_low"):TEXT("attack_high");Swing=Clips->HasField(First)?First:Clips->HasField(Second)?Second:FString();}
                FString Path;if(!Swing.IsEmpty()&&Clips->TryGetStringField(Swing,Path))if(auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Path)){Binding.ActionClip=Swing;Binding.ActionBegan=Now-Age/1000;Binding.ActionDuration=Clip->GetPlayLength();}
            }
            const double Age=Now-Binding.ActionBegan;const bool Action=!Binding.ActionClip.IsEmpty()&&Age>=0&&Age<Binding.ActionDuration;
            const FString Wanted=Action?Binding.ActionClip:Binding.Drawn?TEXT("combat_idle"):TEXT("idle");FString Path;if(!Clips->TryGetStringField(Wanted,Path))continue;
            if(Binding.Animation!=Wanted||!Mesh->GetSingleNodeInstance()){if(auto* Clip=LoadObject<UAnimSequenceBase>(nullptr,*Path)){Mesh->PlayAnimation(Clip,!Action);Binding.Animation=Wanted;}}
            if(Action)if(auto* Instance=Mesh->GetSingleNodeInstance())Instance->SetPosition(float(Age),false);
        }
    };
    Animate(TEXT("player:local"),LocalEquipment);for(auto& Pair:RemoteEquipment)Animate(Pair.Key,Pair.Value.Bindings);EquipmentAnimationLastMs=(FPlatformTime::Seconds()-Now)*1000;EquipmentAnimationPeakMs=FMath::Max(EquipmentAnimationPeakMs,EquipmentAnimationLastMs);
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::EquipmentReport() const{
    auto Out=MakeShared<FJsonObject>();int32 RemoteCount=0;for(const auto& Pair:RemoteEquipment)RemoteCount+=Pair.Value.Bindings.Num();Out->SetNumberField(TEXT("dye_missing_parameters"),EquipmentDyeMissingParameters);Out->SetBoolField(TEXT("dye_palette_loaded"),EquipmentDyePalette.IsValid());Out->SetNumberField(TEXT("animation_last_ms"),EquipmentAnimationLastMs);Out->SetNumberField(TEXT("animation_peak_ms"),EquipmentAnimationPeakMs);Out->SetNumberField(TEXT("remote_visible_count"),RemoteCount);Out->SetNumberField(TEXT("remote_missing_models"),RemoteEquipmentMissingModels);Out->SetNumberField(TEXT("remote_missing_bones"),RemoteEquipmentMissingBones);Out->SetNumberField(TEXT("visible_count"),LocalEquipment.Num());Out->SetNumberField(TEXT("missing_models"),EquipmentMissingModels);Out->SetNumberField(TEXT("missing_bones"),EquipmentMissingBones);Out->SetNumberField(TEXT("visual_test_steps"),EquipmentVisualTestSteps);TArray<TSharedPtr<FJsonValue>> Rows;
    for(const auto& Pair:LocalEquipment){auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("slot"),Pair.Key);Row->SetNumberField(TEXT("model"),Pair.Value.Model);Row->SetStringField(TEXT("bone"),Pair.Value.Bone);Row->SetNumberField(TEXT("dye"),Pair.Value.Dye);Row->SetNumberField(TEXT("dyed_materials"),Pair.Value.DyedMaterials);Row->SetBoolField(TEXT("component_valid"),Pair.Value.Component.IsValid());Rows.Add(MakeShared<FJsonValueObject>(Row));}Out->SetArrayField(TEXT("bindings"),Rows);return Out;
}
void UDAoCBridgeSubsystem::UpdateEquipmentVisualTest(double Elapsed){
    if(!GearFlag(PlayerState,TEXT("ready"))||!GearFlag(InventoryState,TEXT("ready")))return;
    if(Elapsed>18&&!(EquipmentVisualTestSteps&1)){FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/TEXT("Equipment_Sheathed.png"),true,false);EquipmentVisualTestSteps|=1;}
    if(Elapsed>22&&!(EquipmentVisualTestSteps&2)){RequestAttack(true);EquipmentVisualTestSteps|=2;}
    if(Elapsed>32&&!(EquipmentVisualTestSteps&4)){FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/TEXT("Equipment_Drawn.png"),true,false);EquipmentVisualTestSteps|=4;}
    if(Elapsed>45&&!(EquipmentVisualTestSteps&8)){RequestAttack(false);EquipmentVisualTestSteps|=8;}
    if(Elapsed>55&&!(EquipmentVisualTestSteps&16)){FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/TEXT("Equipment_Restored.png"),true,false);EquipmentVisualTestSteps|=16;}
}
