#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Components/PrimitiveComponent.h"
#include "Widgets/SCanvas.h"
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElements.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SDPIScaler.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SBox.h"
#include "Styling/CoreStyle.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "Misc/Paths.h"
namespace {
class SSpeechTail:public SLeafWidget {
public:SLATE_BEGIN_ARGS(SSpeechTail){}SLATE_END_ARGS()
void Construct(const FArguments&){}
FVector2D ComputeDesiredSize(float)const override{return FVector2D(14,8);}
int32 OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle&,bool)const override{
 for(int32 Y=0;Y<7;++Y){TArray<FVector2D> Row={FVector2D(Y,Y),FVector2D(14-Y,Y)};FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),Row,ESlateDrawEffect::None,FLinearColor(.025f,.03f,.035f,.93f),false,1.5f);}
 TArray<FVector2D> Edge={FVector2D(0,0),FVector2D(7,7),FVector2D(14,0)};FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Edge,ESlateDrawEffect::None,FLinearColor(.65f,.6f,.45f,.9f),true,1);return Layer+1;
}
};
FString Text(const TSharedPtr<FJsonObject>& O,const TCHAR* K){FString S;if(O.IsValid())O->TryGetStringField(K,S);return S;}
double Num(const TSharedPtr<FJsonObject>& O,const TCHAR* K,double D=0){if(O.IsValid())O->TryGetNumberField(K,D);return D;}
FSlateFontInfo Font(int32 Size){return FSlateFontInfo(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/InterfaceFonts/minionpro-regular.ttf"),Size);}
}
void UDAoCBridgeSubsystem::RemoveWorldMessages(){if(WorldMessageOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(WorldMessageOverlay.ToSharedRef());WorldMessageOverlay.Reset();WorldBubblePanels.Empty();WorldMessageSignature.Empty();WorldMessageUntil.Empty();}
void UDAoCBridgeSubsystem::ApplyWorldMessages(const TSharedPtr<FJsonObject>& Snapshot){
 const TSharedPtr<FJsonObject>* Chat=nullptr;if(!Snapshot.IsValid()||!Snapshot->TryGetObjectField(TEXT("chat"),Chat)){RemoveWorldMessages();return;}
 TArray<TSharedPtr<FJsonObject>> Bubbles,Notices;FString Signature;const double Now=FPlatformTime::Seconds();TSet<int64> Active;
 for(int32 Kind=0;Kind<2;++Kind){const TArray<TSharedPtr<FJsonValue>>* Rows=nullptr;if(!(*Chat)->TryGetArrayField(Kind==0?TEXT("bubbles"):TEXT("notices"),Rows))continue;for(int32 I=0;I<FMath::Min(Rows->Num(),Kind==0?8:3);++I){if((*Rows)[I]->Type!=EJson::Object)continue;auto Row=(*Rows)[I]->AsObject();const int64 Id=int64(Num(Row,TEXT("id")));const double Left=FMath::Clamp(Num(Row,TEXT("duration_ms"),6500)-Num(Row,TEXT("age_ms")),0.,14000.)/1000.;if(Left<=0)continue;Active.Add(Id);if(!WorldMessageUntil.Contains(Id))WorldMessageUntil.Add(Id,Now+Left);Signature+=FString::Printf(TEXT("%d:%lld;"),Kind,Id);(Kind==0?Bubbles:Notices).Add(Row);}}
 const TSharedPtr<FJsonObject>* Interaction=nullptr;const TSharedPtr<FJsonObject>* TalkPtr=nullptr;TSharedPtr<FJsonObject> Talk;
 if(Snapshot->TryGetObjectField(TEXT("interaction"),Interaction)&&(*Interaction)->TryGetObjectField(TEXT("talk"),TalkPtr)&&!(*TalkPtr)->Values.IsEmpty())Talk=*TalkPtr;
 if(Talk){const FString Entity=Text(Talk,TEXT("entity_id"));Bubbles.RemoveAll([&](const TSharedPtr<FJsonObject>& B){return Text(B,TEXT("entity_id"))==Entity;});auto Row=MakeShared<FJsonObject>();const int64 Id=-int64(Num(Talk,TEXT("id")))-1;Row->SetNumberField(TEXT("id"),double(Id));Row->SetStringField(TEXT("entity_id"),Entity);Row->SetStringField(TEXT("name"),Text(Talk,TEXT("name")));Row->SetStringField(TEXT("text"),Text(Talk,TEXT("text")));Row->SetBoolField(TEXT("conversation"),true);Bubbles.Add(Row);Active.Add(Id);WorldMessageUntil.FindOrAdd(Id)=Now+86400;Signature+=FString::Printf(TEXT("talk:%lld;"),Id);}
 for(auto It=WorldMessageUntil.CreateIterator();It;++It)if(!Active.Contains(It.Key()))It.RemoveCurrent();
 if(Signature==WorldMessageSignature)return;WorldMessageSignature=Signature;
 if(WorldMessageOverlay.IsValid())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(WorldMessageOverlay.ToSharedRef());
 WorldBubblePanels.Empty();
 if(Bubbles.IsEmpty()&&Notices.IsEmpty()){WorldMessageOverlay.Reset();return;}
 static const FSlateRoundedBoxBrush Background(FLinearColor(.025f,.03f,.035f,.93f),8.f,FLinearColor(.65f,.6f,.45f,.9f),1.f);
 auto C=SNew(SCanvas).Visibility(EVisibility::SelfHitTestInvisible);auto Alive=[this](int64 Id){const auto* Until=WorldMessageUntil.Find(Id);return Until&&FPlatformTime::Seconds()<*Until;};
 for(auto Row:Bubbles){
  const FString Entity=Text(Row,TEXT("entity_id"));const int64 Id=int64(Num(Row,TEXT("id")));bool Conversation=false;Row->TryGetBoolField(TEXT("conversation"),Conversation);
  FString Message=Text(Row,TEXT("text"));const FString Prefix=Text(Row,TEXT("name"))+TEXT(" says, \"");
  if(Message.StartsWith(Prefix)){Message=Message.Mid(Prefix.Len());Message.RemoveFromEnd(TEXT("\""));}
  auto Content=SNew(SVerticalBox);auto Title=SNew(SHorizontalBox);Title->AddSlot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Text(Row,TEXT("name")).Left(80))).Font(Font(9)).ColorAndOpacity(FLinearColor(1,.85f,.4f))];
  if(Conversation)Title->AddSlot().AutoWidth()[SNew(SButton).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>(TEXT("NoBorder"))).OnClicked_Lambda([this](){Send(TEXT("dismiss_interaction"));return FReply::Handled();})[SNew(STextBlock).Text(FText::FromString(TEXT("X"))).Font(Font(8))]];
  Content->AddSlot().AutoHeight()[Title];
  auto MessageText=SNew(STextBlock).Text(FText::FromString(Message.Left(24000))).Font(Font(10)).AutoWrapText(true).ColorAndOpacity(FLinearColor::White);
  Content->AddSlot().AutoHeight().Padding(0,3)[SNew(SBox).MaxDesiredHeight(200)[SNew(SScrollBox)+SScrollBox::Slot()[MessageText]]];
  if(Conversation&&Talk){const TArray<TSharedPtr<FJsonValue>>* Words=nullptr;if(Talk->TryGetArrayField(TEXT("keywords"),Words)){auto Replies=SNew(SWrapBox).UseAllottedSize(true);const int64 ReplyId=int64(Num(Talk,TEXT("id")));for(auto Word:*Words){const FString W=Word->AsString();Replies->AddSlot().Padding(2)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([this,W,ReplyId](){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("word"),W);V->SetNumberField(TEXT("reply_id"),ReplyId);Send(TEXT("keyword"),V);return FReply::Handled();})[SNew(STextBlock).Text(FText::FromString(TEXT("[")+W+TEXT("]"))).Font(Font(9))]];}Content->AddSlot().AutoHeight()[Replies];}}
  auto Body=SNew(SVerticalBox);Body->AddSlot().AutoHeight()[SNew(SBorder).BorderImage(&Background).Padding(9)[Content]];Body->AddSlot().AutoHeight().HAlign(HAlign_Center)[SNew(SSpeechTail)];
  auto Panel=SNew(SBorder).BorderImage(nullptr).Padding(0).Visibility_Lambda([Alive,Id](){return Alive(Id)?EVisibility::Visible:EVisibility::Collapsed;})[Body];WorldBubblePanels.Add(Panel);
  C->AddSlot().Position_Lambda([this,Entity,Body](){FVector Aim;if(!CanSelect(Entity,Aim))return FVector2D(-2000,-2000);const auto* Actor=Entities.Find(Entity);if(Actor)if(auto Root=Cast<UPrimitiveComponent>((*Actor)->GetRootComponent()))Aim.Z=Root->Bounds.GetBox().Max.Z+28;FVector2D Pixel;GetWorld()->GetFirstPlayerController()->ProjectWorldLocationToScreen(Aim,Pixel);FVector2D Raw;GetWorld()->GetGameViewport()->GetViewportSize(Raw);auto Extent=UIViewportSize()/ClassicScale();auto P=Pixel/Raw*Extent;return FVector2D(FMath::Clamp(P.X-140,0.,FMath::Max(0.,Extent.X-280)),FMath::Max(0.,P.Y-FMath::Clamp(double(Body->GetDesiredSize().Y),40.,300.)-4));}).Size_Lambda([Body](){return FVector2D(280,FMath::Clamp(double(Body->GetDesiredSize().Y),40.,300.));})[Panel];
 }
 for(int32 I=0;I<Notices.Num();++I){auto Row=Notices[I];const int64 Id=int64(Num(Row,TEXT("id")));bool Small=false;Row->TryGetBoolField(TEXT("small"),Small);C->AddSlot().Position_Lambda([this,I,Small](){auto Extent=UIViewportSize()/ClassicScale();double Width=FMath::Min(Small?580.:800.,Extent.X-40);return FVector2D((Extent.X-Width)*.5,Small?55+I*38:Extent.Y*.4+I*64);}).Size_Lambda([this,Small](){auto Extent=UIViewportSize()/ClassicScale();return FVector2D(FMath::Min(Small?580.:800.,Extent.X-40),Small?34:60);})[SNew(STextBlock).Text(FText::FromString(Text(Row,TEXT("text")).Left(1000))).Font(Font(Small?11:24)).Justification(ETextJustify::Center).AutoWrapText(true).ColorAndOpacity(FLinearColor(1,.9f,.6f)).ShadowOffset(FVector2D(1,1)).ShadowColorAndOpacity(FLinearColor::Black).Visibility_Lambda([Alive,Id](){return Alive(Id)?EVisibility::HitTestInvisible:EVisibility::Collapsed;})];}
 WorldMessageOverlay=SNew(SDPIScaler).Visibility(EVisibility::SelfHitTestInvisible).DPIScale_Lambda([this](){return ClassicScale();})[C];GetWorld()->GetGameViewport()->AddViewportWidgetContent(WorldMessageOverlay.ToSharedRef(),25);
}
