void UDAoCBridgeSubsystem::ApplyWorldClock(const TSharedPtr<FJsonObject>& Value){
    WorldClockHour=-1.;
    if(!Value.IsValid()||!Value->HasTypedField<EJson::Boolean>(TEXT("ready"))||!Value->GetBoolField(TEXT("ready")))return;
    double Hour=-1.;
    if(Value->TryGetNumberField(TEXT("hour"),Hour)&&FMath::IsFinite(Hour)&&Hour>=0.&&Hour<24.)WorldClockHour=Hour;
}
FString UDAoCBridgeSubsystem::WorldClockText()const{
    if(WorldClockHour<0.)return FString();
    const int32 Minutes=FMath::FloorToInt(WorldClockHour*60.);
    return FString::Printf(TEXT("%02d:%02d"),Minutes/60,Minutes%60);
}
void UDAoCBridgeSubsystem::RefreshWorldClock(){
    if(!ClassicTimeBox)return;
    auto Canvas=SNew(SCanvas);
    At(Canvas,{0,0},{100,32},SNew(SImage).Image(ClassicArt(TEXT("timedisp"))));
    At(Canvas,{10,9},{80,16},SNew(STextBlock).Text_Lambda([this](){return FText::FromString(WorldClockText());}).Font(CF(10)).ColorAndOpacity(Cream).Justification(ETextJustify::Center));
    // Transparent hit target preserves the close cross already painted in the original frame.
    At(Canvas,{88,0},{12,12},SNew(SButton).ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder")).IsFocusable(false).OnClicked_Lambda([this](){ToggleWorldClock();return FReply::Handled();}));
    ClassicTimeBox->SetContent(SNew(SClassicMove).Content(Canvas).Move([this](FVector2D Delta){const auto Extent=UIViewportSize()/ClassicScale();ClassicTimePosition.X=FMath::Clamp(ClassicTimePosition.X+Delta.X,0.,FMath::Max(0.,Extent.X-100));ClassicTimePosition.Y=FMath::Clamp(ClassicTimePosition.Y+Delta.Y,0.,FMath::Max(0.,Extent.Y-32));}).End([this](){SaveClassicLayout();}));
}
void UDAoCBridgeSubsystem::ToggleWorldClock(){
    if(!ClassicState.IsValid()||bExiting)return;
    bClassicTimeOpen=!bClassicTimeOpen;SaveClassicLayout();
}
