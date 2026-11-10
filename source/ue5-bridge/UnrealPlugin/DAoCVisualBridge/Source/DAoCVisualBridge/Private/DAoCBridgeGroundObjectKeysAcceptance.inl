if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeGroundObjectKeysTest"))){
    const auto SavedInteraction=InteractionState;const int64 SavedGeneration=GroundObjectGeneration;GroundObjectGeneration=17;
    auto Ground=MakeShared<FJsonObject>();Ground->SetStringField(TEXT("id"),TEXT("object:345"));Ground->SetStringField(TEXT("object_token"),FString::ChrN(64,TEXT('b')));Ground->SetNumberField(TEXT("world_generation"),17);EntityRows.Add(TEXT("object:345"),Ground);
    InteractionState=MakeShared<FJsonObject>();auto Target=MakeShared<FJsonObject>();Target->SetStringField(TEXT("id"),TEXT("object:345"));InteractionState->SetObjectField(TEXT("target"),Target);
    Press(TEXT("Hyphen"));UpdateClassicInput();auto Loot=Capture(TEXT("target_loot"));if(Loot)Check(Loot->GetNumberField(TEXT("world_generation"))==17,TEXT("actual nearest-loot key uses current world generation"));
    Press(TEXT("Equals"));UpdateClassicInput();auto Pickup=Capture(TEXT("get_object"));if(Pickup)Check(Pickup->GetStringField(TEXT("entity_id"))==TEXT("object:345")&&Pickup->GetStringField(TEXT("object_token"))==Ground->GetStringField(TEXT("object_token")),TEXT("actual Get Item key carries selected current object token"));
    bChatOpen=true;Press(TEXT("Equals"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("typing never picks up a selected item"));bChatOpen=false;
    bOptionsOpen=true;Press(TEXT("Hyphen"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("options block nearest-loot input"));bOptionsOpen=false;
    Ground->SetNumberField(TEXT("world_generation"),16);Press(TEXT("Equals"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("actual key refuses old generation"));Ground->SetNumberField(TEXT("world_generation"),17);
    FString BindMessage;Check(KeyConfiguration->Bind(TEXT("get_item"),0,TEXT("Ctrl+U"),BindMessage),TEXT("Get Item remains editable in original controls page"));Press(TEXT("Equals"));UpdateClassicInput();Check(Outgoing.IsEmpty(),TEXT("old pickup binding becomes inactive"));Press(TEXT("Ctrl+U"));UpdateClassicInput();Capture(TEXT("get_object"));
    KeyConfiguration->Reset();InteractionState=SavedInteraction;GroundObjectGeneration=SavedGeneration;EntityRows.Remove(TEXT("object:345"));PC->PlayerInput->FlushPressedKeys();Outgoing.Empty();
}
