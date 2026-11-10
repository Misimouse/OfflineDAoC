"""Stage and compile quest reward UI without changing installed UE5 files."""
import argparse
import json
from pathlib import Path
import shutil
from build_spell_audio_native import build
from prepare_combined_expansion_data import digest


def build_quest(workspace, engine):
    lab = "QuestRewardsLab/Native"
    root = workspace / lab
    source = Path(__file__).resolve().parents[1] / "UnrealPlugin/DAoCVisualBridge/Source"
    staged = root / "CandidateSource"
    if (root.parent / "installed.json").is_file():
        assert not json.loads((root.parent / "installed.json").read_text()).get("installed"), "Use a fresh lab after installation"
    private = staged / "DAoCVisualBridge/Private"
    central = workspace / "Client/Plugins/DAoCVisualBridge/Content/ClassicUI"
    assert (central / "QuantityUI_v01/dialog_sm.png").is_file()

    patched = set()

    def add(path, pairs):
        relative = path.relative_to(staged)
        patched.add(relative)
        code = (source / relative).read_text(encoding="utf-8-sig")
        for old, new in pairs:
            assert code.count(old) == 1, (path.name, old)
            code = code.replace(old, new, 1)
        if not path.is_file() or path.read_text(encoding="utf-8-sig") != code:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")

    add(staged / "DAoCVisualBridge/Public/DAoCBridgeSubsystem.h", [
        ("    void ApplyPlayerTrade(TSharedPtr<FJsonObject> State);", """    void ApplyPlayerTrade(TSharedPtr<FJsonObject> State);
    void ApplyQuestRewards(TSharedPtr<FJsonObject> State);
    bool TickQuestRewardAcceptance();
    bool CloseQuestRewards(bool Notify=true);
    void RefreshQuestRewards();
    void RespondQuestRewards(const FString& Action,const FString& Token);
    TSharedPtr<FJsonObject> QuestRewardState;
    TSharedPtr<SWidget> QuestRewardOverlay,QuestRewardPanel;
    FString QuestRewardToken,QuestRewardDismissedToken;
    TArray<int32> QuestRewardChoices;"""),
    ])
    add(private / "DAoCBridgeSubsystem.cpp", [
        ("    if(TickPlayerTradeAcceptance())return;", "    if(TickQuestRewardAcceptance())return;\n    if(TickPlayerTradeAcceptance())return;"),
        ('    const TSharedPtr<FJsonObject>* Trade=nullptr;', '''    const TSharedPtr<FJsonObject>* Rewards=nullptr;
    ApplyQuestRewards(M->TryGetObjectField(TEXT("quest_rewards"),Rewards)?*Rewards:nullptr);
    const TSharedPtr<FJsonObject>* Trade=nullptr;'''),
    ])
    add(private / "DAoCBridgeClassicUI.cpp", [
        ("if(CloseClassicQuantity())return true;", "if(CloseQuestRewards())return true;if(CloseClassicQuantity())return true;"),
        ("if(ClassicQuantityPanel.IsValid())return true;", "if(QuestRewardPanel.IsValid()&&QuestRewardPanel->IsHovered())return true;if(ClassicQuantityPanel.IsValid())return true;"),
        ("CloseGuild(false);GuildState.Reset();", "CloseQuestRewards(false);QuestRewardState.Reset();QuestRewardDismissedToken.Empty();CloseGuild(false);GuildState.Reset();"),
        ('#include "DAoCBridgePlayerTrade.inl"', '#include "DAoCBridgePlayerTrade.inl"\n#include "DAoCBridgeQuestRewards.inl"'),
        ('#include "DAoCBridgeQuestRewards.inl"', '#include "DAoCBridgeQuestRewards.inl"\n#include "DAoCBridgeQuestRewardAcceptance.inl"'),
    ])
    add(private / "DAoCBridgeWorldPointer.cpp", [
        ("ClassicMerchantPanel,PlayerTradePanel,ExchangePanel", "ClassicMerchantPanel,PlayerTradePanel,QuestRewardPanel,ExchangePanel"),
    ])
    add(private / "DAoCBridgeViewport.cpp", [
        ("EmblemPickerOverlay,PlayerTradeOverlay,ExchangeOverlay", "EmblemPickerOverlay,PlayerTradeOverlay,QuestRewardOverlay,ExchangeOverlay"),
    ])
    for path in source.rglob("*"):
        if not path.is_file() or path.relative_to(source) in patched:
            continue
        target = staged / path.relative_to(source)
        if not target.is_file() or digest(path) != digest(target):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    result = build(workspace, engine, lab, candidate_source=staged)
    result.update(candidate_source=str(staged), original_dialog_art_sha256=digest(central / "QuantityUI_v01/dialog_sm.png"))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in ["workspace", "engine"]:
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build_quest(args.workspace.resolve(), args.engine.resolve())))
