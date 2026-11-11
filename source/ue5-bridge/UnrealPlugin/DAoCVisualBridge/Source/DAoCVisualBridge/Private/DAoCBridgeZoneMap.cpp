#include "DAoCBridgeSubsystem.h"
#include "DAoCBridgeQuestIndicator.h"
#include "DAoCBridgeQuestMap.h"
#include "DAoCBridgeCharacter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Framework/MultiBox/MultiBoxBuilder.h"
#include "Widgets/SCanvas.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "InputCoreTypes.h"
namespace {
TSharedPtr<FJsonObject> O(const TSharedPtr<FJsonObject>& V,const FString& Key){const TSharedPtr<FJsonObject>* P=nullptr;return V.IsValid()&&V->TryGetObjectField(Key,P)?*P:nullptr;}
FString S(const TSharedPtr<FJsonObject>& V,const TCHAR* Key){FString T;if(V.IsValid())V->TryGetStringField(Key,T);return T;}
double N(const TSharedPtr<FJsonObject>& V,const TCHAR* Key,double Default=0){double D=Default;if(V.IsValid())V->TryGetNumberField(Key,D);return D;}
TArray<TSharedPtr<FJsonValue>> A(const TSharedPtr<FJsonObject>& V,const TCHAR* Key){const TArray<TSharedPtr<FJsonValue>>* P=nullptr;return V.IsValid()&&V->TryGetArrayField(Key,P)?*P:TArray<TSharedPtr<FJsonValue>>();}
FSlateFontInfo Font(int32 Size){return FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-bold.ttf"),Size);}
TSharedRef<STextBlock> Label(const FString& Text,int32 Size=9){return SNew(STextBlock).Text(FText::FromString(Text)).Font(Font(Size)).ColorAndOpacity(FLinearColor(.95,.89,.7));}
class SZoneMapFrame:public SCompoundWidget {
public:SLATE_BEGIN_ARGS(SZoneMapFrame){}SLATE_ARGUMENT(TSharedPtr<SWidget>,Content)SLATE_ARGUMENT(TFunction<void(FVector2D)>,Move)SLATE_ARGUMENT(TFunction<void()>,End)SLATE_END_ARGS()
void Construct(const FArguments& Args){Move=Args._Move;End=Args._End;ChildSlot[Args._Content.ToSharedRef()];}
FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)override{auto P=G.AbsoluteToLocal(E.GetScreenSpacePosition());if(E.GetEffectingButton()==EKeys::LeftMouseButton&&P.X<14&&P.Y<14){Last=P;Dragging=true;return FReply::Handled().CaptureMouse(SharedThis(this));}return FReply::Unhandled();}
FReply OnMouseMove(const FGeometry& G,const FPointerEvent& E)override{if(!Dragging)return FReply::Unhandled();auto Delta=G.AbsoluteToLocal(E.GetScreenSpacePosition())-Last;if(Move)Move(Delta);return FReply::Handled();}
FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent&)override{if(!Dragging)return FReply::Unhandled();Dragging=false;if(End)End();return FReply::Handled().ReleaseMouseCapture();}
private:bool Dragging=false;FVector2D Last;TFunction<void(FVector2D)> Move;TFunction<void()> End;
};
struct FZoneQuestMark
{
    FVector2D Fraction;
    int32 Indicator;
};
class SZoneMapPicture:public SCompoundWidget {
public:SLATE_BEGIN_ARGS(SZoneMapPicture){}SLATE_ARGUMENT(const FSlateBrush*,Image)SLATE_ARGUMENT(TFunction<FVector2D()>,Fraction)SLATE_ARGUMENT(TFunction<FVector2D()>,Forward)SLATE_ARGUMENT(TFunction<TArray<FZoneQuestMark>()>,QuestMarks)SLATE_ARGUMENT(TFunction<void(FVector2D)>,Click)SLATE_END_ARGS()
void Construct(const FArguments& Args){Fraction=Args._Fraction;Forward=Args._Forward;QuestMarks=Args._QuestMarks;Click=Args._Click;ChildSlot[SNew(SImage).Image(Args._Image)];}
FReply OnMouseButtonDown(const FGeometry& G,const FPointerEvent& E)override{if(E.GetEffectingButton()==EKeys::LeftMouseButton&&Click){Click(G.AbsoluteToLocal(E.GetScreenSpacePosition())/G.GetLocalSize());return FReply::Handled();}return FReply::Unhandled();}
int32 OnPaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Cull,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled)const override {
 Layer=SCompoundWidget::OnPaint(Args,G,Cull,Out,Layer,Style,Enabled);if(!Fraction)return Layer;
 if(QuestMarks)
 {
  for(const auto& Mark:QuestMarks())
  {
   const FVector2D Center=Mark.Fraction*G.GetLocalSize();
   if(Mark.Indicator==0)
   {
       TArray<FVector2D> Circle;
       for(int32 I=0;I<=16;++I)
       {
           const double Angle=UE_TWO_PI*I/16.0;
           Circle.Add(Center+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*.5);
       }
       FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Circle,ESlateDrawEffect::None,FLinearColor(.08,.05,0),true,7);
       FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),Circle,ESlateDrawEffect::None,FLinearColor(.95,.2,.15),true,5);
       continue;
   }
   const FLinearColor Tint=BridgeQuestIndicator::Color(Mark.Indicator);
   TArray<FVector2D> Stem;
   if(Mark.Indicator==2) Stem={Center+FVector2D(-2,-3),Center+FVector2D(0,-5),Center+FVector2D(2,-3),Center+FVector2D(0,-1)};
   else if(Mark.Indicator==16) Stem={Center+FVector2D(-3,0),Center+FVector2D(0,-3),Center+FVector2D(3,0),Center+FVector2D(0,3),Center+FVector2D(-3,0)};
   else Stem={Center+FVector2D(0,-5),Center+FVector2D(0,-1)};
   FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Stem,ESlateDrawEffect::None,Tint,true,2);
   if(Mark.Indicator!=16)
   {
       const TArray<FVector2D> Dot={Center+FVector2D(0,2),Center+FVector2D(0,3)};
       FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Dot,ESlateDrawEffect::None,Tint,true,2);
   }
  }
  Layer+=2;
 }
 auto F=Fraction();if(F.X<0||F.Y<0||F.X>1||F.Y>1)return Layer;
 FVector2D At=F*G.GetLocalSize(),Dir=Forward?Forward().GetSafeNormal():FVector2D(0,-1),Side=FVector2D(-Dir.Y,Dir.X);TArray<FVector2D> Points={At+Dir*7,At-Dir*4+Side*4.5,At-Dir*2,At-Dir*4-Side*4.5,At+Dir*7};
 FSlateDrawElement::MakeLines(Out,++Layer,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,FLinearColor(.1,.04,0),true,3);FSlateDrawElement::MakeLines(Out,++Layer,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,FLinearColor(1,.85,.25),true,1.5);return Layer;
}
private:TFunction<FVector2D()> Fraction,Forward;TFunction<TArray<FZoneQuestMark>()> QuestMarks;TFunction<void(FVector2D)> Click;
};
}
void UDAoCBridgeSubsystem::LoadZoneMaps(){if(ZoneMaps.IsValid())return;FString Text;if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/maps/maps.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),ZoneMaps);}
TSharedPtr<FJsonObject> UDAoCBridgeSubsystem::ShownZoneMap()const{if(ZoneMapRegion>=0)return O(O(ZoneMaps,TEXT("regions")),FString::FromInt(ZoneMapRegion));auto Zone=O(O(ZoneMaps,TEXT("zones")),FString::FromInt(ZoneMapZone));auto Areas=A(Zone,TEXT("areas"));return ZoneMapArea>=0&&Areas.IsValidIndex(ZoneMapArea)?Areas[ZoneMapArea]->AsObject():Zone;}
FVector2D UDAoCBridgeSubsystem::ZoneMapFraction(FVector2D Units)const{
 if(!bLocalAvailable)return {-1,-1};
 if(ZoneMapRegion>=0){for(auto V:A(ShownZoneMap(),TEXT("zones"))){auto Q=V->AsObject();if(int32(N(Q,TEXT("zone")))==207)return {(N(Q,TEXT("left"))+Units.X/65536*N(Q,TEXT("width")))/256.,(N(Q,TEXT("top"))+Units.Y/65536*N(Q,TEXT("height")))/256.};}return {-1,-1};}
 if(ZoneMapZone!=207)return {-1,-1};auto Zone=O(O(ZoneMaps,TEXT("zones")),TEXT("207"));auto R=A(Zone,TEXT("map_rect"));FVector2D Offset=R.Num()==4?FVector2D(R[0]->AsNumber(),R[1]->AsNumber()):FVector2D::ZeroVector,Size=R.Num()==4?FVector2D(R[2]->AsNumber(),R[3]->AsNumber()):FVector2D(65536,65536);
 if(ZoneMapArea>=0){auto Rect=A(ShownZoneMap(),TEXT("rect"));if(Rect.Num()!=4)return {-1,-1};Offset+=FVector2D(Rect[0]->AsNumber(),Rect[1]->AsNumber());Size=FVector2D(Rect[2]->AsNumber(),Rect[3]->AsNumber());}return Size.X>0&&Size.Y>0?(Units-Offset)/Size:FVector2D(-1,-1);
}
void UDAoCBridgeSubsystem::FollowZoneMap(){
 LoadZoneMaps();int32 Area=-1;const FVector2D Units((PlayerPosition.X/100+1364)*40,(PlayerPosition.Y/100+1263)*40);auto Areas=A(O(O(ZoneMaps,TEXT("zones")),TEXT("207")),TEXT("areas"));
 for(int32 I=0;I<Areas.Num();++I){auto Rect=A(Areas[I]->AsObject(),TEXT("rect"));if(Rect.Num()==4&&Units.X>Rect[0]->AsNumber()&&Units.Y>Rect[1]->AsNumber()&&Units.X<=Rect[0]->AsNumber()+Rect[2]->AsNumber()&&Units.Y<=Rect[1]->AsNumber()+Rect[3]->AsNumber()){Area=I;break;}}
 if(ZoneMapZone!=207||ZoneMapRegion>=0||ZoneMapArea!=Area){ZoneMapZone=207;ZoneMapRegion=-1;ZoneMapArea=Area;if(bZoneMapOpen)RefreshZoneMap();}
}
void UDAoCBridgeSubsystem::ToggleZoneMap(){if(bZoneMapOpen){CloseZoneMap();return;}LoadZoneMaps();bZoneMapOpen=true;if(bZoneMapFollow)FollowZoneMap();RefreshZoneMap();}
void UDAoCBridgeSubsystem::CloseZoneMap(){if(ZoneMapOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ZoneMapOverlay.ToSharedRef());ZoneMapOverlay.Reset();ZoneMapPanel.Reset();bZoneMapOpen=false;}
void UDAoCBridgeSubsystem::RefreshZoneMap(){
 if(!bZoneMapOpen||!GetWorld()||!GetWorld()->GetGameViewport())return;
 if(ZoneMapOverlay.IsValid())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(ZoneMapOverlay.ToSharedRef());
 auto C=SNew(SCanvas);auto Add=[&](FVector2D P,FVector2D Size,TSharedRef<SWidget> W){C->AddSlot().Position(P).Size(Size)[W];};
 auto Frame=ClassicArt(TEXT("chatext"),{0,.5},{1,1});if(Frame){auto Brush=MakeShared<FSlateBrush>(*Frame);Brush->DrawAs=ESlateBrushDrawType::Box;Brush->Margin=FMargin(.01,.2,.03,.05);ClassicBrushes.Add(TEXT("__map_frame"),Brush);Frame=&Brush.Get();}
 Add({0,0},{292,336},SNew(SBorder).BorderImage(Frame?Frame:FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(Frame?FLinearColor::White:FLinearColor(.07,.065,.06,1)));
 auto Shown=ShownZoneMap();FString Title=S(Shown,TEXT("name"));if(Title.IsEmpty())Title=S(O(O(ZoneMaps,TEXT("zones")),FString::FromInt(ZoneMapZone)),TEXT("name"));Add({17,3},{245,16},Label(Title.ToUpper()));
 Add({269,2},{17,17},SNew(SButton).IsFocusable(false).ContentPadding(0).OnClicked_Lambda([this](){CloseZoneMap();return FReply::Handled();})[Label(TEXT("×"))]);
 Add({12,22},{190,18},SNew(SComboButton).IsFocusable(false).OnGetMenuContent_Lambda([this](){
  FMenuBuilder Menu(true,nullptr);auto Pick=[this](int32 Zone,int32 Area,int32 Region){ZoneMapZone=Zone;ZoneMapArea=Area;ZoneMapRegion=Region;bZoneMapFollow=false;RefreshZoneMap();};
  auto Zones=O(ZoneMaps,TEXT("zones"));TArray<FString> Keys;if(Zones.IsValid())for(auto& Pair:Zones->Values)Keys.Add(FString(Pair.Key));Keys.Sort([&](const FString& L,const FString& R){if(L==TEXT("209"))return R!=L;if(R==TEXT("209"))return false;return S(O(Zones,L),TEXT("name"))<S(O(Zones,R),TEXT("name"));});
  for(auto Key:Keys){auto Z=O(Zones,Key);const int32 Region=int32(N(Z,TEXT("region"),-1));if((Region!=200&&Region!=181)||int32(N(Z,TEXT("type")))!=0&&Key!=TEXT("209"))continue;const int32 Id=FCString::Atoi(*Key);Menu.AddMenuEntry(FText::FromString(S(Z,TEXT("name"))),FText(),FSlateIcon(),FUIAction(FExecuteAction::CreateLambda([Pick,Id](){Pick(Id,-1,-1);})));auto Areas=A(Z,TEXT("areas"));for(int32 I=0;I<Areas.Num();++I){const auto Area=Areas[I]->AsObject();Menu.AddMenuEntry(FText::FromString(TEXT("  ")+S(Area,TEXT("name"))),FText(),FSlateIcon(),FUIAction(FExecuteAction::CreateLambda([Pick,Id,I](){Pick(Id,I,-1);})));}}
  Menu.AddMenuSeparator();for(int32 Id:{200,181}){auto R=O(O(ZoneMaps,TEXT("regions")),FString::FromInt(Id));if(R.IsValid())Menu.AddMenuEntry(FText::FromString(S(R,TEXT("name"))),FText(),FSlateIcon(),FUIAction(FExecuteAction::CreateLambda([Pick,Id](){Pick(207,-1,Id);})));}return Menu.MakeWidget();
 }).ButtonContent()[Label(TEXT("Select map"),8)]);
 Add({210,22},{70,18},SNew(SButton).IsFocusable(false).OnClicked_Lambda([this](){bZoneMapFollow=!bZoneMapFollow;if(bZoneMapFollow)FollowZoneMap();RefreshZoneMap();return FReply::Handled();})[Label(bZoneMapFollow?TEXT("Follow: ON"):TEXT("Follow: OFF"),8)]);
 FString Image=S(Shown,TEXT("map"));Image.RemoveFromEnd(TEXT(".png"));const FSlateBrush* Art=Image.IsEmpty()?nullptr:ClassicArt(TEXT("maps/")+Image);
 Add({16,46},{260,260},SNew(SZoneMapPicture).Image(Art).QuestMarks([this](){
    TArray<FZoneQuestMark> Marks;
    for(const auto& Pair:EntityRows)
    {
        const auto& Row=Pair.Value;
        const int32 Indicator=Row?BridgeQuestIndicator::FromRow(*Row):0;
        if(!Indicator)continue;
        const auto Position=A(Row,TEXT("position_m"));
        if(Position.Num()!=3)continue;
        const FVector2D Fraction=ZoneMapFraction({Position[0]->AsNumber()*40,Position[2]->AsNumber()*40});
        if(Fraction.X>=0&&Fraction.X<=1&&Fraction.Y>=0&&Fraction.Y<=1)Marks.Add({Fraction,Indicator});
    }
    for(const FVector2D& Point:BridgeQuestMap::StepUnits(ClassicState))
    {
        const FVector2D Fraction=ZoneMapFraction(Point);
        if(Fraction.X>=0&&Fraction.X<=1&&Fraction.Y>=0&&Fraction.Y<=1)Marks.Add({Fraction,0});
    }
    return Marks;
 }).Fraction([this](){return ZoneMapFraction({(PlayerPosition.X/100+1364)*40,(PlayerPosition.Y/100+1263)*40});}).Forward([this](){FVector Dir=PlayerPawn?PlayerPawn->GetActorForwardVector():FRotator(0,CameraYaw,0).Vector();return FVector2D(Dir.X,Dir.Y);}).Click([this](FVector2D P){if(ZoneMapRegion<0)return;for(auto V:A(ShownZoneMap(),TEXT("zones"))){auto Z=V->AsObject();FVector2D L(N(Z,TEXT("left"))/256.,N(Z,TEXT("top"))/256.),R=L+FVector2D(N(Z,TEXT("width"))/256.,N(Z,TEXT("height"))/256.);if(P.X>=L.X&&P.Y>=L.Y&&P.X<=R.X&&P.Y<=R.Y){ZoneMapZone=int32(N(Z,TEXT("zone")));ZoneMapRegion=-1;ZoneMapArea=-1;bZoneMapFollow=false;RefreshZoneMap();break;}}}));
 if(!Art)Add({30,150},{230,30},Label(TEXT("Map image unavailable")));
 Add({16,313},{260,18},Label(TEXT("M: map   Esc: close   Yellow arrow: you"),8));
 auto Panel=SNew(SZoneMapFrame).Content(C).Move([this](FVector2D Delta){ZoneMapPosition+=Delta;ZoneMapOverlay->Invalidate(EInvalidateWidgetReason::Layout);}).End([this](){SaveClassicLayout();});ZoneMapPanel=Panel;
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){auto Size=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(ZoneMapPosition.X,0.,FMath::Max(0.,Size.X-292)),FMath::Clamp(ZoneMapPosition.Y,0.,FMath::Max(0.,Size.Y-336)));}).Size(FVector2D(292,336))[Panel];ZoneMapOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];GetWorld()->GetGameViewport()->AddViewportWidgetContent(ZoneMapOverlay.ToSharedRef(),34);
}
