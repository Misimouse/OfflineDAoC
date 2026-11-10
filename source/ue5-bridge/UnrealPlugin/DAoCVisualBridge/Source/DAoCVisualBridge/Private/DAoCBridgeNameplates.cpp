// Shared font atlas, fixed screen size and camera-facing names. No per-NPC render targets.
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/Canvas.h"
#include "Engine/Font.h"
#include "UObject/StrongObjectPtr.h"
#include "GameFramework/HUD.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PrimitiveComponent.h"
#include "CanvasItem.h"
#include "Fonts/SlateFontInfo.h"
#include "Fonts/CompositeFont.h"
#include "Misc/Paths.h"

void UDAoCBridgeSubsystem::SetupNameplates(){
    if(NameplateFontFile.IsEmpty())NameplateFontFile=FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"));
    if(!NameplateFont.IsValid())NameplateFont=MakeShared<FCompositeFont>(FName(TEXT("Regular")),NameplateFontFile,EFontHinting::Default,EFontLoadingPolicy::LazyLoad);
    if(!NameplateDrawHandle.IsValid())NameplateDrawHandle=AHUD::OnHUDPostRender.AddUObject(this,&UDAoCBridgeSubsystem::DrawNameplates);
    if(auto* PC=GetWorld()->GetFirstPlayerController())if(!PC->GetHUD())PC->ClientSetHUD(AHUD::StaticClass());
}
void UDAoCBridgeSubsystem::DrawNameplates(AHUD* HUD,UCanvas* Canvas){
    if(!HUD||HUD->GetWorld()!=GetWorld()||!Canvas||!Canvas->Canvas)return;
    NameplatesVisible=0;NameplatesOccluded=0;if(!bLocalAvailable||!FPaths::FileExists(NameplateFontFile))return;
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC||!PC->PlayerCameraManager)return;
    const FVector CameraPos=PC->PlayerCameraManager->GetCameraLocation();const double Now=FPlatformTime::Seconds();
    const float Size=FMath::Max(8.f,FMath::RoundToFloat(Canvas->SizeY*.018f));
    static TStrongObjectPtr<UFont> RuntimeFont;
    if(!RuntimeFont.IsValid()){RuntimeFont.Reset(NewObject<UFont>());RuntimeFont->FontCacheType=EFontCacheType::Runtime;RuntimeFont->GetMutableInternalCompositeFont()=*NameplateFont;}
    FSlateFontInfo Font(RuntimeFont.Get(),Size,FName(TEXT("Regular"))),GuildFont(RuntimeFont.Get(),FMath::RoundToFloat(Size*.8f),FName(TEXT("Regular")));
    const FString Target=CurrentTarget();
    FVector TargetAim;if(CanSelect(Target,TargetAim))if(auto* Selected=Entities.Find(Target))if(IsValid(*Selected)){
        // One projected ground ring; selection comes only from the acknowledged server target.
        FVector Feet=Target==TEXT("player:local")?PlayerPosition:(*Selected)->GetActorLocation();float Radius=45;
        if(auto* Root=Cast<UPrimitiveComponent>((*Selected)->GetRootComponent()))Radius=FMath::Clamp(float(FMath::Max(Root->Bounds.BoxExtent.X,Root->Bounds.BoxExtent.Y))*.7f,28.f,130.f);
        for(int32 I=0;I<40;++I){double A=I*2*PI/40,B=(I+1)*2*PI/40;FVector2D P,Q;if(PC->ProjectWorldLocationToScreen(Feet+FVector(FMath::Cos(A)*Radius,FMath::Sin(A)*Radius,4),P)&&PC->ProjectWorldLocationToScreen(Feet+FVector(FMath::Cos(B)*Radius,FMath::Sin(B)*Radius,4),Q)){FCanvasLineItem Line(P,Q);Line.SetColor(FLinearColor(1,.85,.2));Line.LineThickness=2;Canvas->DrawItem(Line);}}
    }

    for(const auto& Pair:Entities){
        if(Pair.Key==TEXT("player:local")||!IsValid(Pair.Value)||Pair.Value->IsHidden())continue;
        const auto* Found=EntityRows.Find(Pair.Key);if(!Found)continue;const auto& Row=*Found;
        double Health=1;Row->TryGetNumberField(TEXT("health"),Health);if(Health<=0)continue;
        const bool Selected=Pair.Key==Target;const TSharedPtr<FJsonObject>* Plate=nullptr;Row->TryGetObjectField(TEXT("nameplate"),Plate);
        bool Show=true;if(Plate)(*Plate)->TryGetBoolField(TEXT("show"),Show);if(!Selected&&!Show)continue;
        const float Distance=FVector::Dist2D(PlayerPosition,Pair.Value->GetActorLocation());
        const float EntityRange=Quality==TEXT("accessible")?6000:Quality==TEXT("balanced")?9000:Quality==TEXT("high")?12500:15000;
        if(Distance>EntityRange||(!Selected&&Distance>4000))continue;
        FVector Anchor=Pair.Value->GetActorLocation()+FVector(0,0,210);
        if(Pair.Value->ActorHasTag(TEXT("DAoCBridgeEffectBody"))){const FBox Body=EntitySelectionBounds(Pair.Value.Get());if(!Body.IsValid)continue;Anchor=FVector(Body.GetCenter().X,Body.GetCenter().Y,Body.Max.Z+20);}
        if(auto* Root=Cast<UPrimitiveComponent>(Pair.Value->GetRootComponent()))Anchor.Z=Root->Bounds.GetBox().Max.Z+20;
        FVector2D Screen;if(!PC->ProjectWorldLocationToScreen(Anchor,Screen)||Screen.X<0||Screen.Y<0||Screen.X>Canvas->SizeX||Screen.Y>Canvas->SizeY)continue;
        auto& Visibility=NameplateVisibility.FindOrAdd(Pair.Key);
        if(Now-Visibility.At>.1||FVector::DistSquared(Visibility.Camera,CameraPos)>625||FVector::DistSquared(Visibility.Anchor,Anchor)>625){
            FCollisionQueryParams Q(SCENE_QUERY_STAT(BridgeNameplateSight),true);Q.AddIgnoredActor(Pair.Value);if(PlayerPawn)Q.AddIgnoredActor(PlayerPawn);
            FHitResult Hit;Visibility.Visible=!GetWorld()->LineTraceSingleByChannel(Hit,CameraPos,Anchor,ECC_Camera,Q);
            Visibility.At=Now;Visibility.Camera=CameraPos;Visibility.Anchor=Anchor;
        }
        if(!Visibility.Visible){++NameplatesOccluded;continue;}
        FColor Color=FColor::White;const TArray<TSharedPtr<FJsonValue>>* RGB=nullptr;
        if(!Selected&&Plate&&(*Plate)->TryGetArrayField(TEXT("color_rgb"),RGB)&&RGB->Num()==3)Color=FColor(uint8(FMath::Clamp((*RGB)[0]->AsNumber(),0.,255.)),uint8(FMath::Clamp((*RGB)[1]->AsNumber(),0.,255.)),uint8(FMath::Clamp((*RGB)[2]->AsNumber(),0.,255.)));
        FString Name,Guild;Row->TryGetStringField(TEXT("name"),Name);Row->TryGetStringField(TEXT("guild"),Guild);
        auto Draw=[&](const FString& Text,const FSlateFontInfo& Face,float Y){FCanvasTextItem Item(FVector2D(Screen.X,Y),FText::FromString(Text),Face,FLinearColor(Color));Item.bCentreX=true;Item.bOutlined=true;Item.OutlineColor=FLinearColor(.02f,.04f,.02f,.9f);Canvas->DrawItem(Item);};
        Draw(Name.Left(80),Font,Screen.Y-Size*(Guild.IsEmpty()?1.2f:2.3f));if(!Guild.IsEmpty())Draw(TEXT("<")+Guild.Left(100)+TEXT(">"),GuildFont,Screen.Y-Size);
        ++NameplatesVisible;
    }
    Canvas->Canvas->Flush_GameThread();
}
