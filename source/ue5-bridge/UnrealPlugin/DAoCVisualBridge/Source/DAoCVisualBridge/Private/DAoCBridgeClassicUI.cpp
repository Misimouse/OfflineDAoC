#include "DAoCBridgeKeyConfiguration.h"
#include "HAL/FileManager.h"
#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeInterfaceSettings.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Texture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/SceneCaptureComponent2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/Crc.h"
#include "Framework/Application/SlateApplication.h"
#include "DragAndDrop/DecoratedDragDropOp.h"
#include "Widgets/SCanvas.h"
#include "Widgets/SToolTip.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"
#include "Widgets/Notifications/SProgressBar.h"

namespace {
FString CS(const TSharedPtr<FJsonObject>& O,const TCHAR* K,const FString& F=TEXT("")){FString V=F;if(O.IsValid())O->TryGetStringField(K,V);return V;}
double CN(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double F=0){double V=F;if(O.IsValid())O->TryGetNumberField(K,V);return V;}
TSharedPtr<FJsonObject> CO(const TSharedPtr<FJsonObject>& O,const TCHAR* K){const TSharedPtr<FJsonObject>* V=nullptr;return O.IsValid()&&O->TryGetObjectField(K,V)?*V:nullptr;}
TArray<TSharedPtr<FJsonValue>> CA(const TSharedPtr<FJsonObject>& O,const TCHAR* K){const TArray<TSharedPtr<FJsonValue>>* V=nullptr;return O.IsValid()&&O->TryGetArrayField(K,V)?*V:TArray<TSharedPtr<FJsonValue>>{};}
TSharedPtr<FJsonObject> HoverEntry(const TSharedPtr<FJsonObject>& State,const FString& Id){for(const TCHAR* Key:{TEXT("entries"),TEXT("effects")})for(const auto& Value:CA(State,Key))if(Value->Type==EJson::Object&&CS(Value->AsObject(),TEXT("id"))==Id)return Value->AsObject();return nullptr;}
FLinearColor Cream(.93f,.89f,.78f),Gold(1,.85f,.45f);
const FProgressBarStyle& ClassicBarStyle(){static const FProgressBarStyle Style=[](){FProgressBarStyle S;auto Back=*FCoreStyle::Get().GetBrush("WhiteBrush");Back.TintColor=FSlateColor(FLinearColor(.07f,.07f,.06f));S.SetBackgroundImage(Back);S.SetFillImage(*FCoreStyle::Get().GetBrush("WhiteBrush"));return S;}();return Style;}

FSlateFontInfo CF(int32 Size=8){return FSlateFontInfo(FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf")),Size);}
TSharedRef<STextBlock> CT(const FString& Text,int32 Size=8,FLinearColor Color=Cream){return SNew(STextBlock).Text(FText::FromString(Text.ToUpper())).Font(CF(Size)).ColorAndOpacity(Color).ShadowOffset(FVector2D(1,1)).ShadowColorAndOpacity(FLinearColor::Black).AutoWrapText(true);}
TSharedRef<SWidget> ClassicSymbol(const FString& Text,int32 Size){return SNew(STextBlock).Text(FText::FromString(Text)).Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"),Size)).ColorAndOpacity(Cream).Justification(ETextJustify::Center);}
void At(const TSharedRef<SCanvas>& C,FVector2D P,FVector2D Size,const TSharedRef<SWidget>& W){C->AddSlot().Position(P).Size(Size)[SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[W]];}
TSharedRef<SButton> CB(const TSharedRef<SWidget>& W,TFunction<void()> F){return SNew(SButton).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).ContentPadding(0).OnClicked_Lambda([F](){F();return FReply::Handled();})[W];}
struct FClassicDrag: FDecoratedDragDropOp{
    DRAG_DROP_OPERATOR_TYPE(FClassicDrag,FDecoratedDragDropOp)
    FSlateBrush IconBrush,BorderBrush;bool HasIcon=false,HasBorder=false,Dropped=false;
    TFunction<void(int32,const FString&,FVector2D)> WorldDrop;
    void SetLabel(const FText& Text){DefaultHoverText=Text;}
    void SetIcon(const FSlateBrush* Icon,const FSlateBrush* Border){HasIcon=Icon!=nullptr;HasBorder=Border!=nullptr;if(Icon)IconBrush=*Icon;if(Border)BorderBrush=*Border;}
    virtual TSharedPtr<SWidget> GetDefaultDecorator() const override {
        if(!HasIcon)return SNew(SBox).WidthOverride(128).MinDesiredHeight(40)[SNew(SBorder).Padding(4)[SNew(STextBlock).Text(DefaultHoverText.IsEmpty()?FText::FromString(TEXT("Action")):DefaultHoverText).Font(CF(10)).AutoWrapText(true)]];
        auto Layers=SNew(SOverlay);Layers->AddSlot()[SNew(SImage).Image(&IconBrush)];
        if(HasBorder)Layers->AddSlot()[SNew(SImage).Image(&BorderBrush)];
        return SNew(SBox).WidthOverride(48).HeightOverride(48)[Layers];
    }
    FString Id,Token,ItemToken,VaultToken,ExchangeToken;int64 ExchangeCatalog=-1;int32 Bar=-1,Bank=-1,Slot=-1,InventorySlot=-1;TFunction<void()> Clear;
    virtual void OnDrop(bool Handled,const FPointerEvent& E) override {if(Dropped)return;Dropped=true;if(!Handled&&WorldDrop&&InventorySlot>=0&&E.GetEffectingButton()==EKeys::LeftMouseButton)WorldDrop(InventorySlot,ItemToken,E.GetScreenSpacePosition());else if(!Handled&&Clear)Clear();FDecoratedDragDropOp::OnDrop(Handled,E);}
};
class SClassicAction:public SCompoundWidget{
public:
 SLATE_BEGIN_ARGS(SClassicAction):_Icon(nullptr),_Border(nullptr),_Bar(-1),_Bank(-1),_Slot(-1),_InventorySlot(-1){} SLATE_ARGUMENT(TSharedPtr<FJsonObject>,Entry) SLATE_ARGUMENT(const FSlateBrush*,Icon) SLATE_ARGUMENT(const FSlateBrush*,Border) SLATE_ARGUMENT(FSlateFontInfo,Font) SLATE_ARGUMENT(int32,Bar) SLATE_ARGUMENT(int32,Bank) SLATE_ARGUMENT(int32,Slot) SLATE_ARGUMENT(int32,InventorySlot) SLATE_ARGUMENT(FString,VaultToken) SLATE_ARGUMENT(TFunction<void(int32,const FString&,FVector2D)>,WorldDrop) SLATE_ARGUMENT(TFunction<void()>,Click) SLATE_ARGUMENT(TFunction<void()>,DoubleClick) SLATE_ARGUMENT(TFunction<void()>,Clear) SLATE_ARGUMENT(TFunction<void()>,Inspect) SLATE_ARGUMENT(TFunction<void()>,Hover) SLATE_ATTRIBUTE(FText,HoverText) SLATE_ARGUMENT(TFunction<void(TSharedRef<FClassicDrag>)>,Drop) SLATE_ATTRIBUTE(FText,Cooldown) SLATE_END_ARGS()
 void Construct(const FArguments& A){Entry=A._Entry;Icon=A._Icon;Border=A._Border;Bar=A._Bar;Bank=A._Bank;Slot=A._Slot;InventorySlot=A._InventorySlot;VaultToken=A._VaultToken;WorldDrop=A._WorldDrop;Click=A._Click;Double=A._DoubleClick;Clear=A._Clear;Inspect=A._Inspect;Hover=A._Hover;Drop=A._Drop;
  auto O=SNew(SOverlay);O->AddSlot()[SNew(SImage).Image(A._Icon)];if(A._Border)O->AddSlot()[SNew(SImage).Image(A._Border)];
  if(!A._Icon&&(Bar>=0||CS(Entry,TEXT("kind"))==TEXT("petcmd")||CS(Entry,TEXT("kind"))==TEXT("macro")))O->AddSlot()[SNew(STextBlock).Text(FText::FromString(CS(Entry,TEXT("kind"))==TEXT("petcmd")?CS(Entry,Bar>=0?TEXT("short"):TEXT("label")):CS(Entry,TEXT("name")).Left(14))).Font(A._Font).ColorAndOpacity(Cream).AutoWrapText(true).WrappingPolicy(ETextWrappingPolicy::AllowPerCharacterWrapping)];
  O->AddSlot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(STextBlock).Text(A._Cooldown).Font(CF(9)).ColorAndOpacity(Gold).ShadowOffset(FVector2D(1,1))];
  SetClipping(EWidgetClipping::ClipToBounds);ChildSlot[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0,0,0,.08f)).Padding(0)[O]];if(Hover)SetToolTip(SNew(SToolTip)[SNew(SBox).MaxDesiredWidth(480)[SNew(STextBlock).Text(A._HoverText).Font(CF(12)).ColorAndOpacity(Cream).AutoWrapText(true)]]);else SetToolTipText(FText::FromString(CS(Entry,TEXT("name"))));}
 virtual void OnMouseEnter(const FGeometry& G,const FPointerEvent& E)override{SCompoundWidget::OnMouseEnter(G,E);if(Hover)Hover();}
 virtual FReply OnMouseButtonDown(const FGeometry&,const FPointerEvent& E)override{if(E.GetEffectingButton()==EKeys::RightMouseButton){if(Inspect&&(!Clear||E.IsShiftDown()))Inspect();else if(Clear)Clear();return FReply::Handled();}if(E.GetEffectingButton()==EKeys::LeftMouseButton){Down=true;Dragged=false;return FReply::Handled().DetectDrag(SharedThis(this),EKeys::LeftMouseButton);}return FReply::Unhandled();}
 virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent& E)override{if(Down&&E.GetEffectingButton()==EKeys::LeftMouseButton){Down=false;if(!Dragged&&Click)Click();return FReply::Handled();}return FReply::Unhandled();}
 virtual FReply OnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent& E)override{if(E.GetEffectingButton()==EKeys::LeftMouseButton){Down=false;Dragged=false;if(Double)Double();return FReply::Handled();}return FReply::Unhandled();}
 virtual FReply OnDragDetected(const FGeometry&,const FPointerEvent&)override{if(!Entry.IsValid()||CS(Entry,TEXT("id" )).IsEmpty()||CS(Entry,TEXT("kind"))==TEXT("effect"))return FReply::Unhandled();Dragged=true;auto D=MakeShared<FClassicDrag>();D->Id=CS(Entry,TEXT("id"));D->Token=CS(Entry,TEXT("token"));D->ItemToken=CS(Entry,TEXT("item_token"));D->ExchangeToken=CS(Entry,TEXT("exchange_token"));D->ExchangeCatalog=int64(CN(Entry,TEXT("catalog_revision"),-1));D->Bar=Bar;D->Bank=Bank;D->Slot=Slot;D->InventorySlot=InventorySlot;D->VaultToken=VaultToken;D->WorldDrop=WorldDrop;D->Clear=Clear;D->SetLabel(FText::FromString(CS(Entry,TEXT("name"),CS(Entry,TEXT("label"),TEXT("Action")))));D->SetIcon(Icon,Border);D->Construct();return FReply::Handled().BeginDragDrop(D);}
 virtual FReply OnDrop(const FGeometry&,const FDragDropEvent& E)override{auto D=E.GetOperationAs<FClassicDrag>();if(D.IsValid()&&Drop){Drop(D.ToSharedRef());return FReply::Handled();}return FReply::Unhandled();}
private:const FSlateBrush* Icon=nullptr;const FSlateBrush* Border=nullptr;TSharedPtr<FJsonObject> Entry;FString VaultToken;int32 Bar=-1,Bank=-1,Slot=-1,InventorySlot=-1;bool Down=false,Dragged=false;TFunction<void(int32,const FString&,FVector2D)> WorldDrop;TFunction<void()> Click,Double,Clear,Inspect,Hover;TFunction<void(TSharedRef<FClassicDrag>)> Drop;
};
class SClassicHoverLabel:public SCompoundWidget{
public:
 SLATE_BEGIN_ARGS(SClassicHoverLabel){}SLATE_DEFAULT_SLOT(FArguments,Content)SLATE_ARGUMENT(TFunction<void()>,Hover)SLATE_ATTRIBUTE(FText,HoverText)SLATE_END_ARGS()
 void Construct(const FArguments& A){Hover=A._Hover;ChildSlot[A._Content.Widget];SetToolTip(SNew(SToolTip)[SNew(SBox).MaxDesiredWidth(480)[SNew(STextBlock).Text(A._HoverText).Font(CF(12)).ColorAndOpacity(Cream).AutoWrapText(true)]]);}
 virtual void OnMouseEnter(const FGeometry& G,const FPointerEvent& E)override{SCompoundWidget::OnMouseEnter(G,E);if(Hover)Hover();}
private:TFunction<void()> Hover;
};
class SClassicConcentrationIcon:public SCompoundWidget{
public:SLATE_BEGIN_ARGS(SClassicConcentrationIcon){}SLATE_ARGUMENT(const FSlateBrush*,Icon)SLATE_ARGUMENT(const FSlateBrush*,Border)SLATE_ARGUMENT(FString,Tip)SLATE_ARGUMENT(TFunction<void()>,Cancel)SLATE_END_ARGS()
 void Construct(const FArguments& A){Cancel=A._Cancel;auto Image=SNew(SOverlay);Image->AddSlot()[SNew(SImage).Image(A._Icon)];if(A._Border)Image->AddSlot()[SNew(SImage).Image(A._Border)];ChildSlot[Image];SetToolTipText(FText::FromString(A._Tip));}
 virtual FReply OnMouseButtonDown(const FGeometry&,const FPointerEvent& Event)override{if(Event.GetEffectingButton()==EKeys::RightMouseButton&&Event.IsShiftDown()&&Cancel)Cancel();return FReply::Handled();}
private:TFunction<void()> Cancel;
};
class SClassicShopDrop:public SCompoundWidget{
public:SLATE_BEGIN_ARGS(SClassicShopDrop){}SLATE_DEFAULT_SLOT(FArguments,Content) SLATE_ARGUMENT(TFunction<void(int32,const FString&)>,Sell) SLATE_END_ARGS()
 void Construct(const FArguments& A){Sell=A._Sell;ChildSlot[A._Content.Widget];}
 virtual FReply OnDrop(const FGeometry&,const FDragDropEvent& Event)override{auto D=Event.GetOperationAs<FClassicDrag>();if(D&&D->InventorySlot>=40&&D->InventorySlot<80&&!D->ItemToken.IsEmpty()&&Sell){Sell(D->InventorySlot,D->ItemToken);return FReply::Handled();}return FReply::Unhandled();}
private:TFunction<void(int32,const FString&)> Sell;
};
class SClassicMove:public SCompoundWidget{
public:SLATE_BEGIN_ARGS(SClassicMove){}SLATE_ARGUMENT(TSharedPtr<SWidget>,Content)SLATE_ARGUMENT(TFunction<void(FVector2D)>,Move)SLATE_ARGUMENT(TFunction<void()>,End)SLATE_END_ARGS()
 void Construct(const FArguments&A){Move=A._Move;End=A._End;ChildSlot[A._Content.ToSharedRef()];}
 virtual FReply OnMouseButtonDown(const FGeometry&G,const FPointerEvent&E)override{auto P=G.AbsoluteToLocal(E.GetScreenSpacePosition());if(E.GetEffectingButton()==EKeys::LeftMouseButton&&P.X<13&&P.Y<13){Moving=true;return FReply::Handled().CaptureMouse(SharedThis(this));}return FReply::Unhandled();}
 virtual FReply OnMouseMove(const FGeometry&G,const FPointerEvent&E)override{if(Moving&&HasMouseCapture()){Move(G.AbsoluteToLocal(E.GetScreenSpacePosition())-G.AbsoluteToLocal(E.GetLastScreenSpacePosition()));return FReply::Handled();}return FReply::Unhandled();}
 virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent&E)override{if(Moving){Moving=false;if(End)End();return FReply::Handled().ReleaseMouseCapture();}return FReply::Unhandled();}
private:bool Moving=false;TFunction<void(FVector2D)>Move;TFunction<void()>End;
};
}
bool VerifyDAoCClassicDragIcon(const FSlateBrush* Icon){
    if(!Icon)return false;auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),TEXT("srv:skill:drag-test"));Entry->SetStringField(TEXT("name"),TEXT("Minor Revigoration"));Entry->SetStringField(TEXT("token"),TEXT("unchanged-token"));
    auto Widget=SNew(SClassicAction).Entry(Entry).Icon(Icon).Font(CF());auto Reply=Widget->OnDragDetected(FGeometry(),FPointerEvent());
    auto Operation=StaticCastSharedPtr<FClassicDrag>(Reply.GetDragDropContent());if(!Operation||Operation->Token!=TEXT("unchanged-token")||Operation->IconBrush.GetResourceObject()!=Icon->GetResourceObject())return false;
    auto Decorator=Operation->GetDefaultDecorator();if(!Decorator)return false;Decorator->SlatePrepass(1);return Decorator->GetDesiredSize().Equals(FVector2D(48,48),.1);
}
bool VerifyDAoCClassicHoverWidget(){
 auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),TEXT("srv:40"));Entry->SetStringField(TEXT("name"),TEXT("Training sword"));Entry->SetStringField(TEXT("kind"),TEXT("item"));Entry->SetStringField(TEXT("token"),TEXT("entry"));
 int32 Hovers=0,Inspects=0,Clicks=0;FString Description=TEXT("Training sword");auto Tile=SNew(SClassicAction).Entry(Entry).Font(CF()).Hover([&](){++Hovers;}).HoverText_Lambda([&](){return FText::FromString(Description);}).Click([&](){++Clicks;}).Inspect([&](){++Inspects;});
 Tile->OnMouseEnter(FGeometry(),FPointerEvent());if(Hovers!=1||Clicks||Inspects||!Tile->GetToolTip().IsValid()||Tile->GetToolTip()->IsInteractive())return false;
 auto FindText=[](const TSharedRef<SWidget>& Root){TFunction<FString(const TSharedRef<SWidget>&)> Walk;Walk=[&](const TSharedRef<SWidget>& Widget)->FString{if(Widget->GetTypeAsString()==TEXT("STextBlock"))return StaticCastSharedRef<STextBlock>(Widget)->GetText().ToString();auto* Children=Widget->GetChildren();for(int32 I=0;I<Children->Num();++I){auto Found=Walk(Children->GetChildAt(I));if(!Found.IsEmpty())return Found;}return FString();};return Walk(Root);};
 auto Tip=Tile->GetToolTip()->AsWidget();if(FindText(Tip)!=Description)return false;Description+=TEXT("\nCondition: 81%\nOriginal description");if(FindText(Tip)!=Description)return false;
 auto Label=SNew(SClassicHoverLabel).Hover([&](){++Hovers;}).HoverText_Lambda([&](){return FText::FromString(Description);})[SNew(STextBlock).Text(FText::FromString(TEXT("Sword name")))];Label->OnMouseEnter(FGeometry(),FPointerEvent());
 return Hovers==2&&Clicks==0&&Inspects==0&&Label->GetToolTip().IsValid()&&FindText(Label->GetToolTip()->AsWidget())==Description;
}
bool VerifyDAoCItemHandoverDrag(){
    auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),TEXT("srv:40"));Entry->SetStringField(TEXT("token"),TEXT("entry"));Entry->SetStringField(TEXT("item_token"),TEXT("held-item"));
    int32 Calls=0;bool Correct=true;auto Make=[&](){auto Widget=SNew(SClassicAction).Entry(Entry).Font(CF()).InventorySlot(40).WorldDrop([&](int32 Slot,const FString& Token,FVector2D Point){++Calls;Correct&=Slot==40&&Token==TEXT("held-item")&&Point.Equals(FVector2D(32,64),.01);});return StaticCastSharedPtr<FClassicDrag>(Widget->OnDragDetected(FGeometry(),FPointerEvent()).GetDragDropContent());};
    auto Event=[](FKey Key){return FPointerEvent(0,FVector2D(32,64),FVector2D(32,64),TSet<FKey>(),Key,0,FModifierKeysState());};
    auto First=Make();if(!First)return false;First->OnDrop(false,Event(EKeys::LeftMouseButton));First->OnDrop(false,Event(EKeys::LeftMouseButton));
    auto Handled=Make();Handled->OnDrop(true,Event(EKeys::LeftMouseButton));auto Cancelled=Make();Cancelled->OnDrop(false,FPointerEvent());auto Right=Make();Right->OnDrop(false,Event(EKeys::RightMouseButton));
    return Correct&&Calls==1;
}
float UDAoCBridgeSubsystem::ClassicScale()const{return FBridgeInterfaceSettings::EffectiveScale(UIViewportSize(),InterfaceSettings?InterfaceSettings->Scale:1.f);}
const FSlateBrush* UDAoCBridgeSubsystem::ClassicArt(const FString& Name,FVector2D Min,FVector2D Max){
 const FString Key=Name+Min.ToString()+Max.ToString();if(auto* B=ClassicBrushes.Find(Key))return B->Get();
 UTexture2D* Tex=nullptr;if(auto* Existing=ClassicTextures.Find(Name))Tex=Existing->Get();else{Tex=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI")/(Name+TEXT(".png")));if(Tex){Tex->SRGB=true;Tex->Filter=TF_Bilinear;ClassicTextures.Add(Name,Tex);}}
 if(!Tex)return nullptr;auto B=MakeShared<FSlateBrush>();B->SetResourceObject(Tex);B->ImageSize=FVector2D(Tex->GetSizeX()/4.,Tex->GetSizeY()/4.);B->DrawAs=ESlateBrushDrawType::Image;B->SetUVRegion(FBox2D(Min,Max));ClassicBrushes.Add(Key,B);return &B.Get();
}
const FSlateBrush* UDAoCBridgeSubsystem::ClassicIcon(int32 Icon,bool Border){
 if(Icon<0)return nullptr;FString Sheet;
 if(Border)Sheet=TEXT("BRDR_0");else{static TSharedPtr<FJsonObject> Sheets;if(!Sheets.IsValid()){FString Text;FFileHelper::LoadFileToString(Text,*(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/icon_sheets.json")));FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Sheets);}if(Sheets.IsValid())Sheets->TryGetStringField(FString::FromInt(Icon/100*100),Sheet);}
 if(Sheet.IsEmpty())return nullptr;const int32 Cell=Border?Icon:Icon%100;const double Rows=Border?2.:10.;return ClassicArt(TEXT("icons/")+Sheet,FVector2D((Cell%10)/10.,(Cell/10)/Rows),FVector2D((Cell%10+1)/10.,(Cell/10+1)/Rows));
}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::ClassicEntry(const FString& Id)const{for(auto& V:CA(ClassicState,TEXT("entries")))if(V->Type==EJson::Object&&CS(V->AsObject(),TEXT("id"))==Id)return V->AsObject();return nullptr;}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::ClassicSlot(int32 Bar,int32 Slot)const{auto Bars=CA(ClassicState,TEXT("bars")),Banks=CA(ClassicState,TEXT("banks"));if(Bar<0||Bar>=Bars.Num()||Bar>=Banks.Num()||Slot<0||Slot>9)return nullptr;const auto& Pages=Bars[Bar]->AsArray();int32 K=int32(Banks[Bar]->AsNumber());if(!Pages.IsValidIndex(K))return nullptr;auto Page=Pages[K]->AsArray();return Page.IsValidIndex(Slot)&&Page[Slot]->Type==EJson::Object?Page[Slot]->AsObject():nullptr;}
void UDAoCBridgeSubsystem::ClassicUse(const FString& Id,const FString& Token){if(!bLocalAvailable||bExiting||(PlayerIsDead()&&CS(ClassicEntry(Id),TEXT("kind"))!=TEXT("macro")))return;auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("entry_id"),Id);V->SetStringField(TEXT("entry_token"),Token);Send(TEXT("ui_use"),V);}
void UDAoCBridgeSubsystem::ClassicAssign(int32 Bar,int32 Slot,const FString& Id,const FString& Token,int32 FromBar,int32 FromBank,int32 FromSlot){auto Banks=CA(ClassicState,TEXT("banks"));if(!Banks.IsValidIndex(Bar))return;auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("bar"),Bar);V->SetNumberField(TEXT("bank"),Banks[Bar]->AsNumber());V->SetNumberField(TEXT("slot"),Slot);V->SetStringField(TEXT("entry_id"),Id);V->SetStringField(TEXT("entry_token"),Token);V->SetNumberField(TEXT("from_bar"),FromBar);V->SetNumberField(TEXT("from_bank"),FromBank);V->SetNumberField(TEXT("from_slot"),FromSlot);Send(Id.IsEmpty()?TEXT("ui_clear"):TEXT("ui_assign"),V);}
void UDAoCBridgeSubsystem::SaveClassicLayout(){if(ClassicLayoutFile.IsEmpty())return;auto V=MakeShared<FJsonObject>();auto Extent=UIViewportSize()/ClassicScale();V->SetArrayField(TEXT("viewport_units"),{MakeShared<FJsonValueNumber>(Extent.X),MakeShared<FJsonValueNumber>(Extent.Y)});V->SetArrayField(TEXT("map_position"),{MakeShared<FJsonValueNumber>(ZoneMapPosition.X),MakeShared<FJsonValueNumber>(ZoneMapPosition.Y)});TArray<TSharedPtr<FJsonValue>> P;for(auto& Point:ClassicPositions)P.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(Point.X),MakeShared<FJsonValueNumber>(Point.Y)}));V->SetArrayField(TEXT("positions"),P);V->SetStringField(TEXT("tab"),ClassicTab);V->SetBoolField(TEXT("open"),bClassicOpen);V->SetBoolField(TEXT("mini_group"),bClassicMiniGroupOpen);V->SetArrayField(TEXT("journal_position"),{MakeShared<FJsonValueNumber>(ClassicJournalPosition.X),MakeShared<FJsonValueNumber>(ClassicJournalPosition.Y)});V->SetArrayField(TEXT("trainer_position"),{MakeShared<FJsonValueNumber>(ClassicTrainerPosition.X),MakeShared<FJsonValueNumber>(ClassicTrainerPosition.Y)});V->SetArrayField(TEXT("pet_position"),{MakeShared<FJsonValueNumber>(ClassicPetPosition.X),MakeShared<FJsonValueNumber>(ClassicPetPosition.Y)});V->SetArrayField(TEXT("vault_position"),{MakeShared<FJsonValueNumber>(ClassicVaultPosition.X),MakeShared<FJsonValueNumber>(ClassicVaultPosition.Y)});TArray<TSharedPtr<FJsonValue>> ChatP,ChatS,ChatT;for(int32 I=0;I<2;++I){ChatP.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(ChatPositions[I].X),MakeShared<FJsonValueNumber>(ChatPositions[I].Y)}));ChatS.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(ChatSizes[I].X),MakeShared<FJsonValueNumber>(ChatSizes[I].Y)}));TArray<TSharedPtr<FJsonValue>> Types;for(const auto& Type:ChatTypes[I])Types.Add(MakeShared<FJsonValueString>(Type));ChatT.Add(MakeShared<FJsonValueArray>(Types));}V->SetArrayField(TEXT("chat_positions"),ChatP);V->SetArrayField(TEXT("chat_sizes"),ChatS);V->SetArrayField(TEXT("chat_types"),ChatT);V->SetBoolField(TEXT("chat_combat_open"),bChatCombatOpen);V->SetArrayField(TEXT("concentration_position"),{MakeShared<FJsonValueNumber>(ClassicConcentrationPosition.X),MakeShared<FJsonValueNumber>(ClassicConcentrationPosition.Y)});TArray<TSharedPtr<FJsonValue>> O;for(bool Vertical:ClassicVertical)O.Add(MakeShared<FJsonValueBoolean>(Vertical));V->SetArrayField(TEXT("vertical"),O);FString Text;FJsonSerializer::Serialize(V,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*ClassicLayoutFile);}
void UDAoCBridgeSubsystem::ApplyClassicUI(TSharedPtr<FJsonObject> State){
 if(!State.IsValid()||CA(State,TEXT("bars" )).Num()!=3||CA(State,TEXT("banks")).Num()!=3)return;
 const FString Who=CS(State,TEXT("character"));const bool NewCharacter=ClassicLayoutCharacter!=Who;if(NewCharacter){RemoveClassicUI();ClassicLayoutCharacter=Who;ClassicLayoutFile=FPaths::ProjectSavedDir()/((FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest"))||FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeSpellVisualTest")))?FString::Printf(TEXT("DAoCClassicUI_PREVIEW_%08x.json"),FCrc::StrCrc32(*Who)):FString::Printf(TEXT("DAoCClassicUI_%08x.json"),FCrc::StrCrc32(*Who)));bClassicPositioned=false;bClassicMiniGroupOpen=false;bClassicJournalOpen=false;ClassicQuestIndex=-1;ClassicQuestToken.Empty();ClassicJournalPosition=FVector2D(125,130);bClassicTrainerOpen=false;ClassicTrainerSerial=-1;ClassicTrainingIndex=-1;ClassicTrainingKind.Empty();ClassicTrainingToken.Empty();ClassicTrainerPosition=FVector2D(260,70);ClassicConcentrationPage=0;ClassicVaultPage=0;ClassicVaultSerial=-1;ClassicVaultPosition=FVector2D(200,140);ClassicRevision=-1;}
 ClassicState=State;ClassicReceivedAt=FPlatformTime::Seconds();const int64 Revision=int64(CN(State,TEXT("revision"),-1));
 auto* V=GetWorld()->GetGameViewport();if(!V)return;
 if(!bClassicPositioned){EnsureChatLayout();FVector2D S;S=UIViewportSize();S/=ClassicScale();ClassicPositions[0]=FVector2D(S.X-192,0);ClassicPositions[1]=FVector2D(S.X*.5-186,S.Y-80);ClassicPositions[2]=FVector2D(S.X*.5-186,S.Y-40);ClassicPositions[3]=FVector2D(0,100);ClassicPositions[4]=FVector2D(40,150);ClassicVaultPosition=FVector2D(FMath::Clamp(S.X*.5-230./ClassicScale()-236.,44.,200.),140.);const double AuxReserve=FMath::Max(320.,double(ChatReservedHeight())+16.)/ClassicScale();ClassicPetPosition=FVector2D(S.X-330,S.Y-AuxReserve-198);ClassicConcentrationPosition=FVector2D(S.X-468,S.Y-AuxReserve-198);bClassicPositioned=true;
  FString Text;TSharedPtr<FJsonObject> Saved;if(FFileHelper::LoadFileToString(Text,*ClassicLayoutFile)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Saved)){auto P=CA(Saved,TEXT("positions"));if(P.Num()==4||P.Num()==5)for(int32 I=0;I<P.Num();++I){const auto& XY=P[I]->AsArray();if(XY.Num()==2&&FMath::IsFinite(XY[0]->AsNumber())&&FMath::IsFinite(XY[1]->AsNumber()))ClassicPositions[I]=FVector2D(XY[0]->AsNumber(),XY[1]->AsNumber());}const auto O=CA(Saved,TEXT("vertical"));if(O.Num()==3)for(int32 I=0;I<3;++I)ClassicVertical[I]=O[I]->AsBool();ClassicTab=CS(Saved,TEXT("tab"),TEXT("character"));bool Open=true;Saved->TryGetBoolField(TEXT("open"),Open);bClassicOpen=Open;Saved->TryGetBoolField(TEXT("mini_group"),bClassicMiniGroupOpen);auto JP=CA(Saved,TEXT("journal_position"));if(JP.Num()==2&&JP[0]->Type==EJson::Number&&JP[1]->Type==EJson::Number&&FMath::IsFinite(JP[0]->AsNumber())&&FMath::IsFinite(JP[1]->AsNumber()))ClassicJournalPosition=FVector2D(JP[0]->AsNumber(),JP[1]->AsNumber());auto TP=CA(Saved,TEXT("trainer_position"));if(TP.Num()==2&&TP[0]->Type==EJson::Number&&TP[1]->Type==EJson::Number&&FMath::IsFinite(TP[0]->AsNumber())&&FMath::IsFinite(TP[1]->AsNumber()))ClassicTrainerPosition=FVector2D(TP[0]->AsNumber(),TP[1]->AsNumber());auto PP=CA(Saved,TEXT("pet_position"));if(PP.Num()==2&&PP[0]->Type==EJson::Number&&PP[1]->Type==EJson::Number&&FMath::IsFinite(PP[0]->AsNumber())&&FMath::IsFinite(PP[1]->AsNumber()))ClassicPetPosition=FVector2D(PP[0]->AsNumber(),PP[1]->AsNumber());auto VP=CA(Saved,TEXT("vault_position"));if(VP.Num()==2&&VP[0]->Type==EJson::Number&&VP[1]->Type==EJson::Number&&FMath::IsFinite(VP[0]->AsNumber())&&FMath::IsFinite(VP[1]->AsNumber()))ClassicVaultPosition=FVector2D(VP[0]->AsNumber(),VP[1]->AsNumber());auto CP=CA(Saved,TEXT("concentration_position"));if(CP.Num()==2&&CP[0]->Type==EJson::Number&&CP[1]->Type==EJson::Number&&FMath::IsFinite(CP[0]->AsNumber())&&FMath::IsFinite(CP[1]->AsNumber()))ClassicConcentrationPosition=FVector2D(CP[0]->AsNumber(),CP[1]->AsNumber());
  auto ChatP=CA(Saved,TEXT("chat_positions")),ChatS=CA(Saved,TEXT("chat_sizes")),ChatT=CA(Saved,TEXT("chat_types"));TSet<FString> Allowed;for(int32 I=0;I<2;++I)for(const auto& Type:ChatTypes[I])Allowed.Add(Type);
  for(int32 I=0;I<2;++I){for(int32 Which=0;Which<2;++Which){const auto& Array=Which==0?ChatP:ChatS;if(Array.Num()!=2||Array[I]->Type!=EJson::Array)continue;const auto& XY=Array[I]->AsArray();if(XY.Num()!=2||XY[0]->Type!=EJson::Number||XY[1]->Type!=EJson::Number||!FMath::IsFinite(XY[0]->AsNumber())||!FMath::IsFinite(XY[1]->AsNumber()))continue;if(Which==0)ChatPositions[I]=FVector2D(XY[0]->AsNumber(),XY[1]->AsNumber());else ChatSizes[I]=FVector2D(FMath::Clamp(XY[0]->AsNumber(),160.,900.),FMath::Clamp(XY[1]->AsNumber(),I==0?70.:50.,480.));}if(ChatT.Num()==2&&ChatT[I]->Type==EJson::Array&&ChatT[I]->AsArray().Num()<=21){ChatTypes[I].Empty();for(const auto& Type:ChatT[I]->AsArray())if(Type->Type==EJson::String&&Allowed.Contains(Type->AsString()))ChatTypes[I].AddUnique(Type->AsString());}}
  Saved->TryGetBoolField(TEXT("chat_combat_open"),bChatCombatOpen);
  auto Extent=CA(Saved,TEXT("viewport_units"));if(Extent.Num()==2&&Extent[0]->Type==EJson::Number&&Extent[1]->Type==EJson::Number&&FMath::IsFinite(Extent[0]->AsNumber())&&FMath::IsFinite(Extent[1]->AsNumber())&&Extent[0]->AsNumber()>0&&Extent[1]->AsNumber()>0)UILayoutUnits=FVector2D(Extent[0]->AsNumber(),Extent[1]->AsNumber());
  auto MP=CA(Saved,TEXT("map_position"));if(MP.Num()==2&&MP[0]->Type==EJson::Number&&MP[1]->Type==EJson::Number&&FMath::IsFinite(MP[0]->AsNumber())&&FMath::IsFinite(MP[1]->AsNumber()))ZoneMapPosition=FVector2D(MP[0]->AsNumber(),MP[1]->AsNumber());}
  UpdateUILayout();

 }
 if(!ClassicOverlay.IsValid()){
  auto Canvas=SNew(SCanvas);Canvas->AddSlot().Position_Lambda([this](){FVector2D S;S=UIViewportSize();S/=ClassicScale();return FVector2D(FMath::Clamp(ClassicPositions[0].X,0.,FMath::Max(0.,S.X-192)),FMath::Clamp(ClassicPositions[0].Y,0.,FMath::Max(0.,S.Y-448)));}).Size(FVector2D(192,448))[SAssignNew(ClassicPanelBox,SBox)];
  for(int32 B=0;B<3;++B)Canvas->AddSlot().Position_Lambda([this,B](){FVector2D S;S=UIViewportSize();S/=ClassicScale();FVector2D Size=ClassicVertical[B]?FVector2D(33,372):FVector2D(372,33);return FVector2D(FMath::Clamp(ClassicPositions[B+1].X,0.,FMath::Max(0.,S.X-Size.X)),FMath::Clamp(ClassicPositions[B+1].Y,0.,FMath::Max(0.,S.Y-Size.Y)));}).Size_Lambda([this,B](){return ClassicVertical[B]?FVector2D(33,372):FVector2D(372,33);})[SAssignNew(ClassicBarBoxes[B],SBox)];
  Canvas->AddSlot().Position(FVector2D(10,4)).Size_Lambda([this](){FVector2D S;S=UIViewportSize();return FVector2D(FMath::Max(100.,S.X/ClassicScale()-215),132);})[SAssignNew(ClassicEffectsBox,SBox)];
  Canvas->AddSlot().Position_Lambda([this](){FVector2D S;S=UIViewportSize();S/=ClassicScale();return FVector2D(FMath::Max(0.,S.X*.5-130),FMath::Max(0.,S.Y-135));}).Size(FVector2D(260,42))[SAssignNew(ClassicCastBox,SBox)];
  Canvas->AddSlot().Position_Lambda([this](){FVector2D S;S=UIViewportSize();S/=ClassicScale();return FVector2D(FMath::Clamp(ClassicPositions[4].X,0.,FMath::Max(0.,S.X-192)),FMath::Clamp(ClassicPositions[4].Y,0.,FMath::Max(0.,S.Y-315)));}).Size_Lambda([this](){return FVector2D(192,FMath::Max(70,24+CA(ClassicState,TEXT("group")).Num()*35));})[SAssignNew(ClassicMiniGroupBox,SBox)];
  Canvas->AddSlot().Position_Lambda([this](){FVector2D Size;Size=UIViewportSize();Size/=ClassicScale();return FVector2D(FMath::Clamp(ClassicPetPosition.X,0.,FMath::Max(0.,Size.X-128)),FMath::Clamp(ClassicPetPosition.Y,0.,FMath::Max(0.,Size.Y-186)));}).Size(FVector2D(128,186))[SAssignNew(ClassicPetBox,SBox)];
  Canvas->AddSlot().Position_Lambda([this](){FVector2D Size;Size=UIViewportSize();Size/=ClassicScale();return FVector2D(FMath::Clamp(ClassicConcentrationPosition.X,0.,FMath::Max(0.,Size.X-128)),FMath::Clamp(ClassicConcentrationPosition.Y,0.,FMath::Max(0.,Size.Y-136)));}).Size(FVector2D(128,136))[SAssignNew(ClassicConcentrationBox,SBox)];
  ClassicOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Canvas];V->AddViewportWidgetContent(ClassicOverlay.ToSharedRef(),28);
 }
 if(Revision!=ClassicRevision){ClassicRevision=Revision;RefreshClassicPanel();RefreshClassicBars();RefreshClassicEffects();RefreshClassicCasting();RefreshClassicMiniGroup();RefreshClassicJournal();RefreshClassicTrainer();RefreshClassicPet();RefreshClassicConcentration();RefreshClassicVault();RefreshClassicDetail();}
}
void UDAoCBridgeSubsystem::SetClassicTab(const FString& Tab){if(Tab!=TEXT("character")&&Tab!=TEXT("inventory")&&Tab!=TEXT("skills")&&Tab!=TEXT("combat")&&Tab!=TEXT("magic")&&Tab!=TEXT("group"))return;ClassicTab=Tab;bClassicOpen=true;bInventoryMoving=false;RemoveInventoryUI();RefreshClassicPanel();SaveClassicLayout();}
bool UDAoCBridgeSubsystem::CloseClassicPanel(){
 if(CloseEmblemPicker())return true;if(GuildConfirm){GuildConfirm.Reset();GuildSignature.Empty();RefreshGuild();return true;}if(CloseGuild())return true;if(CloseExchange())return true;if(ClassicMerchantOverlay.IsValid()){CloseClassicMerchant();return true;}if(bZoneMapOpen){CloseZoneMap();return true;}if(CloseGroupConfirmation())return true;if(CloseClassicDetail())return true;if(CloseClassicVault())return true;if(CloseClassicTrainer())return true;if(CloseClassicJournal())return true;if(!ClassicState.IsValid()||!bClassicOpen)return false;if(bInventoryMoving){bInventoryMoving=false;RefreshClassicPanel();return true;}bClassicOpen=false;RefreshClassicPanel();SaveClassicLayout();return true;}
bool UDAoCBridgeSubsystem::ClassicUIHovered()const{if(EmblemPickerPanel.IsValid()&&EmblemPickerPanel->IsHovered())return true;if(GuildPanel.IsValid()&&GuildPanel->IsHovered())return true;if(ExchangePanel.IsValid()&&ExchangePanel->IsHovered())return true;if(ClassicMerchantPanel.IsValid()&&ClassicMerchantPanel->IsHovered())return true;if(ZoneMapPanel.IsValid()&&ZoneMapPanel->IsHovered())return true;if(ChatHovered())return true;if(ClassicVaultPanel.IsValid()&&ClassicVaultPanel->IsHovered())return true;if(ClassicConcentrationBox.IsValid()&&ClassicConcentrationBox->IsHovered())return true;if(ClassicPetBox.IsValid()&&ClassicPetBox->IsHovered())return true;if(ClassicTrainerPanel.IsValid()&&ClassicTrainerPanel->IsHovered())return true;if(ClassicJournalPanel.IsValid()&&ClassicJournalPanel->IsHovered())return true;if(ClassicGroupConfirmPanel.IsValid()&&ClassicGroupConfirmPanel->IsHovered())return true;if(bClassicMiniGroupOpen&&ClassicMiniGroupBox.IsValid()&&ClassicMiniGroupBox->IsHovered())return true;if(ClassicEffectsBox.IsValid()&&ClassicEffectsBox->IsHovered())return true;if(ClassicDetailPanel.IsValid()&&ClassicDetailPanel->IsHovered())return true;if(bClassicOpen&&ClassicPanelBox.IsValid()&&ClassicPanelBox->IsHovered())return true;for(auto& B:ClassicBarBoxes)if(B.IsValid()&&B->IsHovered())return true;return false;}
void UDAoCBridgeSubsystem::RefreshClassicPanel(){
 if(!ClassicPanelBox.IsValid())return;ClassicPanelBox->SetVisibility(bClassicOpen?EVisibility::Visible:EVisibility::Collapsed);if(!bClassicOpen)return;
 auto Canvas=SNew(SCanvas);const FString Skin=ClassicTab==TEXT("inventory")?TEXT("old_pperdoll"):ClassicTab==TEXT("skills")?TEXT("skillsheet"):ClassicTab==TEXT("magic")?TEXT("magicsheet"):ClassicTab==TEXT("combat")?TEXT("combstylesheet"):ClassicTab==TEXT("group")?TEXT("group"):TEXT("charsheet");
 At(Canvas,FVector2D::ZeroVector,FVector2D(192,448),SNew(SImage).Image(ClassicArt(Skin)));
 At(Canvas,FVector2D::ZeroVector,FVector2D(192,32),SNew(SImage).Image(ClassicArt(TEXT("control"),FVector2D(0,0),FVector2D(1,.25))));
 const TCHAR* Tabs[]={TEXT("character"),TEXT("inventory"),TEXT("skills"),TEXT("combat"),TEXT("magic"),TEXT("group")};const TCHAR* Titles[]={TEXT("CHARACTER"),TEXT("INVENTORY"),TEXT("ABILITIES"),TEXT("COMBAT"),TEXT("SPELLS"),TEXT("GROUP")};const int32 TX[]={13,41,70,98,126,154};
 for(int32 I=0;I<6;++I){FString T=Tabs[I];const bool Active=ClassicTab==T;auto Image=SNew(SImage).Image(ClassicArt(TEXT("control"),FVector2D(TX[I]/192.,Active?.7734375:.0234375),FVector2D((TX[I]+25)/192.,Active?.9609375:.2109375)));auto Button=CB(Image,[this,T](){SetClassicTab(T);});Button->SetToolTipText(FText::FromString(Titles[I]));At(Canvas,FVector2D(TX[I],3),FVector2D(25,24),Button);}
 At(Canvas,FVector2D(178,0),FVector2D(13,12),CB(CT(TEXT("\u00d7"),9),[this](){CloseClassicPanel();}));
 auto Text=[&](FVector2D P,FVector2D Size,const FString& V,FLinearColor C=Cream){At(Canvas,P,Size,CT(V,8,C));};
 auto Info=CO(ClassicState,TEXT("info")),Points=CO(ClassicState,TEXT("points")),Weapons=CO(ClassicState,TEXT("weapon_stats"));
 if(ClassicTab==TEXT("character")){
  Text({22,47},{24,14},Info.IsValid()?FString::FromInt(int32(CN(Info,TEXT("level")))):TEXT("\u2014"));Text({107,47},{80,14},Points.IsValid()?FString::Printf(TEXT("%.0f"),CN(Points,TEXT("realm_points"))):TEXT("\u2014"));
  const TCHAR* Names[]={TEXT("race_name"),TEXT("base_class"),TEXT("profession"),TEXT("title")};for(int32 I=0;I<4;++I)Text({64,64.+I*13},{122,12},(CS(Info,Names[I],TEXT("\u2014")).Equals(TEXT("None"),ESearchCase::IgnoreCase)?TEXT("\u2014"):CS(Info,Names[I],TEXT("\u2014"))));
  Text({55,117},{31,15},Weapons.IsValid()&&Weapons->HasField(TEXT("weapon_skill"))?FString::Printf(TEXT("%.0f"),CN(Weapons,TEXT("weapon_skill"))):TEXT("\u2014"));Text({156,117},{31,15},FString::Printf(TEXT("%.0f"),CN(CO(PlayerState,TEXT("vitals")),TEXT("max_health"))));Text({55,135},{31,14},Weapons.IsValid()&&Weapons->HasField(TEXT("weapon_damage"))?FString::Printf(TEXT("%.1f"),CN(Weapons,TEXT("weapon_damage"))):TEXT("\u2014"));Text({156,135},{31,14},Weapons.IsValid()&&Weapons->HasField(TEXT("armor_factor"))?FString::Printf(TEXT("%.0f"),CN(Weapons,TEXT("armor_factor"))):TEXT("\u2014"));
  auto Stats=CA(ClassicState,TEXT("stats")),Buffs=CA(ClassicState,TEXT("stat_buffs"));int32 Order[]={0,1,2,3,4,6,5,7};for(int32 I=0;I<8;++I){int32 Index=Order[I];double Buff=Buffs.IsValidIndex(Index)?Buffs[Index]->AsNumber():0;FLinearColor Color=Buff<0||(Index==1&&CN(ClassicState,TEXT("con_lost"))>0)?FLinearColor(1,.3,.25):Buff>0?FLinearColor(.35,1,.35):Cream;Text({I<4?5.:95.,158.+(I%4)*18.2},{25,16},Stats.IsValidIndex(Index)?FString::Printf(TEXT("%.0f"),Stats[Index]->AsNumber()):TEXT("\u2014"),Color);}
  FString Extra=FString::Printf(TEXT("%s\n%s\nSPECIALIZATION POINTS: %.0f\nREALM SKILL POINTS: %.0f\nEXPERIENCE: %.0f\n"),*CS(ClassicState,TEXT("character")),*CS(Info,TEXT("class_name")),CN(Points,TEXT("spec_points")),CN(Info,TEXT("realm_spec_points")),CN(Points,TEXT("xp")));const FString Guild=CS(Info,TEXT("guild"));if(!Guild.IsEmpty()&&Guild!=TEXT("None"))Extra+=TEXT("GUILD: ")+Guild+TEXT("\n");if(Info.IsValid()&&Info->HasField(TEXT("realm_level")))Extra+=FString::Printf(TEXT("REALM RANK: %dL%d %s\n"),int32(CN(Info,TEXT("realm_level")))/10+1,int32(CN(Info,TEXT("realm_level")))%10,*CS(Info,TEXT("realm_title")));Extra+=TEXT("RESISTS\n");const TCHAR* RNames[]={TEXT("CRUSH"),TEXT("SLASH"),TEXT("THRUST"),TEXT("HEAT"),TEXT("COLD"),TEXT("MATTER"),TEXT("BODY"),TEXT("SPIRIT"),TEXT("ENERGY")};auto Res=CA(ClassicState,TEXT("resists"));for(int32 I=0;I<9&&I<Res.Num();++I)Extra+=FString::Printf(TEXT("%s %.0f%%  "),RNames[I],Res[I]->AsNumber());At(Canvas,{10,258},{162,148},SNew(SScrollBox)+SScrollBox::Slot()[CT(Extra)]);
 }else if(ClassicTab==TEXT("inventory")){
  At(Canvas,{62,34},{70,18},SNew(SImage).Image(ClassicArt(TEXT("old_pperdoll"),FVector2D(62./192,56./448),FVector2D(132./192,74./448))));
  At(Canvas,{72,36},{15,15},SNew(SImage).Image(ClassicArt(TEXT("old_pperdoll"),FVector2D(72./192,36./448),FVector2D(87./192,51./448))));
  const int32 Slots[]={25,21,29,26,28,22,24,32,35,36,33,34,27,23,10,11,12,13,37};const FVector2D Pos[]={{7,36},{155,36},{41,36},{137,36},{7,75},{155,75},{7,116},{171,116},{7,143},{171,143},{7,170},{171,170},{7,196},{155,196},{14,234},{58,234},{102,234},{146,234},{72,36}};
  auto Item=[&](int32 Slot,FVector2D P,FVector2D Size){auto It=InventoryItem(Slot);auto E=ClassicEntry(FString::Printf(TEXT("srv:%d"),Slot));auto Click=[this,Slot](){ClassicVaultSlotClicked(Slot);};auto Double=[this,Slot](){ActivateClassicInventorySlot(Slot);};auto Drop=[this,Slot](TSharedRef<FClassicDrag>D){if(!D->ExchangeToken.IsEmpty()){if(Slot>=40&&Slot<80)ExchangeDropToBackpack(D->Id,D->Token,D->ExchangeToken,D->ExchangeCatalog);return;}if(D->InventorySlot>=0&&D->InventorySlot!=Slot&&!D->ItemToken.IsEmpty()&&CS(InventoryItem(D->InventorySlot),TEXT("token"))==D->ItemToken&&((D->InventorySlot<110&&Slot<110)||D->VaultToken==CS(CO(InventoryState,TEXT("vault")),TEXT("token"))))SendItemAction(TEXT("inventory_move"),D->InventorySlot,Slot);};
   auto Tile=SNew(SClassicAction).Entry(E).Icon(ClassicIcon(int32(CN(It,TEXT("icon"),-1)))).Border(nullptr).Font(CF(6)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(Slot).VaultToken(CS(CO(InventoryState,TEXT("vault")),TEXT("token"))).WorldDrop([this](int32 From,const FString& Token,FVector2D Point){GiveInventoryItemAtCursor(From,Token,Point);}).Inspect([this,E](){if(E.IsValid())ClassicInspect(CS(E,TEXT("id")),CS(E,TEXT("token")));}).Hover([this,E](){if(E.IsValid())ClassicHover(CS(E,TEXT("id")),CS(E,TEXT("token")));}).HoverText_Lambda([this,E](){return ClassicHoverText(CS(E,TEXT("id")),CS(E,TEXT("token")));}).Click(Click).DoubleClick(Double).Drop(Drop);At(Canvas,P,Size,Tile);};
  for(int32 I=0;I<19;++I)Item(Slots[I],Pos[I],FVector2D((I==0||I==1||I==4||I==5||I>=12&&I<=17)?31:15,(I==0||I==1||I==4||I==5||I>=12&&I<=17)?31:15));
  if(ClassicDollTarget){if(!ClassicDollBrush){auto B=MakeShared<FSlateBrush>();B->SetResourceObject(ClassicDollTarget);B->ImageSize=FVector2D(108,156);B->DrawAs=ESlateBrushDrawType::Image;ClassicDollBrush=&B.Get();ClassicBrushes.Add(TEXT("__doll"),B);}At(Canvas,{42,54},{108,156},SNew(SImage).Image(ClassicDollBrush));}
  At(Canvas,{43,195},{16,16},CB(CT(TEXT("<"),10),[this](){ClassicDollYaw-=30;ClassicCapturedAt=0;}));At(Canvas,{131,195},{16,16},CB(CT(TEXT(">"),10),[this](){ClassicDollYaw+=30;ClassicCapturedAt=0;}));
  Text({42,214},{80,13},FString::Printf(TEXT("%.0f / %.0f"),CN(InventoryState,TEXT("weight_now"),-1),CN(InventoryState,TEXT("weight_max"),-1)));
  for(int32 I=0;I<8;++I){int32 Slot=40+InventoryBag*8+I;auto It=InventoryItem(Slot);Item(Slot,{10,277.75+I*16.86},{15,15});auto Entry=ClassicEntry(FString::Printf(TEXT("srv:%d"),Slot));At(Canvas,{28,277.75+I*16.86},{138,16},MakeClassicHoverLabel(CT(It.IsValid()?FString::Printf(TEXT("%s %s"),*CS(It,TEXT("name")),CN(It,TEXT("count"))>1?*FString::Printf(TEXT("x%.0f"),CN(It,TEXT("count"))):TEXT("")):TEXT("")),CS(Entry,TEXT("id")),CS(Entry,TEXT("token"))));}
  const double Y[]={287,313,339,364.5,389.5};for(int32 I=0;I<5;++I)At(Canvas,{172,Y[I]},{15,15},CB(CT(FString::FromInt(I+1),8,I==InventoryBag?Gold:Cream),[this,I](){InventoryBag=I;RefreshClassicPanel();}));
  auto Money=CO(InventoryState,TEXT("money"));const TCHAR* Coins[]={TEXT("mithril"),TEXT("platinum"),TEXT("gold"),TEXT("silver"),TEXT("copper")};for(int32 I=0;I<5;++I)Text({15.+I*39,433},{28,11},FString::Printf(TEXT("%.0f"),CN(Money,Coins[I])));
  auto Selected=InventoryItem(SelectedItemSlot);if(Selected.IsValid()){Text({8,400},{104,14},CS(Selected,TEXT("name")),Gold);if(SelectedItemSlot<80)At(Canvas,{114,400},{70,14},CB(CT(SelectedItemSlot>=40?TEXT("EQUIP"):TEXT("UNEQUIP"),7),[this](){ActivateClassicInventorySlot(SelectedItemSlot);}));}
 }else if(ClassicTab==TEXT("group")){
  At(Canvas,{0,35},{192,304},MakeClassicGroupRows(false));auto Members=CA(ClassicState,TEXT("group"));auto Party=CO(ClassicState,TEXT("party"));TSharedPtr<FJsonObject> Selected;const int32 Oid=int32(CN(ClassicState,TEXT("group_selected_oid")));for(const auto& V:Members)if(int32(CN(V->AsObject(),TEXT("oid")))==Oid)Selected=V->AsObject();bool Pending=false;if(Party.IsValid())Party->TryGetBoolField(TEXT("pending"),Pending);bool Me=false;if(Selected.IsValid())Selected->TryGetBoolField(TEXT("me"),Me);
  At(Canvas,{7,352},{56,15},SNew(SBox).IsEnabled(!Pending)[CB(CT(TEXT("INVITE"),7),[this](){SendGroupAction(TEXT("group_invite"));})]);
  At(Canvas,{67,352},{56,15},SNew(SBox).IsEnabled(!Pending&&Selected.IsValid()&&!Me)[CB(CT(TEXT("REMOVE"),7),[this,Selected](){ShowGroupConfirmation(TEXT("group_remove"),Selected);})]);
  At(Canvas,{127,352},{56,15},SNew(SBox).IsEnabled(!Pending&&!Members.IsEmpty())[CB(CT(TEXT("LEAVE"),7),[this](){ShowGroupConfirmation(TEXT("group_leave"));})]);
  At(Canvas,{37,375},{118,16},CB(CT(TEXT("MINI GROUP"),7),[this](){bClassicMiniGroupOpen=!bClassicMiniGroupOpen;RefreshClassicMiniGroup();SaveClassicLayout();}));
  Text({8,395},{176,34},CS(Party,TEXT("feedback")),Gold);

 }else{
  auto List=SNew(SVerticalBox);auto Rows=CA(ClassicState,TEXT("entries"));
  if(ClassicTab==TEXT("skills")){auto Specs=SNew(SVerticalBox);for(auto& V:CA(ClassicState,TEXT("specs"))){auto E=V->AsObject();Specs->AddSlot().AutoHeight()[CT(FString::Printf(TEXT("%s    %.0f + %.0f"),*CS(E,TEXT("name")),CN(E,TEXT("level")),CN(E,TEXT("bonus"))))];}Specs->AddSlot().AutoHeight()[CT(FString::Printf(TEXT("POINTS: %.0f"),CN(Points,TEXT("spec_points"))),8,Gold)];At(Canvas,{10,57},{162,97},SNew(SScrollBox)+SScrollBox::Slot()[Specs]);}
  FString LastLine;int32 Count=0;for(auto& V:Rows){auto E=V->AsObject();FString Kind=CS(E,TEXT("kind"));if((ClassicTab==TEXT("skills")&&Kind!=TEXT("ability")&&Kind!=TEXT("macro"))||(ClassicTab==TEXT("magic")&&Kind!=TEXT("spell")&&!(Kind==TEXT("style")&&CS(E,TEXT("id")).StartsWith(TEXT("srv:spell:"))))||(ClassicTab==TEXT("combat")&&(Kind!=TEXT("style")||!CS(E,TEXT("id")).StartsWith(TEXT("srv:skill:")))))continue;
   const FString Id=CS(E,TEXT("id")),Token=CS(E,TEXT("token")),Line=CS(E,TEXT("line"));if(ClassicTab==TEXT("magic")&&!Line.IsEmpty()&&LastLine!=Line){List->AddSlot().AutoHeight().Padding(0,4)[CT(Line,8,Gold)];LastLine=Line;}
   auto Tile=SNew(SClassicAction).Entry(E).Icon(ClassicIcon(int32(CN(E,TEXT("icon"),-1)))).Border(ClassicIcon(int32(CN(E,TEXT("border"),-1)),true)).Font(CF(6)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(-1).Inspect([this,Id,Token](){ClassicInspect(Id,Token);}).Hover([this,Id,Token](){ClassicHover(Id,Token);}).HoverText_Lambda([this,Id,Token](){return ClassicHoverText(Id,Token);}).DoubleClick([this,Id,Token](){ClassicUse(Id,Token);});
   auto HoverLabel=MakeClassicHoverLabel(CT((Kind==TEXT("ability")||Kind==TEXT("macro"))?CS(E,TEXT("name")):FString::Printf(TEXT("%s  %.0f"),*CS(E,TEXT("name")),CN(E,TEXT("level")))),Id,Token);
   List->AddSlot().AutoHeight().Padding(0,1)[SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(16).HeightOverride(16)[Tile]]+SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[HoverLabel]];++Count;
  }
  if(!Count)List->AddSlot().AutoHeight()[CT(TEXT("NO ENTRIES RECEIVED FOR THIS TAB"))];double Y=ClassicTab==TEXT("skills")?197:57;At(Canvas,{10,Y},{162,ClassicTab==TEXT("skills")?215.:353.},SNew(SScrollBox)+SScrollBox::Slot()[List]);
 }
 FString Feedback=ClassicTab==TEXT("inventory")?CS(InventoryState,TEXT("feedback")):CS(ClassicState,TEXT("feedback"));if(ClassicTab!=TEXT("group")&&!Feedback.IsEmpty())Text({10,416},{162,15},Feedback,Gold);
 At(Canvas,{5,432},{82,12},CB(CT(TEXT("L: JOURNAL"),7),[this](){ToggleClassicJournal();}));At(Canvas,{92,432},{95,12},CB(CT(TEXT("T: TRAIN"),7),[this](){ToggleClassicTrainer();}));
 ClassicPanelBox->SetContent(SNew(SClassicMove).Content(Canvas).Move([this](FVector2D D){FVector2D S;S=UIViewportSize();S/=ClassicScale();auto& P=ClassicPositions[0];P.X=FMath::Clamp(FMath::Clamp(P.X,0.,FMath::Max(0.,S.X-192))+D.X,0.,FMath::Max(0.,S.X-192));P.Y=FMath::Clamp(FMath::Clamp(P.Y,0.,FMath::Max(0.,S.Y-448))+D.Y,0.,FMath::Max(0.,S.Y-448));}).End([this](){SaveClassicLayout();}));
}
void UDAoCBridgeSubsystem::RefreshClassicBars(){
 auto Banks=CA(ClassicState,TEXT("banks"));for(int32 B=0;B<3;++B){if(!ClassicBarBoxes[B].IsValid()||!Banks.IsValidIndex(B))continue;int32 Bank=int32(Banks[B]->AsNumber());auto C=SNew(SCanvas);const bool Vertical=ClassicVertical[B];At(C,{0,0},Vertical?FVector2D(33,372):FVector2D(372,33),SNew(SImage).Image(ClassicArt(Vertical?TEXT("hbar_vert"):TEXT("hbar_horz"))));
  At(C,{10,0},{10,10},CT(FString::FromInt(Bank+1),7,Gold));At(C,{19,0},{13,11},CB(ClassicSymbol(TEXT("\u2194"),7),[this,B](){ClassicVertical[B]=!ClassicVertical[B];RefreshClassicBars();SaveClassicLayout();}));
  for(int32 D:{-1,1})At(C,{D<0?0.:16.,11},{16,21},CB(ClassicSymbol(D<0?TEXT("\u2039"):TEXT("\u203a"),12),[this,B,Bank,D](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("bar"),B);V->SetNumberField(TEXT("bank"),(Bank+D+10)%10);Send(TEXT("ui_bank"),V);}));
  for(int32 I=0;I<10;++I){auto E=ClassicSlot(B,I);auto Current=ClassicEntry(CS(E,TEXT("id")));const bool Valid=Current.IsValid()&&CS(Current,TEXT("name"))==CS(E,TEXT("name"));auto Tile=SNew(SClassicAction).Entry(E).Icon(ClassicIcon(int32(CN(E,TEXT("icon"),-1)))).Border(ClassicIcon(int32(CN(E,TEXT("border"),-1)),true)).Font(CF(6)).Bar(B).Bank(Bank).Slot(I).InventorySlot(-1)
   .Inspect([this,E](){if(E.IsValid())ClassicInspect(CS(E,TEXT("id")),CS(E,TEXT("token")));}).Hover([this,E](){if(E.IsValid())ClassicHover(CS(E,TEXT("id")),CS(E,TEXT("token")));}).HoverText_Lambda([this,E](){return ClassicHoverText(CS(E,TEXT("id")),CS(E,TEXT("token")));})
   .Click([this,B,I](){if(PlayerIsDead()&&CS(ClassicSlot(B,I),TEXT("kind"))!=TEXT("macro"))return;auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("bar"),B);V->SetNumberField(TEXT("slot"),I);Send(TEXT("ui_use_slot"),V);})
   .Clear([this,B,I](){ClassicAssign(B,I,TEXT(""),TEXT(""));})
   .Drop([this,B,I](TSharedRef<FClassicDrag>D){ClassicAssign(B,I,D->Id,D->Token,D->Bar,D->Bank,D->Slot);})
   .Cooldown_Lambda([this,E](){auto Reuse=CO(ClassicState,TEXT("reuse_ms"));double Left=CN(Reuse,*CS(E,TEXT("id")))/1000-(FPlatformTime::Seconds()-ClassicReceivedAt);return Left>0?FText::FromString(FString::Printf(TEXT("%.0f"),FMath::CeilToDouble(Left))):FText::GetEmpty();});
   Tile->SetColorAndOpacity(Valid?FLinearColor::White:FLinearColor(.5,.5,.5));At(C,Vertical?FVector2D(1,33+I*34):FVector2D(33+I*34,1),{31,31},Tile);
  }
  ClassicBarBoxes[B]->SetContent(SNew(SClassicMove).Content(C).Move([this,B](FVector2D D){FVector2D S;S=UIViewportSize();S/=ClassicScale();const FVector2D Size=ClassicVertical[B]?FVector2D(33,372):FVector2D(372,33);auto& P=ClassicPositions[B+1];P.X=FMath::Clamp(FMath::Clamp(P.X,0.,FMath::Max(0.,S.X-Size.X))+D.X,0.,FMath::Max(0.,S.X-Size.X));P.Y=FMath::Clamp(FMath::Clamp(P.Y,0.,FMath::Max(0.,S.Y-Size.Y))+D.Y,0.,FMath::Max(0.,S.Y-Size.Y));}).End([this](){SaveClassicLayout();}));
 }
}
void UDAoCBridgeSubsystem::UpdateClassicInput(){
 if(!ClassicState.IsValid()||bChatOpen||bOptionsOpen||ExchangeTyping()||bExiting)return;
 auto* PC=GetWorld()->GetFirstPlayerController();if(!PC)return;LoadKeyConfiguration();
 for(int32 Bar=0;Bar<3;++Bar)for(int32 Slot=0;Slot<10;++Slot)if(KeyConfiguration->Pressed(PC,FString::Printf(TEXT("qb%d_%d"),Bar+1,Slot+1))&&(!PlayerIsDead()||CS(ClassicSlot(Bar,Slot),TEXT("kind"))==TEXT("macro"))){
  auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("bar"),Bar);V->SetNumberField(TEXT("slot"),Slot);Send(TEXT("ui_use_slot"),V);
 }
 for(int32 Bank=0;Bank<10;++Bank)if(KeyConfiguration->Pressed(PC,FString::Printf(TEXT("qbank_%d"),Bank+1))){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("bar"),0);V->SetNumberField(TEXT("bank"),Bank);Send(TEXT("ui_bank"),V);}
 if(KeyConfiguration->Pressed(PC,TEXT("inspect_item"))){auto E=ClassicEntry(FString::Printf(TEXT("srv:%d"),SelectedItemSlot));if(E.IsValid())ClassicInspect(CS(E,TEXT("id")),CS(E,TEXT("token")));}
 if(KeyConfiguration->Pressed(PC,TEXT("target_self")))SelectEntity(TEXT("player:local"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_stats")))SetClassicTab(TEXT("character"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_skills")))SetClassicTab(TEXT("skills"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_spells")))SetClassicTab(TEXT("magic"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_combat")))SetClassicTab(TEXT("combat"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_group")))SetClassicTab(TEXT("group"));
 if(KeyConfiguration->Pressed(PC,TEXT("show_guild")))ToggleGuild();
 if(KeyConfiguration->Pressed(PC,TEXT("show_map")))ToggleZoneMap();
 if(KeyConfiguration->Pressed(PC,TEXT("show_journal")))ToggleClassicJournal();
 if(KeyConfiguration->Pressed(PC,TEXT("show_trainer")))ToggleClassicTrainer();
}
void UDAoCBridgeSubsystem::TickClassicUI(){
 if(ClassicState.IsValid()&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeTrainerVisualTest"))){static bool Selected=false;auto Specs=CA(CO(ClassicState,TEXT("trainer")),TEXT("specs"));if(!Selected&&!Specs.IsEmpty()&&Specs[0]->Type==EJson::Object){Selected=true;ClassicTrainingKind=TEXT("spec");ClassicTrainingIndex=int32(CN(Specs[0]->AsObject(),TEXT("index"),-1));ClassicTrainingToken=CS(Specs[0]->AsObject(),TEXT("token"));RefreshClassicTrainer();}}

 if(ClassicState.IsValid()&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeJournalVisualTest"))){static bool Opened=false;if(!Opened){Opened=true;bClassicJournalOpen=true;auto Quests=CA(CO(ClassicState,TEXT("journal")),TEXT("entries"));if(!Quests.IsEmpty()&&Quests[0]->Type==EJson::Object){ClassicQuestIndex=int32(CN(Quests[0]->AsObject(),TEXT("index"),-1));ClassicQuestToken=CS(Quests[0]->AsObject(),TEXT("token"));}RefreshClassicJournal();}}

 if(ClassicState.IsValid()&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeSpellVisualTest"))&&!CaptureFile.IsEmpty()){
  auto C=CO(ClassicState,TEXT("casting"));const FString Phase=CS(C,TEXT("phase"));const double Age=CN(ClassicState,TEXT("casting_age_ms"));
  if((Phase==TEXT("casting")||Phase==TEXT("released")||Phase==TEXT("interrupted"))&&Age>150&&Age<1600){static TSet<FString> Captured;const FString Key=FString::Printf(TEXT("Spell_%d_%s"),int32(CN(C,TEXT("effect_id"))),*Phase);if(!Captured.Contains(Key)){Captured.Add(Key);FScreenshotRequest::RequestScreenshot(FPaths::GetPath(CaptureFile)/(Key+TEXT(".png")),true,false);}}
 }

 if(ClassicState.IsValid()&&FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeClassicVisualTest"))&&PlayerStartedAt>0){
  const double Now=FPlatformTime::Seconds();static int32 Stage=0;static double Began=0,RequestedAt=0;static bool Initialized=false;
  const TCHAR* Tabs[]={TEXT("character"),TEXT("inventory"),TEXT("skills"),TEXT("combat"),TEXT("magic"),TEXT("group")};
  const FString Folder=FPaths::GetPath(CaptureFile);
  if(!Initialized){for(auto Tab:Tabs)IFileManager::Get().Delete(*(Folder/(FString(TEXT("Classic_"))+Tab+TEXT(".png"))),false,true);Initialized=true;Began=Now;SetClassicTab(Tabs[Stage]);}
  const FString Shot=Folder/(FString(TEXT("Classic_"))+Tabs[Stage]+TEXT(".png"));
  if(RequestedAt>0&&Now-RequestedAt>.75&&IFileManager::Get().FileExists(*Shot)&&Stage<5){++Stage;Began=Now;RequestedAt=0;SetClassicTab(Tabs[Stage]);}
  else if(Now-Began>3&&RequestedAt==0){FScreenshotRequest::RequestScreenshot(Shot,true,false);RequestedAt=Now;}
 }

 if(!ClassicState.IsValid()||!bClassicOpen||ClassicTab!=TEXT("inventory")||FPlatformTime::Seconds()-ClassicCapturedAt<.3)return;ClassicCapturedAt=FPlatformTime::Seconds();UpdateClassicDoll();
}

void UDAoCBridgeSubsystem::RemoveClassicUI(){CloseEmblemPicker(false);EmblemPickerState.Reset();EmblemPickerData.Reset();EmblemPickerToken.Empty();EmblemPickerDismissedToken.Empty();
 CloseGuild(false);GuildState.Reset();GuildWindowToken.Empty();GuildDismissedToken.Empty();GuildSelectedToken.Empty();GuildSelectedName.Empty();CloseExchange(false);ExchangeState.Reset();ExchangeFields.Empty();ExchangeWindowToken.Empty();ExchangeDismissedToken.Empty();CloseClassicMerchant(false);CloseZoneMap();RemoveChat();UILayoutUnits=FVector2D::ZeroVector;CloseClassicVault(false);ClassicVaultSerial=-1;ClassicVaultSignature.Empty();CloseClassicTrainer();CloseClassicJournal();CloseGroupConfirmation();if(ClassicDetailOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicDetailOverlay.ToSharedRef());ClassicDetailOverlay.Reset();ClassicDetailPanel.Reset();if(ClassicOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicOverlay.ToSharedRef());ClassicOverlay.Reset();ClassicPanelBox.Reset();ClassicEffectsBox.Reset();ClassicCastBox.Reset();ClassicMiniGroupBox.Reset();ClassicPetBox.Reset();ClassicPetSignature.Empty();ClassicConcentrationBox.Reset();ClassicConcentrationSignature.Empty();for(auto& B:ClassicBarBoxes)B.Reset();ClassicState.Reset();ClassicRevision=-1;if(IsValid(ClassicDollActor))ClassicDollActor->Destroy();ClassicDollActor=nullptr;ClassicDollSignature.Empty();ClassicDollYaw=0;ClassicLastInventorySlot=-1;ClassicLastInventoryClickAt=0;if(IsValid(ClassicCaptureActor))ClassicCaptureActor->Destroy();ClassicCaptureActor=nullptr;ClassicCapture=nullptr;ClassicDollTarget=nullptr;ClassicDollBrush=nullptr;ClassicBrushes.Empty();ClassicTextures.Empty();}

TSharedRef<SWidget> UDAoCBridgeSubsystem::MakeClassicHoverLabel(const TSharedRef<SWidget>& Content,const FString& Id,const FString& Token){return SNew(SClassicHoverLabel).Hover([this,Id,Token](){ClassicHover(Id,Token);}).HoverText_Lambda([this,Id,Token](){return ClassicHoverText(Id,Token);})[Content];}
void UDAoCBridgeSubsystem::ClassicHover(const FString& Id,const FString& Token){
 if(!bLocalAvailable||bExiting||Id.IsEmpty()||Token.IsEmpty())return;
 auto Entry=HoverEntry(ClassicState,Id);if(!Entry.IsValid()||CS(Entry,TEXT("token"))!=Token||CS(Entry,TEXT("kind"))==TEXT("petcmd"))return;
 if(CS(Entry,TEXT("kind"))==TEXT("item")&&!CS(Entry,TEXT("item_token")).IsEmpty()&&CS(InventoryItem(FCString::Atoi(*Id.RightChop(4))),TEXT("token"))!=CS(Entry,TEXT("item_token")))return;
 auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("entry_id"),Id);Value->SetStringField(TEXT("entry_token"),Token);Send(TEXT("ui_hover"),Value);
}
FText UDAoCBridgeSubsystem::ClassicHoverText(const FString& Id,const FString& Token)const{
 auto Entry=HoverEntry(ClassicState,Id);if(!Entry.IsValid()||CS(Entry,TEXT("token"))!=Token)return FText::GetEmpty();
 if(CS(Entry,TEXT("kind"))==TEXT("item")&&!CS(Entry,TEXT("item_token")).IsEmpty()&&CS(InventoryItem(FCString::Atoi(*Id.RightChop(4))),TEXT("token"))!=CS(Entry,TEXT("item_token")))return FText::GetEmpty();
 FString Text=CS(Entry,TEXT("name"));auto Hover=CO(ClassicState,TEXT("hover"));
 if(CS(Hover,TEXT("entry_id"))==Id&&CS(Hover,TEXT("entry_token"))==Token&&CS(Hover,TEXT("status"))==TEXT("ready")){
  Text=CS(Hover,TEXT("caption"),Text);for(const auto& Line:CA(Hover,TEXT("lines")))if(Line->Type==EJson::String&&!Line->AsString().TrimStartAndEnd().IsEmpty())Text+=TEXT("\n")+Line->AsString();
 }
 return FText::FromString(Text);
}
void UDAoCBridgeSubsystem::ClassicInspect(const FString& Id,const FString& Token){
 if(!bLocalAvailable||bExiting||Id.IsEmpty()||Token.IsEmpty())return;
 if(CS(ClassicEntry(Id),TEXT("kind"))==TEXT("petcmd"))return;
 bInventoryMoving=false;
 auto Guide=CO(CO(ClassicState,TEXT("journal")),TEXT("guide"));if(Guide.IsValid()&&!Guide->Values.IsEmpty())Send(TEXT("journal_guide_close"));
 auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("entry_id"),Id);V->SetStringField(TEXT("entry_token"),Token);Send(TEXT("ui_detail"),V);
}
bool UDAoCBridgeSubsystem::CloseClassicDetail(){
 if(!ClassicDetailOverlay.IsValid())return false;
 if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicDetailOverlay.ToSharedRef());
 ClassicDetailOverlay.Reset();ClassicDetailPanel.Reset();auto Guide=CO(CO(ClassicState,TEXT("journal")),TEXT("guide"));auto ServerWindow=CO(ClassicState,TEXT("server_window"));if(Guide.IsValid()&&!Guide->Values.IsEmpty())Send(TEXT("journal_guide_close"));else if(ServerWindow.IsValid()&&!ServerWindow->Values.IsEmpty()){auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("window_token"),CS(ServerWindow,TEXT("token")));Send(TEXT("ui_server_window_close"),Value);}else Send(TEXT("ui_detail_close"));return true;
}
void UDAoCBridgeSubsystem::RefreshClassicDetail(){
 auto* V=GetWorld()->GetGameViewport();if(!V)return;
 auto Guide=CO(CO(ClassicState,TEXT("journal")),TEXT("guide"));const bool IsGuide=Guide.IsValid()&&!Guide->Values.IsEmpty();auto ServerWindow=CO(ClassicState,TEXT("server_window"));const bool IsServerWindow=ServerWindow.IsValid()&&!ServerWindow->Values.IsEmpty();auto D=IsGuide?Guide:IsServerWindow?ServerWindow:CO(ClassicState,TEXT("detail"));FString Stamp;if(D.IsValid())FJsonSerializer::Serialize(D,TJsonWriterFactory<>::Create(&Stamp));Stamp+=(IsGuide?TEXT("guide"):IsServerWindow?TEXT("server_window"):TEXT("detail"));if(ClassicDetailOverlay.IsValid()&&Stamp==ClassicDetailSignature)return;ClassicDetailSignature=Stamp;
 if(ClassicDetailOverlay.IsValid())V->RemoveViewportWidgetContent(ClassicDetailOverlay.ToSharedRef());ClassicDetailOverlay.Reset();ClassicDetailPanel.Reset();
 if(!D.IsValid()||D->Values.IsEmpty())return;
 auto Body=SNew(SVerticalBox);auto Heading=SNew(SHorizontalBox);
 Heading->AddSlot().FillWidth(1)[CT(CS(D,TEXT("caption")),12,Gold)];Heading->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(24).HeightOverride(24)[CB(CT(TEXT("\u00d7"),15),[this](){CloseClassicDetail();})]];
 Body->AddSlot().AutoHeight().Padding(0,0,0,12)[Heading];auto Lines=SNew(SVerticalBox);const FString State=CS(D,TEXT("status"));
 if(State!=TEXT("ready"))Lines->AddSlot().AutoHeight()[CT(State==TEXT("pending")?TEXT("Requesting information from the server..."):TEXT("The server has not sent information for this entry."),10)];
 else for(const auto& Line:CA(D,TEXT("lines")))if(Line->Type==EJson::String)Lines->AddSlot().AutoHeight().Padding(0,2)[SNew(STextBlock).Text(FText::FromString(Line->AsString())).Font(CF(10)).ColorAndOpacity(Cream).AutoWrapText(true)];
 Body->AddSlot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[Lines]];
 if(IsGuide)Body->AddSlot().AutoHeight().Padding(0,8)[SNew(SBox).IsEnabled(State!=TEXT("pending"))[CB(CT(TEXT("NEXT PAGE / QUEST"),9),[this](){SendJournalAction(TEXT("journal_guide"));})]];
 Body->AddSlot().AutoHeight().Padding(0,10,0,0)[CT(CS(D,TEXT("key"))==TEXT("macro-local")?TEXT("Macro command \u00b7 Esc to close"):TEXT("Server information \u00b7 Esc to close"),8)];
 auto Art=SNew(SOverlay);Art->AddSlot()[SNew(SImage).Image(ClassicArt(TEXT("interact")))];Art->AddSlot().Padding(16)[Body];
 ClassicDetailPanel=SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,1)).Padding(0)[Art];
 ClassicDetailOverlay=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(340).HeightOverride(350)[ClassicDetailPanel.ToSharedRef()]]];
 V->AddViewportWidgetContent(ClassicDetailOverlay.ToSharedRef(),40);
}

void UDAoCBridgeSubsystem::RefreshClassicEffects(){
 if(!ClassicEffectsBox.IsValid())return;
 auto Rows=CA(ClassicState,TEXT("effects"));ClassicEffectsBox->SetVisibility(Rows.IsEmpty()?EVisibility::Collapsed:EVisibility::SelfHitTestInvisible);
 auto Wrap=SNew(SWrapBox).Visibility(EVisibility::SelfHitTestInvisible).UseAllottedSize(true).InnerSlotPadding(FVector2D(4,4));
 for(const auto& Value:Rows){
  if(Value->Type!=EJson::Object)continue;auto E=Value->AsObject();const FString Id=CS(E,TEXT("id")),Token=CS(E,TEXT("token"));bool Negative=false;E->TryGetBoolField(TEXT("negative"),Negative);
  auto Tile=SNew(SClassicAction).Entry(E).Icon(ClassicIcon(int32(CN(E,TEXT("icon"),-1)))).Border(ClassicIcon(int32(CN(E,TEXT("border"),-1)),true)).Font(CF(6)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(-1).Inspect([this,Id,Token](){ClassicInspect(Id,Token);}).Hover([this,Id,Token](){ClassicHover(Id,Token);}).HoverText_Lambda([this,Id,Token](){return ClassicHoverText(Id,Token);});
  auto Cell=SNew(SVerticalBox);Cell->AddSlot().AutoHeight()[SNew(SBox).WidthOverride(32).HeightOverride(32)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Negative?FLinearColor(.8f,.12f,.12f,1):FLinearColor(.1f,.1f,.1f,1)).Padding(1)[Tile]]];
  Cell->AddSlot().AutoHeight().HAlign(HAlign_Center)[SNew(STextBlock).Text_Lambda([this,Id](){auto Times=CO(ClassicState,TEXT("effects_remaining_ms"));double Remaining=CN(Times,*Id,-1);if(Remaining<0)return FText::GetEmpty();int32 Seconds=FMath::Max(0,FMath::CeilToInt(Remaining/1000-(FPlatformTime::Seconds()-ClassicReceivedAt)));return FText::FromString(Seconds>=60?FString::Printf(TEXT("%d:%02d"),Seconds/60,Seconds%60):FString::FromInt(Seconds));}).Font(CF(8)).ColorAndOpacity(Negative?FLinearColor(1,.4f,.4f):Cream).ShadowOffset(FVector2D(1,1)).ShadowColorAndOpacity(FLinearColor::Black)];
  Wrap->AddSlot()[Cell];
 }
 ClassicEffectsBox->SetContent(Wrap);
}

void UDAoCBridgeSubsystem::RefreshClassicCasting(){
 if(!ClassicCastBox.IsValid())return;auto C=CO(ClassicState,TEXT("casting"));const FString Phase=CS(C,TEXT("phase"));
 bool Instant=false;if(C.IsValid())C->TryGetBoolField(TEXT("instant"),Instant);
 const bool Shown=C.IsValid()&&!C->Values.IsEmpty()&&!Instant&&Phase!=TEXT("instant");ClassicCastBox->SetVisibility(Shown?EVisibility::SelfHitTestInvisible:EVisibility::Collapsed);if(!Shown)return;
 auto Body=SNew(SVerticalBox);FString Label=CS(C,TEXT("name"));
 if(Phase==TEXT("interrupted"))Label+=TEXT(" \u00b7 INTERRUPTED");else if(Phase==TEXT("released"))Label+=TEXT(" \u00b7 RELEASED");else if(Phase==TEXT("unconfirmed"))Label+=TEXT(" \u00b7 UNCONFIRMED");
 Body->AddSlot().AutoHeight()[CT(Label,10,Phase==TEXT("interrupted")?FLinearColor(1,.4f,.4f):Gold)];
 Body->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(10)[SNew(SProgressBar).Style(&ClassicBarStyle()).Percent_Lambda([this](){auto V=CO(ClassicState,TEXT("casting"));const FString Phase=CS(V,TEXT("phase"));if(Phase==TEXT("released"))return 1.f;if(Phase==TEXT("interrupted"))return 0.f;const double Duration=CN(V,TEXT("duration_ms"));const double Age=CN(ClassicState,TEXT("casting_age_ms"))+(FPlatformTime::Seconds()-ClassicReceivedAt)*1000;return Duration>0?float(FMath::Clamp(Age/Duration,0.,1.)):0.f;}).FillColorAndOpacity(FLinearColor(.25f,.5f,.95f))]];
 ClassicCastBox->SetContent(SNew(SBorder).Visibility(EVisibility::SelfHitTestInvisible).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.02f,.02f,.025f,.9f)).Padding(5)[Body]);
}

TSharedRef<SWidget> UDAoCBridgeSubsystem::MakeClassicGroupRows(bool Mini){
 auto Canvas=SNew(SCanvas);auto Members=CA(ClassicState,TEXT("group"));if(Members.IsEmpty())At(Canvas,{8,12},{176,28},CT(TEXT("YOU ARE NOT IN A GROUP"),8));
 for(int32 I=0;I<FMath::Min(Members.Num(),8);++I){if(Members[I]->Type!=EJson::Object)continue;auto M=Members[I]->AsObject();auto Row=SNew(SCanvas);bool Me=false;M->TryGetBoolField(TEXT("me"),Me);const int32 Oid=int32(CN(M,TEXT("oid")));
  At(Row,{8,1},{101,11},SNew(STextBlock).Text(FText::FromString((CS(M,TEXT("name"))+(Me?TEXT(" \u00b7 ME"):TEXT(""))).ToUpper())).Font(CF(7)).ColorAndOpacity(Cream));
  At(Row,{110,1},{76,11},SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("%s %.0f"),*CS(M,TEXT("class_name")).ToUpper(),CN(M,TEXT("level"))))).Font(CF(6)).ColorAndOpacity(Gold).Justification(ETextJustify::Right));
  const double HP=CN(M,TEXT("hp"),-1),Power=CN(M,TEXT("power"),-1);At(Row,{6,13},{70,7},SNew(SProgressBar).Style(&ClassicBarStyle()).Percent(float(FMath::Clamp(HP/100.,0.,1.))).FillColorAndOpacity(FLinearColor(.8f,.1f,.08f)));At(Row,{6,10},{70,12},CT(HP>=0?FString::Printf(TEXT("%.0f%%"),HP):TEXT("\u2014"),6));At(Row,{6,24},{70,3},SNew(SProgressBar).Style(&ClassicBarStyle()).Percent(float(FMath::Clamp(Power/100.,0.,1.))).FillColorAndOpacity(FLinearColor(.9f,.75f,.1f)));
  auto Effects=CA(M,TEXT("effects"));for(int32 E=0;E<FMath::Min(Effects.Num(),14);++E){auto FX=Effects[E]->AsObject();At(Row,{80.+(E%7)*15,13.+(E/7)*10},{14,10},SNew(SImage).Image(ClassicIcon(int32(CN(FX,TEXT("icon"),-1)))).ToolTipText(FText::FromString(CS(FX,TEXT("name"),TEXT("Group member effect")))));}
  auto Click=CB(Row,[this,M](){SendGroupAction(TEXT("group_target"),M);});At(Canvas,{0,I*(Mini?35.:37.8)},{192,34},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Oid==int32(CN(ClassicState,TEXT("group_selected_oid")))?FLinearColor(.15f,.2f,.35f,.65f):FLinearColor::Transparent).Padding(0)[Click]);
 }
 return Canvas;
}
void UDAoCBridgeSubsystem::SendGroupAction(const FString& Action,TSharedPtr<FJsonObject> Member){
 if(!bLocalAvailable||bExiting||Session.IsEmpty())return;auto V=MakeShared<FJsonObject>();auto Party=CO(ClassicState,TEXT("party"));V->SetStringField(TEXT("group_token"),CS(Party,TEXT("token")));
 if(Member.IsValid()){V->SetNumberField(TEXT("member_oid"),CN(Member,TEXT("oid")));V->SetStringField(TEXT("member_token"),CS(Member,TEXT("token")));}if(Action==TEXT("group_invite"))V->SetStringField(TEXT("entity_id"),CurrentTarget());Send(Action,V);
}
bool UDAoCBridgeSubsystem::CloseGroupConfirmation(){if(!ClassicGroupConfirmOverlay.IsValid())return false;if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicGroupConfirmOverlay.ToSharedRef());ClassicGroupConfirmOverlay.Reset();ClassicGroupConfirmPanel.Reset();return true;}
void UDAoCBridgeSubsystem::ShowGroupConfirmation(const FString& Action,TSharedPtr<FJsonObject> Member){
 if(!bLocalAvailable||bExiting||!ClassicState.IsValid()||(Action!=TEXT("group_leave")&&Action!=TEXT("group_remove")))return;CloseGroupConfirmation();auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("group_token"),CS(CO(ClassicState,TEXT("party")),TEXT("token")));if(Member.IsValid()){V->SetNumberField(TEXT("member_oid"),CN(Member,TEXT("oid")));V->SetStringField(TEXT("member_token"),CS(Member,TEXT("token")));}
 auto Body=SNew(SVerticalBox);Body->AddSlot().AutoHeight().Padding(0,0,0,16)[CT(Action==TEXT("group_leave")?TEXT("LEAVE YOUR GROUP?"):FString::Printf(TEXT("REMOVE %s FROM THE GROUP?"),*CS(Member,TEXT("name"))),11,Gold)];
 Body->AddSlot().AutoHeight()[SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1).Padding(5)[CB(CT(TEXT("CONFIRM"),9),[this,Action,V](){CloseGroupConfirmation();Send(Action,V);})]+SHorizontalBox::Slot().FillWidth(1).Padding(5)[CB(CT(TEXT("CANCEL"),9),[this](){CloseGroupConfirmation();})]];
 ClassicGroupConfirmPanel=SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,1)).Padding(16)[Body];ClassicGroupConfirmOverlay=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(290)[ClassicGroupConfirmPanel.ToSharedRef()]]];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ClassicGroupConfirmOverlay.ToSharedRef(),42);
}
void UDAoCBridgeSubsystem::RefreshClassicMiniGroup(){
 if(!ClassicMiniGroupBox.IsValid())return;ClassicMiniGroupBox->SetVisibility(bClassicMiniGroupOpen?EVisibility::Visible:EVisibility::Collapsed);if(!bClassicMiniGroupOpen)return;auto Canvas=SNew(SCanvas);const double Height=FMath::Max(70,24+CA(ClassicState,TEXT("group")).Num()*35);
 At(Canvas,{0,0},{192,Height},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.95f)));At(Canvas,{16,2},{145,17},CT(TEXT("GROUP"),9,Gold));At(Canvas,{174,1},{16,16},CB(CT(TEXT("\u00d7"),11),[this](){bClassicMiniGroupOpen=false;RefreshClassicMiniGroup();SaveClassicLayout();}));At(Canvas,{0,22},{192,Height-22},MakeClassicGroupRows(true));
 ClassicMiniGroupBox->SetContent(SNew(SClassicMove).Content(Canvas).Move([this](FVector2D D){ClassicPositions[4]+=D;}).End([this](){SaveClassicLayout();}));
}

void UDAoCBridgeSubsystem::ToggleClassicJournal(){bClassicJournalOpen=!bClassicJournalOpen;RefreshClassicJournal();}
bool UDAoCBridgeSubsystem::CloseClassicJournal(){if(!bClassicJournalOpen&&!ClassicJournalOverlay.IsValid())return false;bClassicJournalOpen=false;if(ClassicJournalOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicJournalOverlay.ToSharedRef());ClassicJournalOverlay.Reset();ClassicJournalPanel.Reset();return true;}
void UDAoCBridgeSubsystem::SendJournalAction(const FString& Action,TSharedPtr<FJsonObject> Quest){
 if(!bLocalAvailable||bExiting)return;auto V=MakeShared<FJsonObject>();if(Quest.IsValid()){V->SetNumberField(TEXT("quest_index"),CN(Quest,TEXT("index"),-1));V->SetStringField(TEXT("quest_token"),CS(Quest,TEXT("token")));}Send(Action,V);
}
void UDAoCBridgeSubsystem::ShowJournalRemoval(TSharedPtr<FJsonObject> Quest){
 if(!Quest.IsValid())return;CloseGroupConfirmation();auto Frozen=MakeShared<FJsonObject>(*Quest);auto Body=SNew(SVerticalBox);
 Body->AddSlot().AutoHeight().Padding(0,0,0,12)[CT(TEXT("ABANDON THIS QUEST?"),12,Gold)];Body->AddSlot().AutoHeight().Padding(0,0,0,12)[CT(CS(Frozen,TEXT("name")),10)];Body->AddSlot().AutoHeight()[CT(TEXT("The server decides whether this quest can be abandoned. Quest progress may be lost."),9)];
 Body->AddSlot().AutoHeight().Padding(0,12)[SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[CB(CT(TEXT("CANCEL"),9),[this](){CloseGroupConfirmation();})]+SHorizontalBox::Slot().FillWidth(1)[CB(CT(TEXT("ABANDON"),9),[this,Frozen](){CloseGroupConfirmation();SendJournalAction(TEXT("journal_remove"),Frozen);})]];
 ClassicGroupConfirmPanel=SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,1)).Padding(16)[Body];ClassicGroupConfirmOverlay=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(310)[ClassicGroupConfirmPanel.ToSharedRef()]]];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ClassicGroupConfirmOverlay.ToSharedRef(),42);
}
void UDAoCBridgeSubsystem::RefreshClassicJournal(){
 auto* V=GetWorld()->GetGameViewport();if(!V)return;auto Journal=CO(ClassicState,TEXT("journal"));FString Stamp;if(Journal.IsValid())FJsonSerializer::Serialize(Journal,TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::FromInt(ClassicQuestIndex)+ClassicQuestToken;if(bClassicJournalOpen&&ClassicJournalOverlay.IsValid()&&Stamp==ClassicJournalSignature)return;ClassicJournalSignature=Stamp;if(ClassicJournalOverlay.IsValid())V->RemoveViewportWidgetContent(ClassicJournalOverlay.ToSharedRef());ClassicJournalOverlay.Reset();ClassicJournalPanel.Reset();if(!bClassicJournalOpen)return;
 auto Quests=CA(Journal,TEXT("entries"));TSharedPtr<FJsonObject> Selected;
 for(const auto& Q:Quests)if(Q->Type==EJson::Object&&CN(Q->AsObject(),TEXT("index"),-1)==ClassicQuestIndex&&CS(Q->AsObject(),TEXT("token"))==ClassicQuestToken)Selected=Q->AsObject();
 if(!Selected.IsValid()){ClassicQuestIndex=-1;ClassicQuestToken.Empty();}
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{512,300},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.99f)));At(Canvas,{0,0},{512,256},SNew(SImage).Image(ClassicArt(TEXT("questbg"))));At(Canvas,{490,0},{22,20},CB(CT(TEXT(""),12),[this](){CloseClassicJournal();}));
 auto List=SNew(SVerticalBox);for(const auto& Q:Quests){if(Q->Type!=EJson::Object)continue;auto Row=Q->AsObject();const int32 Index=int32(CN(Row,TEXT("index"),-1));const FString Token=CS(Row,TEXT("token"));List->AddSlot().AutoHeight().Padding(0,2)[CB(CT(CS(Row,TEXT("name")),9,Index==ClassicQuestIndex?Gold:Cream),[this,Index,Token](){ClassicQuestIndex=Index;ClassicQuestToken=Token;RefreshClassicJournal();})];}
 if(Quests.IsEmpty())List->AddSlot().AutoHeight()[CT(TEXT("No active quests received."),9)];At(Canvas,{10,26},{170,220},SNew(SScrollBox)+SScrollBox::Slot()[List]);
 auto Texts=SNew(SVerticalBox);auto Literal=[&](const FString& Text,FLinearColor Color){Texts->AddSlot().AutoHeight().Padding(0,3)[SNew(STextBlock).Text(FText::FromString(Text)).Font(CF(10)).ColorAndOpacity(Color).AutoWrapText(true)];};
 if(Selected.IsValid()){Literal(CS(Selected,TEXT("name")),Gold);Literal(CS(Selected,TEXT("text")),Cream);for(const auto& Goal:CA(Selected,TEXT("goals"))){if(Goal->Type!=EJson::Object)continue;auto G=Goal->AsObject();bool Done=false;G->TryGetBoolField(TEXT("done"),Done);Literal((Done?TEXT("[OK] "):TEXT("\u2022 "))+CS(G,TEXT("text")),Done?FLinearColor(.4f,1,.45f):Cream);}}else Literal(TEXT("Select a quest to read its steps."),Cream);
 At(Canvas,{190,26},{306,194},SNew(SScrollBox)+SScrollBox::Slot()[Texts]);bool Pending=false;if(Journal.IsValid())Journal->TryGetBoolField(TEXT("pending"),Pending);
 At(Canvas,{270,227},{112,18},SNew(SBox).IsEnabled(!Pending)[CB(CT(TEXT("GUIDE"),9),[this](){SendJournalAction(TEXT("journal_guide"));})]);At(Canvas,{392,227},{110,18},SNew(SBox).IsEnabled(!Pending&&Selected.IsValid())[CB(CT(TEXT("ABANDON"),9),[this,Selected](){ShowJournalRemoval(Selected);})]);At(Canvas,{12,263},{488,29},CT(CS(Journal,TEXT("feedback")),9,Gold));
 ClassicJournalPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){ClassicJournalPosition+=Delta;}).End([this](){SaveClassicLayout();});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){FVector2D Size;Size=UIViewportSize();Size/=ClassicScale();return FVector2D(FMath::Clamp(ClassicJournalPosition.X,0.,FMath::Max(0.,Size.X-512)),FMath::Clamp(ClassicJournalPosition.Y,0.,FMath::Max(0.,Size.Y-300)));}).Size(FVector2D(512,300))[ClassicJournalPanel.ToSharedRef()];ClassicJournalOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];V->AddViewportWidgetContent(ClassicJournalOverlay.ToSharedRef(),35);
}

void UDAoCBridgeSubsystem::ToggleClassicTrainer(){if(bClassicTrainerOpen){CloseClassicTrainer();return;}bClassicTrainerOpen=true;RefreshClassicTrainer();SendTrainerAction(TEXT("trainer_refresh"));}
bool UDAoCBridgeSubsystem::CloseClassicTrainer(){if(!bClassicTrainerOpen&&!ClassicTrainerOverlay.IsValid())return false;bClassicTrainerOpen=false;if(ClassicTrainerOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicTrainerOverlay.ToSharedRef());ClassicTrainerOverlay.Reset();ClassicTrainerPanel.Reset();return true;}
void UDAoCBridgeSubsystem::SendTrainerAction(const FString& Action,TSharedPtr<FJsonObject> Row){if(!bLocalAvailable||bExiting||PlayerIsDead())return;auto V=MakeShared<FJsonObject>();if(Row.IsValid()){V->SetStringField(TEXT("training_kind"),CS(Row,TEXT("kind")));V->SetNumberField(TEXT("training_index"),CN(Row,TEXT("index"),-1));V->SetStringField(TEXT("training_token"),CS(Row,TEXT("token")));}Send(Action,V);}
void UDAoCBridgeSubsystem::ShowTrainingConfirmation(TSharedPtr<FJsonObject> Row){
 if(!Row.IsValid())return;CloseGroupConfirmation();auto Frozen=MakeShared<FJsonObject>(*Row);auto Body=SNew(SVerticalBox);Body->AddSlot().AutoHeight().Padding(0,0,0,10)[CT(TEXT("CONFIRM TRAINING"),12,Gold)];Body->AddSlot().AutoHeight().Padding(0,0,0,10)[CT(FString::Printf(TEXT("%s \u00b7 LEVEL %.0f \u2192 %.0f"),*CS(Frozen,TEXT("name")),CN(Frozen,TEXT("level")),CN(Frozen,TEXT("level"))+1),10)];Body->AddSlot().AutoHeight()[CT(FString::Printf(TEXT("Listed cost: %.0f %s points. The server checks requirements and confirms the result."),CN(Frozen,TEXT("cost")),CS(Frozen,TEXT("kind"))==TEXT("realm")?TEXT("realm skill"):TEXT("specialization")),9)];Body->AddSlot().AutoHeight().Padding(0,12)[SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[CB(CT(TEXT("CANCEL"),9),[this](){CloseGroupConfirmation();})]+SHorizontalBox::Slot().FillWidth(1)[CB(CT(TEXT("TRAIN"),9),[this,Frozen](){CloseGroupConfirmation();SendTrainerAction(TEXT("trainer_train"),Frozen);})]];
 ClassicGroupConfirmPanel=SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,1)).Padding(16)[Body];ClassicGroupConfirmOverlay=SNew(SOverlay)+SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)[SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[SNew(SBox).WidthOverride(320)[ClassicGroupConfirmPanel.ToSharedRef()]]];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ClassicGroupConfirmOverlay.ToSharedRef(),42);
}
void UDAoCBridgeSubsystem::RefreshClassicTrainer(){
 auto* V=GetWorld()->GetGameViewport();if(!V)return;auto Trainer=CO(ClassicState,TEXT("trainer"));bool Ready=false;if(Trainer.IsValid())Trainer->TryGetBoolField(TEXT("ready"),Ready);const int32 Serial=int32(CN(Trainer,TEXT("open_serial"),-1));if(Ready&&Serial!=ClassicTrainerSerial){ClassicTrainerSerial=Serial;bClassicTrainerOpen=true;}
 FString Stamp;if(Trainer.IsValid())FJsonSerializer::Serialize(Trainer,TJsonWriterFactory<>::Create(&Stamp));Stamp+=ClassicTrainingKind+FString::FromInt(ClassicTrainingIndex)+ClassicTrainingToken;if(bClassicTrainerOpen&&ClassicTrainerOverlay.IsValid()&&Stamp==ClassicTrainerSignature)return;ClassicTrainerSignature=Stamp;if(ClassicTrainerOverlay.IsValid())V->RemoveViewportWidgetContent(ClassicTrainerOverlay.ToSharedRef());ClassicTrainerOverlay.Reset();ClassicTrainerPanel.Reset();if(!bClassicTrainerOpen)return;
 TSharedPtr<FJsonObject> Selected;auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{580,448},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.99f)));At(Canvas,{0,0},{350,448},SNew(SImage).Image(ClassicArt(TEXT("training"))));At(Canvas,{328,0},{22,20},CB(CT(TEXT("")),[this](){CloseClassicTrainer();}));
 At(Canvas,{172,20},{34,15},CT(CN(Trainer,TEXT("spec_points"),-1)<0?TEXT("\u2014"):FString::Printf(TEXT("%.0f"),CN(Trainer,TEXT("spec_points"))),9,Gold));At(Canvas,{156,224},{50,15},CT(CN(Trainer,TEXT("realm_points"),-1)<0?TEXT("\u2014"):FString::Printf(TEXT("%.0f"),CN(Trainer,TEXT("realm_points"))),9,Gold));
 for(int32 Group=0;Group<2;++Group){const FString Kind=Group?TEXT("realm"):TEXT("spec");auto Rows=SNew(SVerticalBox);auto Entries=CA(Trainer,Group?TEXT("realm"):TEXT("specs"));for(const auto& Value:Entries){if(Value->Type!=EJson::Object)continue;auto Row=Value->AsObject();const int32 Index=int32(CN(Row,TEXT("index"),-1));const FString Token=CS(Row,TEXT("token"));const bool Chosen=ClassicTrainingKind==Kind&&ClassicTrainingIndex==Index&&ClassicTrainingToken==Token;if(Chosen)Selected=Row;bool Can=false;Row->TryGetBoolField(TEXT("can_train"),Can);const FLinearColor Color=Chosen?Gold:Can?Cream:FLinearColor(.5f,.5f,.5f);
  auto Line=SNew(SHorizontalBox)+SHorizontalBox::Slot().FillWidth(1)[CT(CS(Row,TEXT("name")),9,Color)]+SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(30)[CT(FString::Printf(TEXT("%.0f"),CN(Row,TEXT("level"))),9,Color)]]+SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(78)[CT(FString::Printf(TEXT("%.0f PTS"),CN(Row,TEXT("cost"))),9,Color)]];Rows->AddSlot().AutoHeight().Padding(0,2)[CB(Line,[this,Kind,Index,Token](){ClassicTrainingKind=Kind;ClassicTrainingIndex=Index;ClassicTrainingToken=Token;RefreshClassicTrainer();})];
 }if(Entries.IsEmpty())Rows->AddSlot().AutoHeight()[CT(Ready?TEXT("No entries received."):TEXT("Waiting for the server window."),9)];At(Canvas,{10,Group?244.:38.},{322,Group?162.:160.},SNew(SScrollBox)+SScrollBox::Slot()[Rows]);}
 if(!Selected.IsValid()){ClassicTrainingIndex=-1;ClassicTrainingKind.Empty();ClassicTrainingToken.Empty();}
 bool Pending=false;if(Trainer.IsValid())Trainer->TryGetBoolField(TEXT("pending"),Pending);bool Can=false;if(Selected.IsValid())Selected->TryGetBoolField(TEXT("can_train"),Can);At(Canvas,{254,416},{80,18},SNew(SBox).IsEnabled(Ready&&Can&&!Pending&&!PlayerIsDead())[CB(CT(TEXT("TRAIN"),9),[this,Selected](){ShowTrainingConfirmation(Selected);})]);At(Canvas,{10,414},{234,29},CT(CS(Trainer,TEXT("feedback")),8,Gold));
 At(Canvas,{350,0},{230,448},SNew(SImage).Image(ClassicArt(TEXT("interact"))));At(Canvas,{558,0},{22,20},CB(CT(TEXT("")),[this](){CloseClassicTrainer();}));At(Canvas,{365,12},{200,34},CT(Selected.IsValid()?CS(Selected,TEXT("name")):TEXT("TRAINING PREVIEW"),11,Gold));auto Preview=SNew(SVerticalBox);bool PreviewReady=false;if(Trainer.IsValid())Trainer->TryGetBoolField(TEXT("preview_ready"),PreviewReady);
 if(!Selected.IsValid())Preview->AddSlot().AutoHeight()[CT(TEXT("Select a specialization or realm ability."),9)];else if(ClassicTrainingKind==TEXT("realm"))Preview->AddSlot().AutoHeight()[CT(TEXT("Requirements and cost come from the server. Training increases this skill by one level."),9)];else if(!PreviewReady)Preview->AddSlot().AutoHeight()[CT(TEXT("Waiting for the server preview."),9)];else{auto Skills=CA(CO(Trainer,TEXT("previews")),*FString::FromInt(ClassicTrainingIndex));if(Skills.IsEmpty())Preview->AddSlot().AutoHeight()[CT(TEXT("No skills in the received preview."),9)];for(const auto& Skill:Skills){if(Skill->Type!=EJson::Object)continue;auto S=Skill->AsObject();const double Level=CN(S,TEXT("level"));const FLinearColor Color=Level<=CN(Selected,TEXT("level"))?FLinearColor(.5f,.5f,.5f):Level==CN(Selected,TEXT("level"))+1?Gold:Cream;auto Image=SNew(SOverlay);Image->AddSlot()[SNew(SImage).Image(ClassicIcon(int32(CN(S,TEXT("icon"),-1))))];if(CN(S,TEXT("border"),-1)>=0)Image->AddSlot()[SNew(SImage).Image(ClassicIcon(int32(CN(S,TEXT("border"))),true))];Preview->AddSlot().AutoHeight().Padding(0,3)[SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(20).HeightOverride(20)[Image]]+SHorizontalBox::Slot().FillWidth(1).Padding(5,0)[CT(FString::Printf(TEXT("%s \u00b7 %.0f (%s)"),*CS(S,TEXT("name"),TEXT("Name pending")),Level,*CS(S,TEXT("kind"))),9,Color)]];}}
 At(Canvas,{365,56},{200,335},SNew(SScrollBox)+SScrollBox::Slot()[Preview]);At(Canvas,{365,403},{200,31},CT(TEXT("Grey: learned. Gold: next level."),8));
 ClassicTrainerPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){ClassicTrainerPosition+=Delta;}).End([this](){SaveClassicLayout();});auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){FVector2D Size;Size=UIViewportSize();Size/=ClassicScale();return FVector2D(FMath::Clamp(ClassicTrainerPosition.X,0.,FMath::Max(0.,Size.X-580)),FMath::Clamp(ClassicTrainerPosition.Y,0.,FMath::Max(0.,Size.Y-448)));}).Size(FVector2D(580,448))[ClassicTrainerPanel.ToSharedRef()];ClassicTrainerOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];V->AddViewportWidgetContent(ClassicTrainerOverlay.ToSharedRef(),36);
}

void UDAoCBridgeSubsystem::RefreshClassicPet(){
 if(!ClassicPetBox.IsValid())return;auto Pet=CO(ClassicState,TEXT("pet"));bool Valid=false;if(Pet.IsValid())Pet->TryGetBoolField(TEXT("valid"),Valid);ClassicPetBox->SetVisibility(Valid?EVisibility::Visible:EVisibility::Collapsed);if(!Valid)return;FString Stamp;FJsonSerializer::Serialize(Pet,TJsonWriterFactory<>::Create(&Stamp));if(Stamp==ClassicPetSignature&&ClassicPetBox->GetChildren()->Num()>0)return;ClassicPetSignature=Stamp;
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{128,128},SNew(SImage).Image(ClassicArt(TEXT("minipet"))));At(Canvas,{14,2},{100,12},CT(CS(Pet,TEXT("name")).IsEmpty()?TEXT("PET"):CS(Pet,TEXT("name")),7,Gold));const double Health=CN(Pet,TEXT("health"),-1);if(Health>=0)At(Canvas,{8,17},{112,6},SNew(SProgressBar).Style(&ClassicBarStyle()).FillColorAndOpacity(FLinearColor(.8f,.17f,.12f)).Percent(float(FMath::Clamp(Health,0.,1.))));else At(Canvas,{8,15},{112,10},CT(TEXT("\u2014"),7));
 const TCHAR* Commands[]={TEXT("aggressive"),TEXT("defensive"),TEXT("passive"),TEXT("follow"),TEXT("stay"),TEXT("attack"),TEXT("release")};const int32 Aggro=int32(CN(Pet,TEXT("aggro"))),Walk=int32(CN(Pet,TEXT("walk")));
 for(int32 I=0;I<7;++I){const FString Command=Commands[I];auto Entry=ClassicEntry(TEXT("petcmd:")+Command);if(!Entry.IsValid())continue;const FString Id=CS(Entry,TEXT("id")),Token=CS(Entry,TEXT("token"));const bool Active=(I==0&&Aggro==1)||(I==1&&Aggro==2)||(I==2&&Aggro==3)||(I==3&&Walk==1)||(I==4&&Walk==2);const double Width=I==6?112:55;const FVector2D Position(8+(I==6?0:I%2)*57,28+(I/2)*17);auto Tile=SNew(SClassicAction).Entry(Entry).Icon(nullptr).Border(nullptr).Font(CF(7)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(-1).Click([this,Id,Token](){ClassicUse(Id,Token);});At(Canvas,Position,{Width,15},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Active?FLinearColor(.3f,.25f,.1f,.6f):FLinearColor(0,0,0,.15f)).Padding(0)[Tile]);}
 int32 Index=0;for(const auto& Value:CA(Pet,TEXT("effects"))){if(Index>=8||Value->Type!=EJson::Object)break;auto Effect=Value->AsObject();auto Image=SNew(SOverlay);Image->AddSlot()[SNew(SImage).Image(ClassicIcon(int32(CN(Effect,TEXT("icon"),-1))))];if(CN(Effect,TEXT("border"),-1)>=0)Image->AddSlot()[SNew(SImage).Image(ClassicIcon(int32(CN(Effect,TEXT("border"))),true))];Image->SetToolTipText(FText::FromString(TEXT("Pet effect")));At(Canvas,{4+Index*15.,130},{14,14},Image);++Index;}
 At(Canvas,{8,149},{112,34},CT(CS(Pet,TEXT("feedback")),7,Gold));ClassicPetBox->SetContent(SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){ClassicPetPosition+=Delta;}).End([this](){SaveClassicLayout();}));
}

void UDAoCBridgeSubsystem::CancelClassicConcentration(TSharedPtr<FJsonObject> Entry){if(!bLocalAvailable||bExiting||!Entry.IsValid())return;auto Concentration=CO(ClassicState,TEXT("concentration"));bool Pending=false,Stale=false;if(Concentration.IsValid()){Concentration->TryGetBoolField(TEXT("pending"),Pending);Concentration->TryGetBoolField(TEXT("stale"),Stale);}if(Pending||Stale)return;auto Value=MakeShared<FJsonObject>();Value->SetNumberField(TEXT("concentration_index"),CN(Entry,TEXT("index"),-1));Value->SetStringField(TEXT("concentration_token"),CS(Entry,TEXT("token")));Send(TEXT("conc_cancel"),Value);}
void UDAoCBridgeSubsystem::RefreshClassicConcentration(){
 if(!ClassicConcentrationBox.IsValid())return;auto Concentration=CO(ClassicState,TEXT("concentration"));bool Visible=false;if(Concentration.IsValid())Concentration->TryGetBoolField(TEXT("visible"),Visible);ClassicConcentrationBox->SetVisibility(Visible?EVisibility::Visible:EVisibility::Collapsed);if(!Visible)return;auto Entries=CA(Concentration,TEXT("entries"));const int32 Pages=FMath::Max(1,FMath::DivideAndRoundUp(Entries.Num(),18));ClassicConcentrationPage=FMath::Clamp(ClassicConcentrationPage,0,Pages-1);FString Stamp;FJsonSerializer::Serialize(Concentration,TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::FromInt(ClassicConcentrationPage);if(Stamp==ClassicConcentrationSignature&&ClassicConcentrationBox->GetChildren()->Num()>0)return;ClassicConcentrationSignature=Stamp;
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{128,96},SNew(SImage).Image(ClassicArt(TEXT("leftbot_scrl"))));const double Maximum=CN(Concentration,TEXT("maximum")),Remaining=CN(Concentration,TEXT("remaining"));bool PoolKnown=false;Concentration->TryGetBoolField(TEXT("pool_known"),PoolKnown);At(Canvas,{8,3},{100,10},CT(PoolKnown?FString::Printf(TEXT("CONC %.0f / %.0f"),Remaining,Maximum):TEXT("CONC \u2014"),7));if(PoolKnown)At(Canvas,{8,14},{100,7},SNew(SProgressBar).Style(&ClassicBarStyle()).FillColorAndOpacity(FLinearColor(1,.8f,.12f)).Percent(float(Maximum>0?FMath::Clamp(Remaining/Maximum,0.,1.):0.)));
 for(int32 AtIndex=ClassicConcentrationPage*18;AtIndex<FMath::Min(Entries.Num(),(ClassicConcentrationPage+1)*18);++AtIndex){if(Entries[AtIndex]->Type!=EJson::Object)continue;auto Row=Entries[AtIndex]->AsObject();const int32 Tile=AtIndex%18;const FString Tip=FString::Printf(TEXT("%s \u00b7 %s\n%.0f concentration\nShift + right-click: cancel"),*CS(Row,TEXT("name")),*CS(Row,TEXT("owner")),CN(Row,TEXT("conc")));At(Canvas,{7+(Tile%6)*17.,26+(Tile/6)*17.},{16,16},SNew(SClassicConcentrationIcon).Icon(ClassicIcon(int32(CN(Row,TEXT("icon"),-1)))).Border(ClassicIcon(int32(CN(Row,TEXT("border"),-1)),true)).Tip(Tip).Cancel([this,Row](){CancelClassicConcentration(Row);}));}
 At(Canvas,{115,10},{12,12},SNew(SBox).IsEnabled(ClassicConcentrationPage>0)[CB(CT(TEXT("")),[this](){--ClassicConcentrationPage;RefreshClassicConcentration();})]);At(Canvas,{115,76},{12,12},SNew(SBox).IsEnabled(ClassicConcentrationPage+1<Pages)[CB(CT(TEXT("")),[this](){++ClassicConcentrationPage;RefreshClassicConcentration();})]);At(Canvas,{8,80},{100,10},CT(FString::Printf(TEXT("%d / %d"),ClassicConcentrationPage+1,Pages),7,Gold));At(Canvas,{8,100},{112,34},CT(CS(Concentration,TEXT("feedback")).IsEmpty()?TEXT("Shift + right-click: cancel"):CS(Concentration,TEXT("feedback")),7));ClassicConcentrationBox->SetContent(SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){ClassicConcentrationPosition+=Delta;}).End([this](){SaveClassicLayout();}));
}


bool UDAoCBridgeSubsystem::CloseClassicVault(bool Notify){
 if(!bClassicVaultOpen&&!ClassicVaultOverlay.IsValid())return false;
 if(Notify){auto Vault=CO(InventoryState,TEXT("vault"));if(Vault.IsValid()&&!CS(Vault,TEXT("token")).IsEmpty()){auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("vault_token"),CS(Vault,TEXT("token")));Send(TEXT("vault_close"),Value);}}
 bClassicVaultOpen=false;bInventoryMoving=false;ClassicVaultSignature.Empty();
 if(ClassicVaultOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicVaultOverlay.ToSharedRef());
 ClassicVaultOverlay.Reset();ClassicVaultPanel.Reset();return true;
}
void UDAoCBridgeSubsystem::ActivateClassicInventorySlot(int32 Slot){
 ClassicLastInventorySlot=-1;ClassicLastInventoryClickAt=0;if(Slot<0||Slot>=80||!InventoryItem(Slot).IsValid())return;
 SendItemAction(Slot>=40?TEXT("inventory_equip"):TEXT("inventory_unequip"),Slot);bInventoryMoving=false;
}
void UDAoCBridgeSubsystem::ClassicVaultSlotClicked(int32 Slot){
 bool Pending=false;if(InventoryState.IsValid())InventoryState->TryGetBoolField(TEXT("pending"),Pending);if(Pending)return;
 const double Now=FPlatformTime::Seconds();if(Slot<80&&Slot==ClassicLastInventorySlot&&Now-ClassicLastInventoryClickAt<.5){ActivateClassicInventorySlot(Slot);RefreshClassicPanel();return;}ClassicLastInventorySlot=Slot;ClassicLastInventoryClickAt=Now;
 if(bInventoryMoving){if(SelectedItemSlot!=Slot)SendItemAction(TEXT("inventory_move"),SelectedItemSlot,Slot);bInventoryMoving=false;}
 else if(InventoryItem(Slot).IsValid()){SelectedItemSlot=Slot;bInventoryMoving=true;}
 RefreshClassicPanel();RefreshClassicVault();RefreshClassicMerchant();
}
void UDAoCBridgeSubsystem::RefreshClassicVault(){
 if(!GetWorld()||!GetWorld()->GetGameViewport())return;auto* Viewport=GetWorld()->GetGameViewport();auto Vault=CO(InventoryState,TEXT("vault"));bool Valid=false;if(Vault.IsValid())Vault->TryGetBoolField(TEXT("valid"),Valid);
 const int32 Serial=int32(CN(Vault,TEXT("open_serial"),-1));
 if(Serial!=ClassicVaultSerial){ClassicVaultSerial=Serial;ClassicVaultPage=0;bClassicVaultOpen=Valid;ClassicVaultSignature.Empty();if(Valid&&ClassicState.IsValid())SetClassicTab(TEXT("inventory"));}
 if(!Valid||!bClassicVaultOpen){CloseClassicVault(false);return;}
 const int32 First=int32(CN(Vault,TEXT("first"))),Count=int32(CN(Vault,TEXT("count")));if(!((First==110&&Count==40)||(First==150&&Count==100))){CloseClassicVault(false);return;}
 const int32 Pages=(Count+19)/20;ClassicVaultPage=FMath::Clamp(ClassicVaultPage,0,Pages-1);
 FString Stamp;if(InventoryState.IsValid())FJsonSerializer::Serialize(InventoryState,TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::Printf(TEXT("/%d/%d/%d"),ClassicVaultPage,SelectedItemSlot,bInventoryMoving?1:0);
 if(ClassicVaultOverlay.IsValid()&&Stamp==ClassicVaultSignature)return;ClassicVaultSignature=Stamp;
 if(ClassicVaultOverlay.IsValid())Viewport->RemoveViewportWidgetContent(ClassicVaultOverlay.ToSharedRef());ClassicVaultOverlay.Reset();ClassicVaultPanel.Reset();
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{224,400},SNew(SImage).Image(ClassicArt(TEXT("vault"))));At(Canvas,{0,400},{224,40},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.025f,.02f,.98f)));
 At(Canvas,{13,2},{190,15},CT(CS(Vault,TEXT("title")),8,Gold));At(Canvas,{210,1},{12,14},CB(CT(TEXT("\u00d7"),9),[this](){CloseClassicVault();}));
 for(int32 Row=0;Row<20;++Row){
  const int32 Slot=First+ClassicVaultPage*20+Row;auto Item=InventoryItem(Slot);auto Entry=ClassicEntry(FString::Printf(TEXT("srv:%d"),Slot));
  auto Click=[this,Slot](){ClassicVaultSlotClicked(Slot);};
  auto Withdraw=[this,Slot](){if(!InventoryItem(Slot).IsValid())return;for(int32 Free=40;Free<80;++Free)if(!InventoryItem(Free).IsValid()){SendItemAction(TEXT("inventory_move"),Slot,Free);return;}};
  auto Drop=[this,Slot](TSharedRef<FClassicDrag> Drag){if(Drag->InventorySlot<0||Drag->InventorySlot==Slot||Drag->ItemToken.IsEmpty()||Drag->VaultToken!=CS(CO(InventoryState,TEXT("vault")),TEXT("token"))||CS(InventoryItem(Drag->InventorySlot),TEXT("token"))!=Drag->ItemToken)return;SendItemAction(TEXT("inventory_move"),Drag->InventorySlot,Slot);};
  At(Canvas,{6,20+Row*18.},{16,16},SNew(SClassicAction).Entry(Entry).Icon(ClassicIcon(int32(CN(Item,TEXT("icon"),-1)))).Border(nullptr).Font(CF(6)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(Slot).VaultToken(CS(Vault,TEXT("token"))).Click(Click).DoubleClick(Withdraw).Inspect([this,Entry](){if(Entry.IsValid())ClassicInspect(CS(Entry,TEXT("id")),CS(Entry,TEXT("token")));}).Hover([this,Entry](){if(Entry.IsValid())ClassicHover(CS(Entry,TEXT("id")),CS(Entry,TEXT("token")));}).HoverText_Lambda([this,Entry](){return ClassicHoverText(CS(Entry,TEXT("id")),CS(Entry,TEXT("token")));}).Drop(Drop));
  FString Name=CS(Item,TEXT("name"));if(CN(Item,TEXT("count"))>1)Name+=FString::Printf(TEXT(" x%.0f"),CN(Item,TEXT("count")));auto Label=CT(Name,8,Slot==SelectedItemSlot&&bInventoryMoving?Gold:Cream);At(Canvas,{25,20+Row*18.},{192,17},MakeClassicHoverLabel(CB(Label,Click),CS(Entry,TEXT("id")),CS(Entry,TEXT("token"))));
 }
 At(Canvas,{60,383},{18,14},CB(CT(TEXT("<"),8),[this](){--ClassicVaultPage;RefreshClassicVault();}));At(Canvas,{80,383},{66,14},CT(FString::Printf(TEXT("%d / %d"),ClassicVaultPage+1,Pages),8,Gold));At(Canvas,{148,383},{18,14},CB(CT(TEXT(">"),8),[this](){++ClassicVaultPage;RefreshClassicVault();}));
 const FString Feedback=CS(InventoryState,TEXT("feedback"));At(Canvas,{6,404},{212,34},CT(Feedback.IsEmpty()?TEXT("Drag between backpack and vault. Double-click an icon to withdraw."):Feedback,7));
 ClassicVaultPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){ClassicVaultPosition+=Delta;}).End([this](){SaveClassicLayout();});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){FVector2D Size;Size=UIViewportSize();Size/=ClassicScale();return FVector2D(FMath::Clamp(ClassicVaultPosition.X,0.,FMath::Max(0.,Size.X-224)),FMath::Clamp(ClassicVaultPosition.Y,0.,FMath::Max(0.,Size.Y-440)));}).Size(FVector2D(224,440))[ClassicVaultPanel.ToSharedRef()];ClassicVaultOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];Viewport->AddViewportWidgetContent(ClassicVaultOverlay.ToSharedRef(),34);
}

void UDAoCBridgeSubsystem::CloseClassicMerchant(bool Notify){
 if(ClassicMerchantOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ClassicMerchantOverlay.ToSharedRef());
 ClassicMerchantOverlay.Reset();ClassicMerchantPanel.Reset();ClassicMerchantSignature.Empty();
 if(Notify)Send(TEXT("dismiss_interaction"));
}

void UDAoCBridgeSubsystem::RefreshClassicMerchant(){
 if(!GetWorld()||!GetWorld()->GetGameViewport())return;
 auto Merchant=CO(InteractionState,TEXT("merchant")),Pages=CO(Merchant,TEXT("pages"));
 if(!Pages.IsValid()||Pages->Values.IsEmpty()){CloseClassicMerchant(false);ClassicMerchantId.Empty();return;}
 const FString Id=CS(Merchant,TEXT("entity_id"));
 if(Id!=ClassicMerchantId){ClassicMerchantId=Id;ClassicMerchantPage=0;ClassicMerchantSelected=-1;ClassicMerchantClickAt=0;ClassicMerchantSignature.Empty();}
 TArray<int32> PageNumbers;for(int32 I=0;I<10;++I)if(Pages->HasField(FString::FromInt(I)))PageNumbers.Add(I);if(PageNumbers.IsEmpty())return;
 if(!PageNumbers.Contains(ClassicMerchantPage))ClassicMerchantPage=PageNumbers[0];
 FString Stamp;FJsonSerializer::Serialize(Merchant.ToSharedRef(),TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::Printf(TEXT("/%d/%d/%d/%lld/%s"),ClassicMerchantPage,ClassicMerchantSelected,SelectedItemSlot,int64(CN(InventoryState,TEXT("revision"))),*CS(InventoryState,TEXT("feedback")));
 if(ClassicMerchantOverlay.IsValid()&&Stamp==ClassicMerchantSignature)return;
 CloseClassicMerchant(false);ClassicMerchantSignature=Stamp;
 auto Canvas=SNew(SCanvas);At(Canvas,{0,0},{350,448},SNew(SImage).Image(ClassicArt(TEXT("merchant"))));
 At(Canvas,{16,2},{318,14},CT(CS(Merchant,TEXT("name")),11,Gold));At(Canvas,{333,1},{15,16},CB(CT(TEXT("X"),9),[this](){CloseClassicMerchant();}));
 auto List=SNew(SVerticalBox);TSharedPtr<FJsonObject> Selected;
 const int64 Catalog=int64(CN(Merchant,TEXT("catalog_revision"),-1));const int32 Page=ClassicMerchantPage;
 for(auto Value:CA(Pages,*FString::FromInt(Page))){
  auto Item=Value->AsObject();const int32 Index=int32(CN(Item,TEXT("index"),-1));if(Index<0||Index>29)continue;if(Index==ClassicMerchantSelected)Selected=Item;
  bool TravelAvailable=true;Item->TryGetBoolField(TEXT("travel_available"),TravelAvailable);
  auto Buy=[this,Page,Index,Id,Catalog,TravelAvailable](){if(TravelAvailable)BuyMerchantItem(Page,Index,Id,Catalog);};
  auto Select=[this,Index,Buy](){const double Now=FPlatformTime::Seconds();const bool Twice=ClassicMerchantSelected==Index&&Now-ClassicMerchantClickAt<=.5;ClassicMerchantSelected=Index;ClassicMerchantClickAt=Now;if(Twice)Buy();RefreshClassicMerchant();};
  auto Row=SNew(SHorizontalBox);
  Row->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(18).HeightOverride(18)[SNew(SClassicAction).Entry(Item).Icon(ClassicIcon(int32(CN(Item,TEXT("icon"),-1)))).Border(nullptr).Font(CF(6)).Bar(-1).Bank(-1).Slot(-1).InventorySlot(-1).Click(Select).DoubleClick(Buy)]];
  Row->AddSlot().FillWidth(1)[CB(CT(CS(Item,TEXT("name")),8,!TravelAvailable?FLinearColor(.4,.4,.4,1):Index==ClassicMerchantSelected?Gold:Cream),Select)];
  List->AddSlot().AutoHeight()[SNew(SBox).HeightOverride(18)[SNew(SBorder).Padding(0).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(Index==ClassicMerchantSelected?FLinearColor(.25,.2,.08,.45):FLinearColor(0,0,0,.05))[Row]]];
 }
 At(Canvas,{8,20},{324,360},SNew(SScrollBox)+SScrollBox::Slot()[List]);
 const int64 Price=int64(CN(Selected,TEXT("price")));const int64 Divisors[]={10000000000LL,10000000LL,10000LL,100LL,1LL};const int64 Limits[]={1000,1000,1000,100,100};const double CoinX[]={64,109,154,199,244};
 for(int32 I=0;I<5;++I){At(Canvas,{CoinX[I],392},{33,13},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor(.02,.02,.02,1)).Padding(0)[CT(Selected.IsValid()?FString::Printf(TEXT("%lld"),(Price/Divisors[I])%Limits[I]):TEXT(""),8)]);}
 bool TravelAvailable=true;if(Selected)Selected->TryGetBoolField(TEXT("travel_available"),TravelAvailable);
 At(Canvas,{8,406},{328,14},CT(TravelAvailable?CS(InventoryState,TEXT("feedback")):CS(Selected,TEXT("travel_reason")),7,Gold));
 const int32 Position=PageNumbers.Find(Page);
 for(int32 Direction:{-1,1}){const int32 Next=PageNumbers[FMath::Clamp(Position+Direction,0,PageNumbers.Num()-1)];At(Canvas,{Direction<0?10.:96.,426},{22,16},CB(CT(Direction<0?TEXT("<"):TEXT(">"),9),[this,Next](){ClassicMerchantPage=Next;ClassicMerchantSelected=-1;ClassicMerchantClickAt=0;RefreshClassicMerchant();}));}
 At(Canvas,{34,428},{60,12},CT(FString::Printf(TEXT("%d / %d"),Position+1,PageNumbers.Num()),8));
 bool Pending=false;if(InventoryState)InventoryState->TryGetBoolField(TEXT("pending"),Pending);
 At(Canvas,{250,424},{80,18},SNew(SBox).IsEnabled(Selected.IsValid()&&TravelAvailable&&!Pending&&CN(Merchant,TEXT("window"),-1)==0)[CB(CT(TEXT("BUY"),10),[this,Page,Id,Catalog](){if(ClassicMerchantSelected>=0)BuyMerchantItem(Page,ClassicMerchantSelected,Id,Catalog);})]);
 At(Canvas,{160,424},{70,18},SNew(SBox).IsEnabled(SelectedItemSlot>=40&&SelectedItemSlot<80&&InventoryItem(SelectedItemSlot).IsValid()&&!Pending)[CB(CT(TEXT("SELL"),10),[this](){bInventoryMoving=false;SendItemAction(TEXT("merchant_sell"),SelectedItemSlot);})]);
 auto Drop=SNew(SClassicShopDrop).Sell([this](int32 Slot,const FString& Token){if(CS(InventoryItem(Slot),TEXT("token"))==Token){bInventoryMoving=false;SendItemAction(TEXT("merchant_sell"),Slot);}})[Canvas];
 ClassicMerchantPanel=SNew(SClassicMove).Content(Drop).Move([this](FVector2D Delta){if(ClassicMerchantPosition.X<0)ClassicMerchantPosition.X=FMath::Max(0.,(UIViewportSize().X/ClassicScale()-350)*.5);ClassicMerchantPosition+=Delta;});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){const FVector2D Size=UIViewportSize()/ClassicScale();const double X=ClassicMerchantPosition.X<0?(Size.X-350)*.5:ClassicMerchantPosition.X;return FVector2D(FMath::Clamp(X,0.,FMath::Max(0.,Size.X-350)),FMath::Clamp(ClassicMerchantPosition.Y,0.,FMath::Max(0.,Size.Y-448)));}).Size(FVector2D(350,448))[ClassicMerchantPanel.ToSharedRef()];
 ClassicMerchantOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ClassicMerchantOverlay.ToSharedRef(),35);
}

// Shares the original inventory drag operation and classic art helpers in this translation unit.
#include "DAoCBridgeExchange.inl"
#include "DAoCBridgeGuild.inl"
#include "DAoCBridgeEmblemPicker.inl"
