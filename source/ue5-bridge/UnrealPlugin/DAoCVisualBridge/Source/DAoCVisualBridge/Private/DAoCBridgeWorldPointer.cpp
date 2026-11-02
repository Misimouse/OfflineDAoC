#include "DAoCBridgeSubsystem.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/IInputProcessor.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SViewport.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "InputCoreTypes.h"
namespace {
class FWorldPointer:public IInputProcessor {
public:TFunction<void(FKey,bool,FVector2D,bool)> Notify;
void Tick(float,FSlateApplication&,TSharedRef<ICursor>)override{}
bool HandleMouseButtonDownEvent(FSlateApplication&,const FPointerEvent& E)override{Notify(E.GetEffectingButton(),true,E.GetScreenSpacePosition(),false);return false;}
bool HandleMouseButtonDoubleClickEvent(FSlateApplication&,const FPointerEvent& E)override{Notify(E.GetEffectingButton(),true,E.GetScreenSpacePosition(),false);return false;}
bool HandleMouseButtonUpEvent(FSlateApplication&,const FPointerEvent& E)override{Notify(E.GetEffectingButton(),false,E.GetScreenSpacePosition(),false);return false;}
bool HandleMouseMoveEvent(FSlateApplication&,const FPointerEvent& E)override{Notify(FKey(),false,E.GetScreenSpacePosition(),true);return false;}
};
}
void UDAoCBridgeSubsystem::InstallWorldPointerInput(){
 if(WorldPointerInput.IsValid()||!FSlateApplication::IsInitialized())return;
 auto Input=MakeShared<FWorldPointer>();Input->Notify=[this](FKey K,bool Down,FVector2D P,bool Motion){HandleWorldPointer(K,Down,P,Motion);};WorldPointerInput=Input;FSlateApplication::Get().RegisterInputPreProcessor(Input);
}
void UDAoCBridgeSubsystem::RemoveWorldPointerInput(){if(WorldPointerInput.IsValid()&&FSlateApplication::IsInitialized())FSlateApplication::Get().UnregisterInputPreProcessor(WorldPointerInput);WorldPointerInput.Reset();bRightPointerHeld=bRightPointerDragged=false;}
bool UDAoCBridgeSubsystem::WorldPointerBlocked(FVector2D Absolute)const{
 auto Hit=[&](const TSharedPtr<SWidget>& W){return W.IsValid()&&W->GetVisibility().IsVisible()&&W->GetCachedGeometry().IsUnderLocation(Absolute);};
 if(bChatOpen||FSlateApplication::Get().AnyMenusVisible())return true;
 if(bClassicOpen&&Hit(ClassicPanelBox)||bClassicMiniGroupOpen&&Hit(ClassicMiniGroupBox))return true;
 for(const auto& W:{ClassicDetailPanel,ClassicGroupConfirmPanel,ClassicJournalPanel,ClassicTrainerPanel,ClassicVaultPanel,ZoneMapPanel})if(Hit(W))return true;
 for(const auto& W:ClassicBarBoxes)if(Hit(W))return true;
 for(const auto& W:ChatPanels)if(Hit(W))return true;
 if(ClassicEffectsBox.IsValid()&&Hit(ClassicEffectsBox)){TFunction<bool(TSharedRef<SWidget>)> IconHit;IconHit=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("SClassicAction")&&Hit(W))return true;auto Children=W->GetChildren();for(int32 I=0;Children&&I<Children->Num();++I)if(IconHit(Children->GetChildAt(I)))return true;return false;};if(IconHit(ClassicEffectsBox.ToSharedRef()))return true;}
 if(Hit(ClassicPetBox)||Hit(ClassicConcentrationBox)||Hit(PlayerStatusPanel))return true;
 if(InteractionPanel.IsValid()&&InteractionPanel->GetChildren()->Num()>0&&Hit(InteractionPanel))return true;
 if(bInventoryOpen&&Hit(InventoryPanel))return true;
 return false;
}
void UDAoCBridgeSubsystem::HandleWorldPointer(FKey Key,bool Down,FVector2D Absolute,bool Motion){
 if(Motion){if(bRightPointerHeld&&FVector2D::Distance(Absolute,RightPointerStart)>6)bRightPointerDragged=true;return;}
 if(Key==EKeys::RightMouseButton&&!Down){
  const bool Click=bRightPointerHeld&&!bRightPointerDragged;bRightPointerHeld=bRightPointerDragged=false;
  if(Click&&!WorldPointerBlocked(Absolute)){auto Id=TargetAtCursor(false,RightPointerPixel);if(Id.StartsWith(TEXT("npc:")))SelectEntity(Id,true);}return;
 }
 if(!Down||!bLocalAvailable||!bControls||bExiting||bMouseLookToggle||WorldPointerBlocked(Absolute))return;
 auto* V=GetWorld()?GetWorld()->GetGameViewport():nullptr;if(!V||!V->GetGameViewportWidget().IsValid())return;auto G=V->GetGameViewportWidget()->GetCachedGeometry();if(!G.IsUnderLocation(Absolute))return;
 FVector2D Pixels;V->GetViewportSize(Pixels);auto Point=G.AbsoluteToLocal(Absolute)/G.GetLocalSize()*Pixels;
 if(Key==EKeys::LeftMouseButton)SelectEntity(TargetAtCursor(false,Point));
 else if(Key==EKeys::RightMouseButton){RightPointerStart=Absolute;RightPointerPixel=Point;bRightPointerHeld=true;bRightPointerDragged=false;}
}
