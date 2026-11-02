#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/PrimitiveComponent.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"

namespace {
FString Str(const TSharedPtr<FJsonObject>& O,const TCHAR* K){FString S;if(O.IsValid())O->TryGetStringField(K,S);return S;}
double Num(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O.IsValid()&&O->TryGetObjectField(K,V)?*V:nullptr;}
TSharedRef<STextBlock> Text(const FString& S){return SNew(STextBlock).Text(FText::FromString(S)).AutoWrapText(true).ColorAndOpacity(FLinearColor(.92f,.91f,.85f));}
}
FString UDAoCBridgeSubsystem::CurrentTarget() const{return Str(Obj(InteractionState,TEXT("target")),TEXT("id"));}
void UDAoCBridgeSubsystem::SelectEntity(const FString& Id,bool Interact){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting)return;
    if(Id==TEXT("player:local")&&!Interact){Send(TEXT("target_self"));return;}
    auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("entity_id"),Id);Send(Interact?TEXT("interact"):TEXT("target"),V);
}
bool UDAoCBridgeSubsystem::CanSelect(const FString& Id,FVector& Aim) const{
    const auto* A=Entities.Find(Id);const auto* Row=EntityRows.Find(Id);
    if(!A||!IsValid(*A)||!Row||Num(*Row,TEXT("health"),1)<=0)return false;
    bool Targetable=true;(*Row)->TryGetBoolField(TEXT("targetable"),Targetable);if(!Targetable||(*A)->IsHidden())return false;
    const float Range=Quality==TEXT("accessible")?6000:Quality==TEXT("balanced")?9000:Quality==TEXT("high")?12500:15000;
    if(FVector::DistSquared(PlayerPosition,(*A)->GetActorLocation())>FMath::Square(Range))return false;
    auto* Root=Cast<UPrimitiveComponent>((*A)->GetRootComponent());
    Aim=Root?Root->Bounds.Origin:(*A)->GetActorLocation()+FVector(0,0,90);
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC||!PC->PlayerCameraManager)return false;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(BridgeTargetSight),true);Q.AddIgnoredActor(*A);if(PlayerPawn)Q.AddIgnoredActor(PlayerPawn);
    FHitResult Hit;return !GetWorld()->LineTraceSingleByChannel(Hit,PC->PlayerCameraManager->GetCameraLocation(),Aim,ECC_Camera,Q);
}
FString UDAoCBridgeSubsystem::TargetAtCursor(bool Cycle,FVector2D ScreenOverride) const{
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC)return FString();
    int32 Width=0,Height=0;PC->GetViewportSize(Width,Height);float X=Width*.5f,Y=Height*.5f;if(!Cycle){if(ScreenOverride.X>=0){X=ScreenOverride.X;Y=ScreenOverride.Y;}else if(!PC->GetMousePosition(X,Y))return FString();}
    struct FCandidate{FString Id;float Score;};TArray<FCandidate> Candidates;
    for(const auto& Pair:Entities){
        FVector Aim;if(!CanSelect(Pair.Key,Aim))continue;
        if(Cycle){const auto* Row=EntityRows.Find(Pair.Key);const int32 Realm=Row?int32(Num(*Row,TEXT("realm"),-1)):-1;const bool Enemy=Pair.Key!=TEXT("player:local")&&(Realm==0||Realm==1||Realm==2);if(!Enemy||FVector::DistSquared(PlayerPosition,Pair.Value->GetActorLocation())>FMath::Square(6000.f))continue;Candidates.Add({Pair.Key,float(FVector::DistSquared(PlayerPosition,Pair.Value->GetActorLocation()))});continue;}
        FVector2D Screen;
        if(!PC->ProjectWorldLocationToScreen(Aim,Screen)||Screen.X<0||Screen.Y<0||Screen.X>Width||Screen.Y>Height)continue;
        FVector2D Top,Bottom;float Radius=24;
        if(auto* Root=Cast<UPrimitiveComponent>(Pair.Value->GetRootComponent()))if(PC->ProjectWorldLocationToScreen(Aim+FVector(0,0,Root->Bounds.BoxExtent.Z),Top)&&PC->ProjectWorldLocationToScreen(Aim-FVector(0,0,Root->Bounds.BoxExtent.Z),Bottom))Radius=FMath::Clamp(float((Top-Bottom).Size()*.55),16.f,90.f);
        const float Dist=FVector2D::Distance(Screen,FVector2D(X,Y));if(Cycle||Dist<=Radius)Candidates.Add({Pair.Key,Cycle?float(FVector::DistSquared(PlayerPosition,Pair.Value->GetActorLocation())):Dist/Radius});
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Score==B.Score?A.Id<B.Id:A.Score<B.Score;});
    if(Candidates.IsEmpty())return FString();if(!Cycle)return Candidates[0].Id;
    const FString Current=CurrentTarget();for(int I=0;I<Candidates.Num();++I)if(Candidates[I].Id==Current)return Candidates[(I+1)%Candidates.Num()].Id;
    return Candidates[0].Id;
}
void UDAoCBridgeSubsystem::UpdateInteractionInput(){
    auto* PC=GetWorld()->GetFirstPlayerController();bInteractionHovered=InteractionPanel.IsValid()&&InteractionPanel->IsHovered();
    if(!PC||bInteractionHovered||ClassicUIHovered()||InventoryHovered()||PlayerStatusHovered()||bMouseLook)return;
    if(PC->WasInputKeyJustPressed(EKeys::Tab))SelectEntity(TargetAtCursor(true));

}
bool UDAoCBridgeSubsystem::InteractSelected(){
    FString Id=CurrentTarget();if(Id.IsEmpty())return false;
    FVector Aim;if(!Id.StartsWith(TEXT("npc:"))){Status=TEXT("Select an NPC to talk to.");return true;}
    if(!CanSelect(Id,Aim)){Status=TEXT("The target is not in view.");return true;}
    SelectEntity(Id,true);return true;
}
bool UDAoCBridgeSubsystem::CloseInteraction(){
    const TArray<TSharedPtr<FJsonValue>>* Dialogs=nullptr;
    if(InteractionState.IsValid()&&InteractionState->TryGetArrayField(TEXT("dialogs"),Dialogs)&&!Dialogs->IsEmpty()){Status=TEXT("Use the buttons to answer the confirmation.");return true;}
    auto Talk=Obj(InteractionState,TEXT("talk")),Merchant=Obj(InteractionState,TEXT("merchant"));
    if((Talk.IsValid()&&!Talk->Values.IsEmpty())||(Merchant.IsValid()&&!Merchant->Values.IsEmpty())){Send(TEXT("dismiss_interaction"));return true;}
    if(!CurrentTarget().IsEmpty()){SelectEntity(TEXT(""));return true;}return false;
}
void UDAoCBridgeSubsystem::RemoveInteractionUI(){if(InteractionOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(InteractionOverlay.ToSharedRef());InteractionOverlay.Reset();InteractionPanel.Reset();}
void UDAoCBridgeSubsystem::ApplyInteraction(TSharedPtr<FJsonObject> State){
    InteractionState=State;
    auto* Viewport=GetWorld()->GetGameViewport();if(!Viewport)return;
    if(!InteractionOverlay.IsValid()){
        TSharedRef<SOverlay> Overlay=SNew(SOverlay);
        Overlay->AddSlot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(20,0,0,25)[SNew(SBox).WidthOverride(650).MaxDesiredHeight(180)[SNew(STextBlock).Visibility(EVisibility::HitTestInvisible).AutoWrapText(true).Text_Lambda([this](){FString Lines;const TArray<TSharedPtr<FJsonValue>>* Messages=nullptr;if(!bChatStructured&&InteractionState.IsValid()&&InteractionState->TryGetArrayField(TEXT("messages"),Messages)){int Start=FMath::Max(0,Messages->Num()-4);for(int I=Start;I<Messages->Num();++I){if(!Lines.IsEmpty())Lines+=TEXT("\n");Lines+=(*Messages)[I]->AsString();}}FString Feedback=Str(InteractionState,TEXT("feedback"));if(!Feedback.IsEmpty())Lines+=TEXT("\n")+Feedback;return FText::FromString(Lines);})]];
        Overlay->AddSlot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0,280,0,20)[SNew(SBox).WidthOverride(460).MaxDesiredHeight(680)[SAssignNew(InteractionPanel,SVerticalBox)]];
        InteractionOverlay=Overlay;Viewport->AddViewportWidgetContent(Overlay,20);
    }
    const int64 Revision=int64(Num(State,TEXT("revision"),-1));if(Revision==InteractionRevision)return;InteractionRevision=Revision;
    InteractionPanel->ClearChildren();bInteractionHovered=false;
    auto Body=SNew(SVerticalBox);bool HasContent=false;
    auto Button=[&](const FString& Label,TFunction<void()> Action){Body->AddSlot().AutoHeight().Padding(0,3)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([Action](){Action();return FReply::Handled();})[Text(Label)]];};
    const TArray<TSharedPtr<FJsonValue>>* Dialogs=nullptr;
    if(State->TryGetArrayField(TEXT("dialogs"),Dialogs)&&!Dialogs->IsEmpty()){
        auto D=(*Dialogs)[0]->AsObject();const int64 Id=int64(Num(D,TEXT("id")));Body->AddSlot().AutoHeight().Padding(0,5)[Text(Str(D,TEXT("title"))+TEXT("\n")+Str(D,TEXT("text")))];
        auto Reply=[this,Id](int Answer){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("dialog_id"),Id);V->SetNumberField(TEXT("answer"),Answer);Send(TEXT("dialog_response"),V);};
        Button(Num(D,TEXT("type"))==0?TEXT("Accept"):TEXT("Yes / accept"),[Reply](){Reply(1);});if(Num(D,TEXT("type"))!=0)Button(TEXT("No / decline"),[Reply](){Reply(0);});HasContent=true;
    }
    auto Talk=Obj(State,TEXT("talk"));
    if(Talk.IsValid()&&!Talk->Values.IsEmpty()){
        Body->AddSlot().AutoHeight().Padding(0,8)[Text(Str(Talk,TEXT("name"))+TEXT("\n\n")+Str(Talk,TEXT("text")))];const int64 Id=int64(Num(Talk,TEXT("id")));const TArray<TSharedPtr<FJsonValue>>* Words=nullptr;
        if(Talk->TryGetArrayField(TEXT("keywords"),Words))for(const auto& Word:*Words){FString W=Word->AsString();Button(W,[this,W,Id](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("reply_id"),Id);V->SetStringField(TEXT("word"),W);Send(TEXT("keyword"),V);});}HasContent=true;
    }
    auto Merchant=Obj(State,TEXT("merchant"));auto Pages=Obj(Merchant,TEXT("pages"));
    if(Pages.IsValid()&&!Pages->Values.IsEmpty()){
        Body->AddSlot().AutoHeight().Padding(0,8)[Text(Str(Merchant,TEXT("name"))+TEXT(" — Merchandise"))];TArray<FString> Keys;for(int I=0;I<10;++I){FString Key=FString::FromInt(I);if(Pages->HasField(Key))Keys.Add(Key);}
        for(const FString& Key:Keys){Body->AddSlot().AutoHeight().Padding(0,5)[Text(TEXT("Page ")+FString::FromInt(FCString::Atoi(*Key)+1))];for(const auto& Value:Pages->GetArrayField(Key)){auto It=Value->AsObject();int64 Price=int64(Num(It,TEXT("price")));FString Cost=FString::Printf(TEXT("%lld gold %lld silver %lld copper"),Price/10000,(Price/100)%100,Price%100);Body->AddSlot().AutoHeight().Padding(0,3)[Text(Str(It,TEXT("name"))+TEXT("  |  ")+Cost)];const FString Id=Str(Merchant,TEXT("entity_id"));const int64 Catalog=int64(Num(Merchant,TEXT("catalog_revision"),-1));const int32 Page=FCString::Atoi(*Key),Index=int32(Num(It,TEXT("index"),-1));if(Num(Merchant,TEXT("window"),-1)==0)Button(TEXT("Buy one pack"),[this,Page,Index,Id,Catalog](){BuyMerchantItem(Page,Index,Id,Catalog);});}}Button(TEXT("Open inventory to sell"),[this](){if(!bInventoryOpen)ToggleInventory();});HasContent=true;
    }
    if(HasContent){if((Talk.IsValid()&&!Talk->Values.IsEmpty())||(Merchant.IsValid()&&!Merchant->Values.IsEmpty()))Button(TEXT("Close conversation / merchandise"),[this](){Send(TEXT("dismiss_interaction"));});
        InteractionPanel->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.96f)).Padding(14)[SNew(SBox).MaxDesiredHeight(520)[SNew(SScrollBox)+SScrollBox::Slot()[Body]]]];
    }
}
