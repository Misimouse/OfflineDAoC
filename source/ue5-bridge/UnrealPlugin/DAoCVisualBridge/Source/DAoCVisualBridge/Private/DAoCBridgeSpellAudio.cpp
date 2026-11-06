#include "DAoCBridgeSubsystem.h"
#include "Camera/CameraActor.h"
#include "Components/AudioComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundWaveProcedural.h"

namespace SpellAudioData {
using J=TSharedPtr<FJsonObject>;
J Object(const J& O,const TCHAR* K){const J* V=nullptr;return O&&O->TryGetObjectField(K,V)?*V:nullptr;}
FString String(const J& O,const TCHAR* K){FString V;if(O)O->TryGetStringField(K,V);return V;}
double Number(const J& O,const TCHAR* K,double Default=0){double V=Default;if(O)O->TryGetNumberField(K,V);return FMath::IsFinite(V)?V:Default;}
bool Flag(const J& O,const TCHAR* K){bool V=false;if(O)O->TryGetBoolField(K,V);return V;}
TArray<TSharedPtr<FJsonValue>> Array(const J& O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>();}
J Read(const FString& Path){FString Text;J O;if(FFileHelper::LoadFileToString(Text,*Path))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O);return O;}
float Range(const J& Row,const TCHAR* Key,float Default){auto V=Array(Row,Key);if(V.Num()<2||V[0]->Type!=EJson::Number||V[1]->Type!=EJson::Number)return Default;const float A=float(V[0]->AsNumber()),B=float(V[1]->AsNumber());return FMath::IsFinite(A)&&FMath::IsFinite(B)?FMath::FRandRange(FMath::Min(A,B),FMath::Max(A,B)):Default;}
uint16 U16(const TArray<uint8>& B,int32 I){return uint16(B[I])|(uint16(B[I+1])<<8);}
uint32 U32(const TArray<uint8>& B,int32 I){return uint32(B[I])|(uint32(B[I+1])<<8)|(uint32(B[I+2])<<16)|(uint32(B[I+3])<<24);}
}

class FBridgeSpellAudio {
    using J=SpellAudioData::J;
    struct FPCM {TArray<uint8> Bytes;int32 Rate=0,Channels=0;double Seconds=0;};
    struct FPending {J Row;FString Owner,Phase;double At=0;FString Root;FVector Position=FVector::ZeroVector;bool Anchored=false;bool Direct=false,Spatial=false;};
    struct FVoice {TWeakObjectPtr<UAudioComponent> Component;TWeakObjectPtr<USoundWaveProcedural> Wave;FString Owner,Phase;double Until=0;int32 Remaining=0;bool Anchored=false;float BaseGain=1.f;};
    UDAoCBridgeSubsystem* S;
    J Index,Effects,CombatIndex,DoorIndex,FootstepIndex,ServerIndex;
    FString Folder,CombatFolder,DoorFolder,FootstepFolder,ServerFolder,Session,LastName,LastFile;
    FVector Anchor=FVector::ZeroVector;
    bool Anchored=false;
    TMap<FString,FPCM> Cache;
    TMap<FString,int32> Casts;
    TMap<FString,double> Bursts;
    TArray<FPending> Pending;
    TArray<FVoice> Voices;
    int64 LastSequence=0,LastCombatSequence=0,LastServerSequence=0,CacheBytes=0,Consumed=0,FootstepConsumed=0;
    int32 CombatSeen=0;
    int32 FootstepClips=0,ServerSeen=0,ServerClips=0,ServerRejected=0;
    int32 CombatReceived=0,CombatStale=0,CombatRejected=0;
    int32 Seen=0,Played=0,Culled=0,Duplicates=0,Quiet=0,Missing=0,Invalid=0;
    float GainScale=1;

    AActor* Actor(const FString& Owner)const{return S->Entities.FindRef(Owner);}
    J Definition(int32 Id)const{return SpellAudioData::Object(SpellAudioData::Object(Effects,TEXT("effects")),*FString::FromInt(Id));}
    J Sheet(int32 Id)const{return SpellAudioData::Object(SpellAudioData::Object(Index,TEXT("spells")),*FString::FromInt(Id));}
    void StopVoice(FVoice& V){if(V.Component.IsValid()){V.Component->Stop();V.Component->DestroyComponent();}}
    void DropGather(const FString& Owner){
        for(int32 I=Voices.Num()-1;I>=0;--I)if(Voices[I].Owner==Owner&&Voices[I].Phase==TEXT("gather")){StopVoice(Voices[I]);Voices.RemoveAt(I);}
        Pending.RemoveAll([&](const FPending& P){return P.Owner==Owner&&P.Phase==TEXT("gather");});
    }
    void Structure(const FString& Name,const FString& Owner,const FString& Phase,double Delay,TSet<FString> Trail={},int32 Depth=0){
        using namespace SpellAudioData;
        const FString Key=Name.TrimStartAndEnd().ToLower();
        if(Key.IsEmpty()||Key==TEXT("s_null"))return;
        if(Depth>12||Trail.Contains(Key)){++Invalid;return;}
        Trail.Add(Key);
        auto Groups=Object(Index,TEXT("groups"));const TArray<TSharedPtr<FJsonValue>>* Members=nullptr;
        if(Groups&&Groups->TryGetArrayField(Key,Members)){
            if(!Members->IsEmpty())Structure((*Members)[FMath::RandRange(0,Members->Num()-1)]->AsString(),Owner,Phase,Delay,Trail,Depth+1);
            return;
        }
        if(auto Queue=Object(Object(Index,TEXT("queues")),*Key)){
            const double Gap=FMath::Max(0.f,Range(Queue,TEXT("interval_ms"),0))/1000.;
            for(auto Child:Array(Queue,TEXT("members"))){Structure(Child->AsString(),Owner,Phase,Delay,Trail,Depth+1);Delay+=Gap;}
            return;
        }
        if(auto Row=Object(Object(Index,TEXT("named")),*Key)){
            if(Pending.Num()>=256){++Culled;return;}
            Pending.Add({Row,Owner,Phase,FPlatformTime::Seconds()+FMath::Max(0.,Delay)+FMath::Max(0.f,Range(Row,TEXT("offset_ms"),0))/1000.,Folder,Anchor,Anchored});
        }else ++Missing;
    }
    void Phase(int32 Effect,const FString& Name,const FString& Owner,double Delay=0){
        using namespace SpellAudioData;
        if(!Actor(Owner))return;
        auto Def=Definition(Effect);auto Set=Sheet(int32(Number(Def,TEXT("sound_set"))));
        if(!Set){++Missing;return;}
        Structure(String(Set,*Name),Owner,Name,Delay);
    }
    FPCM* PCM(const FString& Root,const FString& Name){
        const FString CacheKey=Root/Name;
        if(auto Found=Cache.Find(CacheKey))return Found;
        if(!FPaths::IsRelative(Name)||FPaths::GetExtension(Name).ToLower()!=TEXT("wav")){++Invalid;return nullptr;}
        FString Path=FPaths::ConvertRelativePathToFull(Root/Name),Base=FPaths::ConvertRelativePathToFull(Root)+TEXT("/");
        FPaths::NormalizeFilename(Path);FPaths::NormalizeFilename(Base);FPaths::CollapseRelativeDirectories(Path);
        if(!Path.StartsWith(Base,ESearchCase::IgnoreCase)){++Invalid;return nullptr;}
        TArray<uint8> Raw;
        if(!FFileHelper::LoadFileToArray(Raw,*Path)||Raw.Num()<44||Raw.Num()>32*1024*1024||FMemory::Memcmp(Raw.GetData(),"RIFF",4)||FMemory::Memcmp(Raw.GetData()+8,"WAVE",4)){++Invalid;return nullptr;}
        int32 Format=-1,Data=-1,Size=0;
        for(int64 At=12;At+8<=Raw.Num();){
            const uint32 Length=SpellAudioData::U32(Raw,int32(At+4));
            if(At+8+Length>Raw.Num()){++Invalid;return nullptr;}
            if(!FMemory::Memcmp(Raw.GetData()+At,"fmt ",4)&&Length>=16)Format=int32(At+8);
            if(!FMemory::Memcmp(Raw.GetData()+At,"data",4)){Data=int32(At+8);Size=int32(Length);}
            At+=8+int64(Length)+(Length&1);
        }
        using namespace SpellAudioData;
        if(Format<0||Data<0||U16(Raw,Format)!=1||U16(Raw,Format+14)!=16){++Invalid;return nullptr;}
        FPCM Value;Value.Channels=U16(Raw,Format+2);Value.Rate=int32(U32(Raw,Format+4));
        if(Value.Channels<1||Value.Channels>2||Value.Rate<8000||Value.Rate>192000||Size<=0||Size%(Value.Channels*2)){++Invalid;return nullptr;}
        Value.Seconds=double(Size)/(Value.Channels*2*Value.Rate);Value.Bytes.Append(Raw.GetData()+Data,Size);
        if(CacheBytes+Size>32*1024*1024){Cache.Empty();CacheBytes=0;}
        CacheBytes+=Size;return &Cache.Add(CacheKey,MoveTemp(Value));
    }
    void Play(const FPending& Job){
        using namespace SpellAudioData;
        auto* Owner=Actor(Job.Owner);
        if(!IsValid(Owner)&&!Job.Anchored)return;
        float Gain=FMath::Clamp(Range(Job.Row,TEXT("vol"),1),0.f,1.f);
        if(Gain<=0)return;
        auto Distances=Array(Job.Row,TEXT("range_units"));
        const float Near=Distances.Num()>1?FMath::Max(0.f,float(Distances[0]->AsNumber())*2.5f):0;
        const float Far=Distances.Num()>1?FMath::Max(Near+1,float(Distances[1]->AsNumber())*2.5f):2500;
        const FVector Position=Job.Anchored?Job.Position:Owner->GetActorLocation();
        const float Distance=S->Camera?FVector::Distance(Position,S->Camera->GetActorLocation()):0;
        if((!Job.Direct&&Distance>=Far)||Voices.Num()>=48||(!Job.Direct&&Voices.Num()>=24&&Gain*FMath::Clamp(1-(Distance-Near)/(Far-Near),0.f,1.f)<.35f)){++Culled;return;}
        const FString File=String(Job.Row,TEXT("file"));auto* Data=PCM(Job.Root,File);if(!Data)return;
        const float Pitch=FMath::Clamp(Range(Job.Row,TEXT("rate"),1),.05f,4.f);
        auto* Wave=NewObject<USoundWaveProcedural>(S);Wave->NumChannels=Data->Channels;Wave->SetSampleRate(Data->Rate);Wave->Duration=float(Data->Seconds);Wave->bLooping=false;Wave->SoundGroup=SOUNDGROUP_Effects;
        Wave->QueueAudio(Data->Bytes.GetData(),Data->Bytes.Num());
        auto* Attenuation=NewObject<USoundAttenuation>(S);auto& Settings=Attenuation->Attenuation;
        Settings.bAttenuate=!Job.Direct;Settings.bSpatialize=!Job.Direct||Job.Spatial;Settings.DistanceAlgorithm=EAttenuationDistanceModel::Linear;
        Settings.AttenuationShape=EAttenuationShape::Sphere;Settings.AttenuationShapeExtents=FVector(Near,0,0);Settings.FalloffDistance=Far-Near;
        auto* Component=Job.Direct&&!Job.Spatial?UGameplayStatics::SpawnSound2D(S,Wave,Gain*GainScale*S->AudioMasterVolume*S->AudioEffectsVolume,Pitch,0,nullptr,false,true):UGameplayStatics::SpawnSoundAtLocation(S,Wave,Position,FRotator::ZeroRotator,Gain*GainScale*S->AudioMasterVolume*S->AudioEffectsVolume,Pitch,0,Attenuation,nullptr,true);
        if(!Component){++Invalid;return;}
        Voices.Add({Component,Wave,Job.Owner,Job.Phase,FPlatformTime::Seconds()+Data->Seconds/Pitch+.1,Data->Bytes.Num(),Job.Anchored,Gain*GainScale});
        ++Played;LastName=String(Job.Row,TEXT("name"));LastFile=File;
        if(Job.Phase==TEXT("footstep"))++FootstepClips;
        if(Job.Direct)++ServerClips;
    }
public:
    explicit FBridgeSpellAudio(UDAoCBridgeSubsystem* Owner):S(Owner){
        S->LoadAudioSettings();
        FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSoundCatalog="),Path);
        Folder=FPaths::GetPath(Path);Index=SpellAudioData::Read(Path);
        FString CombatPath=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalCombatAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCombatSoundCatalog="),CombatPath);
        CombatFolder=FPaths::GetPath(CombatPath);CombatIndex=SpellAudioData::Read(CombatPath);
        FString DoorPath=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalDoorAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDoorSoundCatalog="),DoorPath);
        DoorFolder=FPaths::GetPath(DoorPath);DoorIndex=SpellAudioData::Read(DoorPath);
        FString FootstepPath=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalFootstepAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeFootstepSoundCatalog="),FootstepPath);
        FootstepFolder=FPaths::GetPath(FootstepPath);FootstepIndex=SpellAudioData::Read(FootstepPath);
        FString ServerPath=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/OriginalServerSoundAudio_v01/sounds.json");
        FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeServerSoundCatalog="),ServerPath);
        ServerFolder=FPaths::GetPath(ServerPath);ServerIndex=SpellAudioData::Read(ServerPath);
        Effects=SpellAudioData::Read(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/SpellVisuals_v01/catalog.json"));
        FString Test;if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeSpellAudioTest="),Test)||FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeCombatAudioTest="),Test)||FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeOptionsAudioTest="),Test)||FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeDoorAudioTest="),Test))GainScale=.03f;
    }
    void Clear(){for(auto& V:Voices)StopVoice(V);Voices.Empty();Pending.Empty();Casts.Empty();Bursts.Empty();LastSequence=0;LastCombatSequence=0;LastServerSequence=0;Session.Empty();}
    void Step(int32 Model){
        using namespace SpellAudioData;
        if(!FootstepIndex)return;
        const auto Mapping=Object(Object(FootstepIndex,TEXT("local_player_models")),*FString::FromInt(Model));
        const auto Row=Object(Object(FootstepIndex,TEXT("creatures")),*FString::FromInt(int32(Number(Mapping,TEXT("sound_set")))));
        TGuardValue<J> IndexGuard(Index,FootstepIndex);TGuardValue<FString> FolderGuard(Folder,FootstepFolder);
        Structure(String(Row,TEXT("move_dirt")),TEXT("player:local"),TEXT("footstep"),0);
    }
    void Apply(const J& Snapshot){
        using namespace SpellAudioData;
        if(!Index||!Effects)return;
        const FString IncomingSession=String(Snapshot,TEXT("session"));
        if(!IncomingSession.IsEmpty()&&IncomingSession!=Session){Clear();Session=IncomingSession;}
        for(auto Value:Array(Snapshot,TEXT("spell_visuals"))){
            if(Value->Type!=EJson::Object)continue;
            auto Event=Value->AsObject();const int64 Seq=int64(Number(Event,TEXT("seq")));
            if(Seq<=LastSequence){++Duplicates;continue;}LastSequence=Seq;
            const double Age=Number(Event,TEXT("age_ms"));if(Age<0||Age>1000)continue;
            ++Seen;const FString Kind=String(Event,TEXT("kind")),Caster=String(Event,TEXT("caster")),Target=String(Event,TEXT("target"));
            const int32 Effect=int32(Number(Event,TEXT("effect_id")));
            if(Kind==TEXT("cancel")){
                const int32 Previous=Casts.FindRef(Caster);DropGather(Caster);Casts.Remove(Caster);
                if(Previous>0&&String(Event,TEXT("reason"))==TEXT("interrupt"))Phase(Previous,TEXT("fizzle"),Caster);
            }else if(Kind==TEXT("cast")){
                DropGather(Caster);Casts.Add(Caster,Effect);if(Number(Event,TEXT("duration_ms"))>0)Phase(Effect,TEXT("gather"),Caster);
            }else if(Kind==TEXT("release")){
                DropGather(Caster);Casts.Remove(Caster);
                if(Flag(Event,TEXT("no_sound"))){++Quiet;continue;}
                auto Def=Definition(Effect);if(!Def){++Missing;continue;}
                const FString Burst=Caster+TEXT(":")+FString::FromInt(Effect);const double Now=FPlatformTime::Seconds();
                if(const double* At=Bursts.Find(Burst);At&&Now-*At<.25){++Duplicates;continue;}Bursts.Add(Burst,Now);
                Phase(Effect,TEXT("cast"),Caster);
                double Delay=FMath::Max(0.,Number(Def,TEXT("release_s")));
                if(Number(Def,TEXT("projectile"))>0){auto* A=Actor(Caster);auto* B=Actor(Target);if(A&&B){Phase(Effect,TEXT("travel"),Caster,Delay);Delay+=FVector::Distance(A->GetActorLocation(),B->GetActorLocation())/2125.;}}
                Phase(Effect,Flag(Event,TEXT("resisted"))?TEXT("resisted"):TEXT("hit"),Target,FMath::Max(0.,Delay-Age/1000.));
            }
        }
        if(ServerIndex)for(auto Value:Array(Snapshot,TEXT("server_sound_audio"))){
            if(Value->Type!=EJson::Object)continue;
            auto Event=Value->AsObject();const double RawSequence=Number(Event,TEXT("seq"),-1);
            if(RawSequence<=0||RawSequence!=FMath::FloorToDouble(RawSequence)||RawSequence>9007199254740991.){++ServerRejected;continue;}
            const int64 Seq=int64(RawSequence);if(Seq<=LastServerSequence){++Duplicates;continue;}LastServerSequence=Seq;
            const double Age=Number(Event,TEXT("age_ms"),-1),RawId=Number(Event,TEXT("sound_id"),-1);
            if(Age<0||Age>1000||RawId<=0||RawId>65535||RawId!=FMath::FloorToDouble(RawId)){++ServerRejected;continue;}
            bool Placed=false;if(!Event->TryGetBoolField(TEXT("placed"),Placed)){++ServerRejected;continue;}
            const auto Row=Object(Object(ServerIndex,TEXT("sounds")),*FString::FromInt(int32(RawId)));
            if(!Row){++ServerRejected;continue;}
            FVector Position=FVector::ZeroVector;
            if(Placed){
                auto Point=Array(Event,TEXT("position_m"));const double Radius=Number(Event,TEXT("radius_m"),-1);
                if(Point.Num()!=3||Radius<=0||Radius>1638.375||Point[0]->Type!=EJson::Number||Point[1]->Type!=EJson::Number||Point[2]->Type!=EJson::Number){++ServerRejected;continue;}
                Position=FVector((Point[0]->AsNumber()-1364)*100,(Point[2]->AsNumber()-1263)*100,(Point[1]->AsNumber()-130)*100);
                auto* Player=Actor(TEXT("player:local"));
                if(Position.ContainsNaN()||!Player||FVector::Distance(Position,Player->GetActorLocation())>Radius*100){++ServerRejected;continue;}
            }
            if(Pending.Num()>=256){++Culled;continue;}
            Pending.Add({Row,TEXT("server:sound"),TEXT("server_sound"),FPlatformTime::Seconds(),ServerFolder,Position,true,true,Placed});++ServerSeen;
        }
        if(CombatIndex)for(auto Value:Array(Snapshot,TEXT("combat_audio"))){
            ++CombatReceived;
            if(Value->Type!=EJson::Object)continue;
            auto Event=Value->AsObject();const int64 Seq=int64(Number(Event,TEXT("seq")));
            if(Seq<=LastCombatSequence){++Duplicates;continue;}LastCombatSequence=Seq;
            const double Age=Number(Event,TEXT("age_ms"));if(Age<0||Age>1000){++CombatStale;continue;}
            const FString Owner=String(Event,TEXT("owner")),Kind=String(Event,TEXT("sheet")),Name=String(Event,TEXT("event"));
            const auto Point=Array(Event,TEXT("position_m"));
            if(Owner.IsEmpty()||Point.Num()!=3||Point[0]->Type!=EJson::Number||Point[1]->Type!=EJson::Number||Point[2]->Type!=EJson::Number){++CombatRejected;continue;}
            // Bridge coordinates are metres in DAoC X/up/Y order.
            const FVector Position((Point[0]->AsNumber()-1364)*100,(Point[2]->AsNumber()-1263)*100,(Point[1]->AsNumber()-130)*100);
            if(Position.ContainsNaN())continue;
            const bool Creature=Kind==TEXT("creatures")&&TArray<FString>{TEXT("attack"),TEXT("pain_light"),TEXT("pain_medium"),TEXT("pain_heavy"),TEXT("die"),TEXT("evade"),TEXT("splat")}.Contains(Name);
            const bool Weapon=Kind==TEXT("weapons")&&TArray<FString>{TEXT("activate"),TEXT("deactivate"),TEXT("use"),TEXT("style_use"),TEXT("hit_light"),TEXT("hit_medium"),TEXT("style_hit"),TEXT("parried"),TEXT("blocked")}.Contains(Name);
            const bool Door=Kind==TEXT("doors")&&(Name==TEXT("open")||Name==TEXT("close"));
            if(!Creature&&!Weapon&&!Door)continue;
            const auto EventIndex=Door?DoorIndex:CombatIndex;
            auto Row=Object(Object(EventIndex,*Kind),*FString::FromInt(int32(Number(Event,TEXT("set")))));
            if(!Row){++Missing;continue;}
            FString StructureName=String(Row,*Name);
            if(StructureName.IsEmpty()&&Weapon&&(Name==TEXT("style_use")||Name==TEXT("style_hit")))StructureName=String(Row,Name==TEXT("style_use")?TEXT("use"):TEXT("hit_medium"));
            TGuardValue<J> IndexGuard(Index,EventIndex);TGuardValue<FString> FolderGuard(Folder,Door?DoorFolder:CombatFolder);
            TGuardValue<FVector> AnchorGuard(Anchor,Position);TGuardValue<bool> AnchoredGuard(Anchored,true);
            ++CombatSeen;Structure(StructureName,Owner,TEXT("combat"),0);
        }
    }
    void Tick(){
        const double Now=FPlatformTime::Seconds();
        for(int32 I=Voices.Num()-1;I>=0;--I){
            auto& V=Voices[I];if(V.Component.IsValid())V.Component->SetVolumeMultiplier(V.BaseGain*S->AudioMasterVolume*S->AudioEffectsVolume);if(V.Wave.IsValid()){const int32 Left=V.Wave->GetAvailableAudioByteCount();const int32 Used=FMath::Max(0,V.Remaining-Left);Consumed+=Used;if(V.Phase==TEXT("footstep"))FootstepConsumed+=Used;V.Remaining=Left;}
            auto* Owner=Actor(V.Owner);
            if(!V.Component.IsValid()||(!Owner&&!V.Anchored)||Now>=V.Until){StopVoice(V);Voices.RemoveAt(I);}else if(!V.Anchored)V.Component->SetWorldLocation(Owner->GetActorLocation());
        }
        for(int32 I=0;I<Pending.Num();)if(Pending[I].At<=Now){auto Job=Pending[I];Pending.RemoveAt(I);Play(Job);}else ++I;
        for(auto It=Bursts.CreateIterator();It;++It)if(Now-It.Value()>2)It.RemoveCurrent();
    }
    J Report()const{
        auto Out=MakeShared<FJsonObject>();Out->SetBoolField(TEXT("ready"),Index.IsValid()&&Effects.IsValid());
        float MaxVoice=0;for(const auto& Voice:Voices)if(Voice.Component.IsValid())MaxVoice=FMath::Max(MaxVoice,Voice.Component->VolumeMultiplier);
        Out->SetNumberField(TEXT("max_voice_volume"),MaxVoice);Out->SetNumberField(TEXT("master_volume"),S->AudioMasterVolume);Out->SetNumberField(TEXT("effects_volume"),S->AudioEffectsVolume);
        Out->SetBoolField(TEXT("combat_ready"),CombatIndex.IsValid());Out->SetNumberField(TEXT("combat_events_seen"),CombatSeen);
        Out->SetBoolField(TEXT("door_ready"),DoorIndex.IsValid());
        Out->SetBoolField(TEXT("server_sound_ready"),ServerIndex.IsValid());
        Out->SetNumberField(TEXT("server_sound_events"),ServerSeen);Out->SetNumberField(TEXT("server_sound_clips"),ServerClips);Out->SetNumberField(TEXT("server_sound_rejected"),ServerRejected);
        Out->SetBoolField(TEXT("footstep_ready"),FootstepIndex.IsValid());
        Out->SetNumberField(TEXT("footstep_clips"),FootstepClips);
        Out->SetNumberField(TEXT("footstep_pcm_consumed_bytes"),double(FootstepConsumed));
        Out->SetNumberField(TEXT("combat_events_received"),CombatReceived);Out->SetNumberField(TEXT("combat_events_stale"),CombatStale);Out->SetNumberField(TEXT("combat_events_rejected"),CombatRejected);
        Out->SetNumberField(TEXT("events_seen"),Seen);Out->SetNumberField(TEXT("played_clips"),Played);Out->SetNumberField(TEXT("active_voices"),Voices.Num());Out->SetNumberField(TEXT("pending_clips"),Pending.Num());
        int32 Gather=0;for(const auto& V:Voices)Gather+=V.Phase==TEXT("gather");for(const auto& V:Pending)Gather+=V.Phase==TEXT("gather");Out->SetNumberField(TEXT("active_gather"),Gather);
        Out->SetNumberField(TEXT("pcm_consumed_bytes"),double(Consumed));Out->SetNumberField(TEXT("cached_bytes"),double(CacheBytes));Out->SetNumberField(TEXT("culled_clips"),Culled);Out->SetNumberField(TEXT("duplicates_suppressed"),Duplicates);Out->SetNumberField(TEXT("quiet_events"),Quiet);Out->SetNumberField(TEXT("unresolved_references"),Missing);Out->SetNumberField(TEXT("invalid_resources"),Invalid);
        Out->SetStringField(TEXT("last_sound_name"),LastName);Out->SetStringField(TEXT("last_sound_file"),LastFile);return Out;
    }
};

void UDAoCBridgeSubsystem::ApplySpellAudio(const TSharedPtr<FJsonObject>& Snapshot){if(!SpellAudio)SpellAudio=MakeShared<FBridgeSpellAudio>(this);SpellAudio->Apply(Snapshot);}
void UDAoCBridgeSubsystem::TickSpellAudio(){if(SpellAudio)SpellAudio->Tick();}
void UDAoCBridgeSubsystem::ClearSpellAudio(){if(SpellAudio)SpellAudio->Clear();}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::SpellAudioReport()const{return SpellAudio?SpellAudio->Report():MakeShared<FJsonObject>();}
void UDAoCBridgeSubsystem::PlayLocalFootstep(int32 Model){if(!SpellAudio)SpellAudio=MakeShared<FBridgeSpellAudio>(this);SpellAudio->Step(Model);}
