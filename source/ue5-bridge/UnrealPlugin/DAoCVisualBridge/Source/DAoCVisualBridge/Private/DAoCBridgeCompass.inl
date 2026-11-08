// Original 112x22 compass; the existing 512x32 letter strip is shown at half size.
double UDAoCBridgeSubsystem::CompassDegrees()const{
    double Yaw=0;
    if(IsValid(PlayerPawn))Yaw=PlayerPawn->GetActorRotation().Yaw;
    else if(const auto* Row=EntityRows.Find(TEXT("player:local"))){
        const auto Forward=CA(*Row,TEXT("forward_xz"));
        if(Forward.Num()!=2||Forward[0]->Type!=EJson::Number||Forward[1]->Type!=EJson::Number)return 0;
        const double X=Forward[0]->AsNumber(),Y=Forward[1]->AsNumber();
        if(!FMath::IsFinite(X)||!FMath::IsFinite(Y)||FMath::Square(X)+FMath::Square(Y)<.000001)return 0;
        Yaw=FMath::RadiansToDegrees(FMath::Atan2(Y,X));
    }else return 0;
    // UE +X is east, +Y is south. Original Server.compass_of: 180 + heading*360/4096.
    if(!FMath::IsFinite(Yaw))return 0;
    return FMath::Fmod(FMath::Fmod(Yaw+90.,360.)+360.,360.);
}
void UDAoCBridgeSubsystem::RefreshCompass(){
    if(!ClassicCompassBox)return;
    auto Canvas=SNew(SCanvas);
    At(Canvas,{0,0},{112,22},SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0,0,0,.45f)).Padding(0));
    auto Letters=SNew(SCanvas);
    for(int32 I=0;I<3;++I)Letters->AddSlot().Position_Lambda([this,I](){return FVector2D(54.-256.-(16.+CompassDegrees()/360.*256.)+I*256.,0);}).Size(FVector2D(256,16))[SNew(SImage).Image(ClassicArt(TEXT("compass_bar")))];
    At(Canvas,{2,3},{108,16},SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Letters]);
    At(Canvas,{55.5,0},{1,3},SNew(SImage).Image(FCoreStyle::Get().GetBrush("WhiteBrush")).ColorAndOpacity(Gold));
    ClassicCompassBox->SetContent(SNew(SClassicMove).Whole(true).Content(Canvas).Move([this](FVector2D Delta){const auto Extent=UIViewportSize()/ClassicScale();ClassicCompassPosition.X=FMath::Clamp(ClassicCompassPosition.X+Delta.X,0.,FMath::Max(0.,Extent.X-112));ClassicCompassPosition.Y=FMath::Clamp(ClassicCompassPosition.Y+Delta.Y,0.,FMath::Max(0.,Extent.Y-22));}).End([this](){SaveClassicLayout();}));
}
void UDAoCBridgeSubsystem::ToggleCompass(){
    if(!ClassicState.IsValid()||bExiting)return;
    bClassicCompassOpen=!bClassicCompassOpen;RefreshCompass();SaveClassicLayout();
}
