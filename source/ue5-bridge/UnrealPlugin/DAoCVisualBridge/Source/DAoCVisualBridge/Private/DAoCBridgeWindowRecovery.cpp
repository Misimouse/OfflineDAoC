#include "DAoCBridgeSubsystem.h"
#include "Widgets/Layout/SBox.h"

bool UDAoCBridgeSubsystem::RecoverableWindowOpen(const FString& Id)const{
    if(Id==TEXT("warmap"))return bRealmWarOpen;
    if(Id==TEXT("time"))return bClassicTimeOpen;
    if(Id==TEXT("compass"))return bClassicCompassOpen;
    if(Id==TEXT("panel"))return bClassicOpen;
    if(Id==TEXT("chat_combat"))return bChatCombatOpen;
    if(Id==TEXT("minigroup"))return bClassicMiniGroupOpen;
    if(Id==TEXT("map"))return bZoneMapOpen;
    if(Id==TEXT("journal"))return bClassicJournalOpen;
    if(Id==TEXT("guild"))return GuildOverlay.IsValid();
    return false;
}
void UDAoCBridgeSubsystem::ToggleRecoverableWindow(const FString& Id){
    if(!ClassicState.IsValid()||bExiting)return;
    if(Id==TEXT("warmap"))ToggleRealmWar();
    else if(Id==TEXT("time"))ToggleWorldClock();
    else if(Id==TEXT("compass"))ToggleCompass();
    else if(Id==TEXT("panel")){bClassicOpen=!bClassicOpen;bInventoryMoving=false;RefreshClassicPanel();SaveClassicLayout();}
    else if(Id==TEXT("chat_combat"))ToggleCombatChat();
    else if(Id==TEXT("minigroup")){bClassicMiniGroupOpen=!bClassicMiniGroupOpen;RefreshClassicMiniGroup();SaveClassicLayout();}
    else if(Id==TEXT("map"))ToggleZoneMap();
    else if(Id==TEXT("journal"))ToggleClassicJournal();
    else if(Id==TEXT("guild"))ToggleGuild();
}
void UDAoCBridgeSubsystem::ResetWindowLayout(){
    if(!ClassicState.IsValid()||bExiting)return;
    const FVector2D Size=UIViewportSize()/ClassicScale();
    ClassicTimePosition={127,0};bClassicTimeOpen=true;RefreshWorldClock();
    ClassicCompassPosition={Size.X*.5-56,Size.Y-107};bClassicCompassOpen=true;RefreshCompass();
    ClassicPositions[0]={Size.X-192,0};
    ClassicPositions[1]={Size.X*.5-186,Size.Y-80};ClassicPositions[2]={Size.X*.5-186,Size.Y-40};
    ClassicPositions[3]={0,100};ClassicPositions[4]={40,150};
    ClassicVertical[0]=ClassicVertical[1]=false;ClassicVertical[2]=true;
    ClassicJournalPosition={125,130};ClassicTrainerPosition={260,70};
    ClassicVaultPosition={FMath::Clamp(Size.X*.5-230./ClassicScale()-236.,44.,200.),140};
    // Restore existing native defaults without resetting chat filters or contents.
    ChatSizes[0]={400,112};ChatSizes[1]={400,88};
    ChatPositions[0]={Size.X-400-20./ClassicScale(),Size.Y-112-22./ClassicScale()};
    ChatPositions[1]=ChatPositions[0]-FVector2D(0,96);
    bChatCombatOpen=true;bClassicOpen=true;bClassicMiniGroupOpen=false;
    const double Reserve=FMath::Max(320.,double(ChatReservedHeight())+16.)/ClassicScale();
    ClassicPetPosition={Size.X-330,Size.Y-Reserve-198};ClassicConcentrationPosition={Size.X-468,Size.Y-Reserve-198};
    RealmWarPosition={100,40};CloseRealmWar();
    ZoneMapPosition={60,80};CloseZoneMap();CloseClassicJournal();CloseClassicTrainer();CloseClassicDetail();CloseGuild();
    UILayoutUnits=FVector2D::ZeroVector;UpdateUILayout();
    RefreshClassicPanel();RefreshClassicBars();RefreshClassicMiniGroup();
    if(ChatPanels[1])ChatPanels[1]->SetVisibility(EVisibility::Visible);
    SaveClassicLayout();
}
