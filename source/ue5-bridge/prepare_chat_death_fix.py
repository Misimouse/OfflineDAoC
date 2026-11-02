from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
import shutil
R=Path(str(ROOT));D=R/'Reports/chat_death_fix';D.mkdir(exist_ok=True)
backup=R/'Backups/ChatDeathFix_20261101';backup.mkdir(exist_ok=True)
for name in ['Source','Binaries']:shutil.copytree(R/'Client/Plugins/DAoCVisualBridge'/name,backup/name,dirs_exist_ok=True)
shutil.copy2(R/'Godot/live_gateway.gd',backup/'live_gateway.gd')
p=R/'Godot/live_gateway.gd';s=p.read_text(encoding='utf-8');s=s.replace('position=next\n        move_commands+=1','if player_state.ready and int(player_state.vitals.get("health_pct",0))<=0:return\n        position=next\n        move_commands+=1');s=s.replace('transport.snapshot_metadata["doors"]=states','transport.snapshot_metadata["messages"]=chat_lines.duplicate()\n        transport.snapshot_metadata["doors"]=states');p.write_text(s,encoding='utf-8')
root=R/'UnrealPlugin/DAoCVisualBridge';p=root/'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h';s=p.read_text(encoding='utf-8').replace('class SVerticalBox;','class SVerticalBox;\nclass SEditableTextBox;\nclass STextBlock;');s=s.replace('    bool PlayerCanMove() const;','''    bool PlayerCanMove() const;
    bool PlayerIsDead() const;
    TSharedPtr<SWidget> ChatOverlay;
    TSharedPtr<SEditableTextBox> ChatInput;
    TSharedPtr<STextBlock> ChatHistory;
    bool bChatOpen=false;
    double ChatClosedAt=-1;
    void ApplyChat(TSharedPtr<FJsonObject> Snapshot);
    void OpenChat();
    void CloseChat();
    void RemoveChat();
    void SubmitChat(const FString& Text);
''');p.write_text(s,encoding='utf-8')
p=root/'Source/DAoCVisualBridge/Private/DAoCBridgePlayerStatus.cpp';s=p.read_text(encoding='utf-8').replace('bool UDAoCBridgeSubsystem::PlayerCanMove() const{','bool UDAoCBridgeSubsystem::PlayerIsDead() const{return PlayerNum(PlayerVitals(PlayerState),TEXT("health_pct"),100)<=0;}\nbool UDAoCBridgeSubsystem::PlayerCanMove() const{');p.write_text(s,encoding='utf-8')
p=root/'Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp';s=p.read_text(encoding='utf-8').replace('RemovePlayerStatusUI();RemoveInventoryUI();RemoveInteractionUI();Disconnect();','RemoveChat();RemovePlayerStatusUI();RemoveInventoryUI();RemoveInteractionUI();Disconnect();').replace('void UDAoCBridgeSubsystem::ClearEntities(){','void UDAoCBridgeSubsystem::ClearEntities(){RemoveChat();');s=s.replace('Sequence=static_cast<int64>(Seq);LastSnapshot=', 'ApplyChat(M);\n    Sequence=static_cast<int64>(Seq);LastSnapshot=');s=s.replace('FRotator Rotation(0,Yaw+Offset,0);if(!A->GetActorRotation().Equals(Rotation,.01))','FRotator Rotation(0,Yaw+Offset,0);if(!(Id==TEXT("player:local")&&PlayerIsDead())&&!A->GetActorRotation().Equals(Rotation,.01))')
s=s.replace('    if(!Focused)bMouseLookToggle=false;','''    const bool Dead=PlayerIsDead();
    if(!Focused||Dead||bChatOpen)bMouseLookToggle=false;
    if(!bChatOpen&&FPlatformTime::Seconds()-ChatClosedAt>.2&&PC->WasInputKeyJustPressed(EKeys::Enter))OpenChat();
    PlayerPawn->bUseControllerRotationYaw=!Dead;
    if(Dead){PlayerPawn->ConsumeMovementInputVector();PlayerPawn->GetCharacterMovement()->DisableMovement();}
    else if(bNavigationReady&&PlayerPawn->GetCharacterMovement()->MovementMode==MOVE_None)PlayerPawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);''')
s=s.replace('if(PC->WasInputKeyJustPressed(EKeys::F3))','if(!Dead&&!bChatOpen&&PC->WasInputKeyJustPressed(EKeys::F3))').replace('SetMouseLook(bControls&&!bExiting&&Focused','SetMouseLook(!Dead&&!bChatOpen&&bControls&&!bExiting&&Focused');s=s.replace('    PC->SetControlRotation(FRotator(CameraPitch,CameraYaw,0));','    if(!Dead)PC->SetControlRotation(FRotator(CameraPitch,CameraYaw,0));');s=s.replace('if(bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting){','if(bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&!bChatOpen&&FPlatformTime::Seconds()-ChatClosedAt>.2){');s=s.replace('if(bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&FPlatformTime::Seconds()-LastMove>.1){','if(!Dead&&!bChatOpen&&bControls&&bLocalAvailable&&!Session.IsEmpty()&&!bExiting&&FPlatformTime::Seconds()-LastMove>.1){');s=s.replace('(*Local)->SetActorLocation(PlayerPosition);(*Local)->SetActorRotation(FRotator(0,CameraYaw-90,0));','if(!Dead){(*Local)->SetActorLocation(PlayerPosition);(*Local)->SetActorRotation(FRotator(0,CameraYaw-90,0));}')
s=s.replace('F1: GM protegido | F6: prueba combate','Enter: chat | F1: GM protegido | F6: prueba combate');p.write_text(s,encoding='utf-8')
chat='''#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Styling/CoreStyle.h"
#include "InputCoreTypes.h"
void UDAoCBridgeSubsystem::ApplyChat(TSharedPtr<FJsonObject> Snapshot){
    auto* Viewport=GetWorld()->GetGameViewport();if(!Viewport)return;
    if(!ChatOverlay.IsValid()){
        auto Overlay=SNew(SOverlay);
        Overlay->AddSlot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(0,0,20,22)[SNew(SBox).WidthOverride(560)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0,0,0,.7f)).Padding(8)[SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()[SAssignNew(ChatHistory,STextBlock).AutoWrapText(true).ColorAndOpacity(FLinearColor(.95f,.95f,.9f))]
            +SVerticalBox::Slot().AutoHeight().Padding(0,4)[SAssignNew(ChatInput,SEditableTextBox).Visibility(EVisibility::Collapsed).HintText(FText::FromString(TEXT("Mensaje o /comando · Enter envía · Esc cancela")))
                .OnKeyDownHandler_Lambda([this](const FGeometry&,const FKeyEvent& Event){if(Event.GetKey()==EKeys::Escape){CloseChat();return FReply::Handled();}return FReply::Unhandled();})
                .OnTextCommitted_Lambda([this](const FText& Text,ETextCommit::Type Method){if(Method==ETextCommit::OnEnter)SubmitChat(Text.ToString());})]
            +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("Enter · escribir en el chat"))).ColorAndOpacity(FLinearColor(.7f,.7f,.7f))]
        ]]];
        ChatOverlay=Overlay;Viewport->AddViewportWidgetContent(Overlay,40);
    }
    FString History;const TArray<TSharedPtr<FJsonValue>>* Lines=nullptr;
    if(Snapshot->TryGetArrayField(TEXT("messages"),Lines))for(int32 I=FMath::Max(0,Lines->Num()-8);I<Lines->Num();++I){FString Line;if((*Lines)[I]->TryGetString(Line)){if(!History.IsEmpty())History+=TEXT("\\n");History+=Line.Left(240);}}
    ChatHistory->SetText(FText::FromString(History));
}
void UDAoCBridgeSubsystem::OpenChat(){
    if(bExiting||Session.IsEmpty()||!bLocalAvailable)return;
    if(!ChatInput.IsValid())ApplyChat(MakeShared<FJsonObject>());
    if(!ChatInput.IsValid())return;
    bChatOpen=true;bMouseLookToggle=false;SetMouseLook(false);ChatInput->SetVisibility(EVisibility::Visible);
    if(auto* PC=GetWorld()->GetFirstPlayerController()){FInputModeUIOnly Mode;Mode.SetWidgetToFocus(ChatInput);PC->SetInputMode(Mode);PC->bShowMouseCursor=true;}
    FSlateApplication::Get().SetKeyboardFocus(ChatInput,EFocusCause::SetDirectly);
}
void UDAoCBridgeSubsystem::CloseChat(){
    bChatOpen=false;ChatClosedAt=FPlatformTime::Seconds();
    if(ChatInput.IsValid()){ChatInput->SetText(FText::GetEmpty());ChatInput->SetVisibility(EVisibility::Collapsed);}
    if(auto* PC=GetWorld()->GetFirstPlayerController()){FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(true);Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);PC->SetInputMode(Mode);PC->bShowMouseCursor=true;}
    FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);
}
void UDAoCBridgeSubsystem::SubmitChat(const FString& Text){
    const FString Value=Text.TrimStartAndEnd();
    if(Value.Len()>240||Value.Contains(TEXT("\\n"))||Value.Contains(TEXT("\\r")))return;
    if(!Value.IsEmpty()&&!Session.IsEmpty()&&bLocalAvailable&&!bExiting){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("text"),Value);Send(TEXT("chat"),V);}
    CloseChat();
}
void UDAoCBridgeSubsystem::RemoveChat(){
    if(bChatOpen)CloseChat();
    if(ChatOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ChatOverlay.ToSharedRef());
    ChatInput.Reset();ChatHistory.Reset();ChatOverlay.Reset();bChatOpen=false;
}
'''
(root/'Source/DAoCVisualBridge/Private/DAoCBridgeChat.cpp').write_text(chat,encoding='utf-8')
shutil.copytree(root/'Source',R/'GMCombatTest/NativeHost/Plugins/DAoCVisualBridge/Source',dirs_exist_ok=True)
print('Fuentes preparadas y copia previa guardada')
