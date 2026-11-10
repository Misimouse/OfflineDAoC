// Original trade atlas; incoming authoritative state owns every displayed offer.
namespace {
class SClassicPlayerTradeDrop:public SCompoundWidget{
public:SLATE_BEGIN_ARGS(SClassicPlayerTradeDrop){}SLATE_DEFAULT_SLOT(FArguments,Content)SLATE_ARGUMENT(TFunction<void(int32,const FString&)>,Offer)SLATE_END_ARGS()
 void Construct(const FArguments& A){Offer=A._Offer;ChildSlot[A._Content.Widget];}
 virtual FReply OnDrop(const FGeometry& G,const FDragDropEvent& E)override{const auto P=G.AbsoluteToLocal(E.GetScreenSpacePosition());if(P.X<12||P.X>178||P.Y<14||P.Y>196)return FReply::Unhandled();auto D=E.GetOperationAs<FClassicDrag>();if(!D||D->InventorySlot<40||D->InventorySlot>79||D->ItemToken.IsEmpty()||!Offer)return FReply::Unhandled();Offer(D->InventorySlot,D->ItemToken);return FReply::Handled();}
private:TFunction<void(int32,const FString&)> Offer;
};
}
bool VerifyDAoCPlayerTradeDrop(){
 int32 Calls=0;bool Correct=true;auto Drop=SNew(SClassicPlayerTradeDrop).Offer([&](int32 Slot,const FString& Token){++Calls;Correct&=Slot==40&&Token==TEXT("held");})[SNew(SBox)];
 auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),TEXT("srv:40"));Entry->SetStringField(TEXT("item_token"),TEXT("held"));
 auto Make=[&](int32 Slot){auto Item=SNew(SClassicAction).Entry(Entry).InventorySlot(Slot).Font(CF());return StaticCastSharedPtr<FClassicDrag>(Item->OnDragDetected(FGeometry(),FPointerEvent()).GetDragDropContent());};
 auto G=FGeometry::MakeRoot(FVector2D(384,256),FSlateLayoutTransform());
 auto Event=[&](FVector2D P,int32 Slot){return FDragDropEvent(FPointerEvent(0,P,P,TSet<FKey>(),EKeys::LeftMouseButton,0,FModifierKeysState()),Make(Slot));};
 bool Own=Drop->OnDrop(G,Event({32,50},40)).IsEventHandled();bool Partner=Drop->OnDrop(G,Event({240,50},40)).IsEventHandled();bool Coins=Drop->OnDrop(G,Event({32,220},40)).IsEventHandled();bool Equipment=Drop->OnDrop(G,Event({32,50},10)).IsEventHandled();
 return Own&&!Partner&&!Coins&&!Equipment&&Calls==1&&Correct;
}
bool UDAoCBridgeSubsystem::PlayerTradeTyping()const{return PlayerTradePanel.IsValid()&&PlayerTradePanel->HasAnyUserFocusOrFocusedDescendants();}
bool UDAoCBridgeSubsystem::ClosePlayerTrade(bool Notify){
 if(!PlayerTradeOverlay)return false;
 if(Notify)PlayerTradeRequest(TEXT("player_trade_cancel"),CS(PlayerTradeState,TEXT("token")),-1);
 if(PlayerTradeTyping())FSlateApplication::Get().SetAllUserFocusToGameViewport(EFocusCause::SetDirectly);
 if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(PlayerTradeOverlay.ToSharedRef());
 PlayerTradeOverlay.Reset();PlayerTradePanel.Reset();PlayerTradeSignature.Empty();return true;
}
void UDAoCBridgeSubsystem::ApplyPlayerTrade(TSharedPtr<FJsonObject> State){
 PlayerTradeState=State;
 if(!ExchangeFlag(State,TEXT("visible"))){ClosePlayerTrade(false);PlayerTradeWindowToken.Empty();PlayerTradeMoney.Empty();return;}
 const FString Token=CS(State,TEXT("token"));
 if(Token!=PlayerTradeWindowToken){PlayerTradeWindowToken=Token;PlayerTradeMoney.Empty();auto Coins=CA(CO(State,TEXT("offer")),TEXT("own_money"));for(int32 I=0;I<5;++I)PlayerTradeMoney.Add(FString::FromInt(Coins.IsValidIndex(I)?int32(Coins[I]->AsNumber()):0));}
 RefreshPlayerTrade();
}
void UDAoCBridgeSubsystem::PlayerTradeRequest(const FString& Action,const FString& Token,int64 Revision,TSharedPtr<FJsonObject> Extra){
 if(!ExchangeFlag(PlayerTradeState,TEXT("visible"))||Token.IsEmpty()||Token!=CS(PlayerTradeState,TEXT("token")))return;
 if(Action!=TEXT("player_trade_cancel")&&ExchangeFlag(PlayerTradeState,TEXT("pending")))return;
 if(!Extra)Extra=MakeShared<FJsonObject>();
 Extra->SetStringField(TEXT("trade_token"),Token);Extra->SetNumberField(TEXT("inventory_revision"),Revision);
 if(Action==TEXT("player_trade_update")){
  if(!InventoryState||CN(InventoryState,TEXT("state_revision"),-2)!=Revision)return;
  TArray<TSharedPtr<FJsonValue>> Coins;for(const FString& Coin:PlayerTradeMoney){if(Coin.IsEmpty()||Coin.Len()>5)return;for(TCHAR C:Coin)if(C<TEXT('0')||C>TEXT('9'))return;const int32 Number=FCString::Atoi(*Coin);if(Number>65535)return;Coins.Add(MakeShared<FJsonValueNumber>(Number));}
  if(Coins.Num()!=5)return;Extra->SetArrayField(TEXT("money"),Coins);
  auto Tokens=MakeShared<FJsonObject>();for(auto V:CA(Extra,TEXT("slots"))){const int32 Slot=int32(V->AsNumber());if(Slot==0)continue;auto Item=InventoryItem(Slot);if(!Item)return;Tokens->SetStringField(FString::FromInt(Slot),CS(Item,TEXT("token")));}Extra->SetObjectField(TEXT("item_tokens"),Tokens);
 }
 Send(Action,Extra);
}
void UDAoCBridgeSubsystem::RefreshPlayerTrade(){
 if(!ExchangeFlag(PlayerTradeState,TEXT("visible"))||!GetWorld()||!GetWorld()->GetGameViewport())return;
 const FString Token=CS(PlayerTradeState,TEXT("token"));const int64 Revision=int64(CN(InventoryState,TEXT("state_revision"),-1));
 const FString Signature=Token+FString::Printf(TEXT("/%lld/%d"),Revision,ExchangeFlag(PlayerTradeState,TEXT("pending")));
 if(PlayerTradeOverlay&&Signature==PlayerTradeSignature)return;
 ClosePlayerTrade(false);PlayerTradeSignature=Signature;
 const bool Ready=!ExchangeFlag(PlayerTradeState,TEXT("pending"));auto Offer=CO(PlayerTradeState,TEXT("offer"));auto Slots=CA(Offer,TEXT("own_slots"));
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{384,256},SNew(SImage).Image(ClassicArt(TEXT("trade"))));
 auto Text=[&](FVector2D P,FVector2D Size,const FString& T,int32 Font=8){At(Canvas,P,Size,CT(T,Font));};
 auto Button=[&](FVector2D P,FVector2D Size,const FString& T,TFunction<void()> Fn,bool Enabled=true){auto Control=CB(CT(T,8,Gold),Fn);Control->SetEnabled(Enabled);At(Canvas,P,Size,Control);};
 Text({14,1},{156,13},TEXT("YOUR OFFER"),7);Text({204,1},{166,13},CS(Offer,TEXT("title")),7);
 for(int32 I=0;I<10;++I){
  const int32 Slot=Slots.IsValidIndex(I)?int32(Slots[I]->AsNumber()):0;auto Own=InventoryItem(Slot);auto Partners=CA(Offer,TEXT("partner_items"));TSharedPtr<FJsonObject> Partner;if(Partners.IsValidIndex(I)&&Partners[I]->Type==EJson::Object)Partner=Partners[I]->AsObject(); // Wire slot is the partner backpack slot, not a UI row.
  for(int32 Side=0;Side<2;++Side){auto Item=Side?Partner:Own;if(!Item)continue;const double X=Side?202.:12.,Y=16.+I*18.;auto Tile=SNew(SOverlay);Tile->AddSlot()[SNew(SImage).Image(ClassicIcon(int32(CN(Item,TEXT("icon"),-1))))];FString Label=CS(Item,TEXT("name"));const int32 Count=int32(CN(Item,TEXT("count"),1));if(Count>1)Label=FString::Printf(TEXT("%d "),Count)+Label;Tile->SetToolTipText(FText::FromString(Label));
   At(Canvas,{X,Y},{17,17},Tile);Text({X+20,Y},{143,17},Label,7);
   if(!Side)At(Canvas,{X,Y},{166,17},SNew(SBox).IsEnabled(Ready)[CB(SNew(SBox),[this,Token,Revision,Slots,I](){auto NewSlots=Slots;NewSlots[I]=MakeShared<FJsonValueNumber>(0);auto V=MakeShared<FJsonObject>();V->SetArrayField(TEXT("slots"),NewSlots);PlayerTradeRequest(TEXT("player_trade_update"),Token,Revision,V);})]);
  }
 }
 auto PartnerCoins=CA(Offer,TEXT("partner_money"));
 for(int32 I=0;I<5;++I){const double X=13.+I*32.;const FString Value=PlayerTradeMoney.IsValidIndex(I)?PlayerTradeMoney[I]:TEXT("0");
  At(Canvas,{X,215},{29,19},SNew(SEditableTextBox).Text(FText::FromString(Value)).Font(CF(6)).Padding(FMargin(1,0)).IsEnabled(Ready).OnTextChanged_Lambda([this,I](const FText& T){if(PlayerTradeMoney.IsValidIndex(I))PlayerTradeMoney[I]=T.ToString();}).OnTextCommitted_Lambda([this,Token,Revision,Slots](const FText&,ETextCommit::Type Type){if(Type!=ETextCommit::OnEnter)return;auto V=MakeShared<FJsonObject>();V->SetArrayField(TEXT("slots"),Slots);PlayerTradeRequest(TEXT("player_trade_update"),Token,Revision,V);}));
  Text({X+190,217},{30,17},PartnerCoins.IsValidIndex(I)?FString::FromInt(int32(PartnerCoins[I]->AsNumber())):TEXT("0"),7);
 }
 Button({174,237},{17,17},TEXT("OK"),[this,Token,Revision](){PlayerTradeRequest(TEXT("player_trade_accept"),Token,Revision);},Ready);
 Button({372,0},{14,13},TEXT("X"),[this,Token,Revision](){PlayerTradeRequest(TEXT("player_trade_cancel"),Token,Revision);});
 Text({12,197},{355,15},CS(PlayerTradeState,TEXT("feedback")),7);
 auto Drop=SNew(SClassicPlayerTradeDrop).Offer([this,Token,Revision,Slots](int32 Slot,const FString& ItemToken){if(CS(InventoryItem(Slot),TEXT("token"))!=ItemToken)return;auto NewSlots=Slots;for(auto V:NewSlots)if(int32(V->AsNumber())==Slot)return;for(int32 I=0;I<NewSlots.Num();++I)if(NewSlots[I]->AsNumber()==0){NewSlots[I]=MakeShared<FJsonValueNumber>(Slot);auto V=MakeShared<FJsonObject>();V->SetArrayField(TEXT("slots"),NewSlots);PlayerTradeRequest(TEXT("player_trade_update"),Token,Revision,V);return;}})[Canvas];
 PlayerTradePanel=Drop;
 PlayerTradeOverlay=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(384).HeightOverride(256)[Drop]]];
 GetWorld()->GetGameViewport()->AddViewportWidgetContent(PlayerTradeOverlay.ToSharedRef(),37);
}
