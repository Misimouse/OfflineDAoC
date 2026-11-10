#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/SViewport.h"

FVector2D UDAoCBridgeSubsystem::UIViewportSize() const {
    auto* Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;
    if(Viewport){
        // The viewport's overlay has its own engine DPI transform in addition to Windows scaling.
        // Measure the overlay allocation itself, so positions and our SDPIScaler share one space.
        for(const auto& Overlay:{ClassicOverlay,ChatOverlay})if(Overlay.IsValid()){
            const auto Size=Overlay->GetCachedGeometry().GetLocalSize();if(Size.X>1&&Size.Y>1)return Size;
        }
        // Slate overlays use local layout units, not the render target's physical pixels.
        if(auto Widget=Viewport->GetGameViewportWidget()){
            const auto Size=Widget->GetCachedGeometry().GetLocalSize();
            if(Size.X>1&&Size.Y>1)return Size;
        }
        FVector2D Pixels;Viewport->GetViewportSize(Pixels);if(Pixels.X>1&&Pixels.Y>1)return Pixels;
    }
    return FVector2D(1280,720);
}
void UDAoCBridgeSubsystem::ReflowUILayout(FVector2D Previous,FVector2D Current){
    auto Move=[&](FVector2D& P,FVector2D Size){
        for(int32 Axis=0;Axis<2;++Axis){
            const double OldFree=FMath::Max(0.,Previous[Axis]-Size[Axis]),NewFree=FMath::Max(0.,Current[Axis]-Size[Axis]);
            P[Axis]=OldFree>1?FMath::Clamp(P[Axis]/OldFree,0.,1.)*NewFree:FMath::Clamp(P[Axis],0.,NewFree);
        }
    };
    Move(ClassicPositions[0],{192,448});
    for(int32 I=0;I<3;++I)Move(ClassicPositions[I+1],ClassicVertical[I]?FVector2D(33,372):FVector2D(372,33));
    Move(ClassicTimePosition,{100,32});Move(ClassicCompassPosition,{112,22});Move(ClassicPositions[4],{192,315});Move(ClassicJournalPosition,{512,300});Move(ClassicTrainerPosition,{580,448});
    Move(ClassicPetPosition,{128,186});Move(ClassicConcentrationPosition,{128,136});Move(ClassicVaultPosition,{224,440});Move(ZoneMapPosition,{292,336});
    for(int32 I=0;I<2;++I){
        Move(ChatPositions[I],ChatSizes[I]);
        ChatSizes[I].X=FMath::Min(ChatSizes[I].X,FMath::Max(160.,Current.X-8));
        ChatSizes[I].Y=FMath::Min(ChatSizes[I].Y,FMath::Max(I==0?70.:50.,Current.Y-8));
    }
}
void UDAoCBridgeSubsystem::UpdateUILayout(){
    if(!bClassicPositioned)return;
    const FVector2D Current=UIViewportSize()/ClassicScale();
    if(UILayoutUnits.IsNearlyZero())ReflowUILayout(Current,Current);
    else if(!UILayoutUnits.Equals(Current,.5))ReflowUILayout(UILayoutUnits,Current);
    else {if(bZoneMapOpen&&bZoneMapFollow)FollowZoneMap();return;}
    UILayoutUnits=Current;
    for(const auto& W:{ClassicOverlay,ChatOverlay,ClassicJournalOverlay,ClassicTrainerOverlay,ClassicVaultOverlay,ZoneMapOverlay})if(W.IsValid())W->Invalidate(EInvalidateWidgetReason::Layout);
    if(bZoneMapOpen&&bZoneMapFollow)FollowZoneMap();
}

void UDAoCBridgeSubsystem::ApplyInterfaceVisibility(){
    LoadInterfaceSettings();
    if(!bLocalAvailable||CharacterLobbyOverlay.IsValid()||bExiting)InterfaceSettings->SetHidden(false);
    InterfaceSettings->ApplyVisibility({ClassicOverlay,ChatOverlay,ClassicDetailOverlay,ClassicGroupConfirmOverlay,
        ClassicJournalOverlay,ClassicTrainerOverlay,ClassicVaultOverlay,ClassicMerchantOverlay,GuildOverlay,
        EmblemPickerOverlay,PlayerTradeOverlay,ExchangeOverlay,ClassicQuantityOverlay,SiegeOverlay,RealmWarOverlay,ZoneMapOverlay,
        PlayerStatusOverlay,InventoryOverlay,InteractionOverlay,WorldMessageOverlay});
}
