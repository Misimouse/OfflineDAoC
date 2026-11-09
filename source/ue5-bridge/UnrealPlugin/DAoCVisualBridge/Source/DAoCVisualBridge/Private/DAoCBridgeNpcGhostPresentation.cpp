#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeGhostMaterials.h"
#include "GameFramework/Actor.h"
#include "Dom/JsonObject.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace {
bool NpcGhostBoolean(const TSharedPtr<FJsonObject>& Row,const TCHAR* Field,bool& Value){
    const auto* Item=Row->Values.Find(Field);
    return Item&&Item->IsValid()&&(*Item)->Type==EJson::Boolean&&(*Item)->TryGetBool(Value);
}
}

void UDAoCBridgeSubsystem::ClearNpcGhostMaterials(){
    for(auto& Pair:NpcGhostPresentations)if(Pair.Value)Pair.Value->Restore();
    NpcGhostPresentations.Empty();
}

void UDAoCBridgeSubsystem::TickNpcGhostMaterials(){
    if(!bLocalAvailable||CharacterLobbyOverlay.IsValid()||FPlatformTime::Seconds()-LastSnapshot>3.){ClearNpcGhostMaterials();return;}
    TSet<FString> Keep;
    for(const auto& Pair:EntityRows){
        const auto Row=Pair.Value;if(!Row.IsValid())continue;
        FString Kind,Packet;const TSharedPtr<FJsonObject>* Visual=nullptr;bool Known=false,Ghost=false;
        if(!Row->TryGetStringField(TEXT("kind"),Kind)||Kind!=TEXT("npc")||
            !Row->TryGetObjectField(TEXT("npc_visual"),Visual)||
            !NpcGhostBoolean(*Visual,TEXT("known"),Known)||!Known||
            !NpcGhostBoolean(*Visual,TEXT("ghost"),Ghost)||!Ghost||
            !(*Visual)->TryGetStringField(TEXT("source_packet"),Packet)||Packet!=TEXT("npc_create"))continue;
        auto* Actor=Entities.FindRef(Pair.Key).Get();if(!IsValid(Actor))continue;
        const auto* Entry=ModelCatalog.Find(FString::FromInt(EntityModels.FindRef(Pair.Key)));
        const TSharedPtr<FJsonObject>* Definition=nullptr;bool Classified=false,RaceFigure=false,EffectOnly=false;
        if(!Entry||!(*Entry)->TryGetObjectField(TEXT("ghost_render"),Definition)||
            !NpcGhostBoolean(*Definition,TEXT("known"),Classified)||!Classified||
            !NpcGhostBoolean(*Definition,TEXT("race_figure"),RaceFigure)||
            !NpcGhostBoolean(*Definition,TEXT("effect_only"),EffectOnly)||EffectOnly)continue;
        if(!bNpcGhostLibraryTried){
            bNpcGhostLibraryTried=true;
            if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostMaterials="),NpcGhostManifest))NpcGhostManifest=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/npc_ghost_materials.json");
            NpcGhostLibraryProbe=MakeShared<FBridgeGhostMaterials>();bNpcGhostLibraryReady=NpcGhostLibraryProbe->Load(NpcGhostManifest);
            if(!bNpcGhostLibraryReady)UE_LOG(LogTemp,Warning,TEXT("NPC ghost material catalogue unavailable; preserving original appearance."));
        }
        if(!bNpcGhostLibraryReady)continue;
        auto& Presentation=NpcGhostPresentations.FindOrAdd(Pair.Key);
        if(!Presentation){Presentation=MakeShared<FBridgeGhostMaterials>();if(!Presentation->Load(NpcGhostManifest)){Presentation.Reset();continue;}}
        Presentation->Apply(Actor,true,true,RaceFigure,Sequence);Keep.Add(Pair.Key);
    }
    for(auto It=NpcGhostPresentations.CreateIterator();It;++It)if(!Keep.Contains(It.Key())){
        if(It.Value())It.Value()->Restore();It.RemoveCurrent();
    }
}
