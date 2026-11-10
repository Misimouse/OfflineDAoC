// Members of the original procedural effect renderer. Persistent NPC effects have
// their own budget; they never occupy a transient spell or weapon-effect slot.
FString NpcFolder;J NpcCatalog;TArray<FEffect> NpcLive;TMap<FString,J> NpcData;
int64 NpcSequence=MIN_int64;double NpcSyncAt=-1.;int32 NpcCreated=0,NpcMissing=0;

void LoadNpcEffects(){
    if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeNpcEffectsFolder="),NpcFolder))
        NpcFolder=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/NpcEffects_v01");
    NpcCatalog=Read(NpcFolder/TEXT("catalog.json"));
    auto OriginalTextures=Object(Catalog,TEXT("textures")),Extra=Object(NpcCatalog,TEXT("textures"));
    if(OriginalTextures&&Extra)for(const auto& Pair:Extra->Values){FString Path;
        if(Pair.Value->TryGetString(Path)&&Path.StartsWith(TEXT("/DAoCVisualBridge/")))OriginalTextures->Values.Add(Pair.Key,Pair.Value);
    }
}

void ClearNpcEffects(){
    for(auto& E:NpcLive){if(auto* Owner=Entity(E.Owner))if(auto* Bounds=BridgeNpcEffectBounds(Owner))Bounds->SetVisibility(false);if(E.Actor.IsValid())E.Actor->Destroy();}
    NpcLive.Empty();NpcSequence=MIN_int64;NpcSyncAt=-1.;
}

void SyncNpcEffects(){
    const double Now=FPlatformTime::Seconds();
    if(!S->bLocalAvailable||S->CharacterLobbyOverlay.IsValid()||Now-S->LastSnapshot>3.){ClearNpcEffects();return;}
    if(NpcSequence==S->Sequence&&Now-NpcSyncAt<.2)return;
    NpcSequence=S->Sequence;NpcSyncAt=Now;
    auto Models=Object(NpcCatalog,TEXT("models"));if(!Models){ClearNpcEffects();return;}
    struct FCandidate{FString Key,Owner,Model;J Definition;double Distance;bool Body;};
    TArray<FCandidate> Candidates;
    for(const auto& Pair:S->EntityRows){
        auto Row=Pair.Value;auto* Actor=Entity(Pair.Key);if(!Actor||String(Row,TEXT("kind"))!=TEXT("npc"))continue;
        if(auto* Bounds=BridgeNpcEffectBounds(Actor))Bounds->SetVisibility(false);
        if(Actor->IsHidden())continue;
        const FString Model=FString::FromInt(int32(Number(Row,TEXT("model_id"))));auto Info=Object(Models,*Model);if(!Info)continue;
        const auto Effects=Array(Info,TEXT("effects"));if(Effects.Num()>8)continue;
        const double Distance=FVector::DistSquared(Actor->GetActorLocation(),S->PlayerPosition);
        const double QualityRange=S->Quality==TEXT("accessible")?4000.:S->Quality==TEXT("balanced")?6000.:8000.;
        for(int32 Index=0;Index<Effects.Num();++Index){if(Effects[Index]->Type!=EJson::Object)continue;auto Def=Effects[Index]->AsObject();
            const double Range=Number(Def,TEXT("range_m"));const FString Resource=String(Def,TEXT("data"));
            bool ValidKey=Resource.Len()==16;for(TCHAR Letter:Resource)ValidKey&=FChar::IsHexDigit(Letter);
            if(!FMath::IsFinite(Range)||Range<=0||Range>1000||!ValidKey)continue;
            if(Distance>FMath::Square(FMath::Min(Range*100.,QualityRange)))continue;
            Candidates.Add({Pair.Key+TEXT(":")+Model+TEXT(":")+FString::FromInt(Index),Pair.Key,Model,Def,Distance,Flag(Info,TEXT("effect_only"))});
        }
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Body!=B.Body?A.Body:A.Distance!=B.Distance?A.Distance<B.Distance:A.Key<B.Key;});
    const int32 Limit=S->Quality==TEXT("accessible")?8:S->Quality==TEXT("balanced")?16:32;
    TSet<FString> Keep;int32 Count=0;
    for(auto& Candidate:Candidates){if(Count>=Limit)break;
        if(NpcLive.ContainsByPredicate([&](const FEffect& E){return E.Target==Candidate.Key;})){Keep.Add(Candidate.Key);++Count;continue;}
        const FString Key=String(Candidate.Definition,TEXT("data"));J Resource=NpcData.FindRef(Key);
        if(!Resource){Resource=Read(NpcFolder/TEXT("Data")/(Key+TEXT(".json")));if(!Resource){++NpcMissing;continue;}NpcData.Add(Key,Resource);}
        FEffect E;E.Owner=Candidate.Owner;E.Target=Candidate.Key;E.Def=Candidate.Definition;E.Began=Now;
        // Original particles are already burning on entering view.
        double Warmup=0;for(auto V:Array(Resource,TEXT("particles")))if(V->Type==EJson::Object)Warmup=FMath::Max(Warmup,Number(V->AsObject(),TEXT("lifetime"))+Number(V->AsObject(),TEXT("lifetime_random")));
        E.Began-=FMath::Clamp(Warmup,0.,30.);
        FActorSpawnParameters P;P.ObjectFlags|=RF_Transient;P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        E.Actor=S->GetWorld()->SpawnActor<AActor>(P);if(!E.Actor.IsValid())continue;
        BuildParts(E,Resource,true);NpcLive.Add(MoveTemp(E));Keep.Add(Candidate.Key);++Count;++NpcCreated;
    }
    for(int32 I=NpcLive.Num()-1;I>=0;--I)if(!Keep.Contains(NpcLive[I].Target)||!Entity(NpcLive[I].Owner)){
        if(NpcLive[I].Actor.IsValid())NpcLive[I].Actor->Destroy();NpcLive.RemoveAt(I);
    }
}

void TickNpcEffects(){
    TMap<FString,FBox> Bodies;
    for(auto& E:NpcLive){auto* Owner=Entity(E.Owner);if(!Owner||!E.Actor.IsValid())continue;
        auto* Row=S->EntityRows.Find(E.Owner);if(!Row)continue;auto Info=Object(Object(NpcCatalog,TEXT("models")),*FString::FromInt(int32(Number(*Row,TEXT("model_id")))));if(!Info)continue;
        FQuat Rotation;FVector Position=Anchor(Owner,E.Def,Rotation);
        if(Flag(Info,TEXT("effect_only"))){
            // Hover is an offset in the NPC view, not part of the effect's size.
            const auto Float=Array(Info,TEXT("float_units"));double Hover=0;
            if(Float.Num()==2){const double Low=At(Float,0),High=At(Float,1);if(FMath::IsFinite(Low)&&FMath::IsFinite(High)&&Low>=0&&High>=Low&&High<=10000)Hover=FMath::Lerp(Low,High,double(Random(GetTypeHash(E.Owner),0)))*2.5;}
            Position=Owner->GetActorLocation()+FVector(0,0,Hover);
        }
        E.Scale=Flag(E.Def,TEXT("autoscale"))?Owner->GetActorScale3D().GetAbsMax():1.f;
        // An actual bone attachment inherits the model/bone scale even when the
        // origin-only AutoScale flag is off, as in the original NPC scene.
        if(auto* Figure=Cast<ASkeletalMeshActor>(Owner)){
            auto* Body=Figure->GetSkeletalMeshComponent();const FString Node=String(E.Def,TEXT("node"));
            TArray<FName> Bones;Body->GetBoneNames(Bones);
            for(auto Bone:Bones)if(!Node.IsEmpty()&&BoneKey(Bone.ToString())==BoneKey(Node)){E.Scale=Body->GetSocketTransform(Bone,RTS_World).GetScale3D().GetAbsMax();break;}
        }
        const FTransform World(Rotation,Position,FVector(E.Scale));E.Actor->SetActorTransform(World);
        const double Age=FPlatformTime::Seconds()-E.Began;
        for(auto& Part:E.Parts)if(Part.Particle)Sprites(Part,Age,World);else Mesh(Part,Age,&World);
        if(Owner->ActorHasTag(TEXT("DAoCBridgeEffectBody"))){
            FBox Box(ForceInit);for(auto& Part:E.Parts)if(Part.Mesh.IsValid()&&Part.Mesh->IsVisible())Box+=Part.Mesh->CalcBounds(Part.Mesh->GetComponentTransform()).GetBox();
            if(Box.IsValid&&Box.GetSize().GetMax()<3000){auto* Previous=Bodies.Find(E.Owner);if(Previous)*Previous+=Box;else Bodies.Add(E.Owner,Box);}
        }
    }
    for(auto& Pair:Bodies)if(auto* Box=BridgeNpcEffectBounds(Entity(Pair.Key))){
        Box->SetWorldScale3D(FVector::OneVector);Box->SetWorldRotation(FRotator::ZeroRotator);
        Box->SetWorldLocation(Pair.Value.GetCenter());Box->SetBoxExtent(Pair.Value.GetExtent().ComponentMax(FVector(8)),false);Box->SetVisibility(true);
    }
}
