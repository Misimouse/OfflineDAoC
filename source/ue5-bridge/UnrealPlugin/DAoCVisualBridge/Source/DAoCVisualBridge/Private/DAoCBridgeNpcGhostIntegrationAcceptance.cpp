#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeGhostMaterials.h"
#include "Animation/SkeletalMeshActor.h"
#include "Components/SkeletalMeshComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Kismet/KismetSystemLibrary.h"

bool UDAoCBridgeSubsystem::TickNpcGhostIntegrationAcceptance(){
    FString Output;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostIntegrationTest="),Output))return false;
    static bool Done=false;if(Done)return true;Done=true;int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    auto Copy=[](const TSharedPtr<FJsonObject>& Row){auto Value=MakeShared<FJsonObject>();Value->Values=Row->Values;return Value;};
    FString Input,Text;FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcGhostSnapshot="),Input);TSharedPtr<FJsonObject> Snapshot;
    const bool Read=FFileHelper::LoadFileToString(Text,*Input)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Snapshot)&&Snapshot.IsValid();Check(Read,TEXT("original server NPC snapshot loads"));
    const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;Check(Read&&Snapshot->TryGetArrayField(TEXT("entities"),Rows),TEXT("recorded entity rows available"));
    TMap<FString,TSharedPtr<FJsonObject>> Originals;TMap<FString,UMaterialInterface*> OriginalMaterials;FString Spirit,Corporeal,Figure;
    if(Rows)for(auto Value:*Rows){
        if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();FString Name,Id;Row->TryGetStringField(TEXT("name"),Name);Row->TryGetStringField(TEXT("id"),Id);
        if(Name!=TEXT("Codex QA Spirit")&&Name!=TEXT("Codex QA Corporeal")&&Name!=TEXT("Codex QA Figure"))continue;
        auto* Actor=Cast<ASkeletalMeshActor>(CreateEntity(Id,Row,FVector::ZeroVector));Check(Actor!=nullptr,TEXT("actual native entity path loads ")+Name);if(!Actor)continue;
        Originals.Add(Id,Row);EntityRows.Add(Id,Row);OriginalMaterials.Add(Id,Actor->GetSkeletalMeshComponent()->GetMaterial(0));
        if(Name==TEXT("Codex QA Spirit"))Spirit=Id;else if(Name==TEXT("Codex QA Corporeal"))Corporeal=Id;else Figure=Id;
    }
    Check(Originals.Num()==3&&!Spirit.IsEmpty()&&!Corporeal.IsEmpty()&&!Figure.IsEmpty(),TEXT("all three disposable server-created NPCs replayed"));
    if(Originals.Num()==3&&!Spirit.IsEmpty()&&!Corporeal.IsEmpty()&&!Figure.IsEmpty()){
        bLocalAvailable=true;LastSnapshot=FPlatformTime::Seconds();Session=TEXT("PrivateGhostIntegration");TickNpcGhostMaterials();
        auto Material=[&](const FString& Id)->UMaterialInterface*{auto* Actor=Cast<ASkeletalMeshActor>(Entities.FindRef(Id).Get());return Actor?Actor->GetSkeletalMeshComponent()->GetMaterial(0):nullptr;};
        auto Active=[&](const FString& Id){auto P=NpcGhostPresentations.FindRef(Id);return P&&P->ChangedSlots()>0&&P->MissingSlots()==0&&P->DepthProxies()>0;};
        Check(NpcGhostPresentations.Num()==2&&Active(Spirit)&&Active(Figure),TEXT("only the two server-confirmed ghosts receive native presentation"));
        Check(Material(Corporeal)==OriginalMaterials[Corporeal]&&!NpcGhostPresentations.Contains(Corporeal),TEXT("ordinary NPC sharing the zombie asset remains unchanged"));
        float Opacity=0;Check(Material(Spirit)&&Material(Spirit)->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeGhostOpacity")),Opacity)&&FMath::IsNearlyEqual(Opacity,.5f),TEXT("original monster classification selects half opacity"));
        Check(Material(Figure)&&Material(Figure)->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeGhostOpacity")),Opacity)&&FMath::IsNearlyEqual(Opacity,.9f),TEXT("original race classification selects figure opacity"));
        auto RestoreRow=[&](){EntityRows.Add(Spirit,Originals[Spirit]);LastSnapshot=FPlatformTime::Seconds();bLocalAvailable=true;TickNpcGhostMaterials();};
        auto Invalid=Copy(Originals[Spirit]);Invalid->SetStringField(TEXT("kind"),TEXT("player"));EntityRows[Spirit]=Invalid;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Material(Spirit)==OriginalMaterials[Spirit]&&Active(Figure),TEXT("player identity cannot reuse NPC ghost flags"));RestoreRow();
        Invalid=Copy(Originals[Spirit]);Invalid->RemoveField(TEXT("npc_visual"));EntityRows[Spirit]=Invalid;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Material(Spirit)==OriginalMaterials[Spirit],TEXT("missing metadata removes stale ghost presentation"));RestoreRow();
        Invalid=Copy(Originals[Spirit]);auto Flags=Copy(Originals[Spirit]->GetObjectField(TEXT("npc_visual")));Flags->SetBoolField(TEXT("ghost"),false);Invalid->SetObjectField(TEXT("npc_visual"),Flags);EntityRows[Spirit]=Invalid;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Material(Spirit)==OriginalMaterials[Spirit],TEXT("ordinary replacement on the same OID restores original appearance"));RestoreRow();
        Invalid=Copy(Originals[Spirit]);Flags=Copy(Originals[Spirit]->GetObjectField(TEXT("npc_visual")));Flags->SetStringField(TEXT("source_packet"),TEXT("move"));Invalid->SetObjectField(TEXT("npc_visual"),Flags);EntityRows[Spirit]=Invalid;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Active(Figure),TEXT("movement packet flags cannot manufacture ghost state"));RestoreRow();
        Invalid=Copy(Originals[Spirit]);Flags=Copy(Originals[Spirit]->GetObjectField(TEXT("npc_visual")));Flags->SetStringField(TEXT("ghost"),TEXT("true"));Invalid->SetObjectField(TEXT("npc_visual"),Flags);EntityRows[Spirit]=Invalid;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit),TEXT("non-boolean ghost metadata is rejected"));RestoreRow();
        const FString Model=FString::FromInt(EntityModels.FindRef(Spirit));auto Definition=ModelCatalog.FindRef(Model);
        auto Bad=Copy(Definition);Bad->RemoveField(TEXT("ghost_render"));ModelCatalog[Model]=Bad;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Material(Spirit)==OriginalMaterials[Spirit],TEXT("unknown model classification preserves ordinary visible appearance"));ModelCatalog[Model]=Definition;RestoreRow();
        Bad=Copy(Definition);auto Type=Copy(Definition->GetObjectField(TEXT("ghost_render")));Type->SetBoolField(TEXT("effect_only"),true);Bad->SetObjectField(TEXT("ghost_render"),Type);ModelCatalog[Model]=Bad;TickNpcGhostMaterials();
        Check(!NpcGhostPresentations.Contains(Spirit)&&Active(Figure),TEXT("effect-only creature is not treated as an ordinary ghost mesh"));ModelCatalog[Model]=Definition;RestoreRow();
        EntityRows.Remove(Spirit);TickNpcGhostMaterials();Check(!NpcGhostPresentations.Contains(Spirit)&&Material(Spirit)==OriginalMaterials[Spirit],TEXT("removed snapshot identity clears its overrides"));RestoreRow();
        bLocalAvailable=false;TickNpcGhostMaterials();Check(NpcGhostPresentations.IsEmpty()&&Material(Spirit)==OriginalMaterials[Spirit]&&Material(Figure)==OriginalMaterials[Figure],TEXT("menu/missing local player clears every NPC ghost"));RestoreRow();
        LastSnapshot=FPlatformTime::Seconds()-4.;TickNpcGhostMaterials();Check(NpcGhostPresentations.IsEmpty()&&Material(Figure)==OriginalMaterials[Figure],TEXT("stale bridge snapshot cannot retain ghost overrides"));RestoreRow();
        ClearNpcGhostMaterials();Check(NpcGhostPresentations.IsEmpty()&&Material(Spirit)==OriginalMaterials[Spirit]&&Material(Figure)==OriginalMaterials[Figure],TEXT("world cleanup restores original NPC materials"));
    }
    ClearNpcGhostMaterials();for(auto& Pair:Entities)if(IsValid(Pair.Value))Pair.Value->Destroy();Entities.Empty();EntityRows.Empty();EntityModels.Empty();bLocalAvailable=false;Session.Empty();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("installed"),false);Report->SetBoolField(TEXT("recorded_real_server_rows"),true);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Output);UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);return true;
}
