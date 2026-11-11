    FString QuestMapProof;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeQuestMapTest="),QuestMapProof))
    {
        static int32 Phase=0,Checks=0;
        static double Began=0;
        static TArray<TSharedPtr<FJsonValue>> Failures;
        auto Check=[&](bool Passed,const FString& Label)
        {
            ++Checks;
            if(!Passed)Failures.Add(MakeShared<FJsonValueString>(Label));
        };
        if(Phase==0&&GetWorld()&&GetWorld()->GetGameViewport()&&GetWorld()->GetFirstPlayerController())
        {
            bLocalAvailable=true;
            PlayerPosition=FVector(-90000,-90000,0);
            LoadZoneMaps();
            ZoneMapZone=207;ZoneMapArea=-1;ZoneMapRegion=-1;
            ClassicState=MakeShared<FJsonObject>();
            Check(BridgeQuestMap::StepUnits(ClassicState).IsEmpty(),TEXT("No objective invented from an empty state"));
            auto Mark=MakeShared<FJsonObject>();
            Mark->SetArrayField(TEXT("position_m"),{MakeShared<FJsonValueNumber>(1381.375),MakeShared<FJsonValueNumber>(1287.85)});
            ClassicState->SetArrayField(TEXT("quest_map_marks"),{MakeShared<FJsonValueObject>(Mark)});
            const auto Points=BridgeQuestMap::StepUnits(ClassicState);
            Check(Points.Num()==1&&Points[0].Equals(FVector2D(55255,51514),.001),
                TEXT("Original Evan objective uses canonical zone coordinates"));
            const auto Fraction=Points.Num()?ZoneMapFraction(Points[0]):FVector2D(-1,-1);
            Check(Fraction.X>=0&&Fraction.X<=1&&Fraction.Y>=0&&Fraction.Y<=1,
                TEXT("Return to Ardee projects inside Connacht map"));
            auto Invalid=MakeShared<FJsonObject>();
            Invalid->SetArrayField(TEXT("quest_map_marks"),{MakeShared<FJsonValueString>(TEXT("bad")),MakeShared<FJsonValueObject>(MakeShared<FJsonObject>())});
            Check(BridgeQuestMap::StepUnits(Invalid).IsEmpty(),TEXT("Malformed objective data is ignored"));
            bZoneMapOpen=true;ZoneMapPosition=FVector2D(400,150);RefreshZoneMap();
            Check(ZoneMapOverlay.IsValid(),TEXT("Original map displays objective metadata"));
            Began=FPlatformTime::Seconds();Phase=1;
        }
        if(Phase==1&&FPlatformTime::Seconds()-Began>.8)
        {
            FScreenshotRequest::RequestScreenshot(QuestMapProof+TEXT("-map.png"),true,false);
            Began=FPlatformTime::Seconds();Phase=2;
        }
        if(Phase==2&&FPlatformTime::Seconds()-Began>.8)
        {
            ClassicState->SetArrayField(TEXT("quest_map_marks"),{});
            Check(BridgeQuestMap::StepUnits(ClassicState).IsEmpty(),TEXT("Updated state removes finished objectives"));
            Began=FPlatformTime::Seconds();Phase=3;
        }
        if(Phase==3&&FPlatformTime::Seconds()-Began>.8)
        {
            FScreenshotRequest::RequestScreenshot(QuestMapProof+TEXT("-cleared.png"),true,false);
            Began=FPlatformTime::Seconds();Phase=4;
        }
        if(Phase==4&&FPlatformTime::Seconds()-Began>.8)
        {
            auto Report=MakeShared<FJsonObject>();
            Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());
            Report->SetNumberField(TEXT("checks"),Checks);
            Report->SetArrayField(TEXT("failures"),Failures);
            FString Text;
            FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
            FFileHelper::SaveStringToFile(Text,*(QuestMapProof+TEXT(".json")));
            Phase=5;
            UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);
        }
        return;
    }
