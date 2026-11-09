// Original SiegeWindow: server-granted control, original command IDs and frame.
void UDAoCBridgeSubsystem::ApplySiege(TSharedPtr<FJsonObject> State){
    SiegeState=State;SiegeTimeLeft=CN(State,TEXT("time_left"));SiegeReceivedAt=FPlatformTime::Seconds();const int64 Revision=int64(CN(State,TEXT("revision"),-1));
    if(Revision==SiegeRevision)return;SiegeRevision=Revision;bool Visible=false,Controlled=false;if(State){State->TryGetBoolField(TEXT("visible"),Visible);State->TryGetBoolField(TEXT("controlled"),Controlled);}
    if(!Visible||!Controlled){CloseSiege(false);return;}bSiegeOpen=true;RefreshSiege();
}
void UDAoCBridgeSubsystem::SendSiegeCommand(int32 Command){
    auto Weapon=CO(SiegeState,TEXT("weapon"));if(!bLocalAvailable||bExiting||!Weapon||Command<1||Command>10)return;
    auto Value=MakeShared<FJsonObject>();Value->SetNumberField(TEXT("oid"),CN(Weapon,TEXT("oid")));Value->SetNumberField(TEXT("revision"),SiegeRevision);Value->SetNumberField(TEXT("command"),Command);Value->SetNumberField(TEXT("ammo"),Command==1?SiegeAmmoIndex:0);Send(TEXT("siege_command"),Value);
}
bool UDAoCBridgeSubsystem::CloseSiege(bool Notify){
    const bool Open=bSiegeOpen||SiegeOverlay.IsValid();if(Open&&Notify){auto Weapon=CO(SiegeState,TEXT("weapon"));if(Weapon){auto Value=MakeShared<FJsonObject>();Value->SetNumberField(TEXT("oid"),CN(Weapon,TEXT("oid")));Value->SetNumberField(TEXT("revision"),SiegeRevision);Send(TEXT("siege_hide"),Value);}}
    if(SiegeOverlay&&GetWorld()&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(SiegeOverlay.ToSharedRef());bSiegeOpen=false;SiegeOverlay.Reset();SiegePanel.Reset();return Open;
}
void UDAoCBridgeSubsystem::RefreshSiege(){
    auto Viewport=GetWorld()?GetWorld()->GetGameViewport():nullptr;auto Weapon=CO(SiegeState,TEXT("weapon"));if(!bSiegeOpen||!Viewport||!Weapon)return;
    if(SiegeOverlay)Viewport->RemoveViewportWidgetContent(SiegeOverlay.ToSharedRef());const FVector2D Size(210,196);auto Canvas=SNew(SCanvas);
    const double SX[]={0,6,287,300},SY[]={0,19,415,448},DX[]={0,6,197,210},DY[]={0,19,163,196};
    for(int32 Y=0;Y<3;++Y)for(int32 X=0;X<3;++X)At(Canvas,{DX[X],DY[Y]},{DX[X+1]-DX[X],DY[Y+1]-DY[Y]},SNew(SImage).Image(ClassicArt(TEXT("RealmWarUI_v01/frame"),{SX[X]/300.,SY[Y]/448.},{SX[X+1]/300.,SY[Y+1]/448.})));
    At(Canvas,{8,4},{181,14},CT(CS(Weapon,TEXT("name")),9,Gold));At(Canvas,{194,1},{15,13},CB(CT(TEXT("")),[this](){CloseSiege();}));
    At(Canvas,{10,22},{190,13},SNew(STextBlock).Font(CF(8)).ColorAndOpacity(Cream).Text_Lambda([this](){const TCHAR* Labels[]={TEXT("NONE"),TEXT("AIMING"),TEXT("ARMING"),TEXT("LOADING"),TEXT("FIRING")};auto W=CO(SiegeState,TEXT("weapon"));int32 Action=FMath::Clamp(int32(CN(W,TEXT("action"))),0,4);double Left=FMath::Max(0.,SiegeTimeLeft-(FPlatformTime::Seconds()-SiegeReceivedAt));return FText::FromString(Left>.05?FString::Printf(TEXT("%s  %.1fS"),Labels[Action],Left):FString(Labels[Action]));}));
    auto Ammo=CA(Weapon,TEXT("ammo"));bool Found=false;for(auto& V:Ammo)if(int32(CN(V->AsObject(),TEXT("index"),-1))==SiegeAmmoIndex&&CN(V->AsObject(),TEXT("count"))>0)Found=true;
    if(!Found){SiegeAmmoIndex=-1;for(auto& V:Ammo)if(CN(V->AsObject(),TEXT("count"))>0){SiegeAmmoIndex=int32(CN(V->AsObject(),TEXT("index")));break;}}
    auto List=SNew(SScrollBox);for(auto& V:Ammo){auto Entry=V->AsObject();const int32 Index=int32(CN(Entry,TEXT("index"),-1));List->AddSlot()[SNew(SBox).HeightOverride(14)[CB(CT(CS(Entry,TEXT("name")),8,Index==SiegeAmmoIndex?Gold:Cream),[this,Index](){SiegeAmmoIndex=Index;RefreshSiege();})]];}At(Canvas,{10,38},{190,64},List);
    const TCHAR* Labels[]={TEXT("LOAD"),TEXT("ARM"),TEXT("AIM"),TEXT("FIRE"),TEXT("MOVE"),TEXT("STOP"),TEXT("REPAIR"),TEXT("SALVAGE"),TEXT("RELEASE")};const int32 Ids[]={1,2,3,4,5,9,6,7,8};bool CanMove=false;Weapon->TryGetBoolField(TEXT("can_move"),CanMove);
    const int64 BoundRevision=SiegeRevision;const int32 BoundOid=int32(CN(Weapon,TEXT("oid")));
    for(int32 I=0;I<9;++I){const int32 Id=Ids[I];bool Enabled=(Id!=1||SiegeAmmoIndex>=0)&&(Id!=5||CanMove);At(Canvas,{10+(I%3)*64.,108+(I/3)*19.},{60,15},SNew(SBox).IsEnabled(Enabled)[CB(CT(Labels[I],8),[this,Id,BoundRevision,BoundOid](){auto W=CO(SiegeState,TEXT("weapon"));if(SiegeRevision==BoundRevision&&int32(CN(W,TEXT("oid")))==BoundOid)SendSiegeCommand(Id);})]);}
    SiegePanel=SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){SiegePosition+=Delta;}).End([this](){SaveClassicLayout();});auto Root=SNew(SCanvas);Root->AddSlot().Position_Lambda([this,Size](){auto Extent=UIViewportSize()/ClassicScale();return FVector2D(FMath::Clamp(SiegePosition.X,0.,FMath::Max(0.,Extent.X-Size.X)),FMath::Clamp(SiegePosition.Y,0.,FMath::Max(0.,Extent.Y-Size.Y)));}).Size(Size)[SiegePanel.ToSharedRef()];SiegeOverlay=SNew(SDPIScaler).DPIScale_Lambda([this](){return ClassicScale();})[Root];Viewport->AddViewportWidgetContent(SiegeOverlay.ToSharedRef(),37);
}
