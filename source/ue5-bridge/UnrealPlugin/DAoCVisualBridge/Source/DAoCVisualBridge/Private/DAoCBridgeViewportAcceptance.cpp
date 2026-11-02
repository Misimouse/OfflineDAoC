#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "Components/BoxComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Widgets/SViewport.h"
#include "Widgets/SWindow.h"
#include "Widgets/Layout/SBox.h"
#include "Framework/Application/SlateApplication.h"
#include "Kismet/KismetSystemLibrary.h"
#include "SocketSubsystem.h"
#include "Framework/Application/IInputProcessor.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Text/SRichTextBlock.h"
#include "Sockets.h"
#include "UnrealClient.h"
bool UDAoCBridgeSubsystem::TickViewportAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeViewportTest="),Path))return false;
 static int32 Phase=0,N=0;static double At=0;static TSharedPtr<FJsonObject> Fixture;static TArray<TSharedPtr<FJsonValue>> Fail;static TArray<TSharedPtr<FJsonValue>> Measurements;static float OldApplicationScale=1;static TSharedPtr<SWindow> Window;
 auto Check=[&](bool OK,const FString& Label){++N;if(!OK)Fail.Add(MakeShared<FJsonValueString>(Label));};
 auto Inside=[&](TSharedPtr<SWidget> W){if(!W.IsValid())return false;auto V=GetWorld()->GetGameViewport()->GetGameViewportWidget();auto G=V->GetCachedGeometry(),WG=W->GetCachedGeometry();auto P=G.AbsoluteToLocal(WG.GetAbsolutePosition()),End=G.AbsoluteToLocal(WG.LocalToAbsolute(WG.GetLocalSize()));auto Size=G.GetLocalSize();return P.X>=-2&&P.Y>=-2&&End.X<=Size.X+2&&End.Y<=Size.Y+2;};
 auto Finish=[&](){FSlateApplication::Get().SetApplicationScale(OldApplicationScale);auto R=MakeShared<FJsonObject>();R->SetBoolField(TEXT("passed"),Fail.IsEmpty());R->SetNumberField(TEXT("checks"),N);R->SetArrayField(TEXT("failures"),Fail);R->SetArrayField(TEXT("geometry"),Measurements);R->SetBoolField(TEXT("real_window_resizes"),true);R->SetBoolField(TEXT("real_server"),false);FString Text;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Path+TEXT(".native.json")));Phase=99;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);};
 if(Phase==99)return true;const double Now=FPlatformTime::Seconds();if(Phase&&Now-At<1.2)return true;At=Now;
 if(Phase==0){
  FString Text;Check(FFileHelper::LoadFileToString(Text,*Path)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Fixture),TEXT("fixture parsed"));if(!Fixture.IsValid()){Finish();return true;}
  auto UI=Fixture->GetObjectField(TEXT("classic_ui"));UI->SetStringField(TEXT("character"),FString::Printf(TEXT("Viewport QA %lld"),FDateTime::UtcNow().GetTicks()));
  ApplyInventory(Fixture->GetObjectField(TEXT("inventory")));ApplyPlayerStatus(Fixture->GetObjectField(TEXT("player_status")));ApplyClassicUI(UI);ApplyChat(Fixture);Session=TEXT("viewport-qa");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("isolated viewport QA"),false);
  OldApplicationScale=FSlateApplication::Get().GetApplicationScale();Window=FSlateApplication::Get().FindWidgetWindow(GetWorld()->GetGameViewport()->GetGameViewportWidget().ToSharedRef());Check(Window.IsValid(),TEXT("actual game window available"));if(!Window.IsValid()){Finish();return true;}
  auto* PC=GetWorld()->GetFirstPlayerController();auto* Cam=GetWorld()->SpawnActor<ACameraActor>(FVector(-600,0,150),FRotator(0,0,0));Cam->GetCameraComponent()->bConstrainAspectRatio=false;PC->SetViewTarget(Cam);Camera=Cam;PlayerPosition=FVector::ZeroVector;
  auto Actor=[&](FString Id,FVector P,int32 Realm){auto* X=GetWorld()->SpawnActor<AStaticMeshActor>();auto* Box=NewObject<UBoxComponent>(X);Box->SetBoxExtent({30,30,80});Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);X->SetRootComponent(Box);Box->RegisterComponent();X->SetActorLocation(P);Entities.Add(Id,X);auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("realm"),Realm);R->SetNumberField(TEXT("health"),1);R->SetBoolField(TEXT("targetable"),true);EntityRows.Add(Id,R);};
  Actor(TEXT("player:local"),{0,0,80},3);Actor(TEXT("npc:900"),{400,200,80},0);Actor(TEXT("npc:901"),{7000,-400,80},0);Actor(TEXT("npc:902"),{300,-200,80},3);Actor(TEXT("npc:903"),{-900,0,80},0);
  ToggleZoneMap();Check(bZoneMapOpen&&ZoneMapOverlay.IsValid(),TEXT("zone map opens independently of magic sheet"));Check(ClassicArt(TEXT("maps/z207"))!=nullptr&&ZoneMaps.IsValid(),TEXT("original Connacht map and metadata loaded"));auto F=ZoneMapFraction({32768,32768});Check(F.Equals({.5,.5},.0001),TEXT("zone marker uses original DAoC zone units"));ZoneMapRegion=200;F=ZoneMapFraction({32768,32768});Check(F.Equals({99.5/256.,31.5/256.},.0001),TEXT("realm marker uses original region square"));ZoneMapZone=200;ZoneMapRegion=-1;Check(ZoneMapFraction({32768,32768}).X<0,TEXT("viewing another zone never invents a player marker"));bZoneMapFollow=true;FollowZoneMap();Check(ZoneMapZone==207&&ZoneMapRegion==-1,TEXT("follow returns to actual current zone"));ToggleZoneMap();Check(!bZoneMapOpen,TEXT("map toggles closed"));ToggleZoneMap();Check(CloseClassicPanel()&&!bZoneMapOpen,TEXT("Escape close hierarchy consumes map before other windows"));
  Window->Resize(FVector2D(1280,720));Phase=1;return true;
 }
 if(Phase>=1&&Phase<=5){
  auto D=MakeShared<FJsonObject>();D->SetNumberField(TEXT("stage"),Phase);D->SetNumberField(TEXT("app_scale"),FSlateApplication::Get().GetApplicationScale());auto Record=[&](const TCHAR* Key,const FGeometry& G){auto Row=MakeShared<FJsonObject>();Row->SetArrayField(TEXT("local"),{MakeShared<FJsonValueNumber>(G.GetLocalSize().X),MakeShared<FJsonValueNumber>(G.GetLocalSize().Y)});Row->SetArrayField(TEXT("absolute"),{MakeShared<FJsonValueNumber>(G.GetAbsoluteSize().X),MakeShared<FJsonValueNumber>(G.GetAbsoluteSize().Y)});Row->SetArrayField(TEXT("position"),{MakeShared<FJsonValueNumber>(G.GetAbsolutePosition().X),MakeShared<FJsonValueNumber>(G.GetAbsolutePosition().Y)});D->SetObjectField(Key,Row);};Record(TEXT("viewport"),GetWorld()->GetGameViewport()->GetGameViewportWidget()->GetCachedGeometry());Record(TEXT("ui_root"),ClassicOverlay->GetCachedGeometry());Record(TEXT("sheet"),ClassicPanelBox->GetCachedGeometry());Record(TEXT("chat"),ChatPanels[0]->GetCachedGeometry());Measurements.Add(MakeShared<FJsonValueObject>(D));
 }
 if(Phase>=1&&Phase<=4){
  Check(Inside(ClassicPanelBox),FString::Printf(TEXT("character panel fits actual geometry at stage %d"),Phase));Check(Inside(ChatPanels[0])&&Inside(ChatPanels[1]),FString::Printf(TEXT("both chat panes fit actual geometry at stage %d"),Phase));for(int32 I=0;I<3;++I)Check(Inside(ClassicBarBoxes[I]),FString::Printf(TEXT("quickbar %d fits stage %d"),I,Phase));
  Check(UIViewportSize().Equals(ClassicOverlay->GetCachedGeometry().GetLocalSize(),.1),TEXT("layout measures overlay units including engine and Windows DPI"));
  auto VG=GetWorld()->GetGameViewport()->GetGameViewportWidget()->GetCachedGeometry(),PG=ClassicPanelBox->GetCachedGeometry();double Gap=(VG.GetAbsolutePosition().X+VG.GetAbsoluteSize().X)-(PG.GetAbsolutePosition().X+PG.GetAbsoluteSize().X);Check(FMath::Abs(Gap)<3,TEXT("right-anchored character panel follows actual window edge"));
  if(Phase==1){Window->Resize(FVector2D(1800,720));Phase=2;return true;}
  if(Phase==2){FSlateApplication::Get().SetApplicationScale(1.5);Phase=3;return true;}
  if(Phase==3){auto G=ChatPanels[0]->GetCachedGeometry();auto Start=G.LocalToAbsolute(FVector2D(3,9)),End=Start-FVector2D(30,15);auto Before=ChatPositions[0];TSet<FKey> Held;Held.Add(EKeys::LeftMouseButton);FPointerEvent Down(0,Start,Start,Held,EKeys::LeftMouseButton,0,FModifierKeysState()),Move(0,End,Start,Held,EKeys::LeftMouseButton,0,FModifierKeysState()),Up(0,End,End,TSet<FKey>(),EKeys::LeftMouseButton,0,FModifierKeysState());ChatPanels[0]->OnMouseButtonDown(G,Down);ChatPanels[0]->OnMouseMove(G,Move);ChatPanels[0]->OnMouseButtonUp(G,Up);Check((ChatPositions[0]-Before).Equals(G.AbsoluteToLocal(End)-G.AbsoluteToLocal(Start),.1),TEXT("chat drag preserves physical pointer distance with both DPI transforms"));ChatPositions[0]=Before;Window->Resize(FVector2D(1100,850));Phase=4;return true;}
  FSlateApplication::Get().SetApplicationScale(OldApplicationScale);Window->Resize(FVector2D(1280,720));Phase=5;return true;
 }
 if(Phase==5){
  auto* PC=GetWorld()->GetFirstPlayerController();PC->PlayerCameraManager->UpdateCamera(.1);FVector Aim;FVector2D Pixel;
  Check(CanSelect(TEXT("player:local"),Aim)&&PC->ProjectWorldLocationToScreen(Aim,Pixel)&&TargetAtCursor(false,Pixel)==TEXT("player:local"),TEXT("clicking the visible local character resolves self"));
  Check(CanSelect(TEXT("npc:900"),Aim)&&PC->ProjectWorldLocationToScreen(Aim,Pixel)&&TargetAtCursor(false,Pixel)==TEXT("npc:900"),TEXT("clicking a creature resolves it without Tab"));
  Quality=TEXT("superior");Check(TargetAtCursor(true)==TEXT("npc:900"),TEXT("Tab excludes self, friendly NPC and enemies beyond 60m at superior quality"));
  InteractionState=MakeShared<FJsonObject>();auto CycleTarget=MakeShared<FJsonObject>();CycleTarget->SetStringField(TEXT("id"),TEXT("npc:900"));InteractionState->SetObjectField(TEXT("target"),CycleTarget);Check(TargetAtCursor(true)==TEXT("npc:903"),TEXT("Tab cycles a nearby enemy around the player without requiring a mouse hit"));
  SelectEntity(TEXT("player:local"));Outgoing.Add(0);FString Wire=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();Check(Wire.Contains(TEXT("target_self")),TEXT("self click uses original acknowledged self-target action"));
  SelectEntity(TEXT("npc:900"));Outgoing.Add(0);Wire=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();Check(Wire.Contains(TEXT("target"))&&Wire.Contains(TEXT("npc:900"))&&!Wire.Contains(TEXT("combat_attack")),TEXT("creature click selects without starting an attack"));
  auto Pointer=[&](FKey Key,bool Down,FVector2D Pixel){auto G=GetWorld()->GetGameViewport()->GetGameViewportWidget()->GetCachedGeometry();FVector2D Raw;GetWorld()->GetGameViewport()->GetViewportSize(Raw);auto Absolute=G.LocalToAbsolute(Pixel/Raw*G.GetLocalSize());TSet<FKey> Held;if(Down)Held.Add(Key);FPointerEvent Event(0,Absolute,Absolute,Held,Key,0,FModifierKeysState());return Down?WorldPointerInput->HandleMouseButtonDownEvent(FSlateApplication::Get(),Event):WorldPointerInput->HandleMouseButtonUpEvent(FSlateApplication::Get(),Event);};
  Outgoing.Empty();bool PassThrough=true;for(const FString Id:{TEXT("npc:900"),TEXT("npc:902"),TEXT("npc:900")}){CanSelect(Id,Aim);PC->ProjectWorldLocationToScreen(Aim,Pixel);PassThrough&=!Pointer(EKeys::LeftMouseButton,true,Pixel);Pointer(EKeys::LeftMouseButton,false,Pixel);}
  Outgoing.Add(0);Wire=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TArray<FString> Lines;Wire.ParseIntoArrayLines(Lines);TArray<FString> Selected;for(const auto& Line:Lines){TSharedPtr<FJsonObject> C;if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Line),C)&&C->GetStringField(TEXT("action"))==TEXT("target"))Selected.Add(C->GetStringField(TEXT("entity_id")));}
  Check(PassThrough&&Selected==TArray<FString>{TEXT("npc:900"),TEXT("npc:902"),TEXT("npc:900")},TEXT("actual Slate pointer processor sends three different selections without Tab or lost clicks"));
  CanSelect(TEXT("npc:900"),Aim);PC->ProjectWorldLocationToScreen(Aim,Pixel);Pointer(EKeys::RightMouseButton,true,Pixel);Check(Outgoing.IsEmpty(),TEXT("right press waits to distinguish click from camera drag"));Pointer(EKeys::RightMouseButton,false,Pixel);Outgoing.Add(0);Wire=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();Check(Wire.Contains(TEXT("interact"))&&Wire.Contains(TEXT("npc:900")),TEXT("right click requests original NPC interaction"));
  Pointer(EKeys::RightMouseButton,true,Pixel);HandleWorldPointer(FKey(),false,RightPointerStart+FVector2D(20,0),true);Check(bRightPointerDragged,TEXT("right drag activates camera gesture"));Pointer(EKeys::RightMouseButton,false,Pixel);Check(Outgoing.IsEmpty(),TEXT("camera drag does not open NPC services"));
  auto ChatG=ChatPanels[0]->GetCachedGeometry();auto Absolute=ChatG.LocalToAbsolute(ChatG.GetLocalSize()*.5);Check(WorldPointerBlocked(Absolute),TEXT("world click processor respects actual chat geometry"));
  auto Chat=Fixture->GetObjectField(TEXT("chat"));auto Bubble=MakeShared<FJsonObject>();Bubble->SetNumberField(TEXT("id"),100001);Bubble->SetStringField(TEXT("entity_id"),TEXT("npc:900"));Bubble->SetStringField(TEXT("name"),TEXT("annoying lucradan"));Bubble->SetStringField(TEXT("text"),TEXT("Nya, nya. Ha ha ha! He he he!"));Bubble->SetNumberField(TEXT("duration_ms"),14000);auto Notice=MakeShared<FJsonObject>();Notice->SetNumberField(TEXT("id"),100002);Notice->SetStringField(TEXT("text"),TEXT("You have entered Ardee."));Notice->SetNumberField(TEXT("duration_ms"),5000);Chat->SetArrayField(TEXT("bubbles"),{MakeShared<FJsonValueObject>(Bubble)});Chat->SetArrayField(TEXT("notices"),{MakeShared<FJsonValueObject>(Notice)});ApplyWorldMessages(Fixture);
  Check(WorldMessageOverlay.IsValid()&&WorldMessageUntil.Num()==2,TEXT("NPC bubble and region notice have independent timed visuals"));FString Visible;TFunction<void(TSharedRef<SWidget>)> Collect;Collect=[&](TSharedRef<SWidget> W){if(W->GetTypeAsString()==TEXT("STextBlock"))Visible+=StaticCastSharedRef<STextBlock>(W)->GetText().ToString()+TEXT("\n");auto Children=W->GetChildren();for(int32 I=0;Children&&I<Children->Num();++I)Collect(Children->GetChildAt(I));};Collect(WorldMessageOverlay.ToSharedRef());Check(Visible.Contains(TEXT("Nya, nya."))&&Visible.Contains(TEXT("You have entered Ardee.")),TEXT("world visuals retain original English text"));Check(!ChatMainHistory->GetText().ToString().Contains(TEXT("Nya, nya.")),TEXT("NPC speech does not appear in chat history"));
  auto P=ClassicPositions[0];ClassicPositions[0]={99999,99999};ChatPositions[0]={99999,99999};ReflowUILayout(UILayoutUnits,UILayoutUnits);Check(ClassicPositions[0].X+192<=UILayoutUnits.X+.1&&ChatPositions[0].Y+ChatSizes[0].Y<=UILayoutUnits.Y+.1,TEXT("legacy out-of-bounds saved windows are recovered"));ClassicPositions[0]=P;
  ToggleZoneMap();FScreenshotRequest::RequestScreenshot(Path+TEXT(".png"),true,false);Phase=6;return true;
 }
 Check(FPaths::FileExists(Path+TEXT(".png")),TEXT("actual resized viewport captured"));Finish();return true;
}
