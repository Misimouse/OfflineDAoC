#include "DAoCBridgeSubsystem.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Kismet/KismetSystemLibrary.h"
#include "UnrealClient.h"
#include "Engine/World.h"

bool UDAoCBridgeSubsystem::TickQuestRewardAcceptance()
{
    FString Path;
    if (!FParse::Value(FCommandLine::Get(), TEXT("DaocBridgeQuestRewardsTest="), Path))
        return false;
    static int32 Phase = 0, Checks = 0;
    static double Began = 0;
    static TSharedPtr<FJsonObject> Fixture;
    static TArray<TSharedPtr<FJsonValue>> Failures;
    auto Check = [&](bool Passed, const FString& Label) {
        ++Checks;
        if (!Passed)
            Failures.Add(MakeShared<FJsonValueString>(Label));
    };
    TFunction<void(TSharedRef<SWidget>, const FString&, TArray<TSharedPtr<SWidget>>&)> Collect;
    Collect = [&](TSharedRef<SWidget> Widget, const FString& Type, TArray<TSharedPtr<SWidget>>& Out) {
        if (Widget->GetTypeAsString() == Type)
            Out.Add(Widget);
        auto* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            Collect(Children->GetChildAt(Index), Type, Out);
    };
    auto Button = [&](const FString& Text) -> TSharedPtr<SButton> {
        TArray<TSharedPtr<SWidget>> Buttons;
        if (QuestRewardPanel)
            Collect(QuestRewardPanel.ToSharedRef(), TEXT("SButton"), Buttons);
        for (auto Widget : Buttons)
        {
            TArray<TSharedPtr<SWidget>> Labels;
            Collect(Widget.ToSharedRef(), TEXT("STextBlock"), Labels);
            for (auto Label : Labels)
                if (StaticCastSharedPtr<STextBlock>(Label)->GetText().ToString().Equals(Text, ESearchCase::IgnoreCase))
                    return StaticCastSharedPtr<SButton>(Widget);
        }
        return nullptr;
    };
    auto Capture = [&](const FString& Action, const FString& Token) {
        Outgoing.Add(0);
        const FString Text = UTF8_TO_TCHAR(reinterpret_cast<const char*>(Outgoing.GetData()));
        Outgoing.Reset();
        TSharedPtr<FJsonObject> Command;
        Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Command) && Command &&
              Command->GetStringField(TEXT("action")) == TEXT("quest_reward_response") &&
              Command->GetStringField(TEXT("action_name")) == Action &&
              Command->GetStringField(TEXT("token")) == Token &&
              !Command->HasField(TEXT("quest_id")) && !Command->HasField(TEXT("giver_id")), TEXT("Response binds to displayed token: ") + Action);
        return Command;
    };
    if (Phase == 0)
    {
        FString Text;
        const bool Loaded = FFileHelper::LoadFileToString(Text, *Path) &&
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Fixture) && Fixture.IsValid();
        Check(Loaded, TEXT("Fixture loads"));
        if (!Loaded)
        {
            Phase = 3;
            return true;
        }
        Session = TEXT("quest-reward-native-isolated");
        bLocalAvailable = true;
        Socket = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateSocket(NAME_Stream, TEXT("Quest reward acceptance"), false);
        ApplyQuestRewards(Fixture->GetObjectField(TEXT("offer")));
        Began = FPlatformTime::Seconds();
        Phase = 1;
    }
    if (Phase == 1 && FPlatformTime::Seconds() - Began > .5)
    {
        Check(QuestRewardOverlay && QuestRewardPanel, TEXT("Original offer opens"));
        Check(ClassicArt(TEXT("QuantityUI_v01/dialog_sm")) != nullptr, TEXT("Original dialog atlas loads"));
        if (QuestRewardPanel)
        {
            const auto Geometry = QuestRewardPanel->GetCachedGeometry();
            Check(WorldPointerBlocked(Geometry.LocalToAbsolute(FVector2D(60, 90))), TEXT("Dialog does not click through to world"));
        }
        const auto Accept = Button(TEXT("Accept"));
        const auto Decline = Button(TEXT("Decline"));
        Check(Accept && Accept->IsEnabled() && Decline && Decline->IsEnabled(), TEXT("Offer contains both choices"));
        if (Accept)
        {
            Accept->SimulateClick();
            Capture(TEXT("accept"), TEXT("offer-a"));
        }
        ApplyQuestRewards(Fixture->GetObjectField(TEXT("reward")));
        if (Decline)
            Decline->SimulateClick();
        Check(Outgoing.IsEmpty(), TEXT("Old offer control cannot affect reward window"));
        Began = FPlatformTime::Seconds();
        Phase = 2;
    }
    if (Phase == 2 && FPlatformTime::Seconds() - Began > .5)
    {
        const auto Finish = Button(TEXT("Finish"));
        const auto NotYet = Button(TEXT("Not Yet"));
        Check(Finish && !Finish->IsEnabled() && NotYet && NotYet->IsEnabled(), TEXT("Finish waits for exact selection"));
        TArray<TSharedPtr<SWidget>> Checkboxes;
        if (QuestRewardPanel)
            Collect(QuestRewardPanel.ToSharedRef(), TEXT("SCheckBox"), Checkboxes);
        Check(Checkboxes.Num() == 2, TEXT("Two selectable server reward rows"));
        if (Checkboxes.Num() == 2)
        {
            auto Box = StaticCastSharedPtr<SCheckBox>(Checkboxes[1]);
            const FKeyEvent Key(EKeys::SpaceBar, FModifierKeysState(), 0, false, 0, 0);
            const auto Geometry = Box->GetCachedGeometry();
            Box->OnKeyDown(Geometry, Key);
            Box->OnKeyUp(Geometry, Key);
            Check(Box->IsChecked() && QuestRewardChoices.Num() == 1 && QuestRewardChoices[0] == 1, TEXT("Original row can be selected using Slate input"));
        }
        Began = FPlatformTime::Seconds();
        Phase = 3;
        return true;
    }
    if (Phase == 3 && FPlatformTime::Seconds() - Began > .25)
    {
        const auto Finish = Button(TEXT("Finish"));
        TArray<TSharedPtr<SWidget>> Checkboxes;
        if (QuestRewardPanel)
            Collect(QuestRewardPanel.ToSharedRef(), TEXT("SCheckBox"), Checkboxes);
        Check(Checkboxes.Num() == 2 && !Checkboxes[0]->IsEnabled() && Finish && Finish->IsEnabled(),
              TEXT("Selection cap prevents another option after Slate updates attributes"));
        if (Finish && Finish->IsEnabled())
        {
            Finish->SimulateClick();
            const auto Command = Capture(TEXT("finish"), TEXT("reward-a"));
            const auto* Choices = Command ? Command->GetArrayField(TEXT("choices")).GetData() : nullptr;
            Check(Choices && Command->GetArrayField(TEXT("choices")).Num() == 1 && (*Choices)->AsNumber() == 1, TEXT("Sends the original zero-based row index"));
        }
        Check(QuestRewardOverlay.IsValid(), TEXT("Click does not pretend the server completed the quest"));
        FScreenshotRequest::RequestScreenshot(Path + TEXT(".png"), true, false);
        Began = FPlatformTime::Seconds();
        Phase = 4;
        return true;
    }
    if ((Phase == 4 || (Phase == 3 && !Fixture)) && FPlatformTime::Seconds() - Began > .5)
    {
        if (Fixture)
        {
            const auto NotYet = Button(TEXT("Not Yet"));
            if (NotYet)
            {
                NotYet->SimulateClick();
                Capture(TEXT("close"), TEXT("reward-a"));
            }
            Check(!QuestRewardOverlay && QuestRewardChoices.IsEmpty(), TEXT("Not Yet dismisses without a reward request"));
            ApplyQuestRewards(Fixture->GetObjectField(TEXT("reward")));
            Check(!QuestRewardOverlay, TEXT("Late snapshot cannot reopen locally dismissed dialog"));
            ApplyQuestRewards(nullptr);
            ApplyQuestRewards(Fixture->GetObjectField(TEXT("reward")));
            Check(QuestRewardOverlay.IsValid(), TEXT("New server dialog opens after close"));
            ApplyQuestRewards(nullptr);
            Check(!QuestRewardOverlay, TEXT("Missing server dialog closes native window"));
        }
        auto Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("passed"), Failures.IsEmpty());
        Result->SetNumberField(TEXT("checks"), Checks);
        Result->SetArrayField(TEXT("failures"), Failures);
        FString Text;
        FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Text));
        FFileHelper::SaveStringToFile(Text, *(Path + TEXT(".native.json")));
        Phase = 5;
        UKismetSystemLibrary::QuitGame(GetWorld(), GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, false);
    }
    return true;
}
