// Offscreen original-effect witness. Never active in ordinary gameplay.
void CaptureNpcEffects(const FString& Output){
    static int32 Model=0,View=0,Frame=0,Captures=0;static double Ready=0;
    static AActor* Owner=nullptr;static AStaticMeshActor* Backdrop=nullptr;
    static AActor* Lamp=nullptr;static AActor* CaptureOwner=nullptr;static ACameraActor* Camera=nullptr;
    static USceneCaptureComponent2D* Capture=nullptr;static UTextureRenderTarget2D* Target=nullptr;
    static FVector Center;static double Distance=200;static bool Setup=false,Warmed=false,Finished=false;
    if(Finished)return;
    auto Finish=[&](const FString& Error){
        ClearNpcEffects();if(IsValid(Owner))Owner->Destroy();S->Entities.Remove(TEXT("npc:visual-effect"));S->EntityRows.Remove(TEXT("npc:visual-effect"));S->EntityModels.Remove(TEXT("npc:visual-effect"));
        for(auto* Actor:{static_cast<AActor*>(Backdrop),Lamp,CaptureOwner,static_cast<AActor*>(Camera)})if(IsValid(Actor))Actor->Destroy();
        S->Camera=nullptr;S->bLocalAvailable=false;auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Error.IsEmpty());Report->SetStringField(TEXT("error"),Error);Report->SetNumberField(TEXT("captures"),Captures);Report->SetBoolField(TEXT("installed"),false);
        FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*FPaths::Combine(Output,TEXT("native.json")));Finished=true;UKismetSystemLibrary::QuitGame(S->GetWorld(),nullptr,EQuitPreference::Quit,false);
    };
    const int32 Id=Model==0?966:2020;S->LastSnapshot=FPlatformTime::Seconds();S->bLocalAvailable=true;S->Quality=TEXT("balanced");S->PlayerPosition=FVector::ZeroVector;
    if(!Camera){
        Camera=S->GetWorld()->SpawnActor<ACameraActor>();S->Camera=Camera;Camera->SetActorLocation(FVector(0,250,125));Camera->SetActorRotation(FRotator(0,-90,0));
        CaptureOwner=S->GetWorld()->SpawnActor<AActor>();Capture=NewObject<USceneCaptureComponent2D>(CaptureOwner);CaptureOwner->SetRootComponent(Capture);Capture->RegisterComponent();
        Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->FOVAngle=40;
        Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Capture->ShowFlags.SetTemporalAA(false);Capture->ShowFlags.SetEyeAdaptation(false);
        Capture->PostProcessSettings.bOverride_AutoExposureMethod=true;Capture->PostProcessSettings.AutoExposureMethod=EAutoExposureMethod::AEM_Manual;
        Capture->PostProcessSettings.bOverride_AutoExposureBias=true;Capture->PostProcessSettings.AutoExposureBias=0;
        Capture->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Capture->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
        Capture->PostProcessSettings.bOverride_BloomIntensity=true;Capture->PostProcessSettings.BloomIntensity=0;
        Target=NewObject<UTextureRenderTarget2D>(CaptureOwner);Target->ClearColor=FLinearColor::Black;Target->InitAutoFormat(512,512);Capture->TextureTarget=Target;
    }
    auto Freeze=[&](double Age){for(auto& E:NpcLive)E.Began=FPlatformTime::Seconds()-Age;Tick(0);};
    if(!Owner){
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("kind"),TEXT("npc"));Row->SetNumberField(TEXT("model_id"),Id);Row->SetNumberField(TEXT("size"),50);Row->SetNumberField(TEXT("health"),1);Row->SetBoolField(TEXT("targetable"),true);
        S->EntityRows.Add(TEXT("npc:visual-effect"),Row);Owner=S->CreateEntity(TEXT("npc:visual-effect"),Row,FVector::ZeroVector);++S->Sequence;Tick(0);
        if(!Owner||NpcLive.Num()!=1){Finish(TEXT("original effect body unavailable"));return;}
        Freeze(.4);FBox Bounds=S->EntitySelectionBounds(Owner);Freeze(.8);Bounds+=S->EntitySelectionBounds(Owner);
        if(!Bounds.IsValid){Finish(TEXT("effect draw bounds unavailable"));return;}
        Center=Bounds.GetCenter();Distance=FMath::Max(150.,Bounds.GetExtent().GetMax()/.364*1.8);
        if(GShaderCompilingManager)GShaderCompilingManager->FinishAllCompilation();
    }
    if(!Setup){
        if(IsValid(Backdrop))Backdrop->Destroy();if(IsValid(Lamp))Lamp->Destroy();
        const FVector Direction=View==0?FVector(1,0,0):View==1?FVector(0,1,0):View==2?FVector(-1,0,0):FVector(0,1,1).GetSafeNormal();
        const FVector Eye=Center+Direction*Distance;const FRotator Rotation=(Center-Eye).Rotation();Camera->SetActorLocationAndRotation(Eye,Rotation);Capture->SetWorldLocationAndRotation(Eye,Rotation);
        Backdrop=S->GetWorld()->SpawnActor<AStaticMeshActor>();auto* Panel=Backdrop->GetStaticMeshComponent();Panel->SetMobility(EComponentMobility::Movable);Panel->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Panel->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial")));Panel->SetCastShadow(false);
        Backdrop->SetActorLocation(Center-Direction*100);Backdrop->SetActorRotation(FRotationMatrix::MakeFromY(Direction).Rotator());Backdrop->SetActorScale3D(FVector(6,.05,6));
        Lamp=S->GetWorld()->SpawnActor<AActor>();auto* Light=NewObject<UPointLightComponent>(Lamp);Lamp->SetRootComponent(Light);Lamp->AddInstanceComponent(Light);Light->SetMobility(EComponentMobility::Movable);Light->SetIntensityUnits(ELightUnits::Lumens);Light->SetIntensity(800);Light->SetAttenuationRadius(3000);Light->SetCastShadows(false);Light->SetIndirectLightingIntensity(0);Light->RegisterComponent();Lamp->SetActorLocation(Center+Direction*150+FVector(0,0,100));
        Setup=true;Warmed=false;Ready=FPlatformTime::Seconds();
    }
    // Prime actual procedural render proxies/PSOs with a visible draw before the
    // background/reference sequence. Merely waiting while hidden does not do so.
    if(!Warmed){
        Freeze(.4);Capture->ShowOnlyActors.Empty();Capture->ShowOnlyActors.Add(Backdrop);
        for(auto& E:NpcLive){E.Actor->SetActorHiddenInGame(false);Capture->ShowOnlyActors.Add(E.Actor.Get());}
        FlushRenderingCommands();Capture->CaptureScene();FlushRenderingCommands();Warmed=true;Ready=FPlatformTime::Seconds();return;
    }
    Freeze(Frame<2?.4:.8);for(auto& E:NpcLive)E.Actor->SetActorHiddenInGame(Frame%2==0);
    if(FPlatformTime::Seconds()-Ready<.35)return;
    Capture->ShowOnlyActors.Empty();Capture->ShowOnlyActors.Add(Backdrop);for(auto& E:NpcLive)Capture->ShowOnlyActors.Add(E.Actor.Get());
    FlushRenderingCommands();Capture->CaptureScene();FlushRenderingCommands();FBufferArchive Bytes;
    const FString Name=FString::Printf(TEXT("%d_view%d_time%d_%s.png"),Id,View,Frame/2,Frame%2==0?TEXT("background"):TEXT("effect"));
    if(!FImageUtils::ExportRenderTarget2DAsPNG(Target,Bytes)||!FFileHelper::SaveArrayToFile(Bytes,*FPaths::Combine(Output,Name))){Finish(TEXT("effect capture failed"));return;}
    ++Captures;Ready=FPlatformTime::Seconds();if(++Frame<4)return;
    Frame=0;Setup=false;if(++View<4)return;View=0;
    ClearNpcEffects();Owner->Destroy();Owner=nullptr;S->Entities.Remove(TEXT("npc:visual-effect"));S->EntityRows.Remove(TEXT("npc:visual-effect"));S->EntityModels.Remove(TEXT("npc:visual-effect"));
    if(++Model>=2)Finish(FString());
}
