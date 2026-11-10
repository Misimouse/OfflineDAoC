#include "Widgets/Input/SCheckBox.h"

void UDAoCBridgeSubsystem::ApplyQuestRewards(TSharedPtr<FJsonObject> State)
{
    QuestRewardState = State;
    const FString Token = CS(State, TEXT("token"));
    const auto Dialog = CO(State, TEXT("dialog"));
    if (Token.IsEmpty() || !Dialog || !Dialog->HasField(TEXT("code")))
    {
        CloseQuestRewards(false);
        QuestRewardDismissedToken.Empty();
        return;
    }
    if (Token == QuestRewardDismissedToken || (QuestRewardOverlay && Token == QuestRewardToken))
        return;
    CloseQuestRewards(false);
    QuestRewardToken = Token;
    RefreshQuestRewards();
}

void UDAoCBridgeSubsystem::RespondQuestRewards(const FString& Action, const FString& Token)
{
    if (!QuestRewardOverlay || Token.IsEmpty() || Token != QuestRewardToken ||
        Token != CS(QuestRewardState, TEXT("token")) || Token == QuestRewardDismissedToken)
        return;
    const auto Dialog = CO(QuestRewardState, TEXT("dialog"));
    const int32 Code = int32(CN(Dialog, TEXT("code")));
    if (Action != TEXT("close") &&
        !((Code == 0x22 && (Action == TEXT("accept") || Action == TEXT("decline"))) ||
          (Code == 0x21 && Action == TEXT("finish") && QuestRewardChoices.Num() == int32(CN(Dialog, TEXT("required_choices"), -1)))))
        return;
    auto Request = MakeShared<FJsonObject>();
    Request->SetStringField(TEXT("token"), Token);
    Request->SetStringField(TEXT("action_name"), Action);
    if (Action == TEXT("finish"))
    {
        QuestRewardChoices.Sort();
        TArray<TSharedPtr<FJsonValue>> Choices;
        for (const int32 Choice : QuestRewardChoices)
            Choices.Add(MakeShared<FJsonValueNumber>(Choice));
        Request->SetArrayField(TEXT("choices"), Choices);
    }
    Send(TEXT("quest_reward_response"), Request);
}

bool UDAoCBridgeSubsystem::CloseQuestRewards(bool Notify)
{
    if (!QuestRewardOverlay)
        return false;
    if (Notify)
    {
        RespondQuestRewards(TEXT("close"), QuestRewardToken);
        QuestRewardDismissedToken = QuestRewardToken;
    }
    if (GetWorld() && GetWorld()->GetGameViewport())
        GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(QuestRewardOverlay.ToSharedRef());
    QuestRewardOverlay.Reset();
    QuestRewardPanel.Reset();
    QuestRewardToken.Empty();
    QuestRewardChoices.Reset();
    return true;
}

void UDAoCBridgeSubsystem::RefreshQuestRewards()
{
    if (!GetWorld() || !GetWorld()->GetGameViewport())
        return;
    const auto Dialog = CO(QuestRewardState, TEXT("dialog"));
    const int32 Code = int32(CN(Dialog, TEXT("code")));
    const bool Offer = Code == 0x22;
    if (!Offer && Code != 0x21)
        return;
    const FString Token = QuestRewardToken;
    const auto Options = CA(Dialog, TEXT("optional_items"));
    const int32 Required = int32(CN(Dialog, TEXT("required_choices"), -1));
    if (Required < 0 || Required > 8 || Required > Options.Num())
        return;
    auto Body = SNew(SScrollBox);
    auto AddText = [&Body](const FString& Text, int32 Size, FLinearColor Color)
    {
        if (!Text.IsEmpty())
            Body->AddSlot().Padding(4, 3)[SNew(STextBlock).Text(FText::FromString(Text)).Font(CF(Size)).ColorAndOpacity(Color).WrapTextAt(335.f)];
    };
    AddText(CS(Dialog, TEXT("summary")), 11, Gold);
    AddText(CS(Dialog, TEXT("story")), 11, Cream);
    for (const auto& Goal : CA(Dialog, TEXT("goals")))
        if (Goal->Type == EJson::String)
            AddText(Goal->AsString(), 10, Cream);

    const int64 Copper = int64(CN(Dialog, TEXT("money")));
    const int32 Experience = int32(CN(Dialog, TEXT("experience_percent")));
    if (Copper > 0)
        AddText(FString::Printf(TEXT("Money: %lld copper"), Copper), 10, Gold);
    if (Experience > 0)
        AddText(FString::Printf(TEXT("Experience: %d%%"), Experience), 10, Gold);

    auto AddItem = [&](TSharedPtr<FJsonObject> Item, int32 Index)
    {
        const FString Name = CS(Item, TEXT("name"));
        if (Name.IsEmpty())
            return;
        auto Row = SNew(SHorizontalBox);
        if (Index >= 0 && !Offer)
        {
            Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 5, 0)
            [
                SNew(SCheckBox)
                .IsChecked_Lambda([this, Token, Index]() { return Token == QuestRewardToken && QuestRewardChoices.Contains(Index) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
                .IsEnabled_Lambda([this, Token, Index, Required]() { return Token == QuestRewardToken && (QuestRewardChoices.Contains(Index) || QuestRewardChoices.Num() < Required); })
                .OnCheckStateChanged_Lambda([this, Token, Index, Required](ECheckBoxState Checked)
                {
                    if (Token != QuestRewardToken)
                        return;
                    if (Checked != ECheckBoxState::Checked)
                        QuestRewardChoices.Remove(Index);
                    else if (QuestRewardChoices.Num() < Required)
                        QuestRewardChoices.AddUnique(Index);
                })
            ];
        }
        const auto* Icon = ClassicIcon(int32(CN(Item, TEXT("icon"), -1)));
        if (Icon)
            Row->AddSlot().AutoWidth().Padding(0, 0, 6, 0)[SNew(SBox).WidthOverride(16).HeightOverride(16)[SNew(SImage).Image(Icon)]];
        Row->AddSlot().FillWidth(1)[CT(Name, 10, Cream)];
        Body->AddSlot().Padding(6, 2)[Row];
    };
    const auto Fixed = CA(Dialog, TEXT("fixed_items"));
    if (!Fixed.IsEmpty())
        AddText(TEXT("Rewards"), 11, Gold);
    for (const auto& Item : Fixed)
        if (Item->Type == EJson::Object)
            AddItem(Item->AsObject(), -1);
    if (!Options.IsEmpty())
        AddText(FString::Printf(TEXT("Choose %d"), Required), 11, Gold);
    for (int32 Index = 0; Index < Options.Num(); ++Index)
        if (Options[Index]->Type == EJson::Object)
            AddItem(Options[Index]->AsObject(), Index);

    auto Confirm = CB(CT(Offer ? TEXT("Accept") : TEXT("Finish"), 11, Gold), [this, Offer, Token]() {
        RespondQuestRewards(Offer ? TEXT("accept") : TEXT("finish"), Token);
    });
    Confirm->SetEnabled(TAttribute<bool>::CreateLambda([this, Token, Required, Offer]() {
        return Token == QuestRewardToken && (Offer || QuestRewardChoices.Num() == Required);
    }));
    auto Cancel = CB(CT(Offer ? TEXT("Decline") : TEXT("Not Yet"), 11, Cream), [this, Offer, Token]() {
        if (Token != QuestRewardToken)
            return;
        if (Offer)
            RespondQuestRewards(TEXT("decline"), Token);
        else
            CloseQuestRewards();
    });
    auto Layout = SNew(SOverlay);
    Layout->AddSlot()[SNew(SImage).Image(ClassicArt(TEXT("QuantityUI_v01/dialog_sm")))];
    Layout->AddSlot().Padding(FMargin(12, 10))
    [
        SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(7, 0, 7, 6)[CT(CS(Dialog, TEXT("title")), 13, Gold)]
        + SVerticalBox::Slot().FillHeight(1)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.022f, .025f, .025f, .95f))[Body]]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).Padding(1)[Confirm]
            + SHorizontalBox::Slot().FillWidth(1).Padding(1)[Cancel]
        ]
    ];
    auto Close = CB(SNew(SBox).WidthOverride(18).HeightOverride(22), [this, Token]() {
        if (Token == QuestRewardToken)
            CloseQuestRewards();
    });
    Close->SetToolTipText(FText::FromString(TEXT("Close")));
    Layout->AddSlot().HAlign(HAlign_Right).VAlign(VAlign_Top)[Close];
    QuestRewardPanel = Layout;
    QuestRewardOverlay = SNew(SOverlay)
        + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(SDPIScaler).DPIScale_Lambda([this]() { return ClassicScale(); })
        [SNew(SBox).WidthOverride(370).HeightOverride(340)[Layout]]];
    GetWorld()->GetGameViewport()->AddViewportWidgetContent(QuestRewardOverlay.ToSharedRef(), 38);
}
