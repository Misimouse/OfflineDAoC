    FString QuestIndicatorProof;
    if (FParse::Value(FCommandLine::Get(), TEXT("DaocBridgeQuestIndicatorTest="), QuestIndicatorProof))
    {
        static int32 Phase = 0, Checks = 0;
        static double Began = 0;
        static TArray<TSharedPtr<FJsonValue>> Failures;
        auto Check = [&](bool Passed, const FString& Label)
        {
            ++Checks;
            if (!Passed)
                Failures.Add(MakeShared<FJsonValueString>(Label));
        };
        if (Phase == 0 && GetWorld() && GetWorld()->GetGameViewport() && GetWorld()->GetFirstPlayerController())
        {
            auto* PC = GetWorld()->GetFirstPlayerController();
            const FVector View(-200, -650, 480);
            auto* TestCamera = GetWorld()->SpawnActor<ACameraActor>(View, (-View).Rotation());
            PC->SetViewTarget(TestCamera);
            bLocalAvailable = true;
            PlayerPosition = FVector(-900, -900, 0);
            auto CreateTestNpc = [&](const FString& Id, int32 Indicator, const FVector& Position)
            {
                auto* Npc = GetWorld()->SpawnActor<AActor>();
                auto* Root = NewObject<USceneComponent>(Npc);
                Npc->SetRootComponent(Root);
                Root->RegisterComponent();
                Npc->SetActorLocation(Position);
                Entities.Add(Id, Npc);
                auto Row = MakeShared<FJsonObject>();
                Row->SetStringField(TEXT("kind"), TEXT("npc"));
                Row->SetNumberField(TEXT("health"), 1);
                Row->SetNumberField(TEXT("quest_indicator"), Indicator);
                Row->SetArrayField(TEXT("position_m"), {MakeShared<FJsonValueNumber>(1364 + Position.X/100),
                    MakeShared<FJsonValueNumber>(130), MakeShared<FJsonValueNumber>(1263 + Position.Y/100)});
                EntityRows.Add(Id, Row);
                UpdateNpcQuestIndicator(Id, *Npc, *Row);
                return Npc;
            };
            auto* Yellow = CreateTestNpc(TEXT("npc:1"), 1, FVector(-195, 0, 0));
            auto* Green = CreateTestNpc(TEXT("npc:2"), 2, FVector(0, 0, 0));
            CreateTestNpc(TEXT("npc:3"), 16, FVector(195, 0, 0));
            Check(NpcQuestRings.Num() == 3, TEXT("Three original quest categories create three rings"));
            auto* Ring = NpcQuestRings.FindRef(TEXT("npc:1")).Get();
            Check(Ring && Ring->GetCollisionEnabled() == ECollisionEnabled::NoCollision &&
                Ring->GetNumSections() == 1 && Ring->GetProcMeshSection(0)->ProcIndexBuffer.Num() == 216,
                TEXT("Three drawn arcs do not add collision"));
            if (Ring)
            {
                Yellow->SetActorLocation(FVector(-260, -35, 10));
                Yellow->SetActorScale3D(FVector(1.5));
                UpdateNpcQuestIndicator(TEXT("npc:1"), *Yellow, *EntityRows.FindRef(TEXT("npc:1")));
                Check(Ring->GetComponentLocation().Equals(Yellow->GetActorLocation()+FVector(0,0,6), .1) &&
                    Ring->GetComponentScale().Equals(FVector(1), .01), TEXT("Ring follows the NPC without stretching with the model"));
            }
            auto GreenRow = EntityRows.FindRef(TEXT("npc:2"));
            GreenRow->SetNumberField(TEXT("quest_indicator"), 7);
            UpdateNpcQuestIndicator(TEXT("npc:2"), *Green, *GreenRow);
            Check(!NpcQuestRings.Contains(TEXT("npc:2")), TEXT("Unrecognized indicator cannot create a ring"));
            GreenRow->SetNumberField(TEXT("quest_indicator"), 2);
            GreenRow->SetNumberField(TEXT("health"), 0);
            UpdateNpcQuestIndicator(TEXT("npc:2"), *Green, *GreenRow);
            Check(!NpcQuestRings.Contains(TEXT("npc:2")), TEXT("Dead NPC cannot retain a ring"));
            GreenRow->SetNumberField(TEXT("health"), 1);
            UpdateNpcQuestIndicator(TEXT("npc:2"), *Green, *GreenRow);
            Check(NpcQuestRings.FindRef(TEXT("npc:2")).IsValid(), TEXT("Server turn-in recreates the ring"));
            Began = FPlatformTime::Seconds();
            Phase = 1;
        }
        if (Phase == 1 && FPlatformTime::Seconds()-Began > .7)
        {
            FScreenshotRequest::RequestScreenshot(QuestIndicatorProof+TEXT("-rings.png"), true, false);
            Began = FPlatformTime::Seconds();
            Phase = 2;
        }
        if (Phase == 2 && FPlatformTime::Seconds()-Began > .7)
        {
            for (int32 Index = 1; Index <= 3; ++Index)
            {
                const FString Id = FString::Printf(TEXT("npc:%d"), Index);
                const double Offset = (Index - 2) * 180.0;
                Entities.FindRef(Id)->SetActorLocation(FVector(Offset*100, -Offset*60, 0));
                EntityRows.FindRef(Id)->SetArrayField(TEXT("position_m"), {MakeShared<FJsonValueNumber>(1364 + Offset),
                    MakeShared<FJsonValueNumber>(130), MakeShared<FJsonValueNumber>(1263 - Offset*.6)});
            }
            LoadZoneMaps();
            ZoneMapZone = 207;
            ZoneMapArea = -1;
            ZoneMapRegion = -1;
            bZoneMapOpen = true;
            ZoneMapPosition = FVector2D(20, 20);
            RefreshZoneMap();
            Check(ZoneMapOverlay.IsValid(), TEXT("Original zone map opens with quest marks"));
            Began = FPlatformTime::Seconds();
            Phase = 3;
        }
        if (Phase == 3 && FPlatformTime::Seconds()-Began > .7)
        {
            FScreenshotRequest::RequestScreenshot(QuestIndicatorProof+TEXT("-map.png"), true, false);
            Began = FPlatformTime::Seconds();
            Phase = 4;
        }
        if (Phase == 4 && FPlatformTime::Seconds()-Began > .7)
        {
            ClearEntities();
            Check(NpcQuestRings.IsEmpty(), TEXT("Session reset removes all quest rings"));
            auto Report = MakeShared<FJsonObject>();
            Report->SetBoolField(TEXT("passed"), Failures.IsEmpty());
            Report->SetNumberField(TEXT("checks"), Checks);
            Report->SetArrayField(TEXT("failures"), Failures);
            FString Text;
            FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Text));
            FFileHelper::SaveStringToFile(Text, *(QuestIndicatorProof+TEXT(".json")));
            Phase = 5;
            UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
        }
        return;
    }
