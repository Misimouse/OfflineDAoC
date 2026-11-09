// Original value_chooser.xml layout and original classic artwork. Included in
// ClassicUI.cpp so it shares the established art, font and layout helpers.
bool UDAoCBridgeSubsystem::ClassicQuantityValid() const {
    if(!ClassicQuantityCommand.IsValid()||!bLocalAvailable||bExiting||PlayerIsDead()||Session.IsEmpty()||Session!=ClassicQuantitySession)return false;
    bool Pending=false;if(InventoryState.IsValid())InventoryState->TryGetBoolField(TEXT("pending"),Pending);if(Pending)return false;
    const auto& V=ClassicQuantityCommand;
    if(CN(InventoryState,TEXT("state_revision"),-1)!=CN(V,TEXT("inventory_revision"),-2))return false;
    const int32 Source=int32(CN(V,TEXT("slot"),-1)),Destination=int32(CN(V,TEXT("to_slot"),-1));
    const auto Item=InventoryItem(Source);
    if(!Item.IsValid()||CS(Item,TEXT("token"))!=CS(V,TEXT("item_token"))||InventoryItem(Destination).IsValid()||CN(Item,TEXT("count"))!=ClassicQuantityMaximum)return false;
    auto Vault=CO(InventoryState,TEXT("vault"));bool Valid=false;if(Vault.IsValid())Vault->TryGetBoolField(TEXT("valid"),Valid);
    if(Source>=110||Destination>=110){if(!Valid||CS(Vault,TEXT("token"))!=CS(V,TEXT("vault_token")))return false;}
    auto Storage=[&](int32 Slot){return (Slot>=40&&Slot<80)||(Valid&&Slot>=int32(CN(Vault,TEXT("first")))&&Slot<int32(CN(Vault,TEXT("first"))+CN(Vault,TEXT("count"))));};
    return Storage(Source)&&Storage(Destination)&&Source!=Destination&&ClassicQuantitySelected>=1&&ClassicQuantitySelected<=ClassicQuantityMaximum;
}

void UDAoCBridgeSubsystem::MoveClassicInventoryDrag(int32 Source,int32 Destination,bool ChooseQuantity){
    if(!ChooseQuantity){CloseClassicQuantity();SendItemAction(TEXT("inventory_move"),Source,Destination);return;}
    CloseClassicQuantity();const auto Item=InventoryItem(Source);const double Count=CN(Item,TEXT("count"));
    if(!FMath::IsFinite(Count)||Count!=FMath::FloorToDouble(Count)||Count<2||Count>65535)return;
    ClassicQuantityMaximum=int32(Count);ClassicQuantitySelected=1;ClassicQuantitySession=Session;
    auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("slot"),Source);V->SetNumberField(TEXT("to_slot"),Destination);V->SetStringField(TEXT("item_token"),CS(Item,TEXT("token")));V->SetNumberField(TEXT("inventory_revision"),CN(InventoryState,TEXT("state_revision"),-1));
    if(Source>=110||Destination>=110)V->SetStringField(TEXT("vault_token"),CS(CO(InventoryState,TEXT("vault")),TEXT("token")));
    ClassicQuantityCommand=V;if(!ClassicQuantityValid()){CloseClassicQuantity();return;}RefreshClassicQuantity();
}

bool UDAoCBridgeSubsystem::CloseClassicQuantity(){
    const bool WasOpen=ClassicQuantityCommand.IsValid()||ClassicQuantityOverlay.IsValid();
    if(ClassicQuantityOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicQuantityOverlay.ToSharedRef());
    ClassicQuantityOverlay.Reset();ClassicQuantityPanel.Reset();ClassicQuantityCommand.Reset();ClassicQuantitySession.Empty();ClassicQuantityMaximum=0;ClassicQuantitySelected=1;return WasOpen;
}

void UDAoCBridgeSubsystem::AcceptClassicQuantity(){
    if(!ClassicQuantityValid()){CloseClassicQuantity();return;}
    auto Value=ClassicQuantityCommand;Value->SetNumberField(TEXT("count"),ClassicQuantitySelected);
    CloseClassicQuantity();Send(TEXT("inventory_move"),Value);
}

void UDAoCBridgeSubsystem::RefreshClassicQuantity(){
    if(!ClassicQuantityValid()){CloseClassicQuantity();return;}
    auto Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;if(!Viewport){CloseClassicQuantity();return;}
    if(ClassicQuantityOverlay.IsValid())Viewport->RemoveViewportWidgetContent(ClassicQuantityOverlay.ToSharedRef());
    auto Canvas=SNew(SCanvas);
    // Nine-slice preserves the original frame border at the XML's 128 x 96 size.
    auto Original=ClassicArt(TEXT("QuantityUI_v01/dialog_sm"));if(!Original){CloseClassicQuantity();return;}
    const FString FrameKey=TEXT("quantity-frame-box");auto Frame=ClassicBrushes.Find(FrameKey);
    if(!Frame){auto B=MakeShared<FSlateBrush>(*Original);B->DrawAs=ESlateBrushDrawType::Box;B->Margin=FMargin(10.f/256,20.f/96,10.f/256,10.f/96);ClassicBrushes.Add(FrameKey,B);Frame=ClassicBrushes.Find(FrameKey);}
    At(Canvas,{0,0},{128,96},SNew(SImage).Image(Frame->Get()));
    At(Canvas,{8,2},{112,14},CT(TEXT("Choose Quantity"),8,Gold));
    At(Canvas,{8,16},{112,14},CT(CS(InventoryItem(int32(CN(ClassicQuantityCommand,TEXT("slot")))),TEXT("name")),7));
    At(Canvas,{116,0},{12,12},CB(CT(TEXT("")),[this](){CloseClassicQuantity();}));
    auto Arrow=[&](bool Increase,FVector2D Position){const float Left=Increase?.5f:0.f;At(Canvas,Position,{8,14},CB(SNew(SImage).Image(ClassicArt(TEXT("QuantityUI_v01/arrows"),{Left,0},{Left+.5f,.25f})),[this,Increase](){const int32 Step=FSlateApplication::Get().GetModifierKeys().IsShiftDown()?10:1;ClassicQuantitySelected=FMath::Clamp(ClassicQuantitySelected+(Increase?Step:-Step),1,ClassicQuantityMaximum);RefreshClassicQuantity();}));};
    Arrow(false,{32,30});Arrow(true,{82,30});At(Canvas,{49,32},{34,18},CT(FString::FromInt(ClassicQuantitySelected),9));
    At(Canvas,{35,52},{60,16},CB(SNew(SImage).Image(ClassicArt(TEXT("QuantityUI_v01/buttons"),{0,96.f/256},{60.f/256,112.f/256})),[this](){AcceptClassicQuantity();}));
    At(Canvas,{35,70},{60,16},CB(SNew(SImage).Image(ClassicArt(TEXT("QuantityUI_v01/buttons"),{116.f/256,96.f/256},{176.f/256,112.f/256})),[this](){CloseClassicQuantity();}));
    ClassicQuantityPanel=Canvas;auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){auto Extent=UIViewportSize()/ClassicScale();return FVector2D(FMath::Max(0.,(Extent.X-128)*.5),FMath::Max(0.,(Extent.Y-96)*.5));}).Size(FVector2D(128,96))[Canvas];
    ClassicQuantityOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor::Transparent).Padding(0)[Root]];
    Viewport->AddViewportWidgetContent(ClassicQuantityOverlay.ToSharedRef(),60);
}
