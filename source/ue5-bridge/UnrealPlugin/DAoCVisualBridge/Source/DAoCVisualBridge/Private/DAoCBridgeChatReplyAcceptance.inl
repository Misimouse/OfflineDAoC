if(FParse::Param(FCommandLine::Get(),TEXT("DaocBridgeChatReplyKeysTest"))){
    ApplyChat(MakeShared<FJsonObject>());const auto SavedChat=ChatState;
    ChatState=MakeShared<FJsonObject>();ChatState->SetStringField(TEXT("reply_to"),TEXT("Codexfriend"));
    Press(TEXT("Ctrl+R"));UpdateChatInput();Check(bChatOpen&&ChatInput.IsValid()&&ChatInput->GetText().ToString()==TEXT("/send Codexfriend "),TEXT("actual reply chord opens existing chat with pinned original recipient"));Check(Outgoing.IsEmpty(),TEXT("opening reply does not send a message"));
    ChatState->SetStringField(TEXT("reply_to"),TEXT("Anotherfriend"));Check(ChatInput.IsValid()&&ChatInput->GetText().ToString()==TEXT("/send Codexfriend "),TEXT("new incoming sender cannot silently retarget text being written"));
    SubmitChat(TEXT("/send Codexfriend Private reply"));auto Sent=Capture(TEXT("chat"));if(Sent)Check(Sent->GetStringField(TEXT("text"))==TEXT("/send Codexfriend Private reply"),TEXT("existing submit sends exact explicit recipient without introducing another transport action"));Check(!bChatOpen,TEXT("submission closes existing chat normally"));
    bOptionsOpen=true;Press(TEXT("Ctrl+R"));UpdateChatInput();Check(!bChatOpen&&Outgoing.IsEmpty(),TEXT("options prevent opening a reply"));bOptionsOpen=false;
    const FString SavedReplySession=Session;Session.Empty();Press(TEXT("Ctrl+R"));UpdateChatInput();Check(!bChatOpen,TEXT("missing session cannot start reply"));Session=SavedReplySession;
    ChatState->SetStringField(TEXT("reply_to"),TEXT("Bad;quit"));Press(TEXT("Ctrl+R"));UpdateChatInput();Check(bChatOpen&&ChatInput->GetText().ToString()==TEXT("/r "),TEXT("malformed recipient is never inserted into an explicit send command"));CloseChat();
    FString ReplyMessage;Check(KeyConfiguration->Bind(TEXT("reply"),0,TEXT("Ctrl+Y"),ReplyMessage),TEXT("reply shortcut remains editable"));Press(TEXT("Ctrl+R"));UpdateChatInput();Check(!bChatOpen,TEXT("former reply chord becomes inactive"));Press(TEXT("Ctrl+Y"));UpdateChatInput();Check(bChatOpen&&Outgoing.IsEmpty(),TEXT("new reply binding opens existing chat without sending"));CloseChat();
    KeyConfiguration->Reset();ChatState=SavedChat;RefreshChatHistory();Outgoing.Empty();PC->PlayerInput->FlushPressedKeys();
}
