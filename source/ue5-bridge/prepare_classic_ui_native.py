from bridge_paths import ROOT, INSTALL, ENGINE, ART_PROJECT
from pathlib import Path
R=Path(str(ROOT));P=R/'UnrealPlugin/DAoCVisualBridge'
p=P/'Source/DAoCVisualBridge/Public/DAoCBridgeSubsystem.h';s=p.read_text(encoding='utf-8').replace('class STextBlock;','class STextBlock;\nclass SBox;\nclass SCanvas;\nclass UTexture2D;\nclass UTextureRenderTarget2D;\nclass USceneCaptureComponent2D;\nstruct FSlateBrush;');a='    TSharedPtr<SWidget> InventoryOverlay;';n='''    TSharedPtr<FJsonObject> ClassicState;
    TSharedPtr<SWidget> ClassicOverlay;
    TSharedPtr<SBox> ClassicPanelBox,ClassicBarBoxes[3];
    TMap<FString,TSharedPtr<FSlateBrush>> ClassicBrushes;
    UPROPERTY() TMap<FString,TObjectPtr<UTexture2D>> ClassicTextures;
    UPROPERTY() TObjectPtr<UTextureRenderTarget2D> ClassicDollTarget;
    UPROPERTY() TObjectPtr<AActor> ClassicCaptureActor;
    USceneCaptureComponent2D* ClassicCapture=nullptr;
    FSlateBrush* ClassicDollBrush=nullptr;
    FString ClassicTab=TEXT("character"),ClassicLayoutFile,ClassicLayoutCharacter;
    bool bClassicOpen=true,ClassicVertical[3]={false,false,true};
    FVector2D ClassicPositions[4];
    bool bClassicPositioned=false;
    int64 ClassicRevision=-1;
    double ClassicReceivedAt=0,ClassicCapturedAt=0;
    void ApplyClassicUI(TSharedPtr<FJsonObject> State);
    void RemoveClassicUI();
    void RefreshClassicPanel();
    void RefreshClassicBars();
    void SetClassicTab(const FString& Tab);
    bool CloseClassicPanel();
    bool ClassicUIHovered() const;
    void UpdateClassicInput();
    void TickClassicUI();
    float ClassicScale() const;
    void SaveClassicLayout();
    const FSlateBrush* ClassicArt(const FString& Name,FVector2D UVMin=FVector2D(0,0),FVector2D UVMax=FVector2D(1,1));
    const FSlateBrush* ClassicIcon(int32 Icon,bool Border=false);
    TSharedPtr<FJsonObject> ClassicEntry(const FString& Id) const;
    TSharedPtr<FJsonObject> ClassicSlot(int32 Bar,int32 Slot) const;
    void ClassicUse(const FString& Id,const FString& Token);
    void ClassicAssign(int32 Bar,int32 Slot,const FString& Id,const FString& Token,int32 FromBar=-1,int32 FromBank=-1,int32 FromSlot=-1);
    bool TickClassicAcceptance();
''';assert a in s;s=s.replace(a,n+a);p.write_text(s,encoding='utf-8')
p=P/'Source/DAoCVisualBridge/DAoCVisualBridge.Build.cs';s=p.read_text(encoding='utf-8').replace('PCHUsage =','RuntimeDependencies.Add("$(PluginDir)/Content/ClassicUI/...", StagedFileType.UFS);\n        PCHUsage =');p.write_text(s,encoding='utf-8')
p=P/'Source/DAoCVisualBridge/Private/DAoCBridgeSubsystem.cpp';s=p.read_text(encoding='utf-8').replace('RemoveChat();RemovePlayerStatusUI();','RemoveClassicUI();RemoveChat();RemovePlayerStatusUI();').replace('ClearEntities(){RemoveChat();','ClearEntities(){RemoveClassicUI();RemoveChat();');s=s.replace('    ApplyChat(M);','    const TSharedPtr<FJsonObject>* Classic=nullptr;if(M->TryGetObjectField(TEXT("classic_ui"),Classic))ApplyClassicUI(*Classic);\n    ApplyChat(M);');s=s.replace('Focused&&!InventoryHovered()','Focused&&!ClassicUIHovered()&&!InventoryHovered()');s=s.replace('        UpdatePlayerStatusInput();','        UpdateClassicInput();\n        UpdatePlayerStatusInput();').replace('if(PC->WasInputKeyJustPressed(EKeys::Escape)&&!CloseInventory()','if(PC->WasInputKeyJustPressed(EKeys::Escape)&&!CloseClassicPanel()&&!CloseInventory()');s=s.replace('    if(TickCombatVisualAcceptance())return;','    if(TickClassicAcceptance())return;\n    if(TickCombatVisualAcceptance())return;');s=s.replace('UpdateControls(Dt);UpdateLocalEquipment();','UpdateControls(Dt);UpdateLocalEquipment();TickClassicUI();');s=s.replace('    O->SetNumberField(TEXT("interaction_test_steps"),','    if(ClassicState.IsValid()){O->SetObjectField(TEXT("classic_ui"),ClassicState);O->SetStringField(TEXT("classic_tab"),ClassicTab);O->SetBoolField(TEXT("classic_panel_open"),bClassicOpen);O->SetBoolField(TEXT("classic_ui_visible"),ClassicOverlay.IsValid());}\n    O->SetNumberField(TEXT("interaction_test_steps"),');p.write_text(s,encoding='utf-8')
p=P/'Source/DAoCVisualBridge/Private/DAoCBridgeInventory.cpp';s=p.read_text(encoding='utf-8').replace('void UDAoCBridgeSubsystem::ToggleInventory(){','void UDAoCBridgeSubsystem::ToggleInventory(){if(ClassicState.IsValid()){if(bClassicOpen&&ClassicTab==TEXT("inventory"))CloseClassicPanel();else SetClassicTab(TEXT("inventory"));return;}');s=s.replace('void UDAoCBridgeSubsystem::RefreshInventoryUI(){','void UDAoCBridgeSubsystem::RefreshInventoryUI(){\n    if(ClassicState.IsValid()){RemoveInventoryUI();if(ClassicTab==TEXT("inventory"))RefreshClassicPanel();return;}');p.write_text(s,encoding='utf-8')
