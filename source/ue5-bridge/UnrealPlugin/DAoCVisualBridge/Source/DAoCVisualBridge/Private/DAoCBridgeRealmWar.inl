// Original WarMapWindow data/art and original server ownership. No teleport action.
void UDAoCBridgeSubsystem::LoadRealmWarData(){
    if(RealmWarData.IsValid())return;FString Text;
    if(FFileHelper::LoadFileToString(Text,*(FPaths::ProjectPluginsDir()/TEXT("DAoCVisualBridge/Content/ClassicUI/RealmWarUI_v01/warmap.json"))))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),RealmWarData);
}
void UDAoCBridgeSubsystem::ApplyRealmWar(TSharedPtr<FJsonObject> State){
    RealmWarState=State;const int64 Revision=int64(CN(State,TEXT("revision"),-1));
    if(Revision!=RealmWarRevision){RealmWarRevision=Revision;RefreshRealmWar();}
}
void UDAoCBridgeSubsystem::RequestRealmWarPage(int32 Page){
    if(!bLocalAvailable||bExiting||Session.IsEmpty()||Page<1||Page>3||FPlatformTime::Seconds()-RealmWarLastRequest<1.)return;
    bool Pending=false;if(RealmWarState.IsValid())RealmWarState->TryGetBoolField(TEXT("pending"),Pending);if(Pending)return;
    RealmWarPage=Page;RealmWarLastRequest=FPlatformTime::Seconds();auto Value=MakeShared<FJsonObject>();Value->SetNumberField(TEXT("page"),Page);Send(TEXT("warmap_request"),Value);RealmWarSignature.Empty();RefreshRealmWar();
}
void UDAoCBridgeSubsystem::ToggleRealmWar(){
    if(!bLocalAvailable||bExiting)return;if(bRealmWarOpen){CloseRealmWar();return;}
    bRealmWarOpen=true;LoadRealmWarData();RequestRealmWarPage(RealmWarPage);RefreshRealmWar();
}
bool UDAoCBridgeSubsystem::CloseRealmWar(bool Notify){
    const bool WasOpen=bRealmWarOpen||RealmWarOverlay.IsValid();if(WasOpen&&Notify)Send(TEXT("warmap_close"));
    if(RealmWarOverlay.IsValid()&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(RealmWarOverlay.ToSharedRef());
    bRealmWarOpen=false;RealmWarOverlay.Reset();RealmWarPanel.Reset();RealmWarSignature.Empty();return WasOpen;
}
void UDAoCBridgeSubsystem::RefreshRealmWar(){
    if(!bRealmWarOpen)return;auto Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;if(!Viewport)return;LoadRealmWarData();if(!RealmWarData.IsValid())return;
    FString Stamp;if(RealmWarState.IsValid())FJsonSerializer::Serialize(RealmWarState,TJsonWriterFactory<>::Create(&Stamp));Stamp+=FString::FromInt(RealmWarPage);
    if(RealmWarOverlay.IsValid()&&RealmWarSignature==Stamp)return;RealmWarSignature=Stamp;
    if(RealmWarOverlay.IsValid())Viewport->RemoveViewportWidgetContent(RealmWarOverlay.ToSharedRef());
    const TCHAR* Keys[]={TEXT("alb"),TEXT("mid"),TEXT("hib")};const TCHAR* Names[]={TEXT("ALBION"),TEXT("MIDGARD"),TEXT("HIBERNIA")};const FString Key=Keys[FMath::Clamp(RealmWarPage,1,3)-1];
    auto Page=CO(CO(RealmWarData,TEXT("pages")),*Key);auto SizeValues=CA(Page,TEXT("size"));if(SizeValues.Num()!=2)return;const FVector2D Body(SizeValues[0]->AsNumber(),SizeValues[1]->AsNumber()),Size=Body+FVector2D(12,42),Offset(6,20);
    auto Canvas=SNew(SCanvas);
    // Explicit original-art patches keep x4 resource pixels from enlarging
    // the frame margins when Slate derives borders from the texture size.
    const double SX[]={0,6,287,300},SY[]={0,19,415,448};
    const double DX[]={0,6,Size.X-13,Size.X},DY[]={0,19,Size.Y-33,Size.Y};
    for(int32 Y=0;Y<3;++Y)for(int32 X=0;X<3;++X)At(Canvas,{DX[X],DY[Y]},{DX[X+1]-DX[X],DY[Y+1]-DY[Y]},SNew(SImage).Image(ClassicArt(TEXT("RealmWarUI_v01/frame"),{SX[X]/300.,SY[Y]/448.},{SX[X+1]/300.,SY[Y+1]/448.})));
    At(Canvas,{14,2},{Size.X-35,15},CT(TEXT("WAR MAP"),9,Gold));At(Canvas,{Size.X-18,1},{16,15},CB(CT(TEXT("")),[this](){CloseRealmWar();}));
    bool Pending=false;if(RealmWarState.IsValid())RealmWarState->TryGetBoolField(TEXT("pending"),Pending);
    auto Enabled=[this](){bool Waiting=false;if(RealmWarState.IsValid())RealmWarState->TryGetBoolField(TEXT("pending"),Waiting);return !Waiting&&FPlatformTime::Seconds()-RealmWarLastRequest>=1.;};
    for(int32 I=0;I<3;++I){const int32 Number=I+1;At(Canvas,Offset+FVector2D(15+I*64,2),{62,15},SNew(SBox).IsEnabled_Lambda(Enabled)[CB(CT(Names[I],8,Number==RealmWarPage?Gold:Cream),[this,Number](){RequestRealmWarPage(Number);})]);}
    At(Canvas,Offset+FVector2D(Body.X-76,2),{62,15},SNew(SBox).IsEnabled_Lambda(Enabled)[CB(CT(TEXT("UPDATE"),8),[this](){RequestRealmWarPage(RealmWarPage);})]);
    auto Pair=[](const TArray<TSharedPtr<FJsonValue>>& Values){return Values.Num()==2?FVector2D(Values[0]->AsNumber(),Values[1]->AsNumber()):FVector2D::ZeroVector;};
    const FString Texture=TEXT("RealmWarUI_v01/")+FPaths::GetBaseFilename(CS(Page,TEXT("texture")));
    // The original three map atlases are each 256 x 256; preserve their XML quads.
    for(const auto& Value:CA(Page,TEXT("tiles"))){auto Tile=Value->AsObject();auto P=Pair(CA(Tile,TEXT("pos"))),Q=Pair(CA(Tile,TEXT("quad")));At(Canvas,Offset+P,{128,128},SNew(SImage).Image(ClassicArt(Texture,Q/256.,(Q+FVector2D(128,128))/256.)));}
    auto Symbol=CO(Page,TEXT("symbol"));if(Symbol){auto P=Pair(CA(Symbol,TEXT("pos"))),Q=Pair(CA(Symbol,TEXT("quad")));At(Canvas,Offset+P,{64,64},SNew(SImage).Image(ClassicArt(TEXT("RealmWarUI_v01/realm_symb"),Q/128.,(Q+FVector2D(64,64))/128.)));}
    auto ServerPage=CO(CO(RealmWarState,TEXT("pages")),*FString::FromInt(RealmWarPage));auto Keeps=CO(ServerPage,TEXT("keeps"));int32 Held[4]={0,0,0,0},Known=0;
    const TCHAR* OwnerNames[]={TEXT("UNCLAIMED"),TEXT("ALBION"),TEXT("MIDGARD"),TEXT("HIBERNIA")};
    auto Icon=[&](FVector2D Position,FVector2D Quad,FVector2D IconSize,const FString& Tip){auto Widget=SNew(SImage).Image(ClassicArt(TEXT("RealmWarUI_v01/map_icons"),FVector2D(Quad.X/256.,Quad.Y/128.),FVector2D((Quad.X+IconSize.X)/256.,(Quad.Y+IconSize.Y)/128.)));if(!Tip.IsEmpty())Widget->SetToolTipText(FText::FromString(Tip));At(Canvas,Offset+Position,IconSize,Widget);};
    for(const auto& Value:CA(Page,TEXT("keeps"))){auto Keep=Value->AsObject();const int32 Id=int32(CN(Keep,TEXT("id")));auto Live=CO(Keeps,*FString::FromInt(Id));const bool Relic=CS(Keep,TEXT("kind"))==TEXT("relic");int32 Owner=Live.IsValid()?FMath::Clamp(int32(CN(Live,TEXT("realm"))),0,3):-1;auto P=Pair(CA(Keep,TEXT("at")));
        FString Tip=CS(Keep,TEXT("name"));if(Owner>=0){++Known;++Held[Owner];Tip+=TEXT("\nHELD BY ")+FString(OwnerNames[Owner]);const auto Guild=CS(Live,TEXT("guild"));if(!Guild.IsEmpty())Tip+=TEXT("\nCLAIMED BY ")+Guild;}else Tip+=TEXT("\nOWNERSHIP NOT RECEIVED");
        bool Siege=false;if(Live.IsValid())Live->TryGetBoolField(TEXT("siege"),Siege);if(Siege){Tip+=TEXT("\nUNDER SIEGE");Icon(P-FVector2D(16,20),{96,96},{32,32},TEXT(""));}
        if(Relic){auto Relics=CA(ServerPage,TEXT("relics"));const FString Name=CS(Keep,TEXT("name")).ToLower();const TCHAR* Words[]={TEXT("excalibur"),TEXT("mjollner"),TEXT("lamfhota"),TEXT("myrddin"),TEXT("grallarhorn"),TEXT("dagda")};if(Relics.Num()==6)for(int32 I=0;I<6;++I)if(Name.Contains(Words[I])){const int32 Holder=FMath::Clamp(int32(Relics[I]->AsNumber()),0,3);Tip+=Holder>0?TEXT("\nRELIC HELD BY ")+FString(OwnerNames[Holder]):TEXT("\nRELIC HOLDER NOT AVAILABLE");}}
        const int32 Column=Owner==3?16:Owner==2?32:Owner==1?48:0;Icon(P-FVector2D(8,8),Relic?FVector2D(96,16):FVector2D(Column,16),{16,16},Tip);
    }
    // Match actual zone IDs before drawing a reported battle. In particular,
    // never place New Frontiers coordinates onto a classic-frontier tile.
    TMap<int32,FVector2D> TilePositions;for(const auto& Value:CA(Page,TEXT("tiles"))){auto Tile=Value->AsObject();TilePositions.Add(int32(CN(Tile,TEXT("zone"),-1)),Pair(CA(Tile,TEXT("pos"))));}
    for(const auto& Value:CA(RealmWarState,TEXT("fights"))){auto Fight=Value->AsObject();auto Tile=TilePositions.Find(int32(CN(Fight,TEXT("zone"),-1)));if(!Tile)continue;const int32 X=int32(CN(Fight,TEXT("x"),-1)),Y=int32(CN(Fight,TEXT("y"),-1));if(X<0||X>3||Y<0||Y>3)continue;const int32 Color=int32(CN(Fight,TEXT("color"))),RawSize=int32(CN(Fight,TEXT("size")));bool Group=false;Fight->TryGetBoolField(TEXT("group"),Group);FVector2D Quad;FString Tip;
        if(Group){if(Color!=1&&Color!=2&&Color!=4)continue;const int32 Category=FMath::Clamp(FMath::Max3(RawSize&3,(RawSize>>2)&3,(RawSize>>4)&3),1,3);Quad={Color==1?96.:Color==2?80.:64.,Category==1?32.:Category==2?48.:64.};Tip=Color==1?TEXT("AN ALBION FORCE"):Color==2?TEXT("A MIDGARD FORCE"):TEXT("A HIBERNIAN FORCE");}
        else{Quad={Color==1?32.:Color==2?0.:Color==3?16.:48.,RawSize==0?64.:RawSize==1?48.:32.};Tip=Color==1?TEXT("ALBION AND MIDGARD FIGHT"):Color==2?TEXT("ALBION AND HIBERNIA FIGHT"):Color==3?TEXT("MIDGARD AND HIBERNIA FIGHT"):TEXT("A BATTLE");}
        Icon(*Tile+FVector2D(X*32+8,Y*32+8),Quad,{16,16},Tip);
    }
    const auto Labels=CA(Page,TEXT("labels"));TArray<FString> Lines{FString(Names[RealmWarPage-1])+TEXT(" FRONTIER"),FString::Printf(TEXT("ALBION HOLDS %d"),Held[1]),FString::Printf(TEXT("MIDGARD HOLDS %d"),Held[2]),FString::Printf(TEXT("HIBERNIA HOLDS %d"),Held[3])};
    if(Known==0)for(int32 I=1;I<Lines.Num();++I)Lines[I]=FString(Names[I-1])+TEXT(" OWNERSHIP UNKNOWN");
    for(int32 I=0;I<FMath::Min(Lines.Num(),Labels.Num());++I){auto P=Pair(Labels[I]->AsArray());At(Canvas,Offset+P,{Body.X-P.X-5,14},CT(Lines[I],8,I==0?Gold:Cream));}
    bool FightsReady=false;if(RealmWarState.IsValid())RealmWarState->TryGetBoolField(TEXT("fights_ready"),FightsReady);FString Feedback=CS(RealmWarState,TEXT("feedback"));if(Feedback.IsEmpty()&&!FightsReady)Feedback=TEXT("Battle information not received.");
    if(Labels.Num()>4){auto P=Pair(Labels[4]->AsArray());At(Canvas,Offset+P,{Body.X-P.X-5,40},SNew(STextBlock).Text(FText::FromString(Pending?TEXT("Waiting for the server map update."):Feedback)).Font(CF(7)).ColorAndOpacity(Cream).AutoWrapText(true));}
    RealmWarPanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){RealmWarPosition+=Delta;}).End([this](){SaveClassicLayout();});auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this,Size](){auto Extent=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(RealmWarPosition.X,0.,FMath::Max(0.,Extent.X-Size.X)),FMath::Clamp(RealmWarPosition.Y,0.,FMath::Max(0.,Extent.Y-Size.Y)));}).Size(Size)[RealmWarPanel.ToSharedRef()];RealmWarOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];Viewport->AddViewportWidgetContent(RealmWarOverlay.ToSharedRef(),36);
}
