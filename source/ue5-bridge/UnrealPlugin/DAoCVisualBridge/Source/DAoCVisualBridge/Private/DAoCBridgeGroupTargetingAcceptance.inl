// Actual key dispatcher and existing identity-bearing group command, private only.
if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeGroupTargetKeysTest"))){
    const auto OriginalRows=ClassicState->GetArrayField(TEXT("group"));
    auto Row=[](int32 Oid,bool Own){auto M=MakeShared<FJsonObject>();M->SetNumberField(TEXT("oid"),Oid);M->SetBoolField(TEXT("me"),Own);M->SetStringField(TEXT("token"),FString::Printf(TEXT("current-member-%d"),Oid));M->SetNumberField(TEXT("hp"),-1);return MakeShared<FJsonValueObject>(M);};
    TArray<TSharedPtr<FJsonValue>> Roster;for(int32 I=0;I<7;++I)Roster.Add(Row(100+I,false));Roster.Insert(Row(42,true),4);ClassicState->SetArrayField(TEXT("group"),Roster);
    const auto Ordered=FBridgeGroupTargeting::Ordered(Roster);Check(Ordered.Num()==8&&FBridgeGroupTargeting::Me(Ordered[0])&&Ordered[1]==Roster[0]&&Ordered[7]==Roster[7],TEXT("shared group presentation puts self first without changing peer order"));
    Check(Roster[4]->AsObject()->GetBoolField(TEXT("me")),TEXT("view ordering never edits indexed server roster"));
    const TCHAR* Keys[]={TEXT("NumPadTwo"),TEXT("NumPadThree"),TEXT("NumPadFour"),TEXT("NumPadFive"),TEXT("NumPadSix"),TEXT("NumPadSeven"),TEXT("NumPadEight")};
    for(int32 I=0;I<7;++I){Press(Keys[I]);UpdateClassicInput();auto V=Capture(TEXT("group_target"));if(V)Check(V->GetIntegerField(TEXT("member_oid"))==100+I&&V->GetStringField(TEXT("member_token"))==FString::Printf(TEXT("current-member-%d"),100+I),TEXT("actual group shortcut carries correct current member and token"));}
    auto Replacement=Row(900,false);Roster[0]=Replacement;ClassicState->SetArrayField(TEXT("group"),Roster);Press(TEXT("NumPadTwo"));UpdateClassicInput();auto Updated=Capture(TEXT("group_target"));if(Updated)Check(Updated->GetIntegerField(TEXT("member_oid"))==900,TEXT("roster replacement cannot send previously displayed member identity"));
    Replacement->AsObject()->SetNumberField(TEXT("hp"),0);Press(TEXT("NumPadTwo"));UpdateClassicInput();Capture(TEXT("group_target"));
    Check(FBridgeGroupTargeting::Member(FBridgeGroupTargeting::Ordered(Roster),1)==Replacement->AsObject(),TEXT("dead and unknown-health members retain target slots for resurrection"));
    for(double Bad:{0.,-1.,1.5,65536.}){Replacement->AsObject()->SetNumberField(TEXT("oid"),Bad);Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("invalid member object cannot select its neighbor"));}Replacement->AsObject()->SetNumberField(TEXT("oid"),900);
    Replacement->AsObject()->SetStringField(TEXT("token"),TEXT(""));Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("missing current member token blocks shortcut"));Replacement->AsObject()->SetStringField(TEXT("token"),TEXT("replacement-token"));
    Roster[1]=Row(900,false);ClassicState->SetArrayField(TEXT("group"),Roster);Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("ambiguous duplicated object identity cannot target"));Roster[1]=Row(101,false);
    Roster.RemoveAt(4);ClassicState->SetArrayField(TEXT("group"),Roster);Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("roster without self cannot misnumber peers"));
    Roster={Row(42,true),Row(900,false)};ClassicState->SetArrayField(TEXT("group"),Roster);Press(TEXT("NumPadEight"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("missing group slot does not wrap to another member"));
    bChatOpen=true;Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("chat blocks group shortcuts"));bChatOpen=false;
    bOptionsOpen=true;Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("options blocks group shortcuts"));bOptionsOpen=false;
    const FString SavedSession=Session;Session.Empty();Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("no session cannot dispatch group shortcut"));Session=SavedSession;
    Check(KeyConfiguration->Bind(TEXT("target_group_2"),0,TEXT("Ctrl+Y"),Message),TEXT("group target shortcut is editable"));Press(TEXT("Ctrl+Y"));UpdateClassicInput();Capture(TEXT("group_target"));
    Press(TEXT("NumPadTwo"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("former group shortcut is inactive after reassignment"));
    const FString LegacyGroupKeys=KeyConfiguration->Path+TEXT(".group-migration.ini");
    Check(FFileHelper::SaveStringToFile(TEXT("[KeyConfiguration]\nVersion=1\n[Bindings]\nshow_map0=NumPadTwo\n"),*LegacyGroupKeys),TEXT("private older custom key settings fixture saves"));
    FBridgeKeyConfiguration GroupMigration;GroupMigration.Load(LegacyGroupKeys);
    Check(GroupMigration.Text(TEXT("show_map"),0)==TEXT("NumPadTwo")&&GroupMigration.Text(TEXT("target_group_2"),0)==TEXT("-"),TEXT("explicit older custom binding wins over newly added group default"));
    Check(!FBridgeGroupTargeting::Member({},1).IsValid(),TEXT("empty group cannot invent a target"));
    ClassicState->SetArrayField(TEXT("group"),OriginalRows);KeyConfiguration->Reset();Outgoing.Empty();
}
