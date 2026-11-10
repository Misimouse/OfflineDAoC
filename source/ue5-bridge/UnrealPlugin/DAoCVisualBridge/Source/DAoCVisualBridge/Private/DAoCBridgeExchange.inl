// Included by ClassicUI.cpp to share its inventory drag type and original art cache.
namespace {
bool ExchangeFlag(TSharedPtr<FJsonObject> O,const TCHAR* Key){bool V=false;if(O)O->TryGetBoolField(Key,V);return V;}
FString ExchangeMoney(int64 Copper){if(Copper<0)return TEXT("UNKNOWN");return FString::Printf(TEXT("%lldg %llds %lldc"),Copper/10000,(Copper/100)%100,Copper%100);}
TSharedPtr<FJsonObject> ExchangeRow(TSharedPtr<FJsonObject> State,int32 Index){for(auto V:CA(State,CS(State,TEXT("tab"))==TEXT("browse")?TEXT("market_rows"):TEXT("listing_rows")))if(V->Type==EJson::Object&&CN(V->AsObject(),TEXT("index"),-1)==Index)return V->AsObject();return nullptr;}
}

bool UDAoCBridgeSubsystem::ExchangeTyping()const{return PlayerTradeTyping()||(ExchangePanel.IsValid()&&(ExchangePanel->HasAnyUserFocusOrFocusedDescendants()||FSlateApplication::Get().AnyMenusVisible()));}
bool UDAoCBridgeSubsystem::ExchangeDropToBackpack(const FString& Id,const FString& ItemToken,const FString& WindowToken,int64 Catalog){
 if(WindowToken.IsEmpty()||WindowToken!=CS(ExchangeState,TEXT("token"))||Catalog!=int64(CN(ExchangeState,TEXT("catalog_revision"))))return false;
 for(auto Value:CA(ExchangeState,CS(ExchangeState,TEXT("tab"))==TEXT("browse")?TEXT("market_rows"):TEXT("listing_rows"))){auto Row=Value->AsObject();if(CS(Row,TEXT("id"))!=Id||CS(Row,TEXT("token"))!=ItemToken)continue;const int32 Index=int32(CN(Row,TEXT("index")));if(CS(ExchangeState,TEXT("tab"))==TEXT("browse"))ExchangeSelect(Index,true);else{auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("index"),Index);V->SetStringField(TEXT("exchange_item_token"),ItemToken);ExchangeRequest(TEXT("exchange_take"),V);}return true;}
 return false;
}
bool UDAoCBridgeSubsystem::CloseExchange(bool Notify){
 if(!ExchangeOverlay.IsValid())return false;
 if(Notify){ExchangeDismissedToken=CS(ExchangeState,TEXT("token"));auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("exchange_token"),ExchangeDismissedToken);Send(TEXT("exchange_close"),V);}
 if(ExchangeTyping())FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);
 if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ExchangeOverlay.ToSharedRef());
 ExchangeOverlay.Reset();ExchangePanel.Reset();ExchangeSignature.Empty();ExchangeConfirm.Reset();return true;
}
void UDAoCBridgeSubsystem::ApplyExchange(TSharedPtr<FJsonObject> State){
 ExchangeState=State;
 if(!ExchangeFlag(State,TEXT("visible"))){CloseExchange(false);return;}
 const FString Token=CS(State,TEXT("token"));
 if(!Token.IsEmpty()&&Token==ExchangeDismissedToken)return;
 if(Token!=ExchangeWindowToken){ExchangeWindowToken=Token;ExchangeSelected=-1;ExchangeListingPage=0;ExchangeConfirm.Reset();ExchangeFields.Empty();auto Filters=CO(State,TEXT("filters"));if(Filters)for(auto& P:Filters->Values)ExchangeFields.Add(FString(P.Key),P.Value->Type==EJson::String?P.Value->AsString():FString::Printf(TEXT("%lld"),int64(P.Value->AsNumber())));}
 RefreshExchange();
}
void UDAoCBridgeSubsystem::ExchangeRequest(const FString& Action,TSharedPtr<FJsonObject> V){
 if(!ExchangeFlag(ExchangeState,TEXT("visible"))||ExchangeFlag(ExchangeState,TEXT("pending"))||ExchangeFlag(ExchangeState,TEXT("stale")))return;
 if(Action==TEXT("exchange_search")&&!V){auto Filters=MakeShared<FJsonObject>();for(const auto& P:ExchangeFields){if(P.Key==TEXT("name"))Filters->SetStringField(P.Key,P.Value);else if(P.Key!=TEXT("price")){if(!P.Value.IsNumeric()||P.Value.Contains(TEXT(".")))return;Filters->SetNumberField(P.Key,FCString::Atoi64(*P.Value));}}V=MakeShared<FJsonObject>();V->SetObjectField(TEXT("filters"),Filters);}
 if(!V)V=MakeShared<FJsonObject>();V->SetStringField(TEXT("exchange_token"),CS(ExchangeState,TEXT("token")));V->SetNumberField(TEXT("catalog_revision"),CN(ExchangeState,TEXT("catalog_revision")));
 if(ExchangeTyping())FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);
 Send(Action,V);
}
void UDAoCBridgeSubsystem::ExchangeSelect(int32 Index,bool Confirm){
 if(ExchangeTyping())FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);
 ExchangeSelected=Index;ExchangeConfirm.Reset();
 if(CS(ExchangeState,TEXT("tab"))==TEXT("listings")){auto Row=ExchangeRow(ExchangeState,Index);if(Row)ExchangeFields.Add(TEXT("price"),FString::Printf(TEXT("%lld"),FMath::Max<int64>(0,int64(CN(Row,TEXT("price"),0)))));}
 if(Confirm&&CS(ExchangeState,TEXT("tab"))==TEXT("browse")){auto Row=ExchangeRow(ExchangeState,Index);if(Row&&CN(Row,TEXT("price"))>0){ExchangeConfirm=MakeShared<FJsonObject>();ExchangeConfirm->Values=Row->Values;ExchangeConfirm->SetStringField(TEXT("window_token"),CS(ExchangeState,TEXT("token")));ExchangeConfirm->SetNumberField(TEXT("catalog_revision"),CN(ExchangeState,TEXT("catalog_revision")));}}
 ExchangeSignature.Empty();RefreshExchange();
}
void UDAoCBridgeSubsystem::ExchangeListItem(int32 Slot,const FString& ItemToken,int32 ToSlot){
 auto Item=InventoryItem(Slot);if(Slot<40||Slot>=80||!Item||CS(Item,TEXT("token"))!=ItemToken)return;
 auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("slot"),Slot);V->SetNumberField(TEXT("to_slot"),ToSlot);V->SetStringField(TEXT("item_token"),ItemToken);V->SetNumberField(TEXT("inventory_revision"),CN(InventoryState,TEXT("state_revision"),-1));ExchangeRequest(TEXT("exchange_list"),V);
}
void UDAoCBridgeSubsystem::RefreshExchange(){
 if(!ExchangeFlag(ExchangeState,TEXT("visible"))||!GetWorld()||!GetWorld()->GetGameViewport())return;
 FString Stamp;FJsonSerializer::Serialize(ExchangeState.ToSharedRef(),TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::Printf(TEXT("/%d/%d/%d/%lld"),ExchangeSelected,ExchangeListingPage,ExchangeConfirm.IsValid(),int64(CN(InventoryState,TEXT("state_revision"))));
 if(ExchangeOverlay.IsValid()&&(Stamp==ExchangeSignature||ExchangeTyping()))return;
 // CloseExchange also clears a confirmation; retain its immutable purchase identity when rebuilding.
 auto Confirmation=ExchangeConfirm;CloseExchange(false);ExchangeConfirm=Confirmation;ExchangeSignature=Stamp;
 const bool Browse=CS(ExchangeState,TEXT("tab"))==TEXT("browse");const bool Ready=!ExchangeFlag(ExchangeState,TEXT("pending"))&&!ExchangeFlag(ExchangeState,TEXT("stale"));
 auto Canvas=SNew(SCanvas);
 // The original Godot window uses this exact chatext atlas region and patch margins.
 const auto* Art=ClassicArt(TEXT("chatext"),{0,.5},{1,1});
 if(Art){if(!ClassicBrushes.Contains(TEXT("exchange_frame"))){auto Frame=MakeShared<FSlateBrush>(*Art);Frame->ImageSize=FVector2D(512,64);Frame->DrawAs=ESlateBrushDrawType::Box;Frame->Margin=FMargin(3.f/512,12.f/64,12.f/512,3.f/64);ClassicBrushes.Add(TEXT("exchange_frame"),Frame);}At(Canvas,{0,0},{700,556},SNew(SImage).Image(ClassicBrushes[TEXT("exchange_frame")].Get()));}
 auto Text=[&](FVector2D P,FVector2D Size,const FString& T,int Font=10,FLinearColor Color=Cream){At(Canvas,P,Size,CT(T,Font,Color));};
 auto Button=[&](FVector2D P,FVector2D Size,const FString& T,TFunction<void()> Click,bool Enabled=true){At(Canvas,P,Size,SNew(SBox).IsEnabled(Enabled)[CB(CT(T,10,Gold),Click)]);};
 Text({240,6},{330,20},TEXT("REALM EXCHANGE"),13,Gold);Button({666,6},{24,20},TEXT("X"),[this](){CloseExchange();});
 for(const FString Tab:{FString(TEXT("browse")),FString(TEXT("listings"))})Button({Tab==TEXT("browse")?14.:142.,32},{122,22},Tab==TEXT("browse")?TEXT("BROWSE"):TEXT("MY LISTINGS"),[this,Tab](){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("tab"),Tab);ExchangeRequest(TEXT("exchange_tab"),V);},Ready);
 Text({274,33},{310,22},TEXT("PROCEEDS: ")+ExchangeMoney(int64(CN(ExchangeState,TEXT("proceeds"),-1))));Button({598,32},{88,22},TEXT("CLAIM"),[this](){ExchangeRequest(TEXT("exchange_claim"));},Ready&&CN(ExchangeState,TEXT("proceeds"))>0);
 auto Inset=[&](FVector2D P,FVector2D Size){At(Canvas,P,Size,SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor(.02f,.025f,.02f,.85f)));};
 Inset({10,66},{204,430});Inset({218,66},{472,430});
 auto Edit=[&](const FString& Key,FVector2D P,FVector2D Size,const FString& Default){if(!ExchangeFields.Contains(Key))ExchangeFields.Add(Key,Default);At(Canvas,P,Size,SNew(SEditableTextBox).Font(CF(10)).Text(FText::FromString(ExchangeFields[Key])).OnKeyDownHandler_Lambda([this](const FGeometry&,const FKeyEvent& Event){if(Event.GetKey()==EKeys::Escape){CloseExchange();return FReply::Handled();}return FReply::Unhandled();}).OnTextCommitted_Lambda([this](const FText&,ETextCommit::Type Method){if(Method==ETextCommit::OnEnter){FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);if(CS(ExchangeState,TEXT("tab"))==TEXT("browse"))ExchangeRequest(TEXT("exchange_search"));}}).OnTextChanged_Lambda([this,Key](const FText& T){ExchangeFields.Add(Key,T.ToString().Left(Key==TEXT("name")?63:12));}));};
 auto Choice=[&](const FString& Key,double Y,const TArray<TPair<FString,int32>>& Options){
  int32 Current=FCString::Atoi(*ExchangeFields.FindRef(Key));if(!Options.ContainsByPredicate([Current](const auto& Option){return Option.Value==Current;})){Current=Options[0].Value;ExchangeFields.Add(Key,FString::FromInt(Current));}FString Label=Options[0].Key;auto Menu=SNew(SVerticalBox);
  for(const auto& Option:Options){if(Option.Value==Current)Label=Option.Key;const int32 Value=Option.Value;Menu->AddSlot().AutoHeight()[CB(CT(Option.Key,10),[this,Key,Value](){ExchangeFields.Add(Key,FString::FromInt(Value));ExchangeSignature.Empty();FSlateApplication::Get().DismissAllMenus();FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);RefreshExchange();})];}
  At(Canvas,{18,Y},{186,24},SNew(SComboButton).IsFocusable(false).ButtonContent()[CT(Label,10)].MenuContent()[SNew(SBox).MaxDesiredHeight(280)[SNew(SScrollBox)+SScrollBox::Slot()[Menu]]]);
 };
 if(Browse){
  Text({18,68},{186,16},TEXT("NAME"));Edit(TEXT("name"),{18,84},{186,23},TEXT(""));
  Choice(TEXT("slot"),114,{{TEXT("ANY SLOT"),0},{TEXT("HEAD"),1},{TEXT("TORSO"),5},{TEXT("ARMS"),8},{TEXT("HANDS"),2},{TEXT("LEGS"),7},{TEXT("FEET"),3},{TEXT("CLOAK"),6},{TEXT("NECK"),9},{TEXT("JEWEL"),4},{TEXT("WAIST"),12},{TEXT("WRIST"),13},{TEXT("RING"),15},{TEXT("ONE HANDED"),100},{TEXT("LEFT HAND"),101},{TEXT("TWO HANDED"),102},{TEXT("RANGED"),103},{TEXT("INSTRUMENT"),104},{TEXT("SHIELD"),105},{TEXT("OTHER ITEMS"),106}});
  Choice(TEXT("armor"),144,{{TEXT("ANY ARMOR"),0},{TEXT("CLOTH"),1},{TEXT("LEATHER"),2},{TEXT("STUDDED"),3},{TEXT("CHAIN"),4},{TEXT("PLATE"),5},{TEXT("REINFORCED"),6},{TEXT("SCALE"),7}});
  Choice(TEXT("damage"),174,{{TEXT("ANY DAMAGE"),0},{TEXT("CRUSH"),1},{TEXT("SLASH"),2},{TEXT("THRUST"),3}});
  Text({18,205},{186,16},TEXT("LEVEL FROM / TO"));Edit(TEXT("level_min"),{18,221},{86,23},TEXT("1"));Edit(TEXT("level_max"),{116,221},{88,23},TEXT("52"));
  Text({18,250},{186,16},TEXT("MINIMUM QUALITY %"));Edit(TEXT("quality_min"),{18,266},{186,23},TEXT("0"));
  Text({18,295},{186,16},TEXT("MAXIMUM PRICE (COPPER)"));Edit(TEXT("price_max"),{18,311},{186,23},TEXT("0"));
  Choice(TEXT("crafted"),340,{{TEXT("ANY ORIGIN"),0},{TEXT("CRAFTED ONLY"),1}});Choice(TEXT("bonus1"),370,{{TEXT("ANY BONUS"),0},{TEXT("STAT"),1},{TEXT("RESIST"),5},{TEXT("HIT POINTS"),4},{TEXT("POWER"),3}});
  const int32 Bonus=FCString::Atoi(*ExchangeFields.FindRef(TEXT("bonus1")));
  if(Bonus==1)Choice(TEXT("bonus1_value"),400,{{TEXT("CONSTITUTION"),1},{TEXT("DEXTERITY"),2},{TEXT("QUICKNESS"),3},{TEXT("PIETY"),4},{TEXT("EMPATHY"),5},{TEXT("INTELLIGENCE"),6},{TEXT("CHARISMA"),7},{TEXT("ANY ACUITY"),8}});
  else if(Bonus==5)Choice(TEXT("bonus1_value"),400,{{TEXT("BODY"),0},{TEXT("COLD"),1},{TEXT("HEAT"),2},{TEXT("ENERGY"),3},{TEXT("MATTER"),4},{TEXT("SPIRIT"),5},{TEXT("THRUST"),6},{TEXT("CRUSH"),7},{TEXT("SLASH"),8}});
  else{Text({18,402},{186,16},TEXT("BONUS VALUE"));Edit(TEXT("bonus1_value"),{18,420},{186,23},TEXT("0"));}
  Button({18,458},{186,24},TEXT("SEARCH"),[this](){auto Filters=MakeShared<FJsonObject>();for(const auto& P:ExchangeFields){if(P.Key==TEXT("name"))Filters->SetStringField(P.Key,P.Value);else if(P.Key!=TEXT("price")){if(!P.Value.IsNumeric()||P.Value.Contains(TEXT(".")))return;Filters->SetNumberField(P.Key,FCString::Atoi64(*P.Value));}}auto V=MakeShared<FJsonObject>();V->SetObjectField(TEXT("filters"),Filters);ExchangeSelected=-1;ExchangeConfirm.Reset();ExchangeRequest(TEXT("exchange_search"),V);},Ready);
 }else{
  Text({18,74},{186,110},TEXT("Drag a backpack item into this chest, or select it in your inventory and press LIST ITEM. Then set its price. A price of zero stores it without offering it for sale."));
  Button({18,194},{186,24},TEXT("LIST SELECTED ITEM"),[this](){auto Item=InventoryItem(SelectedItemSlot);if(Item)ExchangeListItem(SelectedItemSlot,CS(Item,TEXT("token")));},Ready&&SelectedItemSlot>=40&&SelectedItemSlot<80&&InventoryItem(SelectedItemSlot).IsValid());
  Text({18,232},{186,16},TEXT("PRICE (TOTAL COPPER)"));Edit(TEXT("price"),{18,252},{186,24},TEXT("0"));
  Text({18,300},{186,65},TEXT("Right click an item for its details. TAKE BACK returns the item to your backpack."));
  Text({18,384},{186,20},FString::Printf(TEXT("CHEST PAGE %d"),int32(CN(ExchangeState,TEXT("listing_page")))+1));
  for(int32 Step:{-1,1})Button({Step<0?18.:116.,414},{88,24},Step<0?TEXT("PREVIOUS"):TEXT("NEXT"),[this,Step](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("step"),Step);ExchangeRequest(TEXT("exchange_chest_page"),V);},Ready&&(Step>0||CN(ExchangeState,TEXT("listing_page"))>0));
 }
 Text({250,70},{222,18},TEXT("ITEM"),10,Gold);Text({490,70},{36,18},TEXT("LVL"),10,Gold);Text({530,70},{40,18},TEXT("QUA"),10,Gold);Text({574,70},{110,18},TEXT("PRICE"),10,Gold);
 auto Rows=CA(ExchangeState,Browse?TEXT("market_rows"):TEXT("listing_rows"));int32 MarketVisible=0;
 for(auto Value:Rows){if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();const int32 Index=int32(CN(Row,TEXT("index"),-1));const int32 Offset=Browse?MarketVisible++:Index-150-ExchangeListingPage*20;if(Offset<0||Offset>=20)continue;const double Y=92+Offset*20;
  if(Index==ExchangeSelected)At(Canvas,{222,Y},{462,20},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor(.25f,.2f,.08f,.65f)));
  auto Select=[this,Index](){ExchangeSelect(Index);};auto Double=[this,Index,Browse](){ExchangeSelect(Index,Browse);};auto Inspect=[this,Index](){auto Row=ExchangeRow(ExchangeState,Index);if(!Row)return;auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("index"),Index);V->SetStringField(TEXT("exchange_item_token"),CS(Row,TEXT("token")));ExchangeRequest(TEXT("exchange_inspect"),V);};
  auto Entry=MakeShared<FJsonObject>();Entry->Values=Row->Values;Entry->SetStringField(TEXT("kind"),Browse?TEXT("exchange_market"):TEXT("exchange_listing"));Entry->SetStringField(TEXT("exchange_token"),CS(ExchangeState,TEXT("token")));Entry->SetNumberField(TEXT("catalog_revision"),CN(ExchangeState,TEXT("catalog_revision")));
  At(Canvas,{224,Y},{18,18},SNew(SClassicAction).Entry(Entry).Icon(ClassicIcon(int32(CN(Row,TEXT("icon"))))).Border(nullptr).Font(CF(10)).Click(Select).DoubleClick(Double).Inspect(Inspect));
  At(Canvas,{250,Y},{234,20},CB(CT(CS(Row,TEXT("name")),11,Index==ExchangeSelected?Gold:Cream),Select));Text({490,Y},{36,20},FString::FromInt(int32(CN(Row,TEXT("level")))),11);Text({530,Y},{40,20},FString::FromInt(int32(CN(Row,TEXT("quality")))),11);Text({574,Y},{110,20},ExchangeMoney(int64(CN(Row,TEXT("price"),-1))),10);
 }
 const int32 Page=Browse?int32(CN(ExchangeState,TEXT("market_page"))):ExchangeListingPage;const int32 Max=Browse?int32(CN(ExchangeState,TEXT("market_pages"))):4;
 for(int32 Step:{-1,1})Button({Step<0?222.:364.,506},{28,22},Step<0?TEXT("<"):TEXT(">"),[this,Page,Step,Browse](){ExchangeSelected=-1;ExchangeConfirm.Reset();if(Browse){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("page"),Page+Step);ExchangeRequest(TEXT("exchange_page"),V);}else{ExchangeListingPage=Page+Step;ExchangeSignature.Empty();RefreshExchange();}},Ready&&Page+Step>=0&&Page+Step<=Max);
 Text({252,509},{108,20},FString::Printf(TEXT("%d / %d"),Page+1,Max+1),11);
 auto Selected=ExchangeRow(ExchangeState,ExchangeSelected);
 Button({460,506},{108,22},Browse?TEXT("DETAILS"):TEXT("SET PRICE"),[this,Browse](){auto Row=ExchangeRow(ExchangeState,ExchangeSelected);if(!Row)return;auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("index"),ExchangeSelected);V->SetStringField(TEXT("exchange_item_token"),CS(Row,TEXT("token")));if(!Browse){FString Price=ExchangeFields.FindRef(TEXT("price"));if(Price.IsEmpty()||!Price.IsNumeric()||Price.Contains(TEXT(".")))return;V->SetNumberField(TEXT("copper"),FCString::Atoi64(*Price));}ExchangeRequest(Browse?TEXT("exchange_inspect"):TEXT("exchange_price"),V);},Ready&&Selected.IsValid());
 Button({574,506},{108,22},Browse?TEXT("BUY"):TEXT("TAKE BACK"),[this,Browse](){if(Browse){ExchangeSelect(ExchangeSelected,true);return;}auto Row=ExchangeRow(ExchangeState,ExchangeSelected);if(!Row)return;auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("index"),ExchangeSelected);V->SetStringField(TEXT("exchange_item_token"),CS(Row,TEXT("token")));ExchangeRequest(TEXT("exchange_take"),V);},Ready&&Selected.IsValid()&&(!Browse||CN(Selected,TEXT("price"))>0));
 Text({18,533},{664,20},CS(ExchangeState,TEXT("feedback")),10,Gold);
 if(ExchangeConfirm){Inset({220,190},{464,134});Text({232,200},{438,58},TEXT("BUY ")+CS(ExchangeConfirm,TEXT("name"))+TEXT(" FOR ")+ExchangeMoney(int64(CN(ExchangeConfirm,TEXT("price"))))+TEXT("?"),11,Gold);
  Button({236,280},{188,24},TEXT("CONFIRM PURCHASE"),[this](){auto Row=ExchangeRow(ExchangeState,int32(CN(ExchangeConfirm,TEXT("index"),-1)));if(!Row||CS(Row,TEXT("token"))!=CS(ExchangeConfirm,TEXT("token"))||CS(ExchangeState,TEXT("token"))!=CS(ExchangeConfirm,TEXT("window_token"))||CN(ExchangeState,TEXT("catalog_revision"))!=CN(ExchangeConfirm,TEXT("catalog_revision"))){ExchangeConfirm.Reset();ExchangeSignature.Empty();RefreshExchange();return;}auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("index"),CN(Row,TEXT("index")));V->SetStringField(TEXT("exchange_item_token"),CS(Row,TEXT("token")));ExchangeConfirm.Reset();ExchangeRequest(TEXT("exchange_buy"),V);ExchangeSignature.Empty();RefreshExchange();},Ready);
  Button({450,280},{188,24},TEXT("CANCEL"),[this](){ExchangeConfirm.Reset();ExchangeSignature.Empty();RefreshExchange();});
 }
 auto Drop=SNew(SClassicShopDrop).Sell([this,Browse](int32 Slot,const FString& Token){if(!Browse)ExchangeListItem(Slot,Token);})[Canvas];
 ExchangePanel=SNew(SClassicMove).Content(Drop).Move([this](FVector2D Delta){if(ExchangePosition.X<0)ExchangePosition.X=FMath::Max(0.,(UIViewportSize().X/ClassicScale()-700)*.5);ExchangePosition+=Delta;});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){auto Size=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(ExchangePosition.X<0?(Size.X-700)*.5:ExchangePosition.X,0.,FMath::Max(0.,Size.X-700)),FMath::Clamp(ExchangePosition.Y,0.,FMath::Max(0.,Size.Y-556)));}).Size(FVector2D(700,556))[ExchangePanel.ToSharedRef()];
 ExchangeOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ExchangeOverlay.ToSharedRef(),36);
}
