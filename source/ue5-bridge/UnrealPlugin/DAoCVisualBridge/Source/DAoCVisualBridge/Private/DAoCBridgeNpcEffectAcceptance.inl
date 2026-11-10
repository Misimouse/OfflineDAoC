J TestNpcEffects(){
    int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    Check(Object(NpcCatalog,TEXT("models"))&&Object(NpcCatalog,TEXT("models"))->Values.Num()==45,TEXT("original monster-effect catalogue loads"));
    const auto PreviousCamera=S->Camera;auto* View=S->GetWorld()->SpawnActor<ACameraActor>();S->Camera=View;
    View->SetActorLocation(FVector(0,300,150));View->SetActorRotation(FRotator(0,-90,0));
    S->PlayerPosition=FVector::ZeroVector;S->bLocalAvailable=true;S->LastSnapshot=FPlatformTime::Seconds();S->Sequence=1;S->Quality=TEXT("balanced");
    TArray<FString> Ids;
    auto Spawn=[&](FString Id,int32 Model,FVector Position){
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),Id);Row->SetStringField(TEXT("kind"),TEXT("npc"));
        Row->SetNumberField(TEXT("model_id"),Model);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);Row->SetBoolField(TEXT("targetable"),true);
        S->EntityRows.Add(Id,Row);Ids.Add(Id);return S->CreateEntity(Id,Row,Position);
    };
    auto* Wisp=Spawn(TEXT("npc:effect-wisp"),966,FVector::ZeroVector);
    auto* Flies=Spawn(TEXT("npc:effect-flies"),2020,FVector(200,0,0));
    Check(Wisp&&Flies&&Wisp->ActorHasTag(TEXT("DAoCBridgeEffectBody"))&&Flies->ActorHasTag(TEXT("DAoCBridgeEffectBody")),TEXT("effect-only models create invisible logical bodies without placeholder meshes"));
    if(Wisp&&Flies){
        Check(!S->EntitySelectionBounds(Wisp).IsValid,TEXT("body is not clickable before a visible effect exists"));
        Tick(0);Check(NpcLive.Num()==2&&Live.IsEmpty(),TEXT("both persistent effects use their independent allowance"));
        Check(NpcMissing==0,TEXT("all original current NPC resources are present"));
        auto Find=[&](const FString& Id)->FEffect*{return NpcLive.FindByPredicate([&](const FEffect& E){return E.Owner==Id;});};
        auto* Effect=Find(TEXT("npc:effect-wisp"));Check(Effect&&Effect->Parts.Num()==2,TEXT("original Wisp retains its glow card and emitter"));
        FPart* WispParticles=Effect?Effect->Parts.FindByPredicate([](const FPart& Part){return Part.Particle;}):nullptr;
        Check(WispParticles&&WispParticles->SourceSlots==59&&WispParticles->Slots==59,TEXT("original Wisp particle amount is preserved within its quality budget"));
        double Diameter=0;if(WispParticles&&WispParticles->Mesh.IsValid())if(auto* Section=WispParticles->Mesh->GetProcMeshSection(0))for(int32 I=0;I+3<Section->ProcVertexBuffer.Num();I+=4)Diameter=FMath::Max(Diameter,double(FVector::Distance(Section->ProcVertexBuffer[I].Position,Section->ProcVertexBuffer[I+1].Position)));
        Check(FMath::IsNearlyEqual(Diameter,15.,.2),TEXT("original particle size is a radius, producing a fifteen-centimetre Wisp sprite"));
        auto* FlyEffect=Find(TEXT("npc:effect-flies"));FPart* FlyParticles=FlyEffect?FlyEffect->Parts.FindByPredicate([](const FPart& Part){return Part.Particle;}):nullptr;
        Check(FlyParticles&&FlyParticles->SourceSlots==512&&FlyParticles->Slots==64,TEXT("dense original emitter is sampled across its lifetime within the balanced budget"));
        Check(Effect&&FMath::IsNearlyEqual(Effect->Actor->GetActorLocation().Z,125.,.1),TEXT("original fifty world units float at 1.25 metres"));
        const FBox First=S->EntitySelectionBounds(Wisp);
        Check(First.IsValid&&First.Max.Z>125&&First.GetSize().GetMax()<150,TEXT("selection follows drawn Wisp without the four-metre visibility safety box"));
        Check(BridgeNpcEffectBounds(Wisp)->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("effect selection bounds cannot block movement or spells"));
        for(auto& E:NpcLive)for(auto& Part:E.Parts){
            Check(Part.Material.IsValid()&&Part.Created,TEXT("original effect texture and procedural section load"));
            Check(Part.Mesh.IsValid()&&Part.Mesh->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("NPC glow/particles never introduce world collision"));
        }
        const int32 Before=NpcCreated;NpcSyncAt=-1.;Tick(0);Check(NpcCreated==Before&&NpcLive.Num()==2,TEXT("repeated original state never duplicates persistent effects"));
        Wisp->SetActorScale3D(FVector(.5));++S->Sequence;Tick(0);Effect=Find(TEXT("npc:effect-wisp"));
        Check(Effect&&FMath::IsNearlyEqual(Effect->Scale,.5f)&&FMath::IsNearlyEqual(Effect->Actor->GetActorLocation().Z,125.,.1),TEXT("size changes effect geometry without scaling its float offset"));
        Check(S->EntitySelectionBounds(Wisp).GetSize().GetMax()<First.GetSize().GetMax()*.7,TEXT("effect hit bounds follow its visible size"));
        Wisp->SetActorLocation(FVector(6100,0,0));++S->Sequence;Tick(0);
        Check(!Find(TEXT("npc:effect-wisp"))&&!S->EntitySelectionBounds(Wisp).IsValid,TEXT("source sixty-metre limit removes visual and selectable bounds"));
        Wisp->SetActorLocation(FVector::ZeroVector);++S->Sequence;Tick(0);Check(Find(TEXT("npc:effect-wisp"))!=nullptr,TEXT("returning to original range restores exactly one effect"));
        Wisp->SetActorHiddenInGame(true);++S->Sequence;Tick(0);Check(!Find(TEXT("npc:effect-wisp"))&&!S->EntitySelectionBounds(Wisp).IsValid,TEXT("hidden owner cannot leave a visible or selectable effect behind"));
        Wisp->SetActorHiddenInGame(false);++S->Sequence;Tick(0);Check(Find(TEXT("npc:effect-wisp"))!=nullptr,TEXT("visible owner recovers one original effect"));
        S->EntityRows[TEXT("npc:effect-wisp")]->SetNumberField(TEXT("model_id"),307);++S->Sequence;Tick(0);
        Check(!Find(TEXT("npc:effect-wisp"))&&!S->EntitySelectionBounds(Wisp).IsValid,TEXT("same identity changing model releases obsolete Wisp visuals"));
        S->EntityRows[TEXT("npc:effect-wisp")]->SetNumberField(TEXT("model_id"),966);++S->Sequence;Tick(0);
        S->LastSnapshot=FPlatformTime::Seconds()-4.;Tick(0);Check(NpcLive.IsEmpty()&&!S->EntitySelectionBounds(Wisp).IsValid,TEXT("stale bridge state releases persistent effects"));
        S->LastSnapshot=FPlatformTime::Seconds();++S->Sequence;Tick(0);S->bLocalAvailable=false;Tick(0);
        Check(NpcLive.IsEmpty(),TEXT("leaving gameplay clears original NPC effects"));
        S->bLocalAvailable=true;S->Quality=TEXT("accessible");S->LastSnapshot=FPlatformTime::Seconds();
        for(int32 I=0;I<12;++I)Spawn(FString::Printf(TEXT("npc:effect-budget-%d"),I),966,FVector(300+I*10,0,0));
        ++S->Sequence;Tick(0);Check(NpcLive.Num()==8&&Live.IsEmpty(),TEXT("accessible profile bounds persistent effects independently of spell allowance"));
        const auto* Closest=Find(TEXT("npc:effect-wisp"));Check(Closest!=nullptr,TEXT("nearest effect bodies keep priority within the budget"));
        Clear();Check(NpcLive.IsEmpty()&&Live.IsEmpty(),TEXT("explicit visual/session reset leaves no persistent effect actors"));
    }
    for(const auto& Id:Ids){if(auto* Actor=Entity(Id))Actor->Destroy();S->Entities.Remove(Id);S->EntityRows.Remove(Id);S->EntityModels.Remove(Id);}
    S->Camera=PreviousCamera;View->Destroy();S->bLocalAvailable=false;
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("installed"),false);return Report;
}
