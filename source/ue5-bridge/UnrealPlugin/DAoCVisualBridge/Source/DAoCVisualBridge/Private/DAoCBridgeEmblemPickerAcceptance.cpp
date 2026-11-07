#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/World.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Layout/SScrollBox.h"
#include "ImageUtils.h"
#include "SocketSubsystem.h"
#include "Sockets.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "RenderingThread.h"

bool UDAoCBridgeSubsystem::TickEmblemPickerAcceptance(){
 FString Path;if(!FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeEmblemPickerTest="),Path))return false;
 static bool Started=false,Done=false;static double Began=0;static int32 Checks=0;static TArray<FString> Failures;static FQuat InitialRotation;
 if(Done)return true;auto Check=[&](bool V,const TCHAR* Label){++Checks;if(!V)Failures.Add(Label);};if(!GetWorld()||!GetWorld()->GetGameViewport())return true;
 auto Capture=[&](const TCHAR* Action){Outgoing.Add(0);FString Text=UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));Outgoing.Empty();TSharedPtr<FJsonObject> Value;Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Value)&&Value&&Value->GetStringField(TEXT("action"))==Action,TEXT("only expected emblem command dispatched"));return Value;};
 if(!Started){Started=true;Began=FPlatformTime::Seconds();Session=TEXT("isolated-emblem-picker");bLocalAvailable=true;Socket=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream,TEXT("Private emblem command capture"),false);Outgoing.Empty();ClassicState=MakeShared<FJsonObject>();ClassicLayoutCharacter=TEXT("PRIVATE-EMBLEM-QA");ClassicLayoutFile=Path+TEXT(".layout.json");LoadEquipmentCatalog();
  EmblemPickerSelect(TEXT("logo"),1);EmblemPickerSubmit();Check(Outgoing.IsEmpty(),TEXT("closed native picker cannot change or submit a guild emblem"));
  auto State=MakeShared<FJsonObject>();State->SetBoolField(TEXT("visible"),true);State->SetStringField(TEXT("token"),TEXT("qa:emblem:1"));State->SetStringField(TEXT("guild"),TEXT("QA Guild"));State->SetNumberField(TEXT("revision"),1);State->SetNumberField(TEXT("emblem"),131071);
  auto Draft=MakeShared<FJsonObject>();Draft->SetNumberField(TEXT("logo"),255);Draft->SetNumberField(TEXT("pattern"),3);Draft->SetNumberField(TEXT("primary"),15);Draft->SetNumberField(TEXT("secondary"),7);State->SetObjectField(TEXT("draft"),Draft);ApplyEmblemPicker(State);
  Check(EmblemPickerOverlay&&EmblemPickerPanel,TEXT("original picker frame builds from server state"));Check(EmblemPickerData.IsValid()&&ClassicTextures.Contains(TEXT("emblem_picker_frame")),TEXT("original palette and frame load"));
  int32 Logos=0;for(const auto& Pair:ClassicTextures)Logos+=Pair.Key.StartsWith(TEXT("emblem_picker_logo_"));Check(Logos==255,TEXT("all 255 original insignia textures are available in the scroll grid"));
  TSet<FString> Labels;TFunction<void(TSharedRef<SWidget>)> Visit=[&](TSharedRef<SWidget> W){if(W->GetType()==TEXT("STextBlock"))Labels.Add(StaticCastSharedRef<STextBlock>(W)->GetText().ToString());auto* Children=W->GetChildren();for(int32 I=0;I<Children->Num();++I)Visit(Children->GetChildAt(I));};if(EmblemPickerOverlay)Visit(EmblemPickerOverlay.ToSharedRef());
  Check(Labels.Contains(TEXT("GUILD EMBLEM"))&&Labels.Contains(TEXT("SET EMBLEM"))&&Labels.Contains(TEXT("CANCEL")),TEXT("original English actions are present"));Check(Labels.Contains(TEXT("PATTERN"))&&Labels.Contains(TEXT("FIELD"))&&Labels.Contains(TEXT("CHARGE"))&&Labels.Contains(TEXT("LOGO"))&&Labels.Contains(TEXT("4 OF 4")),TEXT("original four editing fields display server draft"));
  Check(EmblemPickerPreviewActor&&EmblemPickerCapture&&EmblemPickerTarget&&EmblemPickerPreviewBrush,TEXT("original shield has an actual 3D preview"));
  if(EmblemPickerPreviewActor){auto* Mesh=EmblemPickerPreviewActor->GetStaticMeshComponent();Check(Mesh->GetStaticMesh()!=nullptr&&Mesh->GetNumMaterials()>0,TEXT("preview uses existing native shield geometry"));Check(Mesh->bVisibleInSceneCaptureOnly&&Mesh->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("preview is invisible and non-colliding in the main world"));InitialRotation=EmblemPickerPreviewActor->GetActorQuat();}
  EmblemPickerSelect(TEXT("primary"),16);EmblemPickerSelect(TEXT("logo"),0);EmblemPickerSelect(TEXT("unknown"),2);Check(Outgoing.IsEmpty(),TEXT("invalid native choices send no request"));
  EmblemPickerSelect(TEXT("primary"),4);auto Selected=Capture(TEXT("emblem_select"));Check(Selected&&Selected->GetIntegerField(TEXT("primary"))==4&&Selected->GetStringField(TEXT("token"))==TEXT("qa:emblem:1"),TEXT("preview edit carries only bounded field and current window identity"));Check(Draft->GetIntegerField(TEXT("primary"))==15,TEXT("native edit does not invent an accepted server or equipment change"));
  EmblemPickerSubmit();auto Submit=Capture(TEXT("emblem_submit"));Check(Submit&&Submit->GetStringField(TEXT("token"))==TEXT("qa:emblem:1"),TEXT("submit references current server-authorized picker"));Check(!EmblemPickerOverlay&&!EmblemPickerPreviewActor&&!EmblemPickerTarget,TEXT("submit closes and destroys preview resources"));
  EmblemPickerSubmit();UpdateEmblemPickerPreview();ApplyEmblemPicker(State);Check(Outgoing.IsEmpty()&&!EmblemPickerOverlay&&!EmblemPickerPreviewActor,TEXT("delayed visible snapshot cannot reopen or recreate dismissed preview"));
  State->SetStringField(TEXT("token"),TEXT("qa:emblem:2"));ApplyEmblemPicker(State);Check(EmblemPickerOverlay.IsValid(),TEXT("a new original server dialogue can reopen the picker"));Check(CloseClassicPanel(),TEXT("Escape closes the picker before other classic panels"));auto Closed=Capture(TEXT("emblem_close"));Check(Closed&&Closed->GetStringField(TEXT("token"))==TEXT("qa:emblem:2"),TEXT("cancel sends close only, without a chosen emblem packet"));
  State->SetStringField(TEXT("token"),TEXT("qa:emblem:3"));ApplyEmblemPicker(State);Outgoing.Empty();if(EmblemPickerPreviewActor)InitialRotation=EmblemPickerPreviewActor->GetActorQuat();
  Check(EmblemPickerLogoScroll.IsValid(),TEXT("original logo catalogue has an actual scroll control"));
  if(EmblemPickerLogoScroll){EmblemPickerLogoScroll->SetScrollOffset(120);State->SetNumberField(TEXT("revision"),2);ApplyEmblemPicker(State);Check(FMath::IsNearlyEqual(EmblemPickerLogoScroll->GetScrollOffset(),120.f),TEXT("draft refresh preserves the player's position in the logo catalogue"));}
 }
 if(FPlatformTime::Seconds()-Began<1.5)return true;UpdateEmblemPickerPreview();
 Check(EmblemPickerPanel&&WorldPointerBlocked(EmblemPickerPanel->GetCachedGeometry().GetAbsolutePosition()+FVector2D(12,12)),TEXT("actual picker blocks world selection through its frame and logo area"));
 if(EmblemPickerPreviewActor){Check(!InitialRotation.Equals(EmblemPickerPreviewActor->GetActorQuat(),.0001),TEXT("shield turns in its own preview"));Check((EmblemPickerPreviewActor->GetStaticMeshComponent()->Bounds.Origin-EmblemPickerPreviewActor->GetActorLocation()).Size()<1,TEXT("shield turns around its center without orbiting away"));}
 TArray<FColor> Pixels;TArray<uint8> Bytes;int32 Bright=0;TSet<uint32> Colors;bool Preview=false;
 if(EmblemPickerCapture&&EmblemPickerTarget){EmblemPickerCapture->CaptureScene();FlushRenderingCommands();if(auto* R=EmblemPickerTarget->GameThread_GetRenderTargetResource())Preview=R->ReadPixels(Pixels);for(auto P:Pixels){Bright+=FMath::Max3(P.R,P.G,P.B)>25;Colors.Add(P.DWColor());}if(Preview){FImageUtils::CompressImageArray(168,216,Pixels,Bytes);Preview=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".shield.png")));}}
 Check(Preview&&Bright>300&&Colors.Num()>20,TEXT("actual shield capture contains visible textured geometry"));
 Pixels.Empty();Bytes.Empty();FIntVector Size=FIntVector::ZeroValue;bool Captured=EmblemPickerOverlay&&FSlateApplication::Get().TakeScreenshot(EmblemPickerOverlay.ToSharedRef(),Pixels,Size);if(Captured){FImageUtils::CompressImageArray(Size.X,Size.Y,Pixels,Bytes);Captured=FFileHelper::SaveArrayToFile(Bytes,*(Path+TEXT(".png")));}Check(Captured,TEXT("original emblem window captured from actual viewport"));
 CloseEmblemPicker(false);EmblemPickerState.Reset();Check(!EmblemPickerOverlay&&!EmblemPickerPanel&&!EmblemPickerLogoScroll&&!EmblemPickerPreviewActor&&!EmblemPickerCapture&&!EmblemPickerTarget,TEXT("logout cleanup removes all picker widgets and preview resources"));Socket->Close();ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(Socket);Socket=nullptr;Session.Empty();bLocalAvailable=false;
 auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Failures.IsEmpty());Report->SetNumberField(TEXT("checks"),Checks);Report->SetNumberField(TEXT("shield_bright_pixels"),Bright);Report->SetNumberField(TEXT("shield_colors"),Colors.Num());TArray<TSharedPtr<FJsonValue>> Values;for(auto Failure:Failures)Values.Add(MakeShared<FJsonValueString>(Failure));Report->SetArrayField(TEXT("failures"),Values);Report->SetBoolField(TEXT("server_started"),false);FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*Path);Done=true;UKismetSystemLibrary::QuitGame(GetWorld(),GetWorld()->GetFirstPlayerController(),EQuitPreference::Quit,false);return true;
}
