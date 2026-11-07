// Original 219 x 288 picker, using ClassicUI's existing font and draggable frame.
namespace {
bool EmblemVisible(TSharedPtr<FJsonObject> State){bool Value=false;return State&&State->TryGetBoolField(TEXT("visible"),Value)&&Value;}
}
bool UDAoCBridgeSubsystem::CloseEmblemPicker(bool Notify){
 if(!EmblemPickerOverlay){EmblemPickerLogoScroll.Reset();ClearEmblemPickerPreview();return false;}
 if(Notify){EmblemPickerDismissedToken=CS(EmblemPickerState,TEXT("token"));auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("token"),EmblemPickerDismissedToken);Send(TEXT("emblem_close"),Value);}
 if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(EmblemPickerOverlay.ToSharedRef());
 EmblemPickerOverlay.Reset();EmblemPickerPanel.Reset();EmblemPickerLogoScroll.Reset();EmblemPickerSignature.Empty();ClearEmblemPickerPreview();return true;
}
void UDAoCBridgeSubsystem::ApplyEmblemPicker(TSharedPtr<FJsonObject> State){
 EmblemPickerState=State;if(!EmblemVisible(State)){CloseEmblemPicker(false);return;}
 const FString Token=CS(State,TEXT("token"));if(Token.IsEmpty()||Token==EmblemPickerDismissedToken)return;
 if(Token!=EmblemPickerToken){EmblemPickerToken=Token;EmblemPickerSignature.Empty();}
 RefreshEmblemPicker();
}
void UDAoCBridgeSubsystem::EmblemPickerSelect(const FString& Key,int32 Value){
 if(!EmblemPickerOverlay||!EmblemVisible(EmblemPickerState))return;
 if(Key!=TEXT("primary")&&Key!=TEXT("secondary")&&Key!=TEXT("pattern")&&Key!=TEXT("logo"))return;
 const int32 Minimum=Key==TEXT("logo")?1:0,Maximum=Key==TEXT("primary")?15:Key==TEXT("secondary")?7:Key==TEXT("pattern")?3:255;
 if(Value<Minimum||Value>Maximum)return;
 auto Request=MakeShared<FJsonObject>();Request->SetStringField(TEXT("token"),CS(EmblemPickerState,TEXT("token")));Request->SetNumberField(Key,Value);Send(TEXT("emblem_select"),Request);
}
void UDAoCBridgeSubsystem::EmblemPickerSubmit(){
 if(!EmblemPickerOverlay||!EmblemVisible(EmblemPickerState))return;
 EmblemPickerDismissedToken=CS(EmblemPickerState,TEXT("token"));auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("token"),EmblemPickerDismissedToken);Send(TEXT("emblem_submit"),Value);CloseEmblemPicker(false);
}
void UDAoCBridgeSubsystem::RefreshEmblemPicker(){
 if(!EmblemVisible(EmblemPickerState)||!GetWorld()||!GetWorld()->GetGameViewport())return;
 FString Stamp;FJsonSerializer::Serialize(EmblemPickerState.ToSharedRef(),TJsonWriterFactory<>::Create(&Stamp));if(EmblemPickerOverlay&&Stamp==EmblemPickerSignature)return;
 if(!EmblemPickerData){
  FString Root=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/EmblemUI_v01");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeEmblemUI="),Root);FString Text;
  if(FFileHelper::LoadFileToString(Text,*(Root/TEXT("picker.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),EmblemPickerData);
  if(auto* Frame=FImageUtils::ImportFileAsTexture2D(Root/TEXT("emblempick.png"))){Frame->SRGB=true;Frame->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("emblem_picker_frame"),Frame);auto Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(Frame);Brush->ImageSize=FVector2D(219,288);ClassicBrushes.Add(TEXT("emblem_picker_frame"),Brush);}
 }
 UpdateEmblemPickerPreview();
 const float LogoScrollOffset=EmblemPickerLogoScroll?EmblemPickerLogoScroll->GetScrollOffset():0;
 if(EmblemPickerOverlay)GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(EmblemPickerOverlay.ToSharedRef());EmblemPickerOverlay.Reset();EmblemPickerPanel.Reset();EmblemPickerSignature=Stamp;
 auto Canvas=SNew(SCanvas);if(ClassicBrushes.Contains(TEXT("emblem_picker_frame")))At(Canvas,{0,0},{219,288},SNew(SImage).Image(ClassicBrushes[TEXT("emblem_picker_frame")].Get()));
 auto Text=[&](FVector2D P,FVector2D Size,const FString& Label,int32 Font=8,FLinearColor Color=Cream){auto W=CT(Label,Font,Color);W->SetAutoWrapText(false);W->SetToolTipText(FText::FromString(Label));At(Canvas,P,Size,W);};
 auto Button=[&](FVector2D P,FVector2D Size,const FString& Label,TFunction<void()> Click){At(Canvas,P,Size,SNew(SButton).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).ContentPadding(0).OnClicked_Lambda([Click](){Click();return FReply::Handled();})[CT(Label,8)]);};
 Text({30,15},{175,16},TEXT("GUILD EMBLEM"),11,Gold);Button({202,2},{13,13},TEXT("X"),[this](){CloseEmblemPicker();});
 if(EmblemPickerPreviewBrush)At(Canvas,{10,34},{84,108},SNew(SImage).Image(EmblemPickerPreviewBrush.Get()));
 auto Draft=CO(EmblemPickerState,TEXT("draft")),Palette=CO(EmblemPickerData,TEXT("palette"));
 const TArray<FString> Keys={TEXT("pattern"),TEXT("primary"),TEXT("secondary"),TEXT("logo")},Labels={TEXT("PATTERN"),TEXT("FIELD"),TEXT("CHARGE"),TEXT("LOGO")};
 for(int32 I=0;I<4;++I){const FString Key=Keys[I];const int32 Value=int32(CN(Draft,*Key,Key==TEXT("logo")?1:0)),Min=Key==TEXT("logo")?1:0,Count=Key==TEXT("logo")?255:Key==TEXT("primary")?16:Key==TEXT("secondary")?8:4;const double Y=36+26*I;
  Text({100,Y},{104,12},Labels[I],8,Gold);
  Button({100,Y+11},{14,13},TEXT("<"),[this,Key,Value,Min,Count](){EmblemPickerSelect(Key,Min+(Value-Min+Count-1)%Count);});Button({195,Y+11},{14,13},TEXT(">"),[this,Key,Value,Min,Count](){EmblemPickerSelect(Key,Min+(Value-Min+1)%Count);});
  FString Label=FString::FromInt(Value);double X=117,Width=77;
  if(Key==TEXT("pattern"))Label=FString::Printf(TEXT("%d OF 4"),Value+1);
  else if(Key==TEXT("logo")){const FString Name=CS(CO(CO(Palette,TEXT("logos")),*FString::FromInt(Value)),TEXT("name"));if(!Name.IsEmpty())Label=Name;}
  else {auto Colors=CA(Palette,*Key);if(Colors.IsValidIndex(Value)&&Colors[Value]->Type==EJson::Object){auto Color=Colors[Value]->AsObject();Label=CS(Color,TEXT("name"));auto RGB=CA(Color,TEXT("rgb"));if(RGB.Num()==3)At(Canvas,{117,Y+12},{11,11},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor::FromSRGBColor(FColor(uint8(RGB[0]->AsNumber()),uint8(RGB[1]->AsNumber()),uint8(RGB[2]->AsNumber())))));}X=130;Width=64;}
  Text({X,Y+12},{Width,12},Label);
 }
 auto Grid=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(1,1));const int32 Selected=int32(CN(Draft,TEXT("logo"),1));
 for(int32 Id=1;Id<=255;++Id){const FString Key=TEXT("emblem_picker_logo_")+FString::FromInt(Id);if(!ClassicBrushes.Contains(Key)){const FString Asset=CS(CO(CO(EmblemPickerData,TEXT("assets")),TEXT("logos")),*FString::FromInt(Id));if(auto* Texture=LoadObject<UTexture2D>(nullptr,*Asset)){ClassicTextures.Add(Key,Texture);auto Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(Texture);Brush->ImageSize=FVector2D(23,23);ClassicBrushes.Add(Key,Brush);}}
  auto Pick=SNew(SButton).IsFocusable(false).ContentPadding(0).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>(TEXT("NoBorder"))).ToolTipText(FText::FromString(CS(CO(CO(Palette,TEXT("logos")),*FString::FromInt(Id)),TEXT("name")))).OnClicked_Lambda([this,Id](){EmblemPickerSelect(TEXT("logo"),Id);return FReply::Handled();})[SNew(SImage).Image(ClassicBrushes.Contains(Key)?ClassicBrushes[Key].Get():nullptr).ColorAndOpacity(Id==Selected?FLinearColor(1,.85,.45):FLinearColor(.82,.82,.82))];
  Grid->AddSlot()[SNew(SBox).WidthOverride(23).HeightOverride(23)[Pick]];
 }
 EmblemPickerLogoScroll=SNew(SScrollBox)+SScrollBox::Slot()[Grid];EmblemPickerLogoScroll->SetScrollOffset(LogoScrollOffset);
 At(Canvas,{10,148},{199,104},EmblemPickerLogoScroll.ToSharedRef());
 Button({30,260},{72,16},TEXT("SET EMBLEM"),[this](){EmblemPickerSubmit();});Button({117,260},{72,16},TEXT("CANCEL"),[this](){CloseEmblemPicker();});
 EmblemPickerPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){if(EmblemPickerPosition.X<0)EmblemPickerPosition.X=FMath::Max(0.,(UIViewportSize().X/ClassicScale()-219)*.5);EmblemPickerPosition+=Delta;});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){auto Size=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(EmblemPickerPosition.X<0?(Size.X-219)*.5:EmblemPickerPosition.X,0.,FMath::Max(0.,Size.X-219)),FMath::Clamp(EmblemPickerPosition.Y,0.,FMath::Max(0.,Size.Y-288)));}).Size(FVector2D(219,288))[EmblemPickerPanel.ToSharedRef()];
 EmblemPickerOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];GetWorld()->GetGameViewport()->AddViewportWidgetContent(EmblemPickerOverlay.ToSharedRef(),38);
}
