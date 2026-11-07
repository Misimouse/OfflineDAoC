// Included by ClassicUI.cpp to reuse the original fonts, frame atlas and move widget.
namespace {
bool GuildFlag(TSharedPtr<FJsonObject> State,const TCHAR* Key){bool Value=false;if(State)State->TryGetBoolField(Key,Value);return Value;}
TSharedPtr<FJsonObject> GuildRow(TSharedPtr<FJsonObject> State,const FString& Token){for(auto Value:CA(State,TEXT("members")))if(Value->Type==EJson::Object&&CS(Value->AsObject(),TEXT("token"))==Token)return Value->AsObject();return nullptr;}
}
void UDAoCBridgeSubsystem::ToggleGuild(){
 if(GuildOverlay.IsValid()){CloseGuild();return;}
 GuildDismissedToken.Empty();auto Value=MakeShared<FJsonObject>();Value->SetBoolField(TEXT("open"),true);Send(TEXT("guild_open"),Value);
}
bool UDAoCBridgeSubsystem::CloseGuild(bool Notify){
 if(!GuildOverlay)return false;
 if(Notify){GuildDismissedToken=CS(GuildState,TEXT("token"));auto Value=MakeShared<FJsonObject>();Value->SetBoolField(TEXT("open"),false);Send(TEXT("guild_open"),Value);}
 if(GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(GuildOverlay.ToSharedRef());
 GuildOverlay.Reset();GuildPanel.Reset();GuildSignature.Empty();GuildConfirm.Reset();return true;
}
void UDAoCBridgeSubsystem::ApplyGuild(TSharedPtr<FJsonObject> State){
 const FString Name=GuildSelectedName;GuildState=State;
 if(!GuildFlag(State,TEXT("visible"))){CloseGuild(false);return;}
 const FString Token=CS(State,TEXT("token"));if(!Token.IsEmpty()&&Token==GuildDismissedToken)return;
 if(Token!=GuildWindowToken){GuildWindowToken=Token;GuildSelectedToken.Empty();GuildSelectedName.Empty();GuildConfirm.Reset();}
 else if(!Name.IsEmpty())for(auto Value:CA(State,TEXT("members")))if(Value->Type==EJson::Object&&CS(Value->AsObject(),TEXT("name"))==Name)GuildSelectedToken=CS(Value->AsObject(),TEXT("token"));
 if(!GuildRow(State,GuildSelectedToken))GuildSelectedToken.Empty();
 if(GuildConfirm&&(CS(GuildConfirm,TEXT("guild_token"))!=Token||(!CS(GuildConfirm,TEXT("member_token")).IsEmpty()&&!GuildRow(State,CS(GuildConfirm,TEXT("member_token"))))))GuildConfirm.Reset();
 RefreshGuild();
}
void UDAoCBridgeSubsystem::GuildRequest(const FString& Action,TSharedPtr<FJsonObject> Value){
 if(!GuildFlag(GuildState,TEXT("visible"))||GuildFlag(GuildState,TEXT("pending")))return;
 if(!Value)Value=MakeShared<FJsonObject>();
 if(Value->HasField(TEXT("guild_token"))&&CS(Value,TEXT("guild_token"))!=CS(GuildState,TEXT("token")))return;
 Value->SetStringField(TEXT("guild_token"),CS(GuildState,TEXT("token")));Send(Action,Value);
}
void UDAoCBridgeSubsystem::GuildMemberAction(const FString& Verb){
 auto Row=GuildRow(GuildState,GuildSelectedToken);if(!Row||GuildFlag(GuildState,TEXT("pending"))||GuildFlag(GuildState,TEXT("stale")))return;
 if(CS(GuildState,TEXT("tab"))==TEXT("alliance")&&(Verb==TEXT("promote")||Verb==TEXT("demote")||Verb==TEXT("remove")))return;
 if(Verb==TEXT("send")){OpenChat();if(ChatInput)ChatInput->SetText(FText::FromString(TEXT("/send ")+CS(Row,TEXT("name"))+TEXT(" ")));return;}
 auto Value=MakeShared<FJsonObject>();Value->SetStringField(TEXT("member_token"),GuildSelectedToken);Value->SetStringField(TEXT("guild_token"),CS(GuildState,TEXT("token")));Value->SetStringField(TEXT("verb"),Verb);
 if(Verb==TEXT("remove")){Value->SetStringField(TEXT("action"),TEXT("guild_member"));Value->SetStringField(TEXT("label"),TEXT("Remove ")+CS(Row,TEXT("name"))+TEXT(" from the guild?"));GuildConfirm=Value;GuildSignature.Empty();RefreshGuild();return;}
 GuildRequest(TEXT("guild_member"),Value);
}
void UDAoCBridgeSubsystem::CompleteGuildConfirmation(bool Accept){
 auto Value=GuildConfirm;GuildConfirm.Reset();
 if(Accept&&Value){Value->SetBoolField(TEXT("confirmed"),true);GuildRequest(CS(Value,TEXT("action")),Value);}
 GuildSignature.Empty();RefreshGuild();
}
void UDAoCBridgeSubsystem::RefreshGuild(){
 if(!GuildFlag(GuildState,TEXT("visible"))||!GetWorld()||!GetWorld()->GetGameViewport())return;
 FString Stamp;FJsonSerializer::Serialize(GuildState.ToSharedRef(),TJsonWriterFactory<>::Create(&Stamp));Stamp+=GuildSelectedToken+FString::FromInt(GuildConfirm.IsValid());
 if(GuildOverlay&&Stamp==GuildSignature)return;
 auto Confirmation=GuildConfirm;CloseGuild(false);GuildConfirm=Confirmation;GuildSignature=Stamp;
 const bool Alliance=CS(GuildState,TEXT("tab"))==TEXT("alliance"),Ready=!GuildFlag(GuildState,TEXT("pending"))&&!GuildConfirm;
 const bool MemberReady=Ready&&!GuildFlag(GuildState,TEXT("stale"))&&GuildRow(GuildState,GuildSelectedToken).IsValid();
 const FString GuildName=CS(GuildState,TEXT("guild"));auto Canvas=SNew(SCanvas);
 const auto* Art=ClassicArt(TEXT("chatext"),{0,.5},{1,1});
 if(Art){if(!ClassicBrushes.Contains(TEXT("guild_frame"))){auto Frame=MakeShared<FSlateBrush>(*Art);Frame->ImageSize=FVector2D(512,64);Frame->DrawAs=ESlateBrushDrawType::Box;Frame->Margin=FMargin(3.f/512,12.f/64,12.f/512,3.f/64);ClassicBrushes.Add(TEXT("guild_frame"),Frame);}At(Canvas,{0,0},{540,318},SNew(SImage).Image(ClassicBrushes[TEXT("guild_frame")].Get()));}
 auto Text=[&](FVector2D P,FVector2D Size,const FString& Label,int32 Font=8,FLinearColor Color=Cream){auto LabelWidget=CT(Label,Font,Color);LabelWidget->SetAutoWrapText(false);LabelWidget->SetToolTipText(FText::FromString(Label));At(Canvas,P,Size,LabelWidget);};
 auto Button=[&](FVector2D P,FVector2D Size,const FString& Label,TFunction<void()> Click,bool Enabled=true){At(Canvas,P,Size,SNew(SButton).IsFocusable(false).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).ContentPadding(0).IsEnabled(Enabled).OnClicked_Lambda([Click](){Click();return FReply::Handled();})[CT(Label,8)]);};
 Text({12,21},{510,16},GuildName.IsEmpty()?TEXT("GUILD"):TEXT("GUILD - ")+GuildName,11,Gold);
 Button({518,4},{16,16},TEXT("X"),[this](){CloseGuild();});
 for(const FString Tab:{FString(TEXT("guild")),FString(TEXT("alliance"))})Button({Tab==TEXT("guild")?14.:86.,40},{70,15},Tab,[this,Tab](){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("tab"),Tab);V->SetNumberField(TEXT("sort"),1);V->SetNumberField(TEXT("page"),1);GuildSelectedToken.Empty();GuildSelectedName.Empty();GuildRequest(TEXT("guild_refresh"),V);},Ready&&!GuildName.IsEmpty());
 if(!ClassicTextures.Contains(TEXT("guild_radio"))){FString Path=FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/GuildUI_v01/radiobutton1.png");FParse::Value(FCommandLine::Get(),TEXT("DaocBridgeGuildRadio="),Path);auto* Texture=FImageUtils::ImportFileAsTexture2D(Path);if(Texture){Texture->SRGB=true;Texture->Filter=TF_Bilinear;ClassicTextures.Add(TEXT("guild_radio"),Texture);}}
 const bool Offline=GuildFlag(GuildState,TEXT("show_offline"));const FString RadioKey=Offline?TEXT("guild_radio_on"):TEXT("guild_radio_off");
 if(ClassicTextures.Contains(TEXT("guild_radio"))){if(!ClassicBrushes.Contains(RadioKey)){auto Brush=MakeShared<FSlateBrush>();Brush->SetResourceObject(ClassicTextures[TEXT("guild_radio")]);Brush->ImageSize=FVector2D(16,16);Brush->SetUVRegion(FBox2D({Offline?.5:0.,0},{Offline?1.:.5,1}));ClassicBrushes.Add(RadioKey,Brush);}At(Canvas,{160,41},{11,11},SNew(SImage).Image(ClassicBrushes[RadioKey].Get()));}
 Text({175,40},{100,15},TEXT("SHOW OFFLINE"));
 Button({160,40},{115,15},TEXT(""),[this,Offline](){auto V=MakeShared<FJsonObject>();V->SetBoolField(TEXT("show_offline"),!Offline);V->SetNumberField(TEXT("page"),1);GuildRequest(TEXT("guild_refresh"),V);},Ready&&!GuildName.IsEmpty());
 Text({365,41},{160,14},FString::Printf(TEXT("%d MEMBERS"),int32(CN(GuildState,TEXT("total")))),8,Gold);
 struct FColumn{const TCHAR* Key;const TCHAR* Label;double X,W;int32 Asc,Desc;};
 const TArray<FColumn> Columns=Alliance?TArray<FColumn>{{TEXT("name"),TEXT("NAME"),14,128,1,-1},{TEXT("level"),TEXT("LVL"),144,30,2,-2},{TEXT("class_name"),TEXT("CLASS"),176,96,3,-3},{TEXT("group"),TEXT("GRP"),274,30,4,-4},{TEXT("zone"),TEXT("ZONE / LAST ON"),306,120,5,-5},{TEXT("guild"),TEXT("GUILD"),428,100,8,-6}}:TArray<FColumn>{{TEXT("name"),TEXT("NAME"),14,118,1,-1},{TEXT("level"),TEXT("LVL"),134,30,2,-2},{TEXT("class_name"),TEXT("CLASS"),166,92,3,-3},{TEXT("rank"),TEXT("RANK"),260,38,4,-4},{TEXT("group"),TEXT("GRP"),300,30,5,-5},{TEXT("zone"),TEXT("ZONE / LAST ON"),332,118,6,-6},{TEXT("note"),TEXT("NOTE"),452,76,7,-7}};
 const int32 Sort=int32(CN(GuildState,TEXT("sort"),1));for(const auto& Col:Columns){const int32 Next=Sort==Col.Asc?Col.Desc:Col.Asc;Button({Col.X,64},{Col.W,15},FString(Col.Label)+(Sort==Col.Asc?TEXT(" ^"):Sort==Col.Desc?TEXT(" v"):TEXT("")),[this,Next](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("sort"),Next);V->SetNumberField(TEXT("page"),1);GuildRequest(TEXT("guild_refresh"),V);},Ready&&!GuildName.IsEmpty());}
 int32 Index=0;for(auto Value:CA(GuildState,TEXT("members"))){if(Value->Type!=EJson::Object||Index>=10)continue;auto Row=Value->AsObject();const double Y=83+16*Index++;const FString Token=CS(Row,TEXT("token"));
  if(Token==GuildSelectedToken)At(Canvas,{12,Y},{516,16},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.35,.28,.13,.5)));
  for(const auto& Col:Columns){FString Label;if(FString(Col.Key)==TEXT("level")||FString(Col.Key)==TEXT("rank")||FString(Col.Key)==TEXT("group"))Label=FString::FromInt(int32(CN(Row,Col.Key)));else Label=CS(Row,Col.Key);Text({Col.X,Y},{Col.W,16},Label,8,GuildFlag(Row,TEXT("online"))?Cream:FLinearColor(.55,.55,.52));}
  Button({12,Y},{516,16},TEXT(""),[this,Token](){GuildSelectedToken=Token;GuildSelectedName=CS(GuildRow(GuildState,Token),TEXT("name"));GuildConfirm.Reset();GuildSignature.Empty();RefreshGuild();},Ready);
 }
 if(Index==0)Text({14,124},{510,48},GuildName.IsEmpty()?TEXT("YOU ARE NOT IN A GUILD"):CS(GuildState,TEXT("feedback")),9);
 const int32 Page=int32(CN(GuildState,TEXT("page"),1)),Total=int32(CN(GuildState,TEXT("total"))),Pages=FMath::Max(1,(Total+9)/10);
 Button({14,246},{18,15},TEXT("<"),[this,Page](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("page"),Page-1);GuildRequest(TEXT("guild_refresh"),V);},Ready&&Page>1);
 Text({34,248},{74,14},FString::Printf(TEXT("PAGE %d / %d"),Page,Pages));Button({110,246},{18,15},TEXT(">"),[this,Page](){auto V=MakeShared<FJsonObject>();V->SetNumberField(TEXT("page"),Page+1);GuildRequest(TEXT("guild_refresh"),V);},Ready&&Page<Pages);
 const TArray<FString> Acts={TEXT("send"),TEXT("invite"),TEXT("promote"),TEXT("demote"),TEXT("remove")};for(int32 I=0;I<Acts.Num();++I){const FString Verb=Acts[I];Button({140.+58*I,246},{56,15},Verb,[this,Verb](){GuildMemberAction(Verb);},MemberReady&&(!Alliance||I<2));}
 Button({14,266},{84,15},TEXT("GUILD INFO"),[this](){GuildRequest(TEXT("guild_info"));},Ready&&!GuildName.IsEmpty());Button({100,266},{84,15},TEXT("MOTD"),[this](){GuildRequest(TEXT("guild_motd"));},Ready&&!GuildName.IsEmpty());Button({186,266},{64,15},TEXT("REFRESH"),[this](){GuildRequest(TEXT("guild_refresh"));},Ready&&!GuildName.IsEmpty());
 Button({442,266},{84,15},TEXT("LEAVE GUILD"),[this](){auto V=MakeShared<FJsonObject>();V->SetStringField(TEXT("action"),TEXT("guild_leave"));V->SetStringField(TEXT("guild_token"),CS(GuildState,TEXT("token")));V->SetStringField(TEXT("label"),TEXT("Leave ")+CS(GuildState,TEXT("guild"))+TEXT("?"));GuildConfirm=V;GuildSignature.Empty();RefreshGuild();},Ready&&!GuildName.IsEmpty());
 Text({14,288},{510,24},CS(GuildState,TEXT("feedback")),8,Gold);
 if(GuildConfirm){At(Canvas,{0,0},{540,318},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0,0,0,.9)));Text({65,110},{410,60},CS(GuildConfirm,TEXT("label")),11,Gold);
  Button({100,188},{150,24},TEXT("CONFIRM"),[this](){CompleteGuildConfirmation(true);});Button({290,188},{150,24},TEXT("CANCEL"),[this](){CompleteGuildConfirmation(false);});}
 GuildPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){if(GuildPosition.X<0)GuildPosition.X=FMath::Max(0.,(UIViewportSize().X/ClassicScale()-540)*.5);GuildPosition+=Delta;});
 auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this](){auto Size=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(GuildPosition.X<0?(Size.X-540)*.5:GuildPosition.X,0.,FMath::Max(0.,Size.X-540)),FMath::Clamp(GuildPosition.Y,0.,FMath::Max(0.,Size.Y-318)));}).Size(FVector2D(540,318))[GuildPanel.ToSharedRef()];
 GuildOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];GetWorld()->GetGameViewport()->AddViewportWidgetContent(GuildOverlay.ToSharedRef(),37);
}
