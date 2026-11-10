#include "DAoCBridgeKeyConfiguration.h"
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SCanvas.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Misc/Paths.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Styling/CoreStyle.h"

namespace {
const FProgressBarStyle& PlayerBarStyle(){static const FProgressBarStyle Style=[](){FProgressBarStyle S;auto Back=*FCoreStyle::Get().GetBrush("WhiteBrush");Back.TintColor=FSlateColor(FLinearColor(.07f,.07f,.06f));S.SetBackgroundImage(Back);S.SetFillImage(*FCoreStyle::Get().GetBrush("WhiteBrush"));return S;}();return Style;}
bool PlayerFlag(const TSharedPtr<FJsonObject>& O,const TCHAR* K){bool V=false;if(O.IsValid())O->TryGetBoolField(K,V);return V;}
double PlayerNum(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
TSharedPtr<FJsonObject> PlayerVitals(const TSharedPtr<FJsonObject>& O){const TSharedPtr<FJsonObject>* V=nullptr;return O.IsValid()&&O->TryGetObjectField(TEXT("vitals"),V)?*V:nullptr;}
TSharedRef<STextBlock> PlayerLabel(const FString& S){return SNew(STextBlock).Text(FText::FromString(S)).AutoWrapText(true).ColorAndOpacity(FLinearColor(.92f,.91f,.85f));}
}
void UDAoCBridgeSubsystem::RemovePlayerStatusUI(){
    if(PlayerStatusOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(PlayerStatusOverlay.ToSharedRef());
    PlayerStatusOverlay.Reset();PlayerStatusPanel.Reset();PlayerControlsArea.Reset();
}
bool UDAoCBridgeSubsystem::PlayerStatusHovered() const{return PlayerStatusPanel.IsValid()&&PlayerStatusPanel->IsHovered();}
bool UDAoCBridgeSubsystem::PlayerIsDead() const{
    const auto Vitals=PlayerVitals(PlayerState);bool Alive=false;
    if(Vitals&&Vitals->TryGetBoolField(TEXT("alive"),Alive))return !Alive;
    if(PlayerFlag(Vitals,TEXT("absolute_health_known")))return PlayerNum(Vitals,TEXT("health"))<=0;
    return PlayerNum(Vitals,TEXT("health_pct"),100)<=0;
}
bool UDAoCBridgeSubsystem::PlayerCanMove() const{
    return PlayerFlag(PlayerState,TEXT("ready"))&&!PlayerIsDead()&&!PlayerFlag(PlayerVitals(PlayerState),TEXT("sitting"))&&!PlayerFlag(PlayerState,TEXT("posture_uncertain"))&&!(PlayerFlag(PlayerState,TEXT("posture_pending"))&&PlayerFlag(PlayerState,TEXT("posture_requested_sitting")));
}
void UDAoCBridgeSubsystem::RequestAttack(bool On){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting)return;
    if(On&&(!PlayerFlag(PlayerState,TEXT("ready"))||PlayerIsDead()||PlayerFlag(PlayerState,TEXT("attack_pending"))||PlayerFlag(PlayerState,TEXT("attack_uncertain"))))return;
    auto V=MakeShared<FJsonObject>();V->SetBoolField(TEXT("on"),On);V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));V->SetStringField(TEXT("entity_id"),CurrentTarget());Send(TEXT("combat_attack"),V);
}
void UDAoCBridgeSubsystem::RequestSit(bool On){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting||!PlayerFlag(PlayerState,TEXT("ready"))||PlayerIsDead())return;
    if(On&&(PlayerFlag(PlayerState,TEXT("posture_pending"))||PlayerFlag(PlayerState,TEXT("posture_uncertain"))))return;
    auto V=MakeShared<FJsonObject>();V->SetBoolField(TEXT("on"),On);V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));Send(TEXT("player_sit"),V);
}
void UDAoCBridgeSubsystem::RequestRelease(){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting||!PlayerFlag(PlayerState,TEXT("ready"))||!PlayerIsDead())return;
    const TSharedPtr<FJsonObject>* Release=nullptr;if(PlayerState->TryGetObjectField(TEXT("release"),Release)&&PlayerFlag(*Release,TEXT("pending")))return;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));Send(TEXT("player_release"),V);
}
void UDAoCBridgeSubsystem::RequestGMMode(bool CombatTest){
    if(!bLocalAvailable||Session.IsEmpty()||bExiting)return;
    const TSharedPtr<FJsonObject>* GM=nullptr;if(PlayerState.IsValid())PlayerState->TryGetObjectField(TEXT("gm_mode"),GM);
    if(CombatTest&&(!GM||!PlayerFlag(*GM,TEXT("ready"))||PlayerFlag(*GM,TEXT("pending"))||PlayerFlag(*GM,TEXT("uncertain"))||PlayerIsDead()))return;
    auto V=MakeShared<FJsonObject>();V->SetBoolField(TEXT("on"),CombatTest);V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));Send(TEXT("gm_test_mode"),V);
}
void UDAoCBridgeSubsystem::UpdatePlayerStatusInput(){
    if(bChatOpen||bOptionsOpen||ExchangeTyping()||bExiting)return;LoadKeyConfiguration();
    auto* PC=GetWorld()->GetFirstPlayerController();if(!PC)return;
    if(PC->WasInputKeyJustPressed(EKeys::F6)){const TSharedPtr<FJsonObject>* GM=nullptr;const bool Combat=PlayerState.IsValid()&&PlayerState->TryGetObjectField(TEXT("gm_mode"),GM)&&PlayerFlag(*GM,TEXT("combat_test"));RequestGMMode(!Combat);}
    if(KeyConfiguration->Pressed(PC,TEXT("attack_mode")))RequestAttack(!(PlayerFlag(PlayerState,TEXT("attack_on"))||PlayerFlag(PlayerState,TEXT("attack_pending"))||PlayerFlag(PlayerState,TEXT("attack_uncertain"))));
    if(KeyConfiguration->Pressed(PC,TEXT("sit")))RequestSit(!(PlayerFlag(PlayerVitals(PlayerState),TEXT("sitting"))||PlayerFlag(PlayerState,TEXT("posture_pending"))||PlayerFlag(PlayerState,TEXT("posture_uncertain"))));
    if(!bLocalAvailable||Session.IsEmpty()||!PlayerFlag(PlayerState,TEXT("ready"))||PlayerIsDead())return;
    auto Request=[&](const TCHAR* Action,const TCHAR* Mode,int32 Slot){
        auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("player_generation"),PlayerNum(PlayerState,TEXT("generation"),-1));
        if(Slot>=0){
            if(!PlayerFlag(InventoryState,TEXT("ready")))return;
            const TArray<TSharedPtr<FJsonValue>>* Items=nullptr;if(!InventoryState->TryGetArrayField(TEXT("items"),Items))return;
            TSharedPtr<FJsonObject> Item;for(auto Entry:*Items)if(Entry->Type==EJson::Object&&PlayerNum(Entry->AsObject(),TEXT("slot"),-1)==Slot){Item=Entry->AsObject();break;}
            FString Token;if(!Item.IsValid()||!Item->TryGetStringField(TEXT("token"),Token)||Token.IsEmpty())return;
            V->SetStringField(TEXT("mode"),Mode);V->SetStringField(TEXT("item_token"),Token);V->SetNumberField(TEXT("inventory_revision"),PlayerNum(InventoryState,TEXT("state_revision"),-1));
        }
        Send(Action,V);
    };
    if(KeyConfiguration->Pressed(PC,TEXT("sprint")))Request(TEXT("player_sprint"),TEXT(""),-1);
    if(KeyConfiguration->Pressed(PC,TEXT("weapon_right")))Request(TEXT("weapon_select"),TEXT("standard"),10);
    if(KeyConfiguration->Pressed(PC,TEXT("weapon_two_hand")))Request(TEXT("weapon_select"),TEXT("twohand"),12);
    if(KeyConfiguration->Pressed(PC,TEXT("weapon_ranged")))Request(TEXT("weapon_select"),TEXT("ranged"),13);

}
bool UDAoCBridgeSubsystem::PlayerSeesTarget() const{
    const FString Id=CurrentTarget();const auto* Target=Entities.Find(Id);if(Id.IsEmpty()||Id==TEXT("player:local")||!Target||!IsValid(*Target))return false;
    const FVector From=PlayerPosition,To=(*Target)->GetActorLocation();FVector Dir=To-From;Dir.Z=0;
    // Original ServerWorld.sees: close range is visible, otherwise three body-height rays.
    Dir=Dir.GetSafeNormal()*40;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(BridgePlayerTargetSight),true);Q.AddIgnoredActor(*Target);if(PlayerPawn)Q.AddIgnoredActor(PlayerPawn);
    if(const auto* Local=Entities.Find(TEXT("player:local")))if(IsValid(*Local))Q.AddIgnoredActor(*Local);
    for(float Height:{60.f,150.f,220.f}){FHitResult Hit;if(!GetWorld()->LineTraceSingleByChannel(Hit,From+Dir+FVector(0,0,Height),To-Dir+FVector(0,0,Height),ECC_Camera,Q))return true;}
    return false;
}
void UDAoCBridgeSubsystem::ApplyPlayerStatus(TSharedPtr<FJsonObject> State){
    PlayerState=State;const int64 Revision=int64(PlayerNum(State,TEXT("revision"),-1));if(Revision==PlayerStatusRevision&&PlayerStatusOverlay.IsValid())return;PlayerStatusRevision=Revision;
    auto* Viewport=GetWorld()->GetGameViewport();if(!Viewport)return;
    if(!PlayerStatusOverlay.IsValid()){
        auto Overlay=SNew(SOverlay);auto Card=SNew(SCanvas);
        auto Put=[&](FVector2D At,FVector2D Size,TSharedRef<SWidget> Widget){Card->AddSlot().Position(At).Size(Size)[Widget];};
        auto Font=[](int32 Size){return FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"),Size);};
        auto Label=[&](FVector2D P,FVector2D Size,const FString& Text,int32 Points){Put(P,Size,SNew(STextBlock).Text(FText::FromString(Text)).Font(Font(Points)).ColorAndOpacity(FLinearColor(.93,.89,.78)).Justification(ETextJustify::Center).ShadowOffset(FVector2D(1,1)).ShadowColorAndOpacity(FLinearColor::Black));};
        Put({0,0},{128,96},SNew(SImage).Image_Lambda([this](){return ClassicArt(TEXT("rightbot"));}));
        Put({14,3},{102,9},SNew(STextBlock).Text_Lambda([this](){return FText::FromString(Character.ToUpper());}).Font(Font(7)).ColorAndOpacity(FLinearColor(1,.85,.45)).Justification(ETextJustify::Center));
        const TCHAR* Keys[]={TEXT("health_pct"),TEXT("endurance_pct"),TEXT("mana_pct")};const TCHAR* Images[]={TEXT("redfull"),TEXT("greenfull"),TEXT("yellowfull")};const TCHAR* Names[]={TEXT("HP"),TEXT("END"),TEXT("POW")};const double Y[]={19.5,31,40.5};
        for(int32 I=0;I<3;++I){FString Key=Keys[I],Image=Images[I];Label({4,Y[I]-1},{21,8},Names[I],6);Card->AddSlot().Position(FVector2D(30,Y[I])).Size_Lambda([this,Key](){return FVector2D(90*FMath::Clamp(PlayerNum(PlayerVitals(PlayerState),*Key)/100,0.,1.),6);})[SNew(SImage).Image_Lambda([this,Image](){return ClassicArt(Image);})];}
        Label({4,51},{21,9},TEXT("EXP"),6);
        for(int32 I=0;I<10;++I)Put({30+I*9.,49.5},{9,8.5},SNew(SImage).Image_Lambda([this,I](){const TSharedPtr<FJsonObject>* P=nullptr;if(ClassicState.IsValid())ClassicState->TryGetObjectField(TEXT("points"),P);double X=P?PlayerNum(*P,TEXT("level_permill"))/100.:0;return ClassicArt(X>=I+1?TEXT("expjwl_full"):TEXT("expjwl_bg"),{I*.1,0},{(I+1)*.1,1});}));
        Put({30,58.5},{90,2.5},SNew(SImage).Image_Lambda([this](){return ClassicArt(TEXT("bluebg"));}));
        Card->AddSlot().Position(FVector2D(30,58.5)).Size_Lambda([this](){const TSharedPtr<FJsonObject>* P=nullptr;if(ClassicState.IsValid())ClassicState->TryGetObjectField(TEXT("points"),P);double X=P?FMath::Clamp(PlayerNum(*P,TEXT("level_permill"))/100.,0.,10.):0;return FVector2D(90*(X-FMath::FloorToDouble(X)),2.5);})[SNew(SImage).Image_Lambda([this](){return ClassicArt(TEXT("bluefull"));})];
        auto Target=[this](){const TSharedPtr<FJsonObject>* T=nullptr;return InteractionState.IsValid()&&InteractionState->TryGetObjectField(TEXT("target"),T)?*T:TSharedPtr<FJsonObject>();};
        Put({6,70},{114,10},SNew(STextBlock).Text_Lambda([Target](){FString Name;auto T=Target();if(T.IsValid())T->TryGetStringField(TEXT("name"),Name);return FText::FromString(Name.ToUpper());}).Font(Font(8)).ColorAndOpacity(FLinearColor(.93,.89,.78)).Justification(ETextJustify::Center));
        Put({3,81},{17,9},SNew(STextBlock).Text_Lambda([Target](){auto T=Target();const double H=PlayerNum(T,TEXT("health"),-1);return !T.IsValid()?FText::GetEmpty():FText::FromString(H<0?TEXT("?"):FString::Printf(TEXT("%.0f"),H*100));}).Font(Font(6)).ColorAndOpacity(FLinearColor(.93,.89,.78)).Justification(ETextJustify::Center));
        Card->AddSlot().Position(FVector2D(22,82.5)).Size_Lambda([Target](){return FVector2D(98*FMath::Clamp(PlayerNum(Target(),TEXT("health"),-1),0.,1.),6);})[SNew(SImage).Image_Lambda([this](){return ClassicArt(TEXT("redfull"));})];
        Overlay->AddSlot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(20,0,0,22)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(128).HeightOverride(96).Visibility(EVisibility::HitTestInvisible)[Card]]];
        Overlay->AddSlot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(20,0,0,140)[SNew(SBox).WidthOverride(270)[SAssignNew(PlayerControlsArea,SExpandableArea).InitiallyCollapsed(true).HeaderContent()[PlayerLabel(TEXT("Controls / GM"))].BodyContent()[SAssignNew(PlayerStatusPanel,SVerticalBox)]]];
        PlayerStatusOverlay=Overlay;Viewport->AddViewportWidgetContent(Overlay,20);
    }
    PlayerStatusPanel->ClearChildren();
    if(!PlayerFlag(State,TEXT("ready"))){PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(TEXT("Receiving character status..."))];return;}
    auto Vitals=PlayerVitals(State);
    const bool Dead=PlayerIsDead();const bool Attack=PlayerFlag(State,TEXT("attack_on"))||PlayerFlag(State,TEXT("attack_pending"))||PlayerFlag(State,TEXT("attack_uncertain"));const bool Sit=PlayerFlag(Vitals,TEXT("sitting"))||PlayerFlag(State,TEXT("posture_pending"))||PlayerFlag(State,TEXT("posture_uncertain"));
    if(Dead){
        if(PlayerControlsArea.IsValid())PlayerControlsArea->SetExpanded(true);
        const TSharedPtr<FJsonObject>* Release=nullptr;State->TryGetObjectField(TEXT("release"),Release);const bool Waiting=Release&&PlayerFlag(*Release,TEXT("pending"));
        PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(TEXT("You are dead"))];
        PlayerStatusPanel->AddSlot().AutoHeight()[SNew(SButton).IsFocusable(false).IsEnabled(!Waiting).OnClicked_Lambda([this](){RequestRelease();return FReply::Handled();})[PlayerLabel(Waiting?TEXT("Waiting for release..."):TEXT("Release to bind point"))]];
        FString Message;if(Release)(*Release)->TryGetStringField(TEXT("feedback"),Message);if(!Message.IsEmpty())PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(Message)];
    }
    PlayerStatusPanel->AddSlot().AutoHeight().Padding(0,4)[SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1).Padding(1)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([this,Attack](){RequestAttack(!Attack);return FReply::Handled();})[PlayerLabel(Attack?TEXT("C: Stop attack"):TEXT("C: Attack"))]]+SHorizontalBox::Slot().FillWidth(1).Padding(1)[SNew(SButton).IsFocusable(false).IsEnabled(!Dead).OnClicked_Lambda([this,Sit](){RequestSit(!Sit);return FReply::Handled();})[PlayerLabel(Sit?TEXT("N: Stand"):TEXT("N: Sit"))]]];
    PlayerStatusPanel->AddSlot().AutoHeight()[SNew(SButton).IsFocusable(false).OnClicked_Lambda([this](){SelectEntity(TEXT("player:local"));return FReply::Handled();})[PlayerLabel(TEXT("F7: Target self"))]];
    const TSharedPtr<FJsonObject>* GM=nullptr;
    if(State->TryGetObjectField(TEXT("gm_mode"),GM)){
        const bool Confirmed=PlayerFlag(*GM,TEXT("ready"))&&!PlayerFlag(*GM,TEXT("uncertain"));const bool Combat=PlayerFlag(*GM,TEXT("combat_test"));const bool Pending=PlayerFlag(*GM,TEXT("pending"));
        PlayerStatusPanel->AddSlot().AutoHeight().Padding(0,3)[PlayerLabel(Pending?TEXT("GM mode: waiting for server..."):!Confirmed?TEXT("GM mode: unconfirmed"):Combat?TEXT("Combat test · you can take damage"):TEXT("GM protected"))];
        PlayerStatusPanel->AddSlot().AutoHeight()[SNew(SButton).IsFocusable(false).IsEnabled(!Pending&&Confirmed&&(!Dead||Combat)).OnClicked_Lambda([this,Combat](){RequestGMMode(!Combat);return FReply::Handled();})[PlayerLabel(Combat?TEXT("F6: Protect GM"):TEXT("F6: Test combat"))]];
        FString Message;(*GM)->TryGetStringField(TEXT("feedback"),Message);if(!Message.IsEmpty())PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(Message)];
    }
    FString Feedback;State->TryGetStringField(TEXT("feedback"),Feedback);if(!Feedback.IsEmpty())PlayerStatusPanel->AddSlot().AutoHeight()[PlayerLabel(Feedback)];
}
