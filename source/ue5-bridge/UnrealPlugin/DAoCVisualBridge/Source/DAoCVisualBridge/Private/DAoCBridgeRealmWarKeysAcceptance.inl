if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeRealmWarKeysTest"))){
    const auto OldWarState=RealmWarState;const auto OldWarPage=RealmWarPage;const auto OldWarLast=RealmWarLastRequest;const bool OldWarOpen=bRealmWarOpen;
    CloseRealmWar(false);RealmWarState=MakeShared<FJsonObject>();RealmWarState->SetBoolField(TEXT("pending"),false);RealmWarPage=3;RealmWarLastRequest=-10000;Outgoing.Empty();
    Press(TEXT("Shift+M"));UpdateClassicInput();auto Request=Capture(TEXT("warmap_request"));
    Check(bRealmWarOpen&&RealmWarOverlay.IsValid(),TEXT("actual Shift M opens existing original realm war window"));if(Request)Check(Request->GetIntegerField(TEXT("page"))==3,TEXT("shortcut requests current original Hibernia page without invented actions"));
    Press(TEXT("Shift+M"));UpdateClassicInput();Capture(TEXT("warmap_close"));Check(!bRealmWarOpen&&!RealmWarOverlay.IsValid(),TEXT("same shortcut closes original window and request state"));
    for(int32 Block=0;Block<3;++Block){bChatOpen=Block==0;bOptionsOpen=Block==1;bExiting=Block==2;Press(TEXT("Shift+M"));UpdateClassicInput();Check(!bRealmWarOpen&&Outgoing.IsEmpty(),TEXT("chat options and exit cannot open war map by key"));}bChatOpen=bOptionsOpen=bExiting=false;
    const auto OldSession=Session;Session.Empty();Press(TEXT("Shift+M"));UpdateClassicInput();Check(!bRealmWarOpen&&Outgoing.IsEmpty(),TEXT("disconnected session cannot open war map"));Session=OldSession;
    FString WarKeyMessage;Check(KeyConfiguration->Bind(TEXT("show_war_map"),0,TEXT("Ctrl+M"),WarKeyMessage),TEXT("realm war shortcut remains editable"));Press(TEXT("Shift+M"));UpdateClassicInput();Check(!bRealmWarOpen&&Outgoing.IsEmpty(),TEXT("former war map binding is inactive"));RealmWarLastRequest=-10000;Press(TEXT("Ctrl+M"));UpdateClassicInput();Capture(TEXT("warmap_request"));Check(bRealmWarOpen,TEXT("rebound shortcut uses same original window"));
    Check(KeyConfiguration->Text(TEXT("show_map"),0)==TEXT("M"),TEXT("ordinary zone map keeps accepted M binding"));
    CloseRealmWar(false);RealmWarState=OldWarState;RealmWarPage=OldWarPage;RealmWarLastRequest=OldWarLast;bRealmWarOpen=OldWarOpen;if(OldWarOpen)RefreshRealmWar();KeyConfiguration->Reset();Outgoing.Empty();PC->PlayerInput->FlushPressedKeys();
}
