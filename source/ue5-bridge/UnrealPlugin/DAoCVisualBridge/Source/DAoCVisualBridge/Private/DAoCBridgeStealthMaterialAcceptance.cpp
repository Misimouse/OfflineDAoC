#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeStealthMaterials.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UObject/GarbageCollection.h"
#include "DAoCBridgeAppearance.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/LightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Serialization/BufferArchive.h"
#include "ImageUtils.h"
#include "RenderingThread.h"
#include "ShaderCompiler.h"
#include "Misc/Paths.h"

bool UDAoCBridgeSubsystem::TickStealthMaterialAcceptance(){
    FString ReportPath;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthMaterialTest="),ReportPath))return false;
    FString CaptureDir;
    if(FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthCapture="),CaptureDir)){
        static int32 Phase=0,Checks=0;static double ReadyAt=0;
        static TArray<TSharedPtr<FJsonValue>> Failures;
        static ASkeletalMeshActor* Avatar=nullptr;static USceneCaptureComponent2D* Capture=nullptr;static UTextureRenderTarget2D* Target=nullptr;

        auto Check=[&](bool Good,const TCHAR* Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
        auto Finish=[&](){ResetLocalStealthMaterials();auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("rendered"),true);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*ReportPath);UKismetSystemLibrary::QuitGame(GetWorld(),nullptr,EQuitPreference::Quit,false);};
        if(Phase==0){
            FString Input,Manifest,Text;TSharedPtr<FJsonObject> Fixture;
            FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthFixture="),Input);FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthMaterials="),Manifest);
            Check(Socket==nullptr,TEXT("render capture has no live account connection"));
            Check(FFileHelper::LoadFileToString(Text,*Input)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("real original character fixture loads"));
            StealthMaterials=MakeShared<FBridgeStealthMaterials>();bStealthMaterialsLoadTried=true;Check(StealthMaterials->Load(Manifest),TEXT("isolated material library loads"));
            if(!Fixture.IsValid()||!Failures.IsEmpty()){Finish();Phase=99;return true;}
            TSharedPtr<FJsonObject> Row;for(const auto& V:Fixture->GetArrayField(TEXT("entities")))if(V->AsObject()->GetStringField(TEXT("id"))==TEXT("player:local")){Row=V->AsObject();break;}
            Check(Row.IsValid(),TEXT("fixture includes local figure"));
            if(!Row.IsValid()){Finish();Phase=99;return true;}
            Avatar=Cast<ASkeletalMeshActor>(CreateEntity(TEXT("player:local"),Row,FVector::ZeroVector));Check(Avatar!=nullptr,TEXT("original native figure loads"));
            if(!Avatar){Finish();Phase=99;return true;}
            EntityRows.Add(TEXT("player:local"),Row);bLocalAvailable=true;PlayerState=Fixture->GetObjectField(TEXT("player_status"));InventoryState=Fixture->GetObjectField(TEXT("inventory"));UpdateLocalEquipment();SetEntityAnimation(TEXT("player:local"),TEXT("idle"));TickEquipmentAnimations();
            TArray<USkeletalMeshComponent*> Parts;Avatar->GetComponents(Parts);for(auto* Part:Parts){if(auto* Anim=Part->GetSingleNodeInstance())Anim->SetPosition(.25f,false);Part->TickAnimation(0,false);Part->RefreshBoneTransforms();Part->bPauseAnims=true;Part->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Part->SetComponentTickEnabled(true);Part->UpdateBounds();}
            const FBox Bounds=Avatar->GetComponentsBoundingBox(true);const FVector Center=Bounds.GetCenter();
            Check(Bounds.IsValid&&Bounds.GetExtent().Z>20,TEXT("figure has usable full-body render bounds"));
            for(int32 I=0;I<2;++I){auto* Light=GetWorld()->SpawnActor<ADirectionalLight>(FVector::ZeroVector,FRotator(I==0?-35.f:-20.f,I==0?120.f:-60.f,0));if(Light)Light->GetLightComponent()->SetIntensity(I==0?3.f:1.5f);}
            auto* Backdrop=GetWorld()->SpawnActor<AActor>();auto* Panel=NewObject<UStaticMeshComponent>(Backdrop);Backdrop->SetRootComponent(Panel);Panel->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Panel->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial")));Panel->SetWorldScale3D(FVector(6,.05,5));Panel->SetWorldLocation(Center+FVector(0,-100,0));Panel->RegisterComponent();
            auto* CaptureOwner=GetWorld()->SpawnActor<AActor>();Capture=NewObject<USceneCaptureComponent2D>(CaptureOwner);CaptureOwner->SetRootComponent(Capture);Capture->RegisterComponent();Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;Capture->FOVAngle=40;ConfigureCharacterPreviewCapture(Capture);Capture->ShowFlags.SetTemporalAA(false);Capture->ShowFlags.SetSeparateTranslucency(true);Capture->ShowFlags.SetTranslucency(true);
            Target=NewObject<UTextureRenderTarget2D>(CaptureOwner);Target->ClearColor=FLinearColor(.08,.08,.08,1);Target->InitAutoFormat(768,1024);Capture->TextureTarget=Target;Capture->ShowOnlyActorComponents(Avatar,true);Capture->ShowOnlyActorComponents(Backdrop,true);
            const double TanH=FMath::Tan(FMath::DegreesToRadians(20.));const double Distance=FMath::Max(Bounds.GetExtent().X/TanH,Bounds.GetExtent().Z/(TanH*1024./768.))*1.3+Bounds.GetExtent().Y;
            const FVector Eye=Center+FVector(0,Distance,0);Capture->SetWorldLocationAndRotation(Eye,(Center-Eye).Rotation());ReadyAt=0;Phase=1;return true;
        }
        if(Phase==99)return true;
        if(GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())return true;
        const double Now=FPlatformTime::Seconds();if(ReadyAt==0)ReadyAt=Now;if(Now-ReadyAt<3){Capture->CaptureScene();return true;}
        Capture->CaptureScene();FlushRenderingCommands();FBufferArchive Bytes;
        const FString Name=Phase==1?TEXT("visible.png"):Phase==2?TEXT("hidden.png"):Phase==3?TEXT("revealed.png"):TEXT("background.png");
        Check(FImageUtils::ExportRenderTarget2DAsPNG(Target,Bytes)&&FFileHelper::SaveArrayToFile(Bytes,*FPaths::Combine(CaptureDir,Name)),TEXT("render capture exported"));
        if(Phase==1){
            auto Row=EntityRows.FindRef(TEXT("player:local"));
            Row->SetBoolField(TEXT("stealth_render_known"),false);Row->SetBoolField(TEXT("stealth_render_hidden"),true);TickLocalStealthMaterials();
            Check(StealthMaterials->ChangedSlots()==0,TEXT("unconfirmed local snapshot preserves original appearance"));
            Row->SetBoolField(TEXT("stealth_render_known"),true);TickLocalStealthMaterials();
            Check(StealthMaterials->ChangedSlots()>0&&StealthMaterials->MissingSlots()==0,TEXT("authoritative local snapshot covers actual character and equipment materials"));
            const int32 Replacements=StealthMaterials->ReplacementCount();TickLocalStealthMaterials();
            Check(StealthMaterials->ReplacementCount()==Replacements,TEXT("ordinary repeated local updates reuse material overrides"));
            Phase=2;ReadyAt=0;return true;
        }
        if(Phase==2){EntityRows.FindRef(TEXT("player:local"))->SetBoolField(TEXT("stealth_render_hidden"),false);TickLocalStealthMaterials();Check(StealthMaterials->ChangedSlots()==0,TEXT("authoritative reveal removes all material overrides"));Phase=3;ReadyAt=0;return true;}
        if(Phase==3){Avatar->SetActorHiddenInGame(true);Phase=4;ReadyAt=0;return true;}
        Finish();Phase=99;return true;
    }
    static bool Ran=false;if(Ran)return true;Ran=true;
    int32 Checks=0;TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check=[&](bool Good,const FString& Label){++Checks;if(!Good)Failures.Add(MakeShared<FJsonValueString>(Label));};
    FString Manifest,Text;TSharedPtr<FJsonObject> Fixture;
    FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeStealthMaterials="),Manifest);
    Check(FFileHelper::LoadFileToString(Text,*Manifest)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("prepared separate material library loads"));
    auto* Actor=GetWorld()->SpawnActor<AActor>();auto* Other=GetWorld()->SpawnActor<AActor>();
    auto MakeComponent=[&](AActor* Owner){auto* C=NewObject<UStaticMeshComponent>(Owner);C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));Owner->SetRootComponent(C);C->RegisterComponent();return C;};
    auto* Mesh=MakeComponent(Actor);auto* OtherMesh=MakeComponent(Other);
    FBridgeStealthMaterials State;Check(State.Load(Manifest),TEXT("mapping accepted without altering character assets"));
    if(Fixture.IsValid()){
        const auto Rows=Fixture->GetObjectField(TEXT("materials"));
        Check(Rows->Values.Num()>=40,TEXT("sample includes original appearance and equipment material chains"));
        TSet<FString> Samples;const TArray<TSharedPtr<FJsonValue>>* Selected=nullptr;
        if(Fixture->TryGetArrayField(TEXT("acceptance_materials"),Selected))for(const auto& V:*Selected){const FString Key=V->AsString();Check(Rows->HasField(Key),TEXT("selected material belongs to prepared library"));Samples.Add(Key);}
        Check(!Selected||Samples.Num()>=40,TEXT("representative runtime sample retains at least forty original materials"));
        for(const auto& Pair:Rows->Values){
            const FString Key(*Pair.Key);if(Selected&&!Samples.Contains(Key))continue;
            auto* Source=LoadObject<UMaterialInterface>(nullptr,*Key);Check(Source!=nullptr,Key+TEXT(": original loads"));if(!Source)continue;
            auto* Original=UMaterialInstanceDynamic::Create(Source,Mesh);Mesh->SetMaterial(0,Original);OtherMesh->SetMaterial(0,Source);
            FLinearColor Colour;const FName Parameter=Source->GetVectorParameterValue(FMaterialParameterInfo(TEXT("FigureTint")),Colour)?TEXT("FigureTint"):TEXT("BaseColorFactor");
            const bool Tinted=Source->GetVectorParameterValue(FMaterialParameterInfo(Parameter),Colour);
            const FLinearColor Dye(.23f,.51f,.67f,1);if(Tinted)Original->SetVectorParameterValue(Parameter,Dye);
            const EBlendMode OriginalBlend=Source->GetBlendMode();
            State.Apply(Actor,false,true);Check(Mesh->GetMaterial(0)==Original,Key+TEXT(": unconfirmed state cannot hide"));
            State.Apply(Actor,true,true);auto* Hidden=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0));
            Check(Hidden&&Hidden!=Original&&Hidden->GetBlendMode()==BLEND_Translucent,Key+TEXT(": only avatar material becomes translucent"));
            Check(State.ChangedSlots()==1&&State.MissingSlots()==0,Key+TEXT(": one mapped slot"));
            float Opacity=0;Check(Hidden&&Hidden->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeStealthOpacity")),Opacity)&&FMath::IsNearlyEqual(Opacity,.45f),Key+TEXT(": intended opacity"));
            float Masked=0,Cutoff=0;
            Check(Hidden&&Hidden->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeStealthMaskEnabled")),Masked)&&FMath::IsNearlyEqual(Masked,Source->GetBlendMode()==BLEND_Masked?1.f:0.f),Key+TEXT(": original effective cutout mode retained"));
            Check(Hidden&&Hidden->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BridgeStealthMaskCutoff")),Cutoff)&&FMath::IsNearlyEqual(Cutoff,Source->GetOpacityMaskClipValue()),Key+TEXT(": original effective cutout threshold retained"));
            if(Tinted){FLinearColor Result;Check(Hidden&&Hidden->GetVectorParameterValue(FMaterialParameterInfo(Parameter),Result)&&Result.Equals(Dye),Key+TEXT(": current skin or dye preserved"));}
            const int32 Replaced=State.ReplacementCount();for(int32 I=0;I<50;++I)State.Apply(Actor,true,true);
            Check(Mesh->GetMaterial(0)==Hidden&&State.ReplacementCount()==Replaced,Key+TEXT(": repeated snapshots reuse override"));
            CollectGarbage(RF_NoFlags);
            State.Apply(Actor,true,false);Check(Mesh->GetMaterial(0)==Original&&State.ChangedSlots()==0,Key+TEXT(": exact original survives GC and reveal"));
            Check(Source->GetBlendMode()==OriginalBlend&&OtherMesh->GetMaterial(0)==Source,Key+TEXT(": shared original and other actor unchanged"));
            State.Apply(Actor,true,true);auto* NewOutfit=UMaterialInstanceDynamic::Create(Source,Mesh);Mesh->SetMaterial(0,NewOutfit);State.Apply(Actor,true,true);State.Restore();
            Check(Mesh->GetMaterial(0)==NewOutfit,Key+TEXT(": equipment changed while hidden restores latest material"));
        }
        State.Apply(Actor,true,true);State.Apply(Other,true,true);
        Check(State.ChangedSlots()==1,TEXT("switching avatar releases previous slot handles"));
        State.Restore();Check(State.ChangedSlots()==0,TEXT("session cleanup releases overrides"));
        auto* Unknown=UMaterial::GetDefaultMaterial(MD_Surface);Mesh->SetMaterial(0,Unknown);State.Apply(Actor,true,true);
        Check(Mesh->GetMaterial(0)==Unknown&&State.MissingSlots()==1,TEXT("unmapped material retained without losing its static configuration"));
        Mesh->DestroyComponent();State.Apply(Actor,true,true);Check(State.ChangedSlots()==0,TEXT("destroyed outfit component cannot retain stale material handles"));State.Restore();
    }
    Actor->Destroy();Other->Destroy();
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("rendered"),false);Report->SetBoolField(TEXT("normal_installation_modified"),false);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*ReportPath);
    UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
